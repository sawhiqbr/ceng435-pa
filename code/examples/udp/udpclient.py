""" ---------------------- SENDER ---------------------- """
""" Sequence numbers will start from 1 and go up to whatever the total number of chunks is """
import socket
import hashlib
import threading
import os
import time
import sys
import queue

SERVER_ADDRESS_PORT   = (socket.gethostbyname("server"), 20001)
LOCAL_IP              = "client"
LOCAL_PORT            = 20002
BUFFER_SIZE           = 1024
CURRENT_DIRECTORY     = os.getcwd()
TIMEOUT               = 1 
WINDOW_SIZE           = 128
SEND_BASE             = 0
FILES                 = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]
# FILES                 = ["large-0"]

sequence_queue        = queue.Queue()
packets_lock          = threading.Lock()
packets               = {}
timers                = {}

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.bind((LOCAL_IP, LOCAL_PORT))
print("UDP client up and running")

# Making packets ready to send
sequence_number = 0
for file_name in FILES:
    print(f"Preparing file {file_name} with size {os.path.getsize(os.path.join(CURRENT_DIRECTORY, 'objects', f'{file_name}.obj'))}")
    # Read file data
    with open(os.path.join(CURRENT_DIRECTORY, "objects", f"{file_name}.obj"), 'rb') as file:
        file_data = file.read()

    # Divide file data into chunks, add checksum to each chunk, and send each chunk
    # Also print sent status and sequence number for each chunk
    chunk_size = 1009 # 1024 - 7 - 4 - 4
    total_chunks = len(file_data) // chunk_size + 1

    print(f"Total chunks: {total_chunks}")
    for i in range(0, len(file_data), chunk_size):
        sequence_number += 1
        message = file_data[i:i+chunk_size]
        packet = file_name.encode() +  sequence_number.to_bytes(4, 'big') + total_chunks.to_bytes(4, 'big') + message
        
        # print(f"Sequence number: {sequence_number}")
        # print(f"Total chunks: {total_chunks}")
        # print(f"Packet length: {len(packet)}")

        with packets_lock:
            packets[sequence_number] = packet
        print(f"Prepared chunk {i//chunk_size + 1} of {total_chunks} - Sequence number: {sequence_number}")

        if (sequence_number < WINDOW_SIZE):
            sequence_queue.put(sequence_number)

    print(f"Finished preparing file {file_name}")


def packet_sender(UDPClientSocket, address):
    while True:
        # Get a sequence number from the queue
        sequence = sequence_queue.get()

        # Send the packet for this sequence number
        UDPClientSocket.sendto(packets[sequence], address)

        # Start a timer for this packet
        timers[sequence] = threading.Timer(TIMEOUT, packet_sender, args=(UDPClientSocket, address))
        timers[sequence].start()

        # Mark this task as done
        sequence_queue.task_done()

# Define and tart the packet sender thread
send_thread = threading.Thread(target=packet_sender, args=(UDPClientSocket, SERVER_ADDRESS_PORT), name="Packet Sender")
send_thread.start()

# Wait for ACKs
while True:
    ack_packet, address = UDPClientSocket.recvfrom(4)
    ack_sequence = int.from_bytes(ack_packet, 'big')

    # If an ACK is received, mark the corresponding packet as acknowledged and stop its timer
    if ack_sequence >= SEND_BASE and ack_sequence < SEND_BASE + WINDOW_SIZE:
        if ack_sequence in packets:
            del packets[ack_sequence]
            timers[ack_sequence].cancel()
            del timers[ack_sequence]

            # If the base of the window is acknowledged, slide the window forward
            if ack_sequence == SEND_BASE:
                while SEND_BASE + 1 not in packets:
                    SEND_BASE += 1
    