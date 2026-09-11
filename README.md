
# ESP32 IoT Telemetry & Reconnaissance Pipeline

An embedded IoT telemetry, Wi-Fi reconnaissance, and Bluetooth Low Energy (BLE) tracking toolkit connecting an ESP32 microcontroller running MicroPython to an Android environment running Termux.

---

## Features

* **Dual-Radio Reconnaissance:** Sequentially scans 2.4 GHz Wi-Fi channels (1–11/14) and BLE advertising frequencies to prevent radio contention on the ESP32.
* **Apple AirTag & iBeacon Decoding:** Parses BLE Manufacturer Specific Data (`0xFF`) with Apple's Company ID (`0x004C`) to identify:
  * **Apple AirTags / Find My Network:** Status flags and rotating public key fragments.
  * **iBeacons:** Proximity UUID, Major ID, Minor ID, and calibrated 1-meter Tx Power.
* **Hardware Failsafe Boot Protection (`boot.py`):** Monitors the physical BOOT button (GPIO 0) during a 3-second power-on window. Holding the button halts execution via `sys.exit()` and opens an interactive REPL, preventing infinite crash loops caused by broken application code.
* **Hardware Watchdog Timer (WDT):** Protects against network stalls or firmware hangs by triggering an automatic reboot if the application loop fails to feed the watchdog.
* **Persistent State Across Sleep:** Tracks boot counts and historical access point discoveries in RTC slow memory across deep sleep cycles.
* **Remote Mobile Development:** Integrated shell utilities to run `code-server` over a private Tailscale or Wi-Fi network, enabling browser-based coding on a computer while Termux handles hardware I/O.

---

## Hardware Pin Mapping

| Peripheral | ESP32 GPIO Pin | Function / Logic |
| :--- | :--- | :--- |
| **Status LED** | `GPIO 2` | Digital Output. Pulses during Wi-Fi association, turns solid during RF scans, and flickers rapidly during TCP transmission. |
| **BOOT Failsafe Button** | `GPIO 0` | Digital Input with Pull-Up. Hold `LOW` (pressed) during the 3-second boot window to abort to the MicroPython REPL. |

---

## Repository Structure

```text
esp32-termux-telemetry/
├── boot.py             # Hardware failsafe recovery and bootloader initialization
├── main.py             # Primary application: Wi-Fi/BLE scanner & Apple decoder
├── esp_server.py       # Termux TCP socket server (port 5000) that logs telemetry
├── esp_toolbox.py      # USB-OTG serial monitor and ESP32 hardware inspector
├── flash_esp32.sh      # Automated MicroPython firmware downloader and flasher
├── start_workspace.sh  # Script to launch code-server across Tailscale / LAN
├── sync_git.sh         # Automated Git staging, commit, and push utility
├── scan_local.sh       # Local subnet port and host scanning utility
├── test_wdt.py         # Diagnostic test script demonstrating Watchdog reboots
└── README.md           # Project documentation and deployment instructions
