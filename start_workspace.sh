#!/usr/bin/env bash
# ==============================================================================
# Script: start_workspace.sh
# Purpose: Launches code-server accessible across your private network/Tailscale
# ==============================================================================

PROJECT_DIR="$HOME/esp32-termux-telemetry"
PORT=8080

# Define an access password for browser logins from your computer
export PASSWORD="telemetry_dev"

# Detect active IP addresses (Tailscale 'tailscale0' or Wi-Fi 'wlan0')
TAILSCALE_IP=$(ip -o -4 addr show tailscale0 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
WLAN_IP=$(ip -o -4 addr show wlan0 2>/dev/null | awk '{print $4}' | cut -d/ -f1)

echo "=================================================="
echo "          REMOTE WORKSPACE LAUNCHER               "
echo "=================================================="
echo "[*] Project Directory: $PROJECT_DIR"
echo "[*] Access Password  : $PASSWORD"
echo ""

if [ -n "$TAILSCALE_IP" ]; then
    echo "[+] Tailscale IP Detected: http://$TAILSCALE_IP:$PORT"
    fi

    if [ -n "$WLAN_IP" ]; then
        echo "[+] Local Wi-Fi IP       : http://$WLAN_IP:$PORT"
        fi

        echo "[+] Local Device URL     : http://127.0.0.1:$PORT"
        echo "=================================================="
        echo "[*] Starting code-server on 0.0.0.0:$PORT..."
        echo "[*] Press Ctrl+C in this window to stop the server."
        echo ""

        # Launch code-server bound to all interfaces
        code-server \
            --auth password \
                --bind-addr 0.0.0.0:$PORT \
                    "$PROJECT_DIR"
                    
