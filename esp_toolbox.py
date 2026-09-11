#!/usr/bin/env python3
"""
ESP32 Management & Diagnostics Utility
Designed for Termux on Android with patched pySerial.
"""

import sys
import time
import serial
import serial.tools.list_ports
import esptool

def find_esp32_port():
    """Scans for connected USB-to-UART bridge chips (CP210x, CH340, FTDI)."""
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None
    
    # Return the first active USB serial port found
    for port in ports:
        if "ttyUSB" in port.device or "ttyACM" in port.device:
            return port.device
    return ports[0].device

def get_chip_details(port_name):
    """Uses esptool to query hardware information from the ESP32."""
    print(f"\n[+] Connecting to ESP32 on {port_name}...")
    try:
        # Run esptool's flash_id command to inspect hardware specs
        esptool.main(['--port', port_name, 'flash_id'])
    except Exception as err:
        print(f"[-] Failed to communicate with bootloader: {err}")

def open_serial_monitor(port_name, baud_rate=115200):
    """Opens a live serial terminal to read output from the running chip."""
    print(f"\n[*] Listening on {port_name} at {baud_rate} baud...")
    print("[*] Press Ctrl + C to exit the monitor.\n" + ("-" * 45))
    
    try:
        with serial.Serial(port_name, baud_rate, timeout=1) as ser:
            while True:
                line = ser.readline().decode('utf-8', errors='replace')
                if line:
                    print(line, end='')
    except KeyboardInterrupt:
        print("\n[*] Exiting serial monitor.")
    except Exception as err:
        print(f"[-] Serial monitor error: {err}")

def main():
    print("==========================================")
    print("       ESP32 TERMUX TOOLBOX READY         ")
    print("==========================================")
    
    port = find_esp32_port()
    if not port:
        print("[-] No ESP32 device detected on USB.")
        print("[*] Plug in your ESP32 with a USB OTG adapter and run this script again.")
        sys.exit(0)

    print(f"[+] Device detected at: {port}")
    print("\nSelect an action:")
    print("  1. Read Chip & Flash Specifications")
    print("  2. Open Live Serial Log Monitor (115200 baud)")
    print("  3. Exit")
    
    choice = input("\nEnter choice [1-3]: ").strip()
    
    if choice == "1":
        get_chip_details(port)
    elif choice == "2":
        open_serial_monitor(port)
    else:
        print("[*] Exiting.")

if __name__ == "__main__":
    main()

