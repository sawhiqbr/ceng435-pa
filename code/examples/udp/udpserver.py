""" ---------------------- SENDER ---------------------- """
""" Sequence numbers will start from 1 and go up to whatever the total number of chunks is """
""" Please comment your code thoroughly, on what your implementation does rather than how. """
import socket
import hashlib
import threading
import os
import time
import sys
import queue
import random

CLIENT_ADDRESS_PORT   = None
LOCAL_IP              = "server"
LOCAL_PORT            = 20002
BUFFER_SIZE           = 1024
CURRENT_DIRECTORY     = os.getcwd()
TIMEOUT               = 0.1
SOCKET_TIMEOUT        = 0.5
THREAD_COUNT          = 256 # random.randint(16, 192) // 16 * 16
SEND_BASE             = 1
TOTAL_CHUNKS_ALL      = 0
FILES                 = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]
ALL_DONE              = False
packets               = {}
timers                = {}
packets_acked         = {}
packets_lock          = threading.Lock()
timers_lock           = threading.Lock()
sendbase_lock         = threading.Lock()
terminate_event       = threading.Event()
resend_counter        = 0

# Create a UDP socket at Server side
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPServerSocket.settimeout(SOCKET_TIMEOUT)
UDPServerSocket.bind((LOCAL_IP, LOCAL_PORT))

# Making packets ready to send
sequence_number = 0
for file_name in FILES:
    # print(f"Preparing file {file_name} with size {os.path.getsize(os.path.join(CURRENT_DIRECTORY, 'objects', f'{file_name}.obj'))}")
    # Read file data
    with open(os.path.join(CURRENT_DIRECTORY, "objects", f"{file_name}.obj"), 'rb') as file:
        file_data = file.read()

    # Divide file data into chunks, add checksum to each chunk, and send each chunk
    # Also # print sent status and sequence number for each chunk
    chunk_size = BUFFER_SIZE - 15
    total_chunks = len(file_data) // chunk_size + 1
    TOTAL_CHUNKS_ALL += total_chunks
    for i in range(0, len(file_data), chunk_size):
        sequence_number += 1
        message = file_data[i:i+chunk_size]
        packet = file_name.encode() +  sequence_number.to_bytes(4, 'big') + total_chunks.to_bytes(4, 'big') + message
        
        # # print(f"Sequence number: {sequence_number}")
        # # print(f"Total chunks: {total_chunks}")
        # # print(f"Packet length: {len(packet)}")

        packets[sequence_number] = packet
        packets_acked[sequence_number] = False

responsible_area = TOTAL_CHUNKS_ALL // THREAD_COUNT + 1
print(f"Testing with BUFFER_SIZE: {BUFFER_SIZE} and THREAD_COUNT: {THREAD_COUNT} and RESPONSIBLE_AREA: {responsible_area}")

responsible = [i for i in range(1, TOTAL_CHUNKS_ALL + 1, responsible_area)]
def packet_resender(UDPServerSocket, responsible):
    global resend_counter

    responsible_packets = {i: packets.get(i) for i in range(responsible, responsible + responsible_area)}
    responsible_packets_acked = {i: False for i in range(responsible, responsible + responsible_area)}

    while not all(responsible_packets_acked.values()) and not terminate_event.is_set():
        for sequence in responsible_packets:
            if responsible_packets_acked[sequence]:
                continue

            with packets_lock:
                if sequence not in packets:
                    responsible_packets_acked[sequence] = True
                    continue

                # print(f"Sending packet with sequence number {sequence}")
                UDPServerSocket.sendto(packets[sequence], CLIENT_ADDRESS_PORT)
                resend_counter += 1
            time.sleep(0.15)
selective_send_threads = [threading.Thread(target=packet_resender, args=(UDPServerSocket, i, ), name=f"Packet Resender {i}") for i in range(1, TOTAL_CHUNKS_ALL + 1, responsible_area)]

# Wait for ACKs
acked_total = 0
timeout_counter = 0
while not terminate_event.is_set():
    try:
        ack_packet, address = UDPServerSocket.recvfrom(4)
        timeout_counter = 0
        if not CLIENT_ADDRESS_PORT:
            print("Other threads started")
            starttime = time.time()
            CLIENT_ADDRESS_PORT = address
            for thread in selective_send_threads:
                thread.start()
    except socket.timeout:
        print(f"Timeout: {acked_total}, {TOTAL_CHUNKS_ALL}")
        timeout_counter += 1
        if timeout_counter == 5:
            terminate_event.set()
        continue

    ack_sequence = int.from_bytes(ack_packet, 'big')
    if ack_sequence == 0:
        print("Received hello")
        continue
    
    # print(f"Received ACK for sequence number {ack_sequence}")

    # If an ACK is received, mark the corresponding packet as acknowledged and stop its timer
    with packets_lock:
        if ack_sequence in packets:
            # print(f"Deleting packet with sequence number {ack_sequence}")
            del packets[ack_sequence]
            acked_total += 1

        # If the base of the window is acknowledged, slide the window forward
            
    if acked_total == TOTAL_CHUNKS_ALL:
        print("All packets have been acknowledged")
        UDPServerSocket.close()
        ALL_DONE = True
        terminate_event.set()
        break
                
    if terminate_event.is_set():
        break

    # print(f"OLD_BASE = {ack_sequence} - NEW_SEND_BASE: {SEND_BASE}")


print(f"Time taken: {time.time() - starttime}")
print(f"Resend counter: {resend_counter}")