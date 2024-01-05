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

CLIENT_ADDRESS_PORT   = None
LOCAL_IP              = "server"
LOCAL_PORT            = 20002
BUFFER_SIZE           = 2048
CURRENT_DIRECTORY     = os.getcwd()
TIMEOUT               = 0.1
SOCKET_TIMEOUT        = 0.1
WINDOW_SIZE           = 128
SEND_BASE             = 1
TOTAL_CHUNKS_ALL      = 0
FILES                 = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]
ALL_DONE              = False
packets               = {}
timers                = {}
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
    if file_name == "small-0":
        TOTAL_CHUNKS_ALL += total_chunks
    if file_name == "large-0":
        TOTAL_CHUNKS_ALL += total_chunks
    print(total_chunks)
    for i in range(0, len(file_data), chunk_size):
        sequence_number += 1
        message = file_data[i:i+chunk_size]
        packet = file_name.encode() +  sequence_number.to_bytes(4, 'big') + total_chunks.to_bytes(4, 'big') + message
        
        # # print(f"Sequence number: {sequence_number}")
        # # print(f"Total chunks: {total_chunks}")
        # # print(f"Packet length: {len(packet)}")

        with packets_lock:
            packets[sequence_number] = packet


def packet_resender(UDPServerSocket, sequence_in_window):
    global resend_counter

    while not terminate_event.is_set():
        with packets_lock:
            with sendbase_lock:
                # If the packet for this sequence number has already been acknowledged, don't send it
                if SEND_BASE + sequence_in_window not in packets:
                    # print(f"Packet with resend_sequence number {SEND_BASE + sequence_in_window} has already been acknowledged")
                    continue

                # Send the packet for this resend_sequence number
                # print(f"Re-sending packet for re-send {resend_sequence} number at time: {time.time()}")
                UDPServerSocket.sendto(packets[SEND_BASE + sequence_in_window], CLIENT_ADDRESS_PORT)
                resend_counter += 1
        if sequence_in_window == 0:
            time.sleep(0.01) # For others
            # ime.sleep(0.2) # For delay
        else:
            time.sleep(0.03) # For others
            # time.sleep(0.4) # For delay


base_send_threads = [threading.Thread(target=packet_resender, args=(UDPServerSocket, i, ), name=f"Packet Resender {i}") for i in range(0, WINDOW_SIZE)] 

# Wait for ACKs
while not terminate_event.is_set():
    try:
        ack_packet, address = UDPServerSocket.recvfrom(4)
        if not CLIENT_ADDRESS_PORT:
            starttime = time.time()
            CLIENT_ADDRESS_PORT = address
            for thread in base_send_threads:
                thread.start()
    except socket.timeout:
        continue
    
    ack_sequence = int.from_bytes(ack_packet, 'big')
    if ack_sequence == 0:
        continue
    
    # print(f"Received ACK for sequence number {ack_sequence} while SEND_BASE = {SEND_BASE}")

    # If an ACK is received, mark the corresponding packet as acknowledged and stop its timer
    if ack_sequence >= SEND_BASE and ack_sequence < SEND_BASE + WINDOW_SIZE:
        with packets_lock:
            if ack_sequence in packets:
                # print(f"Deleting packet with sequence number {ack_sequence}")
                del packets[ack_sequence]

        # If the base of the window is acknowledged, slide the window forward
            
        if ack_sequence == SEND_BASE:
            with sendbase_lock:
                while SEND_BASE not in packets:
                    SEND_BASE += 1
                    # print(f"Task is done for sequence number: {SEND_BASE - 1}")
                    if SEND_BASE == TOTAL_CHUNKS_ALL + 1:
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