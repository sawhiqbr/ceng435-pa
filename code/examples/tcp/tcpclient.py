# echo-client.py

import socket

HOST               = socket.gethostbyname('server')
PORT               = 8000
CURRENT_DIRECTORY  = os.getcwd()

OBJ = "small-0"

client_socket = socket.socket()  # instantiate
client_socket.connect((HOST, PORT))  # connect to the server


with open(f"../objects/{OBJ}.obj", 'rb') as file:
    file_data = file.read()

client_socket.sendall(file_data)  # send file data

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
    
    s.close()
    print(f"Time taken: {time.time() - starttime}")
