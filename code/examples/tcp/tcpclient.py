# echo-client.py

import socket

HOST = socket.gethostbyname("server")
PORT = 8080

OBJ = "small-0"

client_socket = socket.socket()  # instantiate
client_socket.connect((HOST, PORT))  # connect to the server


with open(f"../objects/{OBJ}.obj", 'rb') as file:
    file_data = file.read()

client_socket.sendall(file_data)  # send file data

response = client_socket.recv(1024).decode()  # receive response
print('Received from server: ' + response)  # show in terminal

client_socket.close()  # close the connection