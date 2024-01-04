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
SEND_BASE             = 1
TOTAL_CHUNKS_ALL      = 10010
FILES                 = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]
# FILES                 = ["large-0"]

packets               = {}
timers                = {}
sequence_queue        = queue.Queue()
packets_lock          = threading.Lock()
timers_lock           = threading.Lock()

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

        if (sequence_number <= WINDOW_SIZE):
            sequence_queue.put(sequence_number)

    print(f"Finished preparing file {file_name}")

def packet_resender(UDPClientSocket):
    global timers, sequence_queue

    while True:
        print("Waiting for sequence number to re-send")
        # Get a sequence number from the queue
        sequence = sequence_queue.get()

        with packets_lock:
            # If the packet for this sequence number has already been acknowledged, don't send it
            if sequence not in packets:
                continue

            # Send the packet for this sequence number
            print(f"Re-sending packet for sequence number {sequence} at time: {time.time()}")
            UDPClientSocket.sendto(packets[sequence], SERVER_ADDRESS_PORT)

        with timers_lock:
            # Start a timer for this packet
            if sequence not in timers:
                timers[sequence] = threading.Timer(TIMEOUT, packet_resender, args=(UDPClientSocket, ))
                timers[sequence].start()

def packet_sender(UDPClientSocket):
    global timers, sequence_queue

    while True:
        print("Waiting for sequence number to send")
        # Get a sequence number from the queue
        sequence = sequence_queue.get()

        with packets_lock:
            # If the packet for this sequence number has already been acknowledged, don't send it
            if sequence not in packets:
                continue

            # Send the packet for this sequence number
            print(f"Sending packet for sequence number {sequence} at time: {time.time()}")
            UDPClientSocket.sendto(packets[sequence], SERVER_ADDRESS_PORT)

        with timers_lock:
            # Start a timer for this packet
            if sequence not in timers:
                timers[sequence] = threading.Timer(TIMEOUT, packet_resender, args=(UDPClientSocket, ))
                timers[sequence].start()

# Define and tart the packet sender thread
send_thread = threading.Thread(target=packet_sender, args=(UDPClientSocket, ), name="Packet Sender")
send_thread.start()

# Wait for ACKs
while True:
    print("Waiting for ACK")
    ack_packet, address = UDPClientSocket.recvfrom(4)
    ack_sequence = int.from_bytes(ack_packet, 'big')
    print(f"Received ACK for sequence number {ack_sequence} at time: {time.time()}")

    # If an ACK is received, mark the corresponding packet as acknowledged and stop its timer
    if ack_sequence >= SEND_BASE and ack_sequence < SEND_BASE + WINDOW_SIZE:
        with timers_lock:
            if ack_sequence in timers:
                timers[ack_sequence].cancel()
                
                if timers[ack_sequence].is_alive():
                    timers[ack_sequence].join()
                del timers[ack_sequence]

        with packets_lock:
            if ack_sequence in packets:
                del packets[ack_sequence]

        # If the base of the window is acknowledged, slide the window forward
            
        if ack_sequence == SEND_BASE:
            while SEND_BASE not in packets:
                SEND_BASE += 1
                print(f"Task is done for sequence number: {SEND_BASE - 1}")
                if SEND_BASE == TOTAL_CHUNKS_ALL + 1:
                    print("All packets have been acknowledged")
                    break
                sequence_queue.task_done()
        
            for i in range(ack_sequence + WINDOW_SIZE, SEND_BASE + WINDOW_SIZE):
                print(f"Packet with sequence number: {i} is added to the queue")
                sequence_queue.put(i)
        
            print(f"OLD_BASE = {ack_sequence} - NEW_SEND_BASE: {SEND_BASE}")