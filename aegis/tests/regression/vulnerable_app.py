#!/usr/bin/env python
# tests/regression/vulnerable_app.py
"""
A simple, simulated vulnerable application for testing pwntools integration.
It expects a specific buffer overflow-like payload to print a flag.
"""
import sys


def main():
    try:
        payload = sys.stdin.readline().strip()

        # The "vulnerability" is a hardcoded check for a specific overflow pattern.
        # A real exploit would overwrite a return address, but this simulates the
        # need to find a precise offset and value.
        # 40 'A's represent the buffer, 'BBBB' represents the overwritten value.
        if payload == "A" * 40 + "BBBB":
            print("Success! Here is your flag:")
            print("AEGIS{pwn_t00ls_w0rks_as_3xp3ct3d}")
        else:
            print("Crashing...")
    except Exception:
        print("An error occurred.")


if __name__ == "__main__":
    main()
