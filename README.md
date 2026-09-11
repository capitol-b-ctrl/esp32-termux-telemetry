# ESP32 & Termux Telemetry Pipeline

An embedded telemetry and Wi-Fi reconnaissance toolkit connecting an ESP32 running MicroPython to an Android device running Termux and NetHunter.

## Files

* `esp_server.py`: Python TCP socket listener running in Termux that accepts incoming data and logs it to disk.
* `esp_toolbox.py`: Serial monitor and chip hardware inspector for ESP32 over USB OTG.
* `scan_local.sh`: Subnet scanner targeting local active ports.
* `main.py`: MicroPython firmware for scanning 2.4 GHz beacons and streaming reports over TCP.
* `sync_git.sh`: Quick synchronization script to commit and push changes to GitHub.
