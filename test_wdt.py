# ==============================================================================
# File: test_wdt.py
# Environment: MicroPython on ESP32
# Purpose: Demonstrate hardware watchdog feeding and timeout reboot
# ==============================================================================

import machine
import time

# 1. Inspect why the chip booted
# machine.WDT_RESET indicates the previous run was aborted by a watchdog timeout
if machine.reset_cause() == machine.WDT_RESET:
    print("\n[!] WARNING: Chip just recovered from a hardware Watchdog timeout!")
else:
    print("\n[+] Normal power-on / software reset detected.")

# Configure onboard LED (GPIO 2) for visual feedback
led = machine.Pin(2, machine.Pin.OUT)

# 2. Initialize Watchdog with a 5000 ms (5 second) timeout
# Note: On ESP32, timeout is passed in milliseconds
WATCHDOG_TIMEOUT_MS = 5000
wdt = machine.WDT(timeout=WATCHDOG_TIMEOUT_MS)
print(f"[*] Hardware WDT activated ({WATCHDOG_TIMEOUT_MS}ms timeout).")

# 3. Normal Operation Phase: feeding the watchdog on time
print("[*] Normal operation phase starting (5 healthy cycles)...")
for cycle in range(1, 6):
    # Toggle LED to show active execution
    led.value(1)
    time.sleep_ms(100)
    led.value(0)
    
    print(f"  [Cycle {cycle}/5] Task running normally...")
    time.sleep(1)  # Simulated brief workload
    
    # Reset the countdown timer
    wdt.feed()
    print("  --> Fed watchdog successfully.")

# 4. Freeze Simulation Phase: code halts, starving the watchdog
print("\n[!] SIMULATING A CRASH / UNRESPONSIVE NETWORK CALL...")
print("[*] Stopping wdt.feed() calls. The ESP32 should reboot in ~5 seconds...")

# This tight loop starves the watchdog because wdt.feed() is never called
while True:
    # LED remains solid ON to indicate a frozen state
    led.value(1)

