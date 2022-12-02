from socket import *
import random
import time
import threading
from tqdm import tqdm
import os
import shutil
import hashlib

start = time.time()

lock = threading.Lock()

ServerAddr = gethostbyname(gethostname())
clientAddr = gethostbyname(gethostname())
ServerTCPPort = []
ServerUDPPort = []
clientTCPPort = []
chunks = []
n = 5  # number of peers
initial = [[] for i in range(n)]
avgRTT = [0 for i in range(n)]
RTT = dict()
for clientID in range(n):
    RTT[clientID] = dict()


# ===========================================================#
# Make a directory for each client
# ===========================================================#

def makeDir(n):
    for i in range(n):
        Directory = f'client{i}'
        shutil.rmtree(Directory, ignore_errors=True, onerror=None)
        try:
            os.makedirs(Directory, exist_ok=True)
        except OSError as error:
            print(f'Directory {Directory} can not be created')


makeDir(n)


# ===========================================================#
# Function for combining all the chunks
# ===========================================================#


def combine(Directory):
    with lock:
        path = os.path.join(Directory, 'combinedFile.txt')
        combinedFile = open(path, 'wb')
        for chunkID in chunks:
            chunkPath = os.path.join(Directory, f'chunk{chunkID}.txt')
            chunki = open(chunkPath, 'rb').read()
            combinedFile.write(chunki)
            os.remove(chunkPath)

# ===========================================================#
# Assigning ports for the server and client
# ===========================================================#


currport = 5000

for i in range(n):
    ServerTCPPort.append(currport)
    currport += 1
for i in range(n):
    ServerUDPPort.append(currport)
    currport += 1

for i in range(n):
    clientTCPPort.append(currport)
    currport += 1

# maintain of list of chunks recieved for each client

global clientData
clientData = dict()
for i in range(n):
    clientData[i] = set()
threads = []


def Request_Chunk_IDs(ServerPort, ServerAddr, clientID):
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((ServerAddr, ServerPort))
    request = f'client {clientID} Requesting Chunk IDs'
    clientSocket.send(request.encode())
    ids = ""
    while(True):
        idsRecieved = clientSocket.recv(1024).decode()
        ids += idsRecieved
        if(not idsRecieved):
            break

    clientSocket.close()
    ids = [int(i) for i in ids.split()]
    # print(f'Message from Server to {clientID}: ',IDs)
    for ID in ids:
        clientData[clientID].add(ID)
    return


threads = []
for clientID in range(n):
    ServerPort = random.choice(ServerTCPPort)
    x = threading.Thread(target=Request_Chunk_IDs, args=(
        ServerPort, ServerAddr, clientID,))
    threads.append(x)
    x.start()

# wait till all the threads are finished(by using join method)
for thread in threads:
    thread.join()

# All Chunk IDs are recieved
for chunkID in clientData[0]:
    chunks.append(chunkID)

chunks.sort()
bar = tqdm(total = n*len(chunks), desc ="Simulation time")

def SaveFile(chunkID, clientID, data):
    if(clientID == -1):
        return None
    if(chunkID in clientData[clientID]):
        path = os.path.join(f"client{clientID}", f"chunk{chunkID}.txt")
        text_file = open(path, "wb")
        text_file.write(data)
        text_file.close()
        clientData[clientID].remove(chunkID)
    bar.update(1)

# initialize initial chunk ids for each client

for chunkID in clientData[0]:
    initial[chunkID % n].append(chunkID)

threads.clear()

def Request_Initial_Chunk(chunkID, clientID, ServerAddr, ServerPort):
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((ServerAddr, ServerPort))
    request = f'client {clientID} Requesting Chunk {chunkID}'
    clientSocket.send(request.encode())
    chunkRecieved = b''
    while(True):
        data = clientSocket.recv(1024)
        if(not data):
            break
        chunkRecieved += data

    SaveFile(chunkID, clientID, chunkRecieved)
    clientSocket.close()


def Request_Initial_Chunks(clientID):
    for chunkID in initial[clientID]:
        ServerPort = random.choice(ServerTCPPort)
        Request_Initial_Chunk(chunkID, clientID, ServerAddr, ServerPort)

    ServerPort = random.choice(ServerTCPPort)
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((ServerAddr, ServerPort))
    request = f'client {clientID} Recieved Chunk All'
    clientSocket.send(request.encode())
    clientSocket.close()


for clientID in clientData:
    x = threading.Thread(target=Request_Initial_Chunks, args=(clientID,))
    threads.append(x)
    x.start()


for thread in threads:
    thread.join()

print("All initial chunks have been recieved by each client")


TCPSockets = [[] for i in range(n)]
threads.clear()


def opensockets():
    for (clientID, clientPort) in enumerate(clientTCPPort):
        try:
            clientSocket = socket(AF_INET, SOCK_STREAM)
            clientSocket.bind(("", clientPort))
            clientSocket.listen(5)
        except:
            pass
        TCPSockets[clientID].extend([clientPort, clientSocket])


opensockets()


def check_status():
    for clientID in clientData:
        if(len(clientData[clientID]) > 0):
            return False
    return True


def acceptConncetions(clientSocket):
    while(True):
        connectionSocket, addr = clientSocket.accept()
        # print("Connected to {}".format(addr))
        message = connectionSocket.recv(1024).decode().split()
        chunkID = int(message[-1])
        clientID = int(message[2])

        if(message[0] == "Sending"):
            message = "Ready"
            connectionSocket.send(message.encode())
            message = RecieveToclient(connectionSocket, addr)
            RTT[clientID][chunkID] = time.time() - RTT[clientID][chunkID]
            SaveFile(chunkID, clientID, message)
        elif(message[0] == "Requesting"):
            SendtoServer(chunkID, clientID, connectionSocket)
        else:
            print("Invalid Request from Client")

        connectionSocket.close()


accept = []
for Socket in TCPSockets:
    x = threading.Thread(target=acceptConncetions,
                         args=(Socket[1],), daemon=True)
    accept.append(x)
    x.start()


def RecieveToclient(connectionSocket, addr):
    message = b""
    while(True):
        data = connectionSocket.recv(1024)
        if(not data):
            break
        message = message + data

    return message


def SendtoServer(chunkID, clientID, connectionSocket):

    if(chunkID not in clientData[clientID]):
        path = os.path.join(f"client{clientID}", f"chunk{chunkID}.txt")
        message = open(path, 'rb').read()
        connectionSocket.send(message)

    else:
        message = b"-1"
        connectionSocket.send(message)


def Request_Chunks(clientID):
    remaining_chunks = clientData[clientID].copy()
    for chunkID in remaining_chunks:
        # client ‘p’ identifies what chunk of file
        # it doesn’t have. Call it chunk ‘c

        # p sends a UDP message to S, requesting c
        clientSocket = socket(AF_INET, SOCK_DGRAM)

        request = f'client {clientID} Requesting Chunk {chunkID}'
        ServerPort = random.choice(ServerUDPPort)
        while(True):
            RTT[clientID].update({chunkID:time.time()})
            clientSocket.sendto(request.encode(), (ServerAddr, ServerPort))
            status = clientSocket.recvfrom(1024)[0].decode()
            if(status == "ACK"):
                break

        clientSocket.close()


for clientID in range(n):
    x = threading.Thread(target=Request_Chunks, args=(clientID,))
    x.start()


while(not check_status()):
    pass


print("All Clients have recieved all the chunks")


print("Done")


for clientID in range(n):
    path = f"client{clientID}"
    x = threading.Thread(target=combine, args=(path,))
    threads.append(x)
    x.start()

for x in threads:
    x.join()

for clientID in range(n):
    path = os.path.join(f"client{clientID}", "combinedFile.txt")
    hash = hashlib.md5(open(path, 'rb').read()).hexdigest()
    print(f"client {clientID} hash : {hash}")

for clientID in RTT:
    rtt = 0
    num =0
    for chunkID in RTT[clientID]:
        num += 1
        rtt += RTT[clientID][chunkID]

    rtt = rtt/num 
    avgRTT[clientID] = rtt


# print(len(avgRTT))
# for (clientID,avgrtt) in enumerate(avgRTT):
#     print(f'Average RTT for client {clientID} : {avgrtt}')

print(f"Total Simulation time n: {time.time() - start} ")