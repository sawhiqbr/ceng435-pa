# echo-server.py

import socket
import hashlib

HOST = "server"  # Standard loopback interface address (localhost)
PORT = 8080  # Port to listen on (non-privileged ports are > 1023)

OBJ = "small-0"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            # Calculate MD5 hash of received file data
            md5_hash = hashlib.md5()
            md5_hash.update(data)
            calculated_hash = md5_hash.hexdigest()

            # Read the stored MD5 hash
            with open(f"../objects/{OBJ}.obj.md5", 'r') as md5_file:
                stored_hash = md5_file.read().strip()

            # Compare hashes
            if stored_hash == calculated_hash:
                print("File received intact")
            else:
                print("File corrupted during transfer")

            conn.sendall(b'File received')