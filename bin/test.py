import os

def sum(n1,n2):
	return n1+n2

print(sum(3,4))

filename = os.getcwd()+"\\bin\\rest2.txt"
print()
file = open(filename,"w+")
file.write("Does this work?")
file.close()
