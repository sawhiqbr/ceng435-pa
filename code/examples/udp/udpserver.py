import socket
import hashlib

localIP     = "server"
localPort   = 20001
bufferSize  = 10240  # Increase buffer size to match TCP server

OBJ = "small-0"

# Create a datagram socket
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))

print("UDP server up and listening")

# Listen for incoming datagrams
while(True):
    bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
    file_data = bytesAddressPair[0]
    address = bytesAddressPair[1]

    # Calculate MD5 hash of received file data
    md5_hash = hashlib.md5()
    md5_hash.update(file_data)
    calculated_hash = md5_hash.hexdigest()

    # Read the stored MD5 hash
    with open(f"../objects/{OBJ}.obj.md5", 'r') as md5_file:
        stored_hash = md5_file.read().strip()

    # Compare hashes
    if stored_hash == calculated_hash:
        print("File received intact")
    else:
        print("File corrupted during transfer")

    # Sending a reply to client
    UDPServerSocket.sendto(b'File received', address)