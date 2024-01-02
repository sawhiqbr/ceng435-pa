import socket
import hashlib
import threading
import os
import time

starttime = time.time()

serverAddressPort   = (socket.gethostbyname("server"), 20001)
bufferSize          = 1024  # Increase buffer size to match TCP client
current_directory   = os.getcwd()
TIMEOUT             = 1 
# List of files to send
files = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]
ALL_CHUNKS = 10390
# files = ["large-0"]
# ALL_CHUNKS = 1028

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
print("UDP client up and getting ready to send file info")


# Create a list of file names and sizes, then convert it to a string
file_info = [(file_name, os.path.getsize(os.path.join(current_directory, 'objects', f'{file_name}.obj'))) for file_name in files]
file_info_str = str(file_info)

# Encode the string to bytes and append the checksum to the front of the packet
file_info_bytes = file_info_str.encode()
checksum = hashlib.md5(file_info_bytes).hexdigest()
packet = checksum.encode() + file_info_bytes

timeout_start = time.time()

# First trial of sending the file info
UDPClientSocket.sendto(packet, serverAddressPort) 
while True:
    # Check if the timeout has been reached to resend the packet if lost
    if time.time() - timeout_start > TIMEOUT:
        print("Timeout. Resending packet...")
        UDPClientSocket.sendto(packet, serverAddressPort)
        timeout_start = time.time()
        continue

    ack_packet, server_address = UDPClientSocket.recvfrom(bufferSize)

    # Check if the server sent a NACK
    if ack_packet.decode() == "NACK":
        print("Received NACK from server. Retrying...")
        continue
    
    # Check if the server sent an ACK
    if ack_packet.decode() == "ACK":
        print("Received ACK from server. Proceeding...")
        break
    
    print("Error: Did not receive ACK from server. Retrying...")
    
    # Extract the checksum and file info from the packet
    ack_checksum = ack_packet[:32].decode()
    ack_file_info_bytes = ack_packet[32:]

# Send a special "end" packet to signal that the file info has been correctly received
end_packet = "end".encode()
UDPClientSocket.sendto(end_packet, serverAddressPort)

def wait_for_ack(ALL_CHUNKS=ALL_CHUNKS):
    received = {i: False for i in range(ALL_CHUNKS)}
    while False in received.values():
        # Wait for ACK
        ack, server_address = UDPClientSocket.recvfrom(bufferSize)
        sequence_number = int(ack.decode())
        if sequence_number > ALL_CHUNKS:
            print(f"Trying to insert True into index {sequence_number - 1} where received is dict is of length: {len(received)}")
            continue
        
        received[sequence_number - 1] = True

        print(f"Received ACK for chunk {sequence_number} from {server_address}")
    
    print("All chunks sent and ACKed successfully")

# Create a thread for waiting for ACK
ack_thread = threading.Thread(target=wait_for_ack, args=(ALL_CHUNKS,))
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
