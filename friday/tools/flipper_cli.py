#!/usr/bin/env python3
"""Send CLI commands to a USB-connected Flipper Zero and print the output.

Usage: flipper_cli.py "info device" "storage info /ext" ...
"""
import glob
import os
import sys
import termios
import time
import tty

PROMPT = b">: "


def open_port():
    ports = glob.glob("/dev/cu.usbmodemflip_*")
    if not ports:
        sys.exit("No Flipper found (/dev/cu.usbmodemflip_*)")
    fd = os.open(ports[0], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    tty.setraw(fd)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def read_until_prompt(fd, timeout):
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        try:
            chunk = os.read(fd, 4096)
        except BlockingIOError:
            time.sleep(0.02)
            continue
        if chunk:
            buf += chunk
            if buf.endswith(PROMPT):
                break
    return buf


def run(fd, cmd, timeout=10):
    os.write(fd, cmd.encode() + b"\r")
    out = read_until_prompt(fd, timeout).decode(errors="replace")
    lines = out.replace("\r", "").split("\n")
    # Drop echoed command and trailing prompt
    return "\n".join(lines[1:-1]).strip()


def main():
    fd = open_port()
    try:
        read_until_prompt(fd, 2)  # Banner
        os.write(fd, b"\r")
        read_until_prompt(fd, 2)
        for cmd in sys.argv[1:]:
            print(f"### {cmd}")
            print(run(fd, cmd))
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
