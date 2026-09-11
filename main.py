# ==============================================================================
# File: main.py
# Environment: MicroPython on ESP32
# Purpose: Wi-Fi Reconnaissance Scanner protected by hardware Watchdog Timer
# ==============================================================================

import machine
import network
import socket
import time
import gc

# ------------------------------------------------------------------------------
# Configuration Parameters
# ------------------------------------------------------------------------------
WIFI_SSID = "YOUR_HOTSPOT_OR_WIFI_NAME"
WIFI_PASS = "YOUR_WIFI_PASSWORD"

SERVER_IP = "192.168.0.100"  # Termux IP running esp_server.py
SERVER_PORT = 5000

# Watchdog timeout in milliseconds (15 seconds)
# Keep this longer than wlan.connect() or sock.settimeout() thresholds
WDT_TIMEOUT_MS = 15000

# Hardware pin
status_led = machine.Pin(2, machine.Pin.OUT)

def init_watchdog():
    """Checks previous reset cause and activates the hardware watchdog."""
    if machine.reset_cause() == machine.WDT_RESET:
        print("[!] NOTICE: Prior reboot was triggered by Watchdog Timer recovery.")
    
    # Activate timer (cannot be cancelled once running)
    return machine.WDT(timeout=WDT_TIMEOUT_MS)

def connect_station(wdt, ssid, password):
    """Brings up the Wi-Fi station interface while feeding the watchdog."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"[*] Connecting to {ssid}...")
        wlan.connect(ssid, password)
        
        # Max wait: 8 seconds (less than WDT_TIMEOUT_MS)
        timeout = 8
        while not wlan.isconnected() and timeout > 0:
            wdt.feed()  # Feed watchdog while waiting for AP association
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        print(f"[+] Connected! IP: {wlan.ifconfig()[0]}")
        wdt.feed()
        return wlan
    else:
        print("[-] Wi-Fi connection timed out.")
        return None

def scan_frequencies(wdt, wlan):
    """Scans 2.4 GHz airwaves with safety watchdog feeds."""
    print("[*] Scanning channels...")
    wdt.feed()
    
    try:
        raw_aps = wlan.scan()
    except Exception as err:
        print(f"[-] Scan exception: {err}")
        raw_aps = []
        
    wdt.feed()  # Immediately feed after intensive RF scan completes
    
    parsed = []
    for ap in raw_aps:
        ssid_bytes, bssid_bytes, channel, rssi, authmode, hidden = ap
        ssid_str = ssid_bytes.decode('utf-8', 'ignore').strip() or "<Hidden>"
        mac_str = ":".join(f"{b:02X}" for b in bssid_bytes)
        parsed.append(f"SSID: {ssid_str} | BSSID: {mac_str} | Ch: {channel} | RSSI: {rssi} dBm")
        
    return parsed

def stream_telemetry(wdt, reports):
    """Sends scan reports over TCP with strict socket timeouts."""
    if not reports:
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Crucial: Socket timeout MUST be shorter than watchdog timeout
    sock.settimeout(5.0)

    try:
        wdt.feed()
        sock.connect((SERVER_IP, SERVER_PORT))
        
        header = f"\n--- ESP32 Watchdog-Protected Report ({len(reports)} APs) ---\n"
        sock.sendall(header.encode('utf-8'))
        
        for line in reports:
            sock.sendall((line + "\n").encode('utf-8'))
            wdt.feed()  # Keep timer refreshed during transmission
            
        sock.sendall(b"--- End of Report ---\n")
        print("[+] Telemetry transmitted.")
    except Exception as err:
        print(f"[-] Network stream error: {err}")
    finally:
        sock.close()
        wdt.feed()

def main():
    # 1. Initialize hardware watchdog
    wdt = init_watchdog()
    
    # 2. Connect Wi-Fi
    wlan = connect_station(wdt, WIFI_SSID, WIFI_PASS)

    # 3. Main execution loop
    while True:
        # Keep timer alive at start of every pass
        wdt.feed()
        
        if wlan and wlan.isconnected():
            results = scan_frequencies(wdt, wlan)
            stream_telemetry(wdt, results)
        else:
            # Reconnect attempt if dropped
            wlan = connect_station(wdt, WIFI_SSID, WIFI_PASS)

        gc.collect()
        
        # Sleep in small slices so we can feed the watchdog during idle periods
        # (Sleeping 10s continuously with a 15s WDT is risky; slice-sleeping is safer)
        print("[*] Idling for 10 seconds...")
        for _ in range(10):
            time.sleep(1)
            wdt.feed()

if __name__ == "__main__":
    main()

