import socket

SERVER_ADDRESS_PORT = (socket.gethostbyname("server"), 20002)
BUFFER_SIZE        = 64000
CURRENT_DIRECTORY  = os.getcwd()
SOCKET_TIMEOUT     = 0.5
WINDOW_SIZE        = 128
RECV_BASE          = 1
TOTAL_CHUNKS_SMALL = 0
TOTAL_CHUNKS_LARGE = 0
TOTAL_CHUNKS_ALL   = 0
FILES              = [f"{size}-{i}" for size in ["small", "large"] for i in range(10)]
ALL_DONE           = False
total_acks         = 0
received_acks      = 0
chunks             = {}
files_done         = {}
sequence_queue     = queue.Queue()
chunks_lock        = threading.Lock()
terminate_event    = threading.Event()

OBJ = "small-0"

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Read file data
with open(f"../objects/{OBJ}.obj", 'rb') as file:
    file_data = file.read()

# Send file data to server using created UDP socket
UDPClientSocket.sendto(file_data, serverAddressPort)

msgFromServer = UDPClientSocket.recvfrom(bufferSize)

msg = "Message from Server {}".format(msgFromServer[0])
print(msg)