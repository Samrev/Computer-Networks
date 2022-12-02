import hashlib
import threading
from socket import *
from collections import OrderedDict
import time
import shutil
import os
import sys
import random
from tqdm import tqdm
lock = threading.Lock()
serverTCPPort = []
serverUDPPort = []
clientTCPPort = []
clientAddr = gethostbyname(gethostname())
serverAddr = gethostbyname(gethostname())
n = 5  # number of peers


idsent = [-1 for i in range(n)]
isinitialsent = [-1 for i in range(n)]

# ===========================================================#
# Implement the cache
# ===========================================================#


class servercache:

    def __init__(self, size):
        self.cache = OrderedDict()
        self.size = size

    def get(self, chunkID):
        if chunkID not in self.cache:
            return -1
        else:
            self.cache.move_to_end(chunkID)
            path = os.path.join("servercache", f'chunk{chunkID}.txt')
            try:
                data = open(path , 'rb').read()
            except:
                return -1
            return data
    

    def put(self, chunkID, data):
        if(len(self.cache) >= self.size):
            (ID, _) = self.cache.popitem(last=False)
            path = os.path.join("servercache", f'chunk{ID}.txt')
            os.remove(path)
        self.cache[chunkID] = None
        self.cache.move_to_end(chunkID)
        path = os.path.join("servercache", f'chunk{chunkID}.txt')
        file = open(path, 'wb')
        file.write(data)
        file.close()
        


global cache
cache = servercache(n)

# ===========================================================#
# Make a directory for server cache and server
# ===========================================================#


def makeDir():
    Directory = "servercache"
    Directory1 = "server"
    shutil.rmtree(Directory, ignore_errors=True, onerror=None)
    shutil.rmtree(Directory1, ignore_errors=True, onerror=None)
    try:
        os.makedirs(Directory, exist_ok=True)
        os.makedirs(Directory1, exist_ok=True)
    except OSError as error:
        print(f'Directory {Directory} or {Directory1} can not be created')


makeDir()

# ===========================================================#
# Assigning ports for the server and client
# ===========================================================#

currport = 5000

for i in range(n):
    serverTCPPort.append(currport)
    currport += 1
for i in range(n):
    serverUDPPort.append(currport)
    currport += 1
for i in range(n):
    clientTCPPort.append(currport)
    currport += 1


# ===========================================================#
# Dividing the data into n chunks of equal size
# ===========================================================#
chunk_size = 1024
curr = 0
i = 0
chunks = []
path = sys.argv[1]
with open(path, 'rb') as file:
    data = file.read()
cur = 0
while(True):
    chunki = data[cur:cur+chunk_size]
    cur = cur + chunk_size
    if(not chunki):
        break
    chunks.append(i)
    # print(i)
    path = os.path.join("server", f"chunk{i}.txt")
    i = i + 1
    text_file = open(path, "wb")
    text_file.write(chunki)
    text_file.close()


# ===========================================================#
# Creating TCP and UDP Sockets
# ===========================================================#

TCPSockets = dict()
UDPSockets = dict()
threads = []


def openSockets():
    for serverPort in serverTCPPort:
        try:
            serverSocket = socket(AF_INET, SOCK_STREAM)
            serverSocket.bind(("", serverPort))
            serverSocket.listen(n)
        except :
            pass
        TCPSockets[serverPort] = serverSocket

    for serverPort in serverUDPPort:
        try:
            serverSocket = socket(AF_INET, SOCK_DGRAM)
            serverSocket.bind(("", serverPort))
        except:
            pass
        UDPSockets[serverPort] = serverSocket


def closeTCPsockets():
    for (__, socket) in TCPSockets.items():
        socket.close()


def acceptConncetions(serverSocket):
    while(True):
        connectionSocket, addr = serverSocket.accept()
        # print("Connected to {}".format(addr))
        SendToclient(connectionSocket, addr)
        connectionSocket.close()


def SendToclient(connectionSocket, addr):
    message = ""
    data = connectionSocket.recv(1024)
    message = message + data.decode()

    message = message.split()
    clientID = int(message[1])
    if(message[4] == "IDs"):
        SendchunkIDs(connectionSocket, addr, clientID)

    elif(message[4] == "All"):
        isinitialsent[clientID] = 1

    elif(message[4].isnumeric()):
        chunkID = int(message[4])
        sendChunk(connectionSocket, chunkID, clientID)

    else:
        print("Invalid Request from the client")


# ===========================================================#
# Function for sending Chunk IDs to a particular client
# ===========================================================#
def SendchunkIDs(connectionSocket, addr, clientID):
    message = ""
    for chunkID in chunks:
        message += str(chunkID) + " "
    connectionSocket.send(message.encode())
    connectionSocket.close()
    idsent[clientID] = 1


def sendChunk(connectionSocket, chunkID, clientID):
    path = os.path.join("server", f"chunk{chunkID}.txt")
    message = open(path, 'rb').read()
    connectionSocket.send(message)
    connectionSocket.close()


openSockets()

print("server Set up")

for TCPserverPort in TCPSockets:
    TCPserverSocket = TCPSockets[TCPserverPort]
    x = threading.Thread(target=acceptConncetions, args=(TCPserverSocket,))
    x.start()

# wait till all the IDs are sent to each client


def status(check):
    with lock:
        while(True):
            flag = True
            for status in check:
                if(status == -1):
                    flag = False
                    break
            if(flag):
                return


x = threading.Thread(target=status, args=(idsent,))
x.start()
x.join()

del(idsent)

print("All Chunk ids have been sent to  each client")


# wait till all the IDs are sent to each client

x = threading.Thread(target=status, args=(isinitialsent,))
x.start()
x.join()

del(isinitialsent)

print("All initial chunks have been sent to each client")

# Now delete the file from the server(i.e delete all the chunks)

for chunkID in chunks:
    path = os.path.join("server", f'chunk{chunkID}.txt')
    os.remove(path)

print("server has deleted the file")

threads.clear()
closeTCPsockets()




def UDPRequests(UDPserverSocket):
    while True:
        message, clientAddress = UDPserverSocket.recvfrom(1024)
        message = message.decode().split()

        #send ACK to handle packet loss
        status = "ACK"
        UDPserverSocket.sendto(status.encode(),clientAddress)
        # server checks its cache for chunk.
        # If the query results in a hit, it opens up a TCP connection with
        # client and shares chunk with the client

        chunkID = int(message[-1])
        clientID = int(message[1])
        data = b""
        value = cache.get(chunkID)
        if(value != b"" and value != -1):
            data = value
                
        else:
            # print(f"cache miss of client {clientID}")
            while(True):
                for ID in range(n):
                    if(ID != clientID):
                        clientPort = clientTCPPort[ID]
                        serverSocket = socket(AF_INET, SOCK_STREAM)
                        serverSocket.connect((clientAddr, clientPort))
                        request = f"Requesting client {ID} chunk {chunkID}"
                        serverSocket.send(request.encode())
                        message = serverSocket.recv(1024)
                        if(message and message != b"-1"):
                            data = message
                            break
                        serverSocket.close()
                if(data == b""):
                    continue
                else:
                    cache.put(chunkID, data)
                    break

        clientPort = clientTCPPort[clientID]
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.connect((clientAddr, clientPort))
        request = f"Sending client {clientID} chunk {chunkID}"
        serverSocket.send(request.encode())
        message = serverSocket.recv(1024).decode()
        if(message == "Ready"):
            serverSocket.send(data)
        else:
            print(f"client{clientID} cannot receive data")
        serverSocket.close()

        # save a new chunk in servercache


for UDPserverPort in UDPSockets:
    UDPserverSocket = UDPSockets[UDPserverPort]
    x = threading.Thread(target=UDPRequests, args=(UDPserverSocket,))
    threads.append(x)
    x.start()
