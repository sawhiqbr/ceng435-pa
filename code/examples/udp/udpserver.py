""" --------------------- RECEIVER --------------------- """
import socket
import hashlib
import threading
import os
import time
import sys
import queue

CLIENT_ADDRESS_PORT = (socket.gethostbyname("client"), 20002)
LOCAL_IP           = "server"
LOCAL_PORT         = 20001
BUFFER_SIZE        = 1024
CURRENT_DIRECTORY  = os.getcwd()
TIMEOUT            = 1
WINDOW_SIZE        = 128
RECV_BASE          = 0
TOTAL_CHUNKS_SMALL = 0
TOTAL_CHUNKS_LARGE = 0
FILES              = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]

chunks             = {}
files_done         = {}
sequence_queue     = queue.Queue()
chunks_lock        = threading.Lock()

total_chunks_small_not_set = True
total_chunks_large_not_set = True
new_chunks_not_ready       = True
total_chunks_set_cond      = threading.Condition()
new_chunks_ready_cond      = threading.Condition()

for file_name in FILES:
    files_done[file_name] = False

# Create a datagram socket at the server side and bind it
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPServerSocket.bind((LOCAL_IP, LOCAL_PORT))
print("UDP server up and listening")

def ack_sender(UDPServerSocket, address):
    while True:
        # Get a sequence number from the queue
        sequence = sequence_queue.get()

        # Send an ACK for this sequence number
        ack_packet = sequence.to_bytes(4, 'big')
        UDPServerSocket.sendto(ack_packet, address)

        # Mark this task as done
        sequence_queue.task_done()

# Start the ACK sender thread
ack_thread = threading.Thread(target=ack_sender, args=(UDPServerSocket, LOCAL_IP), name="ACK Sender")
ack_thread.start()

# Checks if all chunks have been received for a file and if so, reassembles the file
def file_creator():
    global files_done
    
    with total_chunks_set_cond:
        while total_chunks_small_not_set and total_chunks_large_not_set:
            total_chunks_set_cond.wait()
    
    while not all(files_done.values()):  # Continue until all files are done
        for file_name in files_done:
            if not files_done[file_name]:  # If the file is not done
                total_chunks = TOTAL_CHUNKS_SMALL if file_name.startswith("small") else TOTAL_CHUNKS_LARGE

                if file_name.startswith("small"):
                    n = int(file_name.split("-")[1])
                    start_sequence = total_chunks * n + 1
                    end_sequence = total_chunks * (n + 1)
                else:
                    n = int(file_name.split("-")[1])
                    start_sequence = TOTAL_CHUNKS_SMALL * 10 + total_chunks * n + 1
                    end_sequence = TOTAL_CHUNKS_SMALL * 10 + total_chunks * (n + 1)

                with chunks_lock:
                    all_chunks_received = all(chunks.get(i) is not None for i in range(start_sequence, end_sequence + 1))
                
                if all_chunks_received:
                    # If all chunks are received, create the file
                    with chunks_lock:
                        with open(os.path.join(CURRENT_DIRECTORY, "object_received", file_name), 'wb') as f:
                            for sequence in range(start_sequence, end_sequence + 1):
                                f.write(chunks[sequence])

                    # Calculate MD5 hash
                    with open(os.path.join(CURRENT_DIRECTORY, "object_received", file_name), 'rb') as f:
                        file_data = f.read()
                        calculated_hash = hashlib.md5(file_data).hexdigest()

                    # Read the stored MD5 hash
                    with open(os.path.join(CURRENT_DIRECTORY, "objects", f"{file_name}.obj.md5"), 'r') as md5_file:
                        stored_hash = md5_file.read().strip()

                    # Compare hashes
                    if stored_hash == calculated_hash:
                        print("File received intact")
                    else:
                        print("File corrupted during transfer")

                    # Mark the file as done
                    files_done[file_name] = True

                    print(f"File {file_name} created")

                    # Break the loop as we have processed a file
                    break

        with new_chunks_ready_cond:
            while new_chunks_not_ready:
                new_chunks_ready_cond.wait()
    
    print("All files created")

file_creator_thread = threading.Thread(target=file_creator, name="File Creator")
file_creator_thread.start()

# Chunks will hold sequence number -> acked info. It will start from 1 and go up to the
# total number of chunks in all of the files. Total chunks will be set when the first packet
# from the file of that kind is received.
while(True):
    print("Waiting for incoming datagrams")
    bytesAddressPair = UDPServerSocket.recvfrom(BUFFER_SIZE)
    packet = bytesAddressPair[0]
    address = bytesAddressPair[1]
    
    # Extract the checksum, length, sequence number, total chunks, and data from the packet
    file_name = packet[0:7].decode()
    sequence_number = int.from_bytes(packet[7:11], 'big')
    total_chunks = int.from_bytes(packet[11:15], 'big')
    message = packet[19:]
    max_sequence_number = sequence_number + total_chunks - 1

    if total_chunks_small_not_set and file_name.startswith("small"):
        TOTAL_CHUNKS_SMALL = total_chunks
    elif total_chunks_large_not_set and file_name.startswith("large"):
        TOTAL_CHUNKS_LARGE = total_chunks
    if total_chunks_small_not_set and total_chunks_large_not_set:
        total_chunks_set_cond.notify_all()

    # print(f"File name: {file_name}")
    # print(f"Sequence number: {sequence_number}")
    # print(f"Total chunks: {total_chunks}")
    # print(f"Packet length: {len(packet)}")
    
    # Correctly received
    if sequence_number >= RECV_BASE and sequence_number < RECV_BASE + WINDOW_SIZE:
        # Put the sequence number in the queue
        sequence_queue.put(sequence_number)

        # If the packet was not previously received, buffer it
        with chunks_lock:
            if chunks.get(sequence_number) is None:
                chunks[sequence_number] = message
        
        # Move the window if sequence number is the receive base
        if sequence_number == RECV_BASE:
            with chunks_lock:
                current_base = RECV_BASE
                while chunks.get(current_base + 1) is not None:
                    current_base += 1
            RECV_BASE = current_base
    
    # Correctly received but previously acknowledged
    if sequence_number >= RECV_BASE - WINDOW_SIZE and sequence_number < RECV_BASE:
        # Put the sequence number in the queue
        sequence_queue.put(sequence_number)

    # Else ignore the packet
    else:
        pass
    
    new_chunks_not_ready = False
    new_chunks_ready_cond.notify_all()
    new_chunks_not_ready = True
