"""Development-only bounded reader for Xvfb's newline-terminated displayfd reply."""
import os
import select
import time


def read_display_number(fd, timeout=10):
    deadline = time.monotonic() + timeout
    data = bytearray()
    while b'\n' not in data:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise AssertionError('Xvfb displayfd startup timeout')
        chunk = os.read(fd, 32 - len(data))
        if not chunk:
            raise AssertionError('Xvfb displayfd EOF before newline')
        data.extend(chunk)
        if len(data) >= 32 and b'\n' not in data:
            raise AssertionError('Xvfb displayfd reply exceeds32 bytes')
    if not data.endswith(b'\n') or not data[:-1] or not all(48 <= b <= 57 for b in data[:-1]):
        raise AssertionError('Xvfb displayfd malformed reply')
    return data[:-1].decode('ascii')
