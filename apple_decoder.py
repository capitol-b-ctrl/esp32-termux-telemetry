# ==============================================================================
# File: apple_decoder.py
# Platform: MicroPython on ESP32
# Purpose: Decodes BLE raw advertising payloads for Apple iBeacons and AirTags
# ==============================================================================

import ustruct as struct

# Apple Bluetooth SIG Company Identifier (0x004C, little-endian: 0x4C, 0x00)
APPLE_COMPANY_ID = 0x004C

# Apple Proprietary Sub-Type Identifiers
APPLE_TYPE_IBEACON = 0x02
APPLE_TYPE_FINDMY  = 0x12

def parse_tlv_records(payload_bytes):
    """
    Parses a raw BLE advertising payload into a list of (ad_type, ad_data) tuples.
    Follows standard BLE Type-Length-Value formatting.
    """
    records = []
    idx = 0
    total_len = len(payload_bytes)

    while idx < total_len:
        length = payload_bytes[idx]
        if length == 0:
            break
        
        # Guard against truncated or malformed packets
        if idx + 1 + length > total_len:
            break

        ad_type = payload_bytes[idx + 1]
        ad_data = payload_bytes[idx + 2 : idx + 1 + length]
        records.append((ad_type, ad_data))
        
        idx += 1 + length

    return records

def decode_apple_payload(adv_payload):
    """
    Inspects raw advertising payload bytes.
    Returns a dictionary of parsed device attributes if Apple hardware is found,
    or None if the packet is generic or belongs to another vendor.
    """
    if not adv_payload:
        return None

    raw_bytes = bytes(adv_payload)
    records = parse_tlv_records(raw_bytes)

    for ad_type, ad_data in records:
        # Check for Manufacturer Specific Data (AD Type 0xFF)
        if ad_type == 0xFF and len(ad_data) >= 2:
            # First 2 bytes are Company ID (little-endian)
            company_id = ad_data[0] | (ad_data[1] << 8)
            
            if company_id == APPLE_COMPANY_ID:
                apple_data = ad_data[2:]  # Strip Company ID bytes
                return _parse_apple_subtypes(apple_data)

    return None

def _parse_apple_subtypes(data):
    """Parses specific Apple message formats based on the sub-type header byte."""
    if len(data) < 2:
        return {"vendor": "Apple", "subtype": "Unknown", "raw": bytes(data)}

    apple_type = data[0]

    # --------------------------------------------------------------------------
    # 1. iBeacon Decoding (Type 0x02, standard length: 21 bytes)
    # --------------------------------------------------------------------------
    if apple_type == APPLE_TYPE_IBEACON and len(data) >= 23:
        # Format: [Type: 1B] [Length: 1B] [UUID: 16B] [Major: 2B] [Minor: 2B] [Power: 1B]
        uuid_raw = data[2:18]
        uuid_formatted = "{:02X}{:02X}{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}".format(*uuid_raw)
        
        # Unpack Major (uint16), Minor (uint16), and Tx Power (signed int8)
        major, minor, tx_power = struct.unpack(">HHb", data[18:23])
        
        return {
            "vendor": "Apple",
            "classification": "iBeacon",
            "uuid": uuid_formatted,
            "major": major,
            "minor": minor,
            "tx_power": tx_power
        }

    # --------------------------------------------------------------------------
    # 2. Apple Find My / AirTag Decoding (Type 0x12)
    # --------------------------------------------------------------------------
    elif apple_type == APPLE_TYPE_FINDMY and len(data) >= 4:
        # Format: [Type: 1B] [Length: 1B] [Status: 1B] [Rotating Public Key Segment]
        status_byte = data[2]
        key_segment = "".join(f"{b:02X}" for b in data[3:])
        
        return {
            "vendor": "Apple",
            "classification": "Apple AirTag / Find My Network",
            "status_flag": f"0x{status_byte:02X}",
            "public_key_segment": key_segment
        }

    # --------------------------------------------------------------------------
    # 3. Other Apple Peripherals (AirPods, Nearby Action, Continuity)
    # --------------------------------------------------------------------------
    return {
        "vendor": "Apple",
        "classification": f"Apple Peripheral (Subtype 0x{apple_type:02X})",
        "raw_payload": "".join(f"{b:02X}" for b in data)
    }

# ------------------------------------------------------------------------------
# Demonstration / Unit Test Harness
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("[*] Running local byte decode test...")

    # Simulated raw AirTag packet
    simulated_airtag_packet = bytes([
        0x02, 0x01, 0x1A,  # Flags
        0x1E, 0xFF,        # Length 30, Type 0xFF (Manufacturer Specific)
        0x4C, 0x00,        # Apple Company ID
        0x12, 0x19, 0x10,  # Type 0x12 (FindMy), Length 25, Status 0x10
        0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x11, 0x22,
        0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0x00,
        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC
    ])

    result = decode_apple_payload(simulated_airtag_packet)
    print("\n[+] Decoded AirTag Packet Result:")
    for key, val in result.items():
        print(f"    {key}: {val}")

