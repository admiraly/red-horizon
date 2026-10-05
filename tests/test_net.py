#!/usr/bin/env python3
"""Four real UDP endpoints exercise the standalone authoritative NASM proof."""
import argparse
import json
import pathlib
import socket
import struct
import subprocess
import tempfile
import time
ROOT = pathlib.Path(__file__).resolve().parents[1]
MAGIC = 0x52484E31


def message(client=0, sequence=1, op=1, company=0, cost=0, target=0, version=1):
    return struct.pack('<8I', MAGIC, version, client, sequence, op, company, cost, target)


def verify(exe):
    # Assemble all traffic before launch so --packets is exact and no job abandoned.
    actions = []
    def add(endpoint, packet, expected, balance=None, owner=None):
        actions.append((endpoint, packet, expected, balance, owner))
    for i in range(4):
        add(i, message(), 0, 100, i+1)
    add(4, message(), 8)  # fifth endpoint denied
    add(0, b'', 1)
    add(0, b'x'*31, 1)
    add(0, b'x'*33, 1)
    add(0, b'x'*1200, 1)
    add(0, b'x'*1201, 1)
    add(0, b'x'*65000, 1)
    add(0, message(1, 2, 3, version=2), 1)
    add(0, message(1, 2, 2, 2, 10, 100), 5, 100, 1) # wrong company
    add(0, message(1, 3, 2, 1, 20, 8000), 0, 80, 1)
    add(0, message(1, 3, 2, 1, 20, 8000), 2, 80, 1) # retransmit lost ack
    add(0, message(1, 5, 2, 1, 10, 400), 3) # reordered before seq4
    add(0, message(1, 4, 2, 1, 10, 400), 0, 70, 1)
    add(0, message(1, 5, 2, 1, 10, 400), 0, 60, 1) # retry accepted
    add(0, message(1, 3, 2, 1, 20, 100), 3) # old sequence
    add(0, message(1, 6, 2, 1, 61, 100), 6, 60, 1) # insufficient funds
    add(0, message(1, 7, 2, 1, 1, 8001), 1)
    add(0, message(1, 8, 2, 1, 0, 100), 1)
    add(0, message(1, 9, 3), 0, 60, 1)
    add(1, message(1, 2, 2, 1, 100, 100), 4) # endpoint/client spoof
    add(1, message(2, 2, 2, 2, 100, 100), 0, 0, 2)
    add(1, message(2, 3, 2, 2, 1, 100), 6, 0, 2)
    add(2, message(3, 2, 3), 0, 100, 3)
    for seq in range(2, 18):
        add(3, message(4, seq, 2, 4, 1, 100), 0, 101-seq, 4)
    add(3, message(4, 18, 2, 4, 1, 100), 7, 84, 4)
    add(3, message(4, 19, 3), 0, 84, 4)
    process = subprocess.Popen([str(exe), '--port', '0', '--packets', str(len(actions))], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sockets = []
    try:
        ready = json.loads(process.stdout.readline())
        assert 0 < ready['port'] <= 65535 and ready['protocol'] == 1
        address = ('127.0.0.1', ready['port'])
        for _ in range(5):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('127.0.0.1', 0))
            sock.settimeout(2)
            sockets.append(sock)
        dropped_ack = False
        for i, packet, expected, balance, owner in actions:
            sock = sockets[i]
            sock.sendto(packet, address)
            result, source = sock.recvfrom(1200)
            assert source == address and len(result) == 32
            if i == 0 and packet == message(1, 3, 2, 1, 20, 8000) and not dropped_ack:
                dropped_ack = True  # deliberately discard first success ACK
                continue
            row = struct.unpack('<8I', result)
            assert row[0:2] == (MAGIC, 1)
            assert row[5] == expected, (i, packet, row, expected)
            if balance is not None:
                assert row[7] == balance, (packet, row, balance)
            if owner is not None:
                assert row[2] == owner and row[6] == owner, (packet, row, owner)
        stdout, stderr = process.communicate(timeout=4)
        assert process.returncode == 0, (stdout, stderr)
        summary = json.loads(stdout)
        assert summary['received'] == len(actions)
        assert summary['rejected'] == sum(a[2] != 0 for a in actions)
    finally:
        for sock in sockets:
            sock.close()
        if process.poll() is None:
            process.kill()
            process.communicate()
    # A dropped request is represented by sequence5 arriving before sequence4;
    # retransmission succeeds after filling the gap. Lost ack => duplicate ack.
    timeout = subprocess.run([str(exe), '--port', '0', '--packets', '1'], capture_output=True, text=True, timeout=4)
    assert timeout.returncode == 3 and json.loads(timeout.stdout.splitlines()[-1])['received'] == 0
    for port, packets in [('-1', '1'), ('65536', '1'), ('1', '0'), ('1', '10001'), ('bad', '1')]:
        assert subprocess.run([str(exe), '--port', port, '--packets', packets], capture_output=True).returncode == 2
    return len(actions)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nasm', default='nasm')
    args = parser.parse_args()
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='red-horizon-net-') as temp:
        obj = pathlib.Path(temp) / 'server.o'
        exe = pathlib.Path(temp) / 'udp-proof'
        subprocess.run([args.nasm, '-f', 'elf64', '-g', '-F', 'dwarf', str(ROOT / 'src/net/server.asm'), '-o', str(obj)], check=True)
        subprocess.run(['cc', str(obj), '-o', str(exe)], check=True)
        packets = verify(exe)
    print(json.dumps({'suite': 'network', 'packets': packets, 'passed': True, 'build_and_test_seconds': round(time.perf_counter()-start, 6)}))


if __name__ == '__main__':
    main()
