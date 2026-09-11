# ==============================================================================
# File: boot.py
# Environment: MicroPython on ESP32
# Purpose: Boot configuration with hardware failsafe recovery for crash loops
# ==============================================================================

import machine
import time
import sys
import gc

# ------------------------------------------------------------------------------
# Hardware Pin Definitions
# ------------------------------------------------------------------------------
# GPIO 0 is wired to the built-in "BOOT" button on standard ESP32 boards
BOOT_BUTTON_PIN = 0

# GPIO 2 is standard for the blue status LED on ESP32 DevKit modules
STATUS_LED_PIN = 2

# Configure the BOOT button as an input with internal pull-up resistor
# Unpressed = 1 (HIGH), Pressed = 0 (LOW)
boot_button = machine.Pin(BOOT_BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
status_led = machine.Pin(STATUS_LED_PIN, machine.Pin.OUT)

def run_failsafe_check(grace_period_seconds=3):
    """
    Monitors GPIO 0 during a brief startup window.
    If the button is held LOW, execution aborts to prevent main.py from loading.
    """
    print("\n[+] ESP32 booting...")
    print(f"[*] Failsafe window active: Hold the BOOT button within {grace_period_seconds}s to abort to REPL.")
    
    # Calculate loops: 10 checks per second (100ms intervals)
    total_checks = grace_period_seconds * 10
    
    for _ in range(total_checks):
        # Toggle LED to show active recovery window
        status_led.value(not status_led.value())
        
        # Check if physical BOOT button is being pressed
        if boot_button.value() == 0:
            status_led.value(1)  # Solid LED indicates recovery triggered
            print("\n" + "=" * 55)
            print(" [!] EMERGENCY RECOVERY TRIGGERED VIA HARDWARE BUTTON")
            print(" [!] Aborting boot sequence. Skipping main.py.")
            print(" [!] Dropping into interactive REPL...")
            print("=" * 55 + "\n")
            
            # sys.exit() halts boot.py without crashing the firmware,
            # leaving the interpreter in the interactive REPL.
            sys.exit()
            
        time.sleep_ms(100)

    # Turn off LED and proceed normally
    status_led.value(0)
    print("[+] Failsafe check passed. Launching main.py...\n")

# Run the failsafe detection
run_failsafe_check(grace_period_seconds=3)

# Run initial garbage collection to start with clean heap
gc.collect()

