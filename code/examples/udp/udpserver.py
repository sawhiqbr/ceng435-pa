import socket
import hashlib

CLIENT_ADDRESS_PORT   = None
LOCAL_IP              = "server"
LOCAL_PORT            = 20002
BUFFER_SIZE           = 64000
CURRENT_DIRECTORY     = os.getcwd()
TIMEOUT               = 0.1
SOCKET_TIMEOUT        = 0.5
THREAD_COUNT          = 40 # random.randint(16, 192) // 16 * 16
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

OBJ = "small-0"

# Create a datagram socket
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))

print("UDP server up and listening")

# Listen for incoming datagrams
while(True):
    bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
    file_data = bytesAddressPair[0]
    address = bytesAddressPair[1]

    # Calculate MD5 hash of received file data
    md5_hash = hashlib.md5()
    md5_hash.update(file_data)
    calculated_hash = md5_hash.hexdigest()

    # Read the stored MD5 hash
    with open(f"../objects/{OBJ}.obj.md5", 'r') as md5_file:
        stored_hash = md5_file.read().strip()

    # Compare hashes
    if stored_hash == calculated_hash:
        print("File received intact")
    else:
        print("File corrupted during transfer")

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
            time.sleep(0.005)
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
