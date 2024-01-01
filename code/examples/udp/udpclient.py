import socket
import hashlib
import threading
import os

serverAddressPort   = (socket.gethostbyname("server"), 20001)
bufferSize          = 1024  # Increase buffer size to match TCP client
current_directory = os.getcwd()

OBJ = "large-0"

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Get the current working directory

# Read file data
with open(os.path.join(current_directory, "objects", f"{OBJ}.obj"), 'rb') as file:
  file_data = file.read()

# Divide file data into chunks, add checksum to each chunk, and send each chunk
# Also print sent status and sequence number for each chunk
chunk_size = 980
total_chunks = len(file_data) // chunk_size + 1


def wait_for_ack(total_chunks):
    received = [False for i in range(total_chunks)]
    while False in received:
        # Wait for ACK
        ack, server_address = UDPClientSocket.recvfrom(bufferSize)
        
        # Process the ACK here
        sequence_number = int(ack.decode())
        received[sequence_number] = True
        
        # Print the received ACK
        print(f"Received ACK for chunk {sequence_number + 1} from {server_address}")
    
    print("All chunks sent and ACKed successfully")

# Create a thread for waiting for ACK
ack_thread = threading.Thread(target=wait_for_ack, args=(total_chunks,))

# Start the thread
ack_thread.start()

print("file_data:", len(file_data))

for i in range(0, len(file_data), chunk_size):
    message = file_data[i:i+chunk_size]
    length = len(message)
    sequence_number = i // chunk_size
    data = length.to_bytes(4, 'big') + sequence_number.to_bytes(4, 'big') + total_chunks.to_bytes(4, 'big') + message
    
    # Calculate checksum
    checksum = hashlib.md5(data).hexdigest()
    
    # Add checksum to the data and create a packet to send
    packet = checksum.encode() + data

    # print(f"Checksum: {checksum}")
    # print(f"Length: {length}")
    # print(f"Sequence number: {sequence_number}")
    # print(f"Total chunks: {total_chunks}")
    # print(f"Message length: {len(message)}")
    # print(f"Data length: {len(data)}")
    # print(f"Packet length: {len(packet)}")

    # Send chunk
    UDPClientSocket.sendto(packet, serverAddressPort)
    # Print status and sequence number
    print(f"Sent chunk {i//chunk_size + 1} of {total_chunks} - Sequence number: {sequence_number}")

# Wait for the ACK thread to finish
ack_thread.join()
