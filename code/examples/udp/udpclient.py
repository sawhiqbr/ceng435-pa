import socket

msgFromClient       = "Hello UDP Server"
serverAddressPort   = (socket.gethostbyname("server"), 20001)
bufferSize          = 10240  # Increase buffer size to match TCP client

OBJ = "small-0"

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Read file data
with open(f"../objects/{OBJ}.obj", 'rb') as file:
    file_data = file.read()

# Send file data to server using created UDP socket
UDPClientSocket.sendto(file_data, serverAddressPort)

msgFromServer = UDPClientSocket.recvfrom(bufferSize)

msg = "Message from Server {}".format(msgFromServer[0])
print(msg)