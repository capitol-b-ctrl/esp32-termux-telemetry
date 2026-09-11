#!/usr/bin/env bash
# ==============================================================================
# Script: flash_esp32.sh
# Purpose: Downloads MicroPython firmware, auto-detects ESP32, and flashes it.
# ==============================================================================

set -e

# MicroPython firmware build for generic ESP32 boards
FIRMWARE_URL="https://micropython.org/resources/firmware/ESP32_GENERIC-20241129-v1.24.1.bin"
FIRMWARE_FILE="esp32_micropython_firmware.bin"

echo "=========================================="
echo "      ESP32 AUTOMATED FIRMWARE FLASHER    "
echo "=========================================="

# 1. Download firmware binary if not already cached locally
if [ ! -f "$FIRMWARE_FILE" ]; then
    echo "[*] Downloading MicroPython firmware binary..."
    curl -L "$FIRMWARE_URL" -o "$FIRMWARE_FILE"
    echo "[+] Download complete."
else
    echo "[+] Using cached firmware: $FIRMWARE_FILE"
fi

# 2. Detect ESP32 Serial Port on Android / Linux
PORT=""
for p in /dev/ttyUSB* /dev/ttyACM*; do
    if [ -e "$p" ]; then
        PORT="$p"
        break
    fi
done

if [ -z "$PORT" ]; then
    echo "[-] No connected ESP32 found."
    echo "[!] Please connect the ESP32 via USB-OTG and ensure Termux has USB permissions."
    exit 1
fi

echo "[+] Detected ESP32 device on port: $PORT"

# 3. Erase existing flash memory
echo "[*] Erasing ESP32 flash memory..."
esptool --port "$PORT" erase_flash

# 4. Flash the MicroPython runtime
echo "[*] Writing MicroPython firmware at memory offset 0x1000..."
esptool --port "$PORT" --chip esp32 write_flash -z 0x1000 "$FIRMWARE_FILE"

echo ""
echo "=========================================="
echo "[+] ESP32 successfully flashed with MicroPython!"
echo "[*] You can now upload main.py using:"
echo "    mpremote connect $PORT cp main.py :main.py"
echo "=========================================="

