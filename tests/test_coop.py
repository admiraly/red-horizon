#!/usr/bin/env python3
"""Real UDP clients verify the dedicated assembly world; no Python simulation."""
import argparse
import ctypes
import hashlib
import json
import pathlib
import select
import os
import signal
import threading
import socket
import struct
import subprocess
import time

MAGIC, VERSION, SCHEMA, CONTENT = 0x52484332, 3, 0x3d7ce8be, 0x5f16a37b
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
        self.events = {}
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
            if self.state and header[7] < self.state["tick"]:
                return header, raw[40:]
            assert len(raw) == 848
            players = [struct.unpack_from('<5f11I', raw, 64+i*64) for i in range(4)]
            self.state = {'tick': header[7], 'units': struct.unpack_from('<I', raw, 40)[0],
                          'operation': struct.unpack_from('<I', raw, 44)[0],
                          'requisition': struct.unpack_from('<2I', raw, 48),
                          'players': players, 'sites': raw[320:704],
                          'vehicles': [struct.unpack_from('<8I',raw,704+i*32) for i in range(4)],
                          'player_vehicle': struct.unpack_from('<4i',raw,832)}
        elif header[4] == 101:
            count = struct.unpack_from('<I', raw, 40)[0]
            assert count <= 32 and len(raw) == 44+count*36
            for offset in range(44, len(raw), 36):
                index = struct.unpack_from('<I', raw, offset)[0]
                record = struct.unpack_from('<2f6I', raw, offset+4)
                assert index < 32768 and 0 <= record[0] <= 8000 and 0 <= record[1] <= 8000
                self.entities[index] = record
        elif header[4] == 102:
            count=struct.unpack_from('<I',raw,40)[0]
            assert count<=32 and len(raw)==44+count*32
            for offset in range(44,len(raw),32):
                event=struct.unpack_from('<3f3IfI',raw,offset)
                assert 1<=event[3]<=5 and event[4]<=1 and event[5]<=header[7]
                self.events[event[7]]=event
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
        assert ready['units'] == 8192 and ready['protocol'] == 3
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
        bad_status, budget_before, budget_tick = a.input(buttons=32)
        assert bad_status == 1
        # Command rejection consumes sequence; normal next command still succeeds.
        assert b.command(4, struct.pack('<IIff', a.front, 0, 3900, 1400))[0] == 5
        status, balance, blocked_tick = a.command(4, struct.pack('<IIff', a.front, 0, 4000, 1300))
        assert status == 1
        assert balance == budget_before + 39 * (blocked_tick//30-budget_tick//30), 'solid destination consumed requisition'
        blocked_retry = a.request(4, struct.pack('<IIff', a.front, 0, 4000, 1300))
        assert blocked_retry[0] == 1 and blocked_retry[1] == balance + 39 * (blocked_retry[2]//30-blocked_tick//30), 'blocked destination charged money'
        status, before, tick = a.command(4, struct.pack('<IIff', a.front, 0, 3900, 1400), lose_ack=True)
        assert status == 0
        duplicated = a.request(4, struct.pack('<IIff', a.front, 0, 3900, 1400))
        assert duplicated[0] == 0 and duplicated[1] == before + 39 * (duplicated[2]//30-tick//30), 'duplicate charged requisition twice'
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


def server_addresses(process, executable):
    symbols = {}
    for line in subprocess.check_output(['nm', '-g', '--defined-only', str(executable)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    base = 0
    elf = executable.read_bytes()
    if int.from_bytes(elf[16:18], 'little') == 3:  # PIE ET_DYN
        for line in pathlib.Path(f'/proc/{process.pid}/maps').read_text().splitlines():
            fields = line.split()
            if len(fields) >= 6 and fields[2] == '00000000' and pathlib.Path(fields[-1]) == executable:
                base = int(fields[0].split('-')[0], 16)
                break
        assert base, 'PIE load mapping not found'
    return {name: base+symbols[name] for name in ('sim_entities', 'sim_players', 'sim_count')}


def verify_death_redeployment(server):
    # Development fixture writes only positions. HP/damage/respawn stay server-owned.
    process = subprocess.Popen([str(server), '--port', '0', '--ticks', '330', '--units', '8192'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    peer = None
    try:
        ready = json.loads(process.stdout.readline())
        peer = Peer(('127.0.0.1', ready['port']))
        assert peer.request(1)[0] == 0
        initial = peer.snapshot()['players'][0]
        addresses = server_addresses(process, server)
        os.kill(process.pid, signal.SIGSTOP)
        try:
            with open(f'/proc/{process.pid}/mem', 'r+b', buffering=0) as memory:
                memory.seek(addresses['sim_entities'])
                records = memory.read(8192*32)
                enemy = None
                for index in range(8192):
                    x, z, hp, side, kind, front, target, generation = struct.unpack_from('<2f4IiI', records, index*32)
                    if side == 0:
                        # Distant allied positions prevent unrelated army fire from
                        # killing the one fixture threat before player death.
                        memory.seek(addresses['sim_entities']+index*32)
                        memory.write(struct.pack('<f', 1000.0))
                    elif hp > 0 and kind == 1 and enemy is None:
                        enemy = index
                assert enemy is not None
                memory.seek(addresses['sim_entities']+enemy*32)
                memory.write(struct.pack('<2f', initial[0], initial[2]+80))
        finally:
            os.kill(process.pid, signal.SIGCONT)
        end = time.monotonic()+9
        saw_death, saw_redeploy, dead = False, False, None
        while time.monotonic() < end:
            time.sleep(0.12)
            peer.input()
            peer.receive(0.02)
            if peer.state:
                player = peer.state['players'][0]
                if player[5] == 0 and player[9] > 0:
                    saw_death, dead = True, player
                    assert player[12] == initial[12], 'fixture unexpectedly fired'
                if saw_death and player[5] > 0 and player[15] > initial[15]:
                    saw_redeploy = True
                    assert player[9] == 0 and (player[0], player[2]) != (dead[0], dead[2])
                    break
        assert saw_death and saw_redeploy, (saw_death, saw_redeploy, peer.state)
        stdout, stderr = process.communicate(timeout=12)
        assert process.returncode == 0, (stdout, stderr)
        return {'death': True, 'safe_redeployment': True, 'fixture_writes': 'entity positions only'}
    finally:
        if peer:
            peer.socket.close()
        if process.poll() is None:
            process.kill()
            process.communicate()


class FaultRelay:
    """Development-only real UDP relay: deterministic 5% drop, jitter and reorder."""
    def __init__(self, server, latency_ms=50):
        self.latency_ms = latency_ms
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('127.0.0.1', 0))
        self.socket.setblocking(False)
        self.server = server
        self.client = None
        self.running = True
        self.received = self.dropped = self.reordered = 0
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        queue = []
        while self.running:
            now = time.monotonic()
            if select.select([self.socket], [], [], 0.005)[0]:
                raw, source = self.socket.recvfrom(65536)
                self.received += 1
                if source == self.server:
                    target = self.client
                else:
                    self.client = source
                    target = self.server
                if self.received % 20 == 0:
                    self.dropped += 1
                elif target:
                    delay = max(0, self.latency_ms/1000 + ((self.received % 3)-1)*0.01)
                    if self.received % 7 == 0:
                        delay += 0.06
                        self.reordered += 1
                    queue.append((now+delay, raw, target))
            ready = [item for item in queue if item[0] <= now]
            queue = [item for item in queue if item[0] > now]
            for _, raw, target in ready:
                self.socket.sendto(raw, target)

    def close(self):
        self.running = False
        self.thread.join(timeout=1)
        assert not self.thread.is_alive()
        self.socket.close()


def verify_faults(server, latency_ms=50):
    process = subprocess.Popen([str(server), '--port', '0', '--ticks', '150', '--units', '8192'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    relay, peer = None, None
    try:
        ready = json.loads(process.stdout.readline())
        relay = FaultRelay(('127.0.0.1', ready['port']), latency_ms)
        peer = Peer(relay.socket.getsockname())
        assert peer.request(1)[0] == 0
        start = peer.snapshot()['players'][peer.id][0]
        end = time.monotonic()+2.4
        accepted = 0
        while time.monotonic() < end:
            time.sleep(0.04)
            accepted += peer.input(x=1.0)[0] == 0
        state = peer.snapshot()
        assert state['players'][peer.id][0] > start and accepted >= 3
        assert relay.dropped > 0 and relay.reordered > 0
        stdout, stderr = process.communicate(timeout=4)
        assert process.returncode == 0, (stdout, stderr)
        return {'received': relay.received, 'dropped': relay.dropped,
                'reordered': relay.reordered, 'accepted_inputs': accepted,
                'one_way_delay_ms': latency_ms, 'jitter_ms': 10}
    finally:
        if relay:
            relay.close()
        if peer:
            peer.socket.close()
        if process.poll() is None:
            process.kill()
            process.communicate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', type=pathlib.Path, required=True)
    parser.add_argument('--client-lib', type=pathlib.Path)
    parser.add_argument('--extended', action='store_true')
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
    extra = {}
    if args.extended:
        extra['combat'] = verify_death_redeployment(args.server.resolve())
        extra['faults'] = [verify_faults(args.server.resolve(), delay) for delay in (0, 50, 100, 150)]
    print(json.dumps({'suite': 'cooperative-world', 'passed': True, 'server': report, **extra}))


if __name__ == '__main__':
    main()
