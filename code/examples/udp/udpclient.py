""" --------------------- RECEIVER --------------------- """
import socket
import hashlib
import threading
import os
import time
import sys
import queue

SERVER_ADDRESS_PORT = (socket.gethostbyname("server"), 20002)
LOCAL_IP           = "client"
LOCAL_PORT         = 20001
BUFFER_SIZE        = 1024
CURRENT_DIRECTORY  = os.getcwd()
TIMEOUT            = 1
WINDOW_SIZE        = 128
RECV_BASE          = 1
TOTAL_CHUNKS_SMALL = 0
TOTAL_CHUNKS_LARGE = 0
FILES              = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]
ALL_DONE           = False

chunks             = {}
files_done         = {}
sequence_queue     = queue.Queue()
chunks_lock        = threading.Lock()
terminate_event    = threading.Event()

total_chunks_small_not_set = True
total_chunks_large_not_set = True
new_chunks_not_ready       = True
total_chunks_set_cond      = threading.Condition()
new_chunks_ready_cond      = threading.Condition()
for file_name in FILES:
    files_done[file_name] = False

# Create a datagram socket at the Client side and bind it
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.settimeout(TIMEOUT)
UDPClientSocket.bind((LOCAL_IP, LOCAL_PORT))

# print("UDP Client up and listening")

# Waits for a sequence number to ACK and sends an ACK for it
def ack_sender(UDPClientSocket):
    while not terminate_event.is_set():
        # Get a sequence number from the queue
        try:
            sequence = sequence_queue.get(False)
        except queue.Empty:
            time.sleep(0.01)
            continue
        # Send an ACK for this sequence number
        ack_packet = sequence.to_bytes(4, 'big')
        # print(f"Sending ACK for sequence number {sequence}")
        UDPClientSocket.sendto(ack_packet, SERVER_ADDRESS_PORT)
        # Mark this task as done
        sequence_queue.task_done()
    
    print("All ACKs sent")
    return

# Start the ACK sender thread
ack_thread = threading.Thread(target=ack_sender, args=(UDPClientSocket, ), name="ACK Sender")
ack_thread.start()

# Checks if all chunks have been received for a file and if so, reassembles the file
def file_creator():
    global files_done, ALL_DONE, new_chunks_not_ready

    with total_chunks_set_cond:
        while total_chunks_small_not_set and total_chunks_large_not_set:
            # print("Waiting for total chunks to be set")
            total_chunks_set_cond.wait()
    
    # print("Total chunks set")
    while not all(files_done.values()):  # Continue until all files are done
        for file_name in files_done:
            if not files_done[file_name]:  # If the file is not done
                # print(f"Checking if file {file_name} is done")
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
                    # Ensure the directory exists
                    os.makedirs(os.path.join(CURRENT_DIRECTORY, "objects_received_udp"), exist_ok=True)

                    with chunks_lock:
                        with open(os.path.join(CURRENT_DIRECTORY, "objects_received_udp", f"{file_name}.obj"), 'wb') as f:
                            f.truncate(0)  # Clear existing content
                            for sequence in range(start_sequence, end_sequence + 1):
                                f.write(chunks[sequence])

                    # Calculate MD5 hash
                    with open(os.path.join(CURRENT_DIRECTORY, "objects_received_udp", f"{file_name}.obj"), 'rb') as f:
                        file_data = f.read()
                        calculated_hash = hashlib.md5(file_data).hexdigest()

                    # Read the stored MD5 hash
                    with open(os.path.join(CURRENT_DIRECTORY, "objects", f"{file_name}.obj.md5"), 'r') as md5_file:
                        stored_hash = md5_file.read().strip()

                    # Compare hashes
                    if stored_hash == calculated_hash:
                        print(f"File {file_name} received intact")
                    else:
                        print(f"File {file_name} corrupted during transfer")

                    # Mark the file as done
                    files_done[file_name] = True
                    if all(files_done.values()):
                        ALL_DONE = True
                        terminate_event.set()
                    # print(f"File {file_name} created")

        if not ALL_DONE:
            with new_chunks_ready_cond:
                while new_chunks_not_ready:
                    # print("Waiting for new chunks")
                    new_chunks_ready_cond.wait()
            # print("Really New chunks ready")
            new_chunks_not_ready = True

    terminate_event.set()
    ALL_DONE = True
    return

file_creator_thread = threading.Thread(target=file_creator, name="File Creator")
file_creator_thread.start()

# Chunks will hold sequence number -> acked info. It will start from 1 and go up to the
# total number of chunks in all of the files. Total chunks will be set when the first packet
# from the file of that kind is received.
while(not terminate_event.is_set()):
    try:
        bytesAddressPair = UDPClientSocket.recvfrom(BUFFER_SIZE)
    except socket.timeout:
        continue
    
    # print(f"Got a packet at time: {time.time()}")
    packet = bytesAddressPair[0]
    address = bytesAddressPair[1]
    
    # Extract the checksum, length, sequence number, total chunks, and data from the packet
    file_name = packet[0:7].decode()
    sequence_number = int.from_bytes(packet[7:11], 'big')
    total_chunks = int.from_bytes(packet[11:15], 'big')
    message = packet[15:]
    max_sequence_number = sequence_number + total_chunks - 1

    # print(file_name.startswith("small"), file_name.startswith("large"), TOTAL_CHUNKS_SMALL, TOTAL_CHUNKS_LARGE)
    if total_chunks_small_not_set and file_name.startswith("small"):
        TOTAL_CHUNKS_SMALL = total_chunks
        total_chunks_small_not_set = False
    elif total_chunks_large_not_set and file_name.startswith("large"):
        TOTAL_CHUNKS_LARGE = total_chunks
        total_chunks_large_not_set = False
    with total_chunks_set_cond:
        # print("Can we enter total chunks set cond?")
        if not total_chunks_small_not_set and not total_chunks_large_not_set:
            total_chunks_set_cond.notify_all()

    # Correctly received
    if sequence_number >= RECV_BASE and sequence_number < RECV_BASE + WINDOW_SIZE:
        # print(f"Correctly Received chunk with sequence number: {sequence_number} and put it into the queue")
        # Put the sequence number in the queue
        sequence_queue.put(sequence_number)

        # If the packet was not previously received, buffer it
        with chunks_lock:
            if chunks.get(sequence_number) is None:
                chunks[sequence_number] = message
                # print(f"Correctly Received chunk with sequence number: {sequence_number} is buffered")

        # Move the window if sequence number is the receive base
        if sequence_number == RECV_BASE:
            with chunks_lock:
                while chunks.get(RECV_BASE) is not None:
                    RECV_BASE += 1
        
        # print(f"Receive base is now: {RECV_BASE}")

    # Correctly received but previously acknowledged
    elif sequence_number >= RECV_BASE - WINDOW_SIZE and sequence_number < RECV_BASE:
        # print(f"Previously Received chunk with sequence number: {sequence_number} and put it into the queue")
        # Put the sequence number in the queue
        sequence_queue.put(sequence_number)

    # Else ignore the packet
    else:
        # print(f"Ignored chunk with sequence number: {sequence_number}")
        pass
    
    new_chunks_not_ready = False
    
    with new_chunks_ready_cond:
        if not new_chunks_not_ready:
            # print("Can we enter new chunks ready cond?")
            new_chunks_ready_cond.notify_all()


print("All chunks received")
