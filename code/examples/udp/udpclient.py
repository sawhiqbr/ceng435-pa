import socket
import hashlib
import threading
import os
import time

starttime = time.time()

serverAddressPort   = (socket.gethostbyname("server"), 20001)
bufferSize          = 1024  # Increase buffer size to match TCP client
current_directory = os.getcwd()

# List of files to send
# files = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]
# ALL_CHUNKS = 10390

# files = ["small-0"]
# ALL_CHUNKS = 11

files = ["large-0"]
ALL_CHUNKS = 1028

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

def wait_for_ack(ALL_CHUNKS=ALL_CHUNKS):
    received = [False for i in range(ALL_CHUNKS)]
    print(f"Waiting for ACKs for {len(received)} chunks")
    while False in received:
        # Wait for ACK
        ack, server_address = UDPClientSocket.recvfrom(bufferSize)
        
        # Process the ACK here
        sequence_number = int(ack.decode())
        try:
            received[sequence_number - 1] = True
        except Exception as e: 
            print(f"Trying to insert True into {sequence_number - 1} where received is array is of length: {len(received)}")
            print(e)

        print(f"Received ACK for chunk {sequence_number} from {server_address}")
    
    print("All chunks sent and ACKed successfully")


# Create a thread for waiting for ACK
ack_thread = threading.Thread(target=wait_for_ack, args=(ALL_CHUNKS,))

# Start the thread
ack_thread.start()

sequence_number = 0
for file_name in files:
    print(f"Sending file {file_name} with size {os.path.getsize(os.path.join(current_directory, 'objects', f'{file_name}.obj'))}")
    # Read file data
    with open(os.path.join(current_directory, "objects", f"{file_name}.obj"), 'rb') as file:
        file_data = file.read()

    # Divide file data into chunks, add checksum to each chunk, and send each chunk
    # Also print sent status and sequence number for each chunk
    chunk_size = 973 # 1024 - 7 - 4 - 4 - 4 - 32
    total_chunks = len(file_data) // chunk_size + 1

    print(f"Total chunks: {total_chunks}")

    for i in range(0, len(file_data), chunk_size):
        sequence_number += 1
        message = file_data[i:i+chunk_size]
        length = len(message)
        data = file_name.encode() + length.to_bytes(4, 'big') + sequence_number.to_bytes(4, 'big') + total_chunks.to_bytes(4, 'big') + message
        
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
        print(f"Packet size is {len(packet)}")
        UDPClientSocket.sendto(packet, serverAddressPort)
        # Print status and sequence number
        print(f"Sent chunk {i//chunk_size + 1} of {total_chunks} - Sequence number: {sequence_number}")


    print(f"Finished sending file {file_name}")

    endtime = time.time()
    print(f"Time elapsed: {endtime - starttime}")

# Wait for the ACK thread to finish
ack_thread.join()
