import socket
import hashlib
import os

localIP     = "server"
localPort   = 20001
bufferSize  = 1024  # Increase buffer size to match TCP server
current_directory = os.getcwd()

OBJ = "large-0"

# Create a datagram socket
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))

print("UDP server up and listening")

chunks = {}
# Listen for incoming datagrams
while(True):
    bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
    packet = bytesAddressPair[0]
    address = bytesAddressPair[1]
    
    # Extract the checksum, length, sequence number, total chunks, and data from the packet
    checksum = packet[:32].decode()
    length = int.from_bytes(packet[32:36], 'big')
    sequence_number = int.from_bytes(packet[36:40], 'big')
    total_chunks = int.from_bytes(packet[40:44], 'big')
    message = packet[44:44+length]
    data = length.to_bytes(4, 'big') + sequence_number.to_bytes(4, 'big') + total_chunks.to_bytes(4, 'big') + message
    
    # print(f"Checksum: {checksum}")
    # print(f"Length: {length}")
    # print(f"Sequence number: {sequence_number}")
    # print(f"Total chunks: {total_chunks}")
    # print(f"Message length: {len(message)}")
    # print(f"Data length: {len(data)}")
    # print(f"Packet length: {len(packet)}")

    # Verify the checksum
    calculated_checksum = hashlib.md5(packet[32:]).hexdigest()
    if checksum != calculated_checksum:
        print("Packet corrupted during transfer")
        continue
    
    # Store the data chunk
    chunks[sequence_number] = message
    
    # Send an ACK back to the client
    ack = str(sequence_number).encode()
    UDPServerSocket.sendto(ack, address)

    # Check if all chunks have been received
    if len(chunks) == total_chunks:
        # Reassemble the file data
        file_data = b''.join(chunks[i] for i in sorted(chunks))

        # Calculate MD5 hash of received file data
        md5_hash = hashlib.md5()
        md5_hash.update(file_data)
        calculated_hash = md5_hash.hexdigest()

        # Read the stored MD5 hash
        # Read file data
        with open(os.path.join(current_directory, "objects", f"{OBJ}.obj.md5"), 'r') as md5_file:
            stored_hash = md5_file.read().strip()

        # Compare hashes
        if stored_hash == calculated_hash:
            print("File received intact")
        else:
            print("File corrupted during transfer")

        # Reset the chunks dictionary for the next file
        chunks = {}