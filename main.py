# ==============================================================================
# File: main.py
# Platform: MicroPython on ESP32
# Purpose: Unified Wi-Fi & BLE Reconnaissance with TCP Telemetry Streaming
# ==============================================================================

import network
import bluetooth
import socket
import time
import machine
import gc
from micropython import const

# ------------------------------------------------------------------------------
# Configuration Parameters
# ------------------------------------------------------------------------------
# Base station credentials (your phone hotspot or home Wi-Fi)
WIFI_SSID = "YOUR_HOTSPOT_OR_WIFI_NAME"
WIFI_PASS = "YOUR_WIFI_PASSWORD"

# Termux TCP server destination
SERVER_IP = "192.168.0.100"  # Replace with phone IP from 'ip -o -4 addr show'
SERVER_PORT = 5000

# Reconnaissance timing parameters (in seconds)
BLE_SCAN_DURATION = 5        # Duration to listen for Bluetooth advertisements
CYCLE_INTERVAL_SECONDS = 15  # Delay between combined scan passes

# Hardware pins
LED_PIN = 2
led = machine.Pin(LED_PIN, machine.Pin.OUT)

# BLE IRQ Event IDs
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

# Wi-Fi authentication mode translation table
AUTH_LOOKUP = {
    0: "OPEN",
    1: "WEP",
    2: "WPA-PSK",
    3: "WPA2-PSK",
    4: "WPA/WPA2-PSK",
    5: "WPA2-ENTERPRISE",
    6: "WPA3-PSK",
    7: "WPA2/WPA3-PSK"
}

# ------------------------------------------------------------------------------
# Bluetooth Low Energy Scanner Engine
# ------------------------------------------------------------------------------
class BLEScannerEngine:
    def __init__(self):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq_handler)
        self.devices = {}
        self.scanning = False

    def _irq_handler(self, event, data):
        """Asynchronous callback fired on every incoming BLE advertisement."""
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr_bytes, adv_type, rssi, adv_payload = data
            
            # Format MAC address into standard uppercase hex string
            mac_str = ":".join(f"{b:02X}" for b in bytes(addr_bytes))
            addr_label = "PUBLIC" if addr_type == 0 else "RANDOM"
            
            # Record or update signal strength
            self.devices[mac_str] = {"type": addr_label, "rssi": rssi}

        elif event == _IRQ_SCAN_DONE:
            self.scanning = False

    def scan_surroundings(self, duration_sec):
        """Runs a BLE discovery window and returns formatted findings."""
        self.devices = {}
        self.scanning = True
        
        # gap_scan(duration_ms, interval_us, window_us)
        # 30000us / 30000us ensures 100% duty cycle (continuous receiver listening)
        self.ble.gap_scan(duration_sec * 1000, 30000, 30000)
        
        while self.scanning:
            time.sleep_ms(100)

        records = []
        for mac, info in self.devices.items():
            records.append(f"[BLE] MAC: {mac} ({info['type']}) | RSSI: {info['rssi']} dBm")
        return records

# ------------------------------------------------------------------------------
# Hardware & Network Helpers
# ------------------------------------------------------------------------------
def blink_led(times=1, on_ms=40, off_ms=40):
    """Provides visual feedback using the onboard LED."""
    for _ in range(times):
        led.value(1)
        time.sleep_ms(on_ms)
        led.value(0)
        time.sleep_ms(off_ms)

def connect_station(ssid, password):
    """Establishes link with the base station or mobile hotspot."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"[*] Associating with Wi-Fi network '{ssid}'...")
        wlan.connect(ssid, password)
        
        timeout = 12
        while not wlan.isconnected() and timeout > 0:
            blink_led(1, 80, 500)
            timeout -= 1
            time.sleep(0.5)

    if wlan.isconnected():
        print(f"[+] Wi-Fi associated. ESP32 IP: {wlan.ifconfig()[0]}")
        blink_led(2, 60, 60)
        return wlan
    else:
        print("[-] Wi-Fi connection timed out.")
        return None

def scan_wifi_airwaves(wlan):
    """Scans 2.4 GHz channels and parses all detected access points."""
    print("[*] Scanning 2.4 GHz Wi-Fi channels...")
    led.value(1)
    try:
        raw_aps = wlan.scan()
    except Exception as err:
        print(f"[-] Wi-Fi scan error: {err}")
        raw_aps = []
    finally:
        led.value(0)

    parsed = []
    for ap in raw_aps:
        ssid_bytes, bssid_bytes, channel, rssi, authmode, hidden = ap
        ssid = ssid_bytes.decode('utf-8', 'ignore').strip() or "<Hidden SSID>"
        bssid = ":".join(f"{b:02X}" for b in bssid_bytes)
        sec = AUTH_LOOKUP.get(authmode, f"UNKNOWN({authmode})")
        parsed.append(f"[WIFI] [{sec}] SSID: {ssid} | BSSID: {bssid} | Ch: {channel:<2} | RSSI: {rssi} dBm")
    
    return parsed

def transmit_telemetry(wifi_records, ble_records):
    """Streams combined reconnaissance data to the Termux TCP socket."""
    total_found = len(wifi_records) + len(ble_records)
    print(f"[*] Streaming payload ({len(wifi_records)} Wi-Fi, {len(ble_records)} BLE) to {SERVER_IP}:{SERVER_PORT}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(6.0)

    try:
        sock.connect((SERVER_IP, SERVER_PORT))
        
        # 1. Main Header
        uptime_sec = time.ticks_ms() // 1000
        header = (
            f"\n======================================================\n"
            f"  ESP32 DUAL RECON REPORT [Uptime: {uptime_sec}s]\n"
            f"  Total Targets Detected: {total_found} ({len(wifi_records)} Wi-Fi | {len(ble_records)} BLE)\n"
            f"======================================================\n"
        )
        sock.sendall(header.encode('utf-8'))

        # 2. Transmit Wi-Fi Records
        sock.sendall(b"--- [ 2.4 GHz Wi-Fi Access Points ] ---\n")
        for entry in wifi_records:
            sock.sendall((entry + "\n").encode('utf-8'))
            blink_led(1, 15, 15)

        # 3. Transmit BLE Records
        sock.sendall(b"\n--- [ Bluetooth Low Energy Advertisements ] ---\n")
        for entry in ble_records:
            sock.sendall((entry + "\n").encode('utf-8'))
            blink_led(1, 15, 15)

        # 4. Footer
        sock.sendall(b"================ End of Report ================\n\n")
        print("[+] Unified telemetry stream successfully delivered.")

    except Exception as err:
        print(f"[-] Socket streaming failure: {err}")
        blink_led(3, 50, 50)
    finally:
        sock.close()

# ------------------------------------------------------------------------------
# Application Lifecycle Entrypoint
# ------------------------------------------------------------------------------
def main():
    print("==================================================")
    print("   ESP32 COMBINED WI-FI & BLE RECON INITIALIZED   ")
    print("==================================================")
    
    # Initialize BLE controller once
    ble_engine = BLEScannerEngine()
    
    # Connect Wi-Fi station
    wlan = connect_station(WIFI_SSID, WIFI_PASS)
    
    cycle = 1
    while True:
        # Re-verify Wi-Fi connection prior to cycle execution
        if not wlan or not wlan.isconnected():
            wlan = connect_station(WIFI_SSID, WIFI_PASS)

        if wlan and wlan.isconnected():
            print(f"\n--- Recon Cycle #{cycle} ---")
            
            # 1. Capture Wi-Fi beacons
            wifi_results = scan_wifi_airwaves(wlan)
            
            # 2. Capture BLE advertisements
            print(f"[*] Scanning BLE spectrum for {BLE_SCAN_DURATION}s...")
            ble_results = ble_engine.scan_surroundings(BLE_SCAN_DURATION)
            
            # 3. Stream combined results over TCP socket
            transmit_telemetry(wifi_results, ble_results)
            
            cycle += 1
        else:
            print("[!] Wi-Fi offline. Waiting before retry...")

        # Reclaim unused RAM after heavy data generation
        gc.collect()
        
        print(f"[*] Pausing for {CYCLE_INTERVAL_SECONDS}s before next cycle...")
        time.sleep(CYCLE_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()

