#!/usr/bin/env python3
"""Real UDP clients verify the dedicated assembly world; no Python simulation."""
import argparse
import ctypes
import hashlib
import json
import pathlib
import select
import socket
import struct
import subprocess
import time

MAGIC, VERSION, SCHEMA, CONTENT = 0x52484332, 2, 0x78e4e670, 0x180de74f
HEADER = struct.Struct('<10I')


class Peer:
    def __init__(self, address):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('127.0.0.1', 0))
        self.socket.setblocking(False)
        self.address = address
        self.id, self.generation, self.sequence, self.front = 0xffffffff, 0, 1, 0
        self.state = None
        self.entities = {}
        self.max_packet = 0
        self.bytes_received = 0

    def packet(self, kind, payload=b'', sequence=None):
        return HEADER.pack(MAGIC, VERSION, SCHEMA, CONTENT, kind, self.id,
                           self.sequence if sequence is None else sequence, 0,
                           len(payload), self.generation) + payload

    def receive(self, timeout=0.1):
        if not select.select([self.socket], [], [], timeout)[0]:
            return None
        raw, source = self.socket.recvfrom(65536)
        assert source == self.address and 40 <= len(raw) <= 1200
        header = HEADER.unpack_from(raw)
        assert header[:4] == (MAGIC, VERSION, SCHEMA, CONTENT)
        assert header[8]+40 == len(raw)
        self.max_packet = max(self.max_packet, len(raw))
        self.bytes_received += len(raw)
        if header[4] == 100:
            assert len(raw) == 704
            players = [struct.unpack_from('<5f11I', raw, 64+i*64) for i in range(4)]
            self.state = {'tick': header[7], 'units': struct.unpack_from('<I', raw, 40)[0],
                          'operation': struct.unpack_from('<I', raw, 44)[0],
                          'requisition': struct.unpack_from('<2I', raw, 48),
                          'players': players, 'sites': raw[320:704]}
        elif header[4] == 101:
            count = struct.unpack_from('<I', raw, 40)[0]
            assert count <= 32 and len(raw) == 44+count*36
            for offset in range(44, len(raw), 36):
                index = struct.unpack_from('<I', raw, offset)[0]
                record = struct.unpack_from('<2f6I', raw, offset+4)
                assert index < 32768 and 0 <= record[0] <= 8000 and 0 <= record[1] <= 8000
                self.entities[index] = record
        return header, raw[40:]

    def request(self, kind, payload=b'', lose_ack=False, sequence=None):
        data = self.packet(kind, payload, sequence)
        wanted = self.sequence if sequence is None else sequence
        end, next_send, dropped = time.monotonic()+1.5, 0, False
        while time.monotonic() < end:
            now = time.monotonic()
            if now >= next_send:
                self.socket.sendto(data, self.address)
                next_send = now+0.11
            row = self.receive(0.04)
            if row and row[0][4] == 2 and row[0][6] == wanted:
                if lose_ack and not dropped:
                    dropped = True
                    continue
                status, front, units, balance = struct.unpack('<4I', row[1])
                if kind == 1:
                    self.id, self.generation, self.front = row[0][5], row[0][9], front
                    assert self.id < 4 and self.generation > 0
                return status, balance, row[0][7]
        raise AssertionError(('ACK timeout', kind, wanted))

    def command(self, kind, payload=b'', **kwargs):
        self.sequence += 1
        return self.request(kind, payload, **kwargs)

    def input(self, buttons=0, x=0.0, z=0.0, yaw=0.0, pitch=0.0, **kwargs):
        return self.command(3, struct.pack('<I4f', buttons, x, z, yaw, pitch), **kwargs)

    def snapshot(self, minimum=0):
        end = time.monotonic()+1
        while time.monotonic() < end:
            if self.state and self.state['tick'] >= minimum:
                return self.state
            self.receive(0.05)
        raise AssertionError('snapshot timeout')


def verify(server, client_lib=None):
    process = subprocess.Popen([str(server), '--port', '0', '--ticks', '180', '--units', '8192'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    peers = []
    try:
        ready = json.loads(process.stdout.readline())
        assert ready['units'] == 8192 and ready['protocol'] == 2
        address = ('127.0.0.1', ready['port'])
        a, b = Peer(address), Peer(address)
        peers.extend([a, b])
        assert a.request(1)[0] == b.request(1)[0] == 0
        assert (a.id, b.id) == (0, 1) and (a.front, b.front) == (0, 1)
        initial = a.snapshot()['players'][a.id]
        status, _, tick = a.input(1, 1.0, 0.0, lose_ack=True)
        assert status == 0
        time.sleep(0.23)
        assert a.input()[0] == 0
        moved = a.snapshot(tick+3)['players'][a.id]
        assert moved[0] > initial[0], (initial, moved)
        assert moved[12] > initial[12], 'authoritative rifle shot counter unchanged'
        time.sleep(0.04)
        assert a.input(x=float('nan'))[0] == 1
        time.sleep(0.04)
        assert a.input(buttons=8)[0] == 1
        # Command rejection consumes sequence; normal next command still succeeds.
        assert b.command(4, struct.pack('<IIff', a.front, 0, 3900, 1400))[0] == 5
        status, before, tick = a.command(4, struct.pack('<IIff', a.front, 0, 3900, 1400), lose_ack=True)
        assert status == 0
        duplicated = a.request(4, struct.pack('<IIff', a.front, 0, 3900, 1400))
        assert duplicated[0] == 0 and duplicated[1] == before, 'duplicate charged requisition twice'
        assert a.command(4, struct.pack('<IIff', a.front, 0, float('inf'), 1400))[0] in (1, 7)
        # Oversized/short/hash-mismatch datagrams cannot modify authoritative state.
        for data in (b'', b'x'*39, b'x'*1201, b'x'*65000,
                     HEADER.pack(MAGIC, VERSION, SCHEMA+1, CONTENT, 3, a.id, 999, 0, 0, a.generation)):
            a.socket.sendto(data, address)
        # Deliberate future packet followed by retransmission in sequence order.
        future = a.packet(3, struct.pack('<I4f', 0, 0, 0, 0, 0), sequence=a.sequence+2)
        a.socket.sendto(future, address)
        time.sleep(0.04)
        assert a.input()[0] == 0
        time.sleep(0.04)
        assert a.input()[0] == 0
        c, d = Peer(address), Peer(address)
        peers.extend([c, d])
        assert c.request(1)[0] == 0
        d_join = d.request(1)
        assert d_join[0] == 0
        assert (c.id, d.id) == (2, 3)
        assert d.command(4, struct.pack('<IIff', d.front, 0, 3500, 1300))[0] == 5
        snapshot = c.snapshot(d_join[2]+1)
        assert snapshot['tick'] > 0 and snapshot['units'] == 8192
        assert all(p[11] == 1 for p in snapshot['players']), 'join-in-progress player states missing'
        assert len(snapshot['sites']) == 384
        while not c.entities:
            c.receive(0.1)
        assert c.max_packet <= 1200 and 0 < len(c.entities) < 8192
        # Explicit leave frees primary ownership; generation prevents delayed packets.
        old_generation = b.generation
        assert b.command(5)[0] == 0
        e = Peer(address)
        peers.append(e)
        assert e.request(1)[0] == 0 and e.id == 1 and e.generation > old_generation
        # Keep two peers active while slots2/3 intentionally expire after90ticks.
        end = time.monotonic()+3.25
        while time.monotonic() < end:
            time.sleep(0.2)
            a.input()
            e.input()
        f = Peer(address)
        peers.append(f)
        assert f.request(1)[0] == 0 and f.id == 2 and f.generation > c.generation
        for peer in (a, e, f):
            peer.input()
        stdout, stderr = process.communicate(timeout=4)
        assert process.returncode == 0, (stdout, stderr)
        report = json.loads(stdout)
        assert report['ticks'] == 180 and report['simulated'] == 8192
        assert report['entity_records'] > 0 and report['disconnects'] >= 2
        assert report['bytes_out'] < 4*180*1200*3, 'outbound cap broken'
        assert report['rejected'] >= 7
        return report
    finally:
        for peer in peers:
            peer.socket.close()
        if process.poll() is None:
            process.kill()
            process.communicate()


def verify_adapter(server, library):
    lib = ctypes.CDLL(str(library.resolve()))
    lib.net_client_open.argtypes = [ctypes.c_char_p, ctypes.c_uint]
    lib.net_client_input.argtypes = [ctypes.c_uint, ctypes.c_uint] + [ctypes.c_float]*4
    lib.net_client_order.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_float, ctypes.c_float]
    for name in ('net_client_open', 'net_client_input', 'net_client_order', 'net_client_poll'):
        getattr(lib, name).restype = ctypes.c_int
    process = subprocess.Popen([str(server), '--port', '0', '--ticks', '60', '--units', '8192'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        ready = json.loads(process.stdout.readline())
        assert lib.net_client_open(b'127.0.0.1', ready['port']) == 0
        entity_bytes = (ctypes.c_ubyte * (32768*32)).in_dll(lib, 'sim_entities')
        assert all(struct.unpack_from('<I', entity_bytes, i*32+8)[0] == 0 for i in range(32768))
        connected = ctypes.c_uint.in_dll(lib, 'net_connected')
        players = (ctypes.c_ubyte * 256).in_dll(lib, 'sim_players')
        end, initial = time.monotonic()+1.5, None
        while time.monotonic() < end:
            lib.net_client_poll()
            if connected.value:
                record = struct.unpack_from('<5f11I', players, 0)
                if record[11] and initial is None:
                    initial = record[0]
                lib.net_client_input(0, 0, 1.0, 0.0, 0.0, 0.0)
            time.sleep(0.035)
        assert connected.value == 1 and initial is not None
        assert struct.unpack_from('<f', players, 0)[0] > initial
        assert sum(struct.unpack_from('<I', entity_bytes, i*32+8)[0] > 0 for i in range(8192)) > 0
        stdout, stderr = process.communicate(timeout=3)
        assert process.returncode == 0, (stdout, stderr)
        lib.net_client_poll()
        server_tick = ctypes.c_uint.in_dll(lib, 'net_server_tick').value
        local_tick = ctypes.c_uint.in_dll(lib, 'sim_tick_count').value
        for _ in range(4):
            lib.net_client_poll()
        assert ctypes.c_uint.in_dll(lib, 'sim_tick_count').value == local_tick == server_tick
        lib.net_client_close()
    finally:
        lib.net_client_close()
        if process.poll() is None:
            process.kill()
            process.communicate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', type=pathlib.Path, required=True)
    parser.add_argument('--client-lib', type=pathlib.Path)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[1]
    assert int(hashlib.sha256((root / "src/net/schema.txt").read_bytes()).hexdigest()[:8], 16) == SCHEMA
    assert int(hashlib.sha256((root / "content/asset-manifest.json").read_bytes()).hexdigest()[:8], 16) == CONTENT
    constants = (root / "src/net/protocol.inc").read_text()
    assert f"%define NET_SCHEMA 0x{SCHEMA:08x}" in constants
    assert f"%define NET_CONTENT 0x{CONTENT:08x}" in constants
    report = verify(args.server.resolve())
    if args.client_lib:
        verify_adapter(args.server.resolve(), args.client_lib)
    print(json.dumps({'suite': 'cooperative-world', 'passed': True, 'server': report}))


if __name__ == '__main__':
    main()
