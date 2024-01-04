""" --------------------- RECEIVER --------------------- """
import socket
import os 
import time

HOST               = socket.gethostbyname('server')
PORT               = 8080
CURRENT_DIRECTORY  = os.getcwd()

def receive_file(conn, filename):
    # Receive the file size first
    file_size_data = conn.recv(8)
    if not file_size_data:
        return  # Handle case where connection is closed
    file_size = int.from_bytes(file_size_data, 'big')

    # Receive the file data

    os.makedirs(os.path.join(CURRENT_DIRECTORY, "objects_received_tcp"), exist_ok=True)

    with open(os.path.join(CURRENT_DIRECTORY, "objects_received_tcp", f"{filename}"), 'wb') as file:
        file.truncate(0)  # Clear existing content
        remaining = file_size
        while remaining > 0:
            chunk_size = 10240 if remaining >= 10240 else remaining
            data = conn.recv(chunk_size)
            if not data:
                break  # Handle case where connection is closed unexpectedly
            file.write(data)
            remaining -= len(data)

    conn.sendall(b'File received')


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    starttime = time.time()
    s.connect((HOST, PORT))
    for i in range(10):
        receive_file(s, f"large-{i}.obj")
        receive_file(s, f"small-{i}.obj")

    print(f"Time taken: {time.time() - starttime}")