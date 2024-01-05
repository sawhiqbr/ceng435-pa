# echo-server.py

import socket
import hashlib

HOST              = 'server'
PORT              = 8000
CURRENT_DIRECTORY = os.getcwd()

OBJ = "small-0"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(10240)
            if not data:
                break
            
            # Calculate MD5 hash of received file data
            md5_hash = hashlib.md5()
            md5_hash.update(data)
            calculated_hash = md5_hash.hexdigest()

            # Read the stored MD5 hash
            with open(f"../objects/{OBJ}.obj.md5", 'r') as md5_file:
                stored_hash = md5_file.read().strip()

    print(f"Time taken: {time.time() - starttime}")
    conn.close()
    s.close()
