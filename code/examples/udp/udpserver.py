import socket
import hashlib
import os
import sys

localIP     = "server"
localPort   = 20001
bufferSize  = 1024  # Increase buffer size to match TCP server
current_directory = os.getcwd()

# Create a datagram socket
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))

print("UDP server up and listening")

chunks = {}
# Listen for incoming datagrams
while(True):
    print("Waiting for incoming datagrams")
    bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
    packet = bytesAddressPair[0]
    address = bytesAddressPair[1]
    
    # Extract the checksum, length, sequence number, total chunks, and data from the packet
    checksum = packet[:32].decode()
    file_name = packet[32:39].decode()
    length = int.from_bytes(packet[39:43], 'big')
    sequence_number = int.from_bytes(packet[43:47], 'big')
    total_chunks = int.from_bytes(packet[47:51], 'big')
    message = packet[51:51+length]
    data = file_name.encode() + length.to_bytes(4, 'big') + sequence_number.to_bytes(4, 'big') + total_chunks.to_bytes(4, 'big') + message
    
    # print(f"Checksum: {checksum}")
    # print(f"Length: {length}")
    # print(f"Sequence number: {sequence_number}")
    # print(f"Total chunks: {total_chunks}")
    # print(f"Message length: {len(message)}")
    # print(f"Data length: {len(data)}")
    # print(f"Packet length: {len(packet)}")
    
    # Store the data chunk
    if file_name not in chunks:
        chunks[file_name] = {}
    chunks[file_name][sequence_number] = message

    # Verify the checksum
    calculated_checksum = hashlib.md5(packet[32:]).hexdigest()
    if checksum != calculated_checksum:
        print(f"Packet corrupted during transfer with checksum {checksum} and calculated checksum {calculated_checksum}")
        continue
    
    # Store the data chunk
    chunks[sequence_number] = message
    
    # Send an ACK back to the client
    ack = str(sequence_number).encode()
    UDPServerSocket.sendto(ack, address)
    print(f"Sent ACK for chunk {ack} to {address}")

    # Check if all chunks have been received
    if len(chunks[file_name]) == total_chunks:
        # Reassemble the file data
        file_data = b''.join(chunks[file_name][i] for i in sorted(chunks[file_name]))
        print(f"Reassembled file data with size {sys.getsizeof(file_data)}")
        calculated_hash = hashlib.md5(file_data).hexdigest()

        # Read the stored MD5 hash
        with open(os.path.join(current_directory, "objects", f"{file_name}.obj.md5"), 'r') as md5_file:
            stored_hash = md5_file.read().strip()

        # Compare hashes
        if stored_hash == calculated_hash:
            print("File received intact")
        else:
            print("File corrupted during transfer")

        print(f"Finished receiving file {file_name}")