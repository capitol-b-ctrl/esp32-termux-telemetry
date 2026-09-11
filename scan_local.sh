#!/usr/bin/env bash

# ==============================================================================
# Script: scan_local.sh
# Purpose: Scan the current Wi-Fi network for open ports and output to <SSID>_scan.txt
# ==============================================================================

echo "[*] Detecting network interface and settings..."

# 1. Detect IPv4 target subnet. Look for non-cellular IP first, then fallback to default route
TARGET_CIDR=$(ip -o -4 addr show | awk '$2 ~ /^(wlan|eth|swlan)/ {print $4}' | head -n 1)

# Fallback: if interface is aliased or hidden by container, pull from route table
if [ -z "$TARGET_CIDR" ]; then
    GATEWAY_IP=$(ip route show default 2>/dev/null | awk '{print $3}' | head -n 1)
    if [ -n "$GATEWAY_IP" ]; then
        # Assume standard /24 subnet based on default gateway
        SUBNET_BASE=$(echo "$GATEWAY_IP" | cut -d'.' -f1-3)
        TARGET_CIDR="${SUBNET_BASE}.0/24"
    fi
fi

# If still not found, target standard local subnet
if [ -z "$TARGET_CIDR" ]; then
    TARGET_CIDR="192.168.1.0/24"
fi

# 2. Extract SSID name from Android Wi-Fi service
RAW_SSID=$(cmd wifi status 2>/dev/null | awk -F'"' '/Wifi is connected to/ {print $2}')

if [ -z "$RAW_SSID" ]; then
    # Secondary check via dumpsys
    RAW_SSID=$(dumpsys wifi 2>/dev/null | grep -o 'SSID: "[^"]*"' | head -n 1 | cut -d'"' -f2)
fi

# Fallback if command line cannot read the SSID string
if [ -z "$RAW_SSID" ] || [ "$RAW_SSID" = "<unknown ssid>" ]; then
    RAW_SSID="SETUP-DD44"
fi

# Clean spaces or special characters in SSID for safe filename creation
CLEAN_SSID=$(echo "$RAW_SSID" | tr -cd '[:alnum:]_-')
OUTPUT_FILE="${CLEAN_SSID}_scan.txt"

echo "[+] Target Range : $TARGET_CIDR"
echo "[+] Network SSID : $CLEAN_SSID"
echo "[*] Scanning for open ports (this may take a minute)..."

# 3. Execute Nmap:
#    --unprivileged : avoids raw socket failures in Android containers
#    -Pn            : skips ping discovery
#    --open         : filters out closed and filtered ports
SCAN_OUTPUT=$(nmap --unprivileged -sV -Pn --open -p 21,22,80,443,445,8080,3389 "$TARGET_CIDR")

# 4. Check if open ports or active hosts were found
if echo "$SCAN_OUTPUT" | grep -qE "(open|/tcp|/udp)"; then
    echo "$SCAN_OUTPUT" > "$OUTPUT_FILE"
    echo "[+] Scan finished! Results saved to: $OUTPUT_FILE"
    echo "--- Summary of Discovered Services ---"
    grep -E "(Nmap scan report|open)" "$OUTPUT_FILE"
else
    echo "[-] No open ports found on $TARGET_CIDR. No output file was created."
fi

