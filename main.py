# ==============================================================================
# File: main.py
# Platform: MicroPython on ESP32
# Purpose: Unified Wi-Fi + BLE Reconnaissance Engine with AirTag / iBeacon Decoder
# ==============================================================================

import network
import bluetooth
import socket
import time
import machine
import gc
import ustruct as struct
from micropython import const

# ------------------------------------------------------------------------------
# 1. User Configuration Parameters
# ------------------------------------------------------------------------------
# Wi-Fi credentials for local connection (phone hotspot or home router)
WIFI_SSID = "YOUR_HOTSPOT_OR_WIFI_NAME"
WIFI_PASS = "YOUR_WIFI_PASSWORD"

# Local IP address of your phone running esp_server.py in Termux
SERVER_IP = "192.168.0.100"
SERVER_PORT = 5000

# Reconnaissance timing parameters (in seconds)
BLE_SCAN_DURATION_SEC = 5     # Time to listen for Bluetooth advertisements
CYCLE_INTERVAL_SEC = 15       # Pause between full reconnaissance cycles

# Hardware pin mapping (GPIO 2 is standard for the onboard LED on ESP32 DevKit)
LED_PIN_NUMBER = 2
led = machine.Pin(LED_PIN_NUMBER, machine.Pin.OUT)

# ------------------------------------------------------------------------------
# 2. Protocol Constants & Lookup Dictionaries
# ------------------------------------------------------------------------------
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
APPLE_COMPANY_ID = 0x004C

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
# 3. Apple AirTag & iBeacon Binary Payload Decoder
# ------------------------------------------------------------------------------
def decode_apple_payload(adv_payload):
    """
    Parses raw advertising bytes to identify Apple signatures.
    Returns a formatted string if an Apple device is identified, else None.
    """
    if not adv_payload:
        return None

    data = bytes(adv_payload)
    idx = 0
    total = len(data)

    # Walk through Type-Length-Value (TLV) blocks
    while idx < total:
        length = data[idx]
        if length == 0 or (idx + 1 + length > total):
            break

        ad_type = data[idx + 1]
        ad_data = data[idx + 2 : idx + 1 + length]

        # Check for Manufacturer Specific Data (0xFF)
        if ad_type == 0xFF and len(ad_data) >= 2:
            company_id = ad_data[0] | (ad_data[1] << 8)

            # Match Apple Inc. Company ID (0x004C)
            if company_id == APPLE_COMPANY_ID and len(ad_data) > 2:
                payload = ad_data[2:]
                subtype = payload[0]

                # Subtype 0x02: Apple iBeacon
                if subtype == 0x02 and len(payload) >= 23:
                    uuid_bytes = payload[2:18]
                    uuid_str = "{:02X}{:02X}{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}".format(*uuid_bytes)
                    major, minor, tx_power = struct.unpack(">HHb", payload[18:23])
                    return f"[iBEACON] UUID: {uuid_str} | Maj: {major} Min: {minor} | Tx: {tx_power}dBm"

                # Subtype 0x12: Apple AirTag / Find My Offline Finding Network
                elif subtype == 0x12 and len(payload) >= 4:
                    status_flag = payload[2]
                    key_snip = "".join(f"{b:02X}" for b in payload[3:11])
                    return f"[AIRTAG] Status: 0x{status_flag:02X} | Key: {key_snip}... (FindMy)"

                return f"[APPLE] Subtype: 0x{subtype:02X}"

        idx += 1 + length

    return None

# ------------------------------------------------------------------------------
# 4. Bluetooth Low Energy Reconnaissance Engine
# ------------------------------------------------------------------------------
class BLEScannerEngine:
    def __init__(self):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq_handler)
        self.records = []
        self.scanning = False

    def _irq_handler(self, event, data):
        """Asynchronous interrupt handler fired upon receiving BLE advertisements."""
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr_bytes, adv_type, rssi, adv_payload = data
            mac = ":".join(f"{b:02X}" for b in bytes(addr_bytes))

            # Decode payload for Apple hardware signatures
            apple_match = decode_apple_payload(adv_payload)

            if apple_match:
                entry = f"{apple_match} | MAC: {mac} | RSSI: {rssi} dBm"
            else:
                addr_label = "PUBLIC" if addr_type == 0 else "RANDOM"
                entry = f"[BLE] MAC: {mac} ({addr_label}) | RSSI: {rssi} dBm"

            # Avoid recording duplicates within the same scan window
            if entry not in self.records:
                self.records.append(entry)

        elif event == _IRQ_SCAN_DONE:
            self.scanning = False

    def scan_surroundings(self, duration_sec):
        """Executes a passive discovery window for the requested duration."""
        self.records = []
        self.scanning = True
        
        # 100% duty cycle: continuous receiver listening (30000us interval / 30000us window)
        self.ble.gap_scan(duration_sec * 1000, 30000, 30000)

        while self.scanning:
            time.sleep_ms(100)

        return self.records

# ------------------------------------------------------------------------------
# 5. Wi-Fi Station & Scanning Drivers
# ------------------------------------------------------------------------------
def blink_led(times=1, on_ms=40, off_ms=40):
    """Provides visual feedback via onboard LED."""
    for _ in range(times):
        led.value(1)
        time.sleep_ms(on_ms)
        led.value(0)
        time.sleep_ms(off_ms)

def connect_station(ssid, password):
    """Associates with the base Wi-Fi network."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"[*] Associating with Wi-Fi network: '{ssid}'...")
        wlan.connect(ssid, password)
        timeout = 12
        while not wlan.isconnected() and timeout > 0:
            blink_led(1, 60, 500)
            timeout -= 1
            time.sleep(0.5)

    if wlan.isconnected():
        print(f"[+] Wi-Fi connected! ESP32 IP: {wlan.ifconfig()[0]}")
        blink_led(2, 60, 60)
        return wlan
    else:
        print("[-] Wi-Fi connection timed out.")
        return None

def scan_wifi(wlan):
    """Scans 2.4 GHz channels and parses all detected access points."""
    print("[*] Scanning 2.4 GHz Wi-Fi channels...")
    led.value(1)
    try:
        raw_aps = wlan.scan()
    except Exception as err:
        print(f"[-] Wi-Fi scan exception: {err}")
        raw_aps = []
    finally:
        led.value(0)

    results = []
    for ap in raw_aps:
        ssid_bytes, bssid_bytes, channel, rssi, authmode, hidden = ap
        ssid = ssid_bytes.decode('utf-8', 'ignore').strip() or "<Hidden SSID>"
        bssid = ":".join(f"{b:02X}" for b in bssid_bytes)
        sec = AUTH_LOOKUP.get(authmode, f"UNKNOWN({authmode})")
        results.append(f"[WIFI] [{sec}] SSID: {ssid} | BSSID: {bssid} | Ch: {channel:<2} | RSSI: {rssi} dBm")

    return results

# ------------------------------------------------------------------------------
# 6. TCP Telemetry Transmission
# ------------------------------------------------------------------------------
def transmit_report(wifi_records, ble_records):
    """Streams structured reconnaissance data to the Termux socket server."""
    total_found = len(wifi_records) + len(ble_records)
    print(f"[*] Sending {len(wifi_records)} Wi-Fi and {len(ble_records)} BLE records to {SERVER_IP}:{SERVER_PORT}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(6.0)

    try:
        sock.connect((SERVER_IP, SERVER_PORT))

        # Header banner
        uptime_sec = time.ticks_ms() // 1000
        header = (
            f"\n======================================================\n"
            f"  ESP32 DUAL RECON REPORT [Uptime: {uptime_sec}s]\n"
            f"  Total Targets Detected: {total_found} ({len(wifi_records)} Wi-Fi | {len(ble_records)} BLE)\n"
            f"======================================================\n"
        )
        sock.sendall(header.encode('utf-8'))

        # Wi-Fi block
        sock.sendall(b"--- [ 2.4 GHz Wi-Fi Access Points ] ---\n")
        for entry in wifi_records:
            sock.sendall((entry + "\n").encode('utf-8'))
            blink_led(1, 15, 15)

        # BLE block
        sock.sendall(b"\n--- [ Bluetooth Low Energy & Apple Trackers ] ---\n")
        for entry in ble_records:
            sock.sendall((entry + "\n").encode('utf-8'))
            blink_led(1, 15, 15)

        # Footer
        sock.sendall(b"================ End of Report ================\n\n")
        print("[+] Telemetry stream delivered successfully.")

    except Exception as err:
        print(f"[-] TCP stream failure: {err}")
        blink_led(3, 50, 50)
    finally:
        sock.close()

# ------------------------------------------------------------------------------
# 7. Main Application Loop
# ------------------------------------------------------------------------------
def main():
    print("==================================================")
    print("   ESP32 WI-FI + BLE + AIRTAG RECON ACTIVE        ")
    print("==================================================")

    ble_engine = BLEScannerEngine()
    wlan = connect_station(WIFI_SSID, WIFI_PASS)

    cycle = 1
    while True:
        # Verify network connection prior to scan pass
        if not wlan or not wlan.isconnected():
            wlan = connect_station(WIFI_SSID, WIFI_PASS)

        if wlan and wlan.isconnected():
            print(f"\n--- Recon Cycle #{cycle} ---")
            
            # Step 1: Wi-Fi Discovery
            wifi_list = scan_wifi(wlan)
            
            # Step 2: BLE & AirTag Discovery
            print(f"[*] Scanning BLE spectrum for {BLE_SCAN_DURATION_SEC}s...")
            ble_list = ble_engine.scan_surroundings(BLE_SCAN_DURATION_SEC)
            
            # Step 3: Stream Combined Telemetry
            transmit_report(wifi_list, ble_list)
            
            cycle += 1
        else:
            print("[!] Wi-Fi disconnected. Pausing before reconnect...")

        # Clear heap memory buffers
        gc.collect()
        
        print(f"[*] Pausing for {CYCLE_INTERVAL_SEC}s before next pass...")
        time.sleep(CYCLE_INTERVAL_SEC)

if __name__ == "__main__":
    main()
