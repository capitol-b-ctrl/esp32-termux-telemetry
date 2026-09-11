# ==============================================================================
# File: main.py
# Environment: MicroPython on ESP32
# Purpose: Connect to Wi-Fi and stream telemetry to your Termux TCP server
# ==============================================================================

import network
import socket
import time
import gc

# ------------------------------------------------------------------------------
# Configuration Parameters
# Replace these strings with your active network credentials
# ------------------------------------------------------------------------------
WIFI_SSID = "YOUR_WIFI_OR_HOTSPOT_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# The local IP address of your phone running esp_server.py
# (Find this on your phone by running 'ip addr show' while connected to Wi-Fi)
SERVER_IP = "192.168.0.100"  
SERVER_PORT = 5000

# Transmission interval in seconds
SEND_INTERVAL_SECONDS = 5

def connect_wifi(ssid, password):
    """Initializes the ESP32 Wi-Fi station interface and connects to the network."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print(f"[*] Connecting to Wi-Fi network: {ssid}...")
        wlan.connect(ssid, password)
        
        # Wait up to 10 seconds for connection
        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
        print("")

    if wlan.isconnected():
        network_info = wlan.ifconfig()
        print(f"[+] Wi-Fi connected! ESP32 IP: {network_info[0]}")
        return True
    else:
        print("[-] Wi-Fi connection failed. Please check SSID and password.")
        return False

def run_client():
    """Connects to the Termux TCP server and transmits telemetry messages."""
    # Ensure Wi-Fi connection is established
    if not connect_wifi(WIFI_SSID, WIFI_PASSWORD):
        return

    while True:
        try:
            print(f"[*] Connecting to server at {SERVER_IP}:{SERVER_PORT}...")
            # Create a standard streaming TCP socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_IP, SERVER_PORT))
            print("[+] Successfully connected to Termux server!")

            counter = 1
            while True:
                # Collect basic hardware telemetry
                uptime_sec = time.ticks_ms() // 1000
                free_ram = gc.mem_free()
                
                # Format payload string
                payload = f"ESP32 Packet #{counter} | Uptime: {uptime_sec}s | Free RAM: {free_ram} bytes\n"
                
                # Convert string to raw bytes and transmit over TCP socket
                client_socket.sendall(payload.encode('utf-8'))
                print(f"[Sent]: {payload.strip()}")
                
                counter += 1
                time.sleep(SEND_INTERVAL_SECONDS)

        except Exception as err:
            print(f"[-] Connection interrupted: {err}")
            print("[*] Retrying connection in 5 seconds...")
            time.sleep(5)
            
        finally:
            client_socket.close()

# Start the client routine on boot
if __name__ == "__main__":
    run_client()

