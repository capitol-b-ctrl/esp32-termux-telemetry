#!/usr/bin/env python3
"""
Script: esp_server.py
Purpose: Listens for incoming TCP connections from an ESP32 on the local network,
         prints received messages to the console, and logs them to a file.
"""

import socket
import datetime

# ==============================================================================
# Configuration Parameters
# ==============================================================================
# '0.0.0.0' binds to all available network interfaces (Wi-Fi, hotspot, loopback)
LISTEN_HOST = '0.0.0.0'

# Choose any open port above 1024 (standard unprivileged port range)
LISTEN_PORT = 5000

# Name of the output log file
LOG_FILE = "esp32_incoming_data.txt"

def start_listener():
    # 1. Create a streaming TCP socket (AF_INET = IPv4, SOCK_STREAM = TCP)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 2. Allow immediate reuse of the port after stopping the script
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # 3. Bind the socket to the host and port, then begin listening
        server_socket.bind((LISTEN_HOST, LISTEN_PORT))
        server_socket.listen(1)
        print(f"[*] Server listening on port {LISTEN_PORT}...")
        print(f"[*] Waiting for ESP32 connection (Press Ctrl+C to exit)...\n")

        while True:
            # 4. Accept incoming connection from the ESP32
            client_conn, client_address = server_socket.accept()
            print(f"[+] Connection established from {client_address[0]}:{client_address[1]}")

            # 5. Receive and decode incoming data packets
            while True:
                data = client_conn.recv(1024)
                if not data:
                    # Client closed the connection
                    print(f"[-] Device {client_address[0]} disconnected.\n")
                    break
                
                # Convert raw bytes into readable text
                message = data.decode('utf-8', errors='replace').strip()
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"[{timestamp}] [{client_address[0]}]: {message}"
                
                print(log_entry)
                
                # Append received data to the log file
                with open(LOG_FILE, "a") as f:
                    f.write(log_entry + "\n")

    except KeyboardInterrupt:
        print("\n[*] Shutting down listener...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_listener()

