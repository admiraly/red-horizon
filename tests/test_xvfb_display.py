#!/usr/bin/env python3
"""Pipe fragmentation must not close displayfd before Xvfb writes its newline."""
import json
import os
import threading
import time
from xvfb_display import read_display_number

cases = []
for chunks, expected in (([b'1', b'23', b'\n'], '123'), ([b'7', b'\n'], '7'),
                         ([b'456\n'], '456')):
    read, write = os.pipe()
    failures = []
    def producer():
        try:
            for chunk in chunks:
                os.write(write, chunk)
                time.sleep(.01)
        except BaseException as error:
            failures.append(repr(error))
        finally:
            os.close(write)
    thread = threading.Thread(target=producer)
    thread.start()
    try:
        assert read_display_number(read, 1) == expected
    finally:
        os.close(read)
        thread.join(1)
    assert not thread.is_alive() and not failures
    cases.append(dict(chunks=[c.decode('ascii') for c in chunks], display=expected))

for payload in (b'', b'123', b'abc\n', b'\n', b'1\n2\n', b'1' * 32):
    read, write = os.pipe()
    os.write(write, payload)
    os.close(write)
    try:
        try:
            read_display_number(read, .1)
        except AssertionError:
            pass
        else:
            raise AssertionError(('accepted malformed/incomplete reply', payload))
    finally:
        os.close(read)
read, write = os.pipe()
start = time.monotonic()
try:
    try:
        read_display_number(read, .03)
    except AssertionError as error:
        assert 'timeout' in str(error)
    else:
        raise AssertionError('missing timeout')
finally:
    os.close(read)
    os.close(write)
assert time.monotonic() - start < 1

# Deterministic old-reader control: a digit is readable before the delimiter.
read, write = os.pipe()
try:
    os.write(write, b'1')
    assert os.read(read, 32) == b'1'
    os.close(read)
    read = -1
    try:
        os.write(write, b'\n')
    except BrokenPipeError:
        old_control_failed = True
    else:
        raise AssertionError('old reader unexpectedly retained the pipe')
finally:
    if read >= 0:
        os.close(read)
    os.close(write)
print(json.dumps(dict(suite='xvfb-displayfd', passed=True, fragmented=cases,
    malformed_or_incomplete=6, bounded_timeout=True, old_control_BrokenPipe=True,
    scope='Development pipe framing only; no game or graphics assertions bypassed.')))
