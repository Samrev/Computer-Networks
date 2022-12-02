import sys

path = sys.argv[1]

X = []
Y = [] 
import matplotlib.pyplot as plt 

with open(path,'r') as file:
	for line in file:
		data = [i for i in line.split()]
		X.append(float(data[0]))
		Y.append(int(data[1]))


	plt.plot(X,Y,'-',linewidth=1.5)
	plt.title("Congestion_window vs time")
	plt.xlabel('Time')
	plt.ylabel('Congestion_window_size')

	
	plt.xticks([i for i in range(int(X[-1] + 1))])
	plt.show()

