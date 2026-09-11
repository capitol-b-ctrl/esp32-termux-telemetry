# ==============================================================================
# File: ble_scanner.py
# Environment: MicroPython on ESP32
# Purpose: Autonomous Bluetooth Low Energy (BLE) Reconnaissance Scanner
# ==============================================================================

import bluetooth
import time
from micropython import const

# Internal BLE IRQ Event Constants
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

class BLEDeviceScanner:
    def __init__(self):
        # 1. Initialize the Bluetooth controller
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        
        # 2. Register interrupt handler for scan events
        self.ble.irq(self._handle_ble_irq)
        self.found_devices = {}
        self.is_scanning = False

    def _handle_ble_irq(self, event, data):
        """Asynchronous interrupt handler fired by the ESP32 Bluetooth stack."""
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr_bytes, adv_type, rssi, adv_payload = data
            
            # Convert raw 6-byte address into standard colon-separated hex MAC
            mac_str = ":".join(f"{byte:02X}" for byte in bytes(addr_bytes))
            
            # Store or update device RSSI and address classification
            addr_label = "PUBLIC" if addr_type == 0 else "RANDOM"
            self.found_devices[mac_str] = {
                "rssi": rssi,
                "type": addr_label
            }

        elif event == _IRQ_SCAN_DONE:
            # Fired when gap_scan duration finishes
            self.is_scanning = False

    def scan(self, scan_seconds=5):
        """Runs a passive BLE scan for a set duration in seconds."""
        self.found_devices = {}
        self.is_scanning = True
        
        # Parameters: duration (ms), interval (us), window (us)
        # 30000us interval / 30000us window = 100% active duty cycle
        self.ble.gap_scan(scan_seconds * 1000, 30000, 30000)
        
        print(f"[*] Scanning BLE frequencies for {scan_seconds} seconds...")
        while self.is_scanning:
            time.sleep_ms(100)

        # Format records for reporting
        records = []
        for mac, info in self.found_devices.items():
            entry = f"[BLE] MAC: {mac} ({info['type']}) | RSSI: {info['rssi']} dBm"
            records.append(entry)
            
        return records

def test_run():
    scanner = BLEDeviceScanner()
    results = scanner.scan(scan_seconds=6)
    
    print(f"\n[+] Scan finished. Detected {len(results)} BLE devices:")
    for device in results:
        print(f"  {device}")

if __name__ == "__main__":
    test_run()

