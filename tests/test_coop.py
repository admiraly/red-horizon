#!/usr/bin/env python3
"""Real UDP clients verify the dedicated assembly world; no Python simulation."""
import argparse
import ctypes
import hashlib
import json
import math
import pathlib
import re
import select
import os
import signal
import threading
import socket
import struct
import subprocess
import time

MAGIC, VERSION, SCHEMA, CONTENT = 0x52484332, 39, 0x212cb081, 0x9118562d
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
        self.company_transfers = None
        self.companies = None
        self.company_tick = -1
        self.aircraft = {}
        self.air_updates = {}
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
            if self.id<4:self.front=players[self.id][10]
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
                assert 1<=event[3]<=10 and event[4]<=1 and event[5]<=header[7]
                self.events[event[7]]=event
        elif header[4] == 103:
            count=struct.unpack_from('<I',raw,40)[0]
            assert count<=18 and len(raw)==44+count*64
            for offset in range(44,len(raw),64):
                index=struct.unpack_from('<I',raw,offset)[0]
                entity=struct.unpack_from('<2f6I',raw,offset+4)
                y,heading,pitch,bank,speed,role,mode=struct.unpack_from('<5fII',raw,offset+36)
                generation=entity[7]
                assert index<32768 and generation>0 and entity[4]==3 and 0<=entity[2]<=200
                assert entity[3]<=1 and entity[5]<=2 and all(map(math.isfinite,(*entity[:2],y,heading,pitch,bank,speed)))
                assert all(0<=v<=8000 for v in entity[:2]) and -100<=y<=1200
                assert abs(heading)<=6.4 and abs(pitch)<=1.6 and abs(bank)<=1.6
                assert 0<=speed<=10 and role<=1 and mode<=3
                self.air_updates.setdefault(index,[]).append((header[7],entity[0],entity[1],speed,generation))
                self.entities[index]=entity
                self.aircraft[index]=(generation,y,heading,pitch,bank,speed,role,mode)
        elif header[4] == 107:
            assert len(raw)==396 and struct.unpack_from('<I',raw,40)[0]==4
            records=[struct.unpack_from('<6I2f2I',raw,44+i*40) for i in range(4)]
            assert [r[0] for r in records]==list(range(4))
            if header[7]>self.company_tick:
                self.company_transfers=[struct.unpack_from('<12I',raw,204+i*48)for i in range(4)]
                self.companies=records
                self.company_tick=header[7]
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
        assert ready['units'] == 8192 and ready['protocol'] == VERSION
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
        bad_status, budget_before, budget_tick = a.input(buttons=128)
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
        assert d.command(4, struct.pack('<IIff', d.front, 0, 3500, 1300))[0] == 0
        assert d.command(4, struct.pack('<IIff', 1, 0, 3500, 1300))[0] == 5
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
        assert report['aircraft_records'] > 0, 'actual server never sent aircraft state'
        assert any(peer.aircraft for peer in peers), 'no real aircraft packets received'
        moved_air = 0
        for peer in peers:
            for updates in peer.air_updates.values():
                for before,after in zip(updates,updates[1:]):
                    dt=after[0]-before[0]
                    if dt<=0 or before[4]!=after[4]:
                        continue
                    distance=math.hypot(after[1]-before[1],after[2]-before[2])
                    assert distance <= max(before[3],after[3])*dt+1., 'air64 X/Z violates flight speed bound'
                    moved_air += distance>1.
        assert moved_air>0, 'actual air64 snapshots never refreshed moving X/Z'
        report['air_xz_refreshes_verified']=moved_air

        for peer in peers:
            for index, air in peer.aircraft.items():
                entity=peer.entities.get(index)
                assert entity is not None and entity[4]==3 and entity[7]==air[0]
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
        air_bytes = (ctypes.c_ubyte * (32768*64)).in_dll(lib, 'sim_aircraft')
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
        replicated_air = 0
        for index in range(8192):
            flags=struct.unpack_from('<I',air_bytes,index*64+60)[0]
            if not flags:
                continue
            generation=struct.unpack_from('<I',air_bytes,index*64+40)[0]
            entity=struct.unpack_from('<2f6I',entity_bytes,index*32)
            assert entity[4]==3 and entity[7]==generation
            y,heading,pitch,bank,speed,role,mode=struct.unpack_from('<5fII',air_bytes,index*64)
            assert all(map(math.isfinite,(y,heading,pitch,bank,speed)))
            assert speed in (5.,7.) and role<=1 and mode<=3
            replicated_air += 1
        assert replicated_air>0, 'assembly adapter never applied actual aircraft sidecars'
        stdout, stderr = process.communicate(timeout=3)
        assert process.returncode == 0, (stdout, stderr)
        # Drain the completed server's final snapshots before testing no local ticks.
        # Each poll keeps its32-packet budget; new self-contained streams may leave
        # more than32 datagrams queued after the stopped60-tick server exits.
        final_tick=json.loads(stdout.strip().splitlines()[-1])['ticks']
        for _ in range(16):
            lib.net_client_poll()
            if ctypes.c_uint.in_dll(lib,'net_server_tick').value==final_tick:break
        server_tick = ctypes.c_uint.in_dll(lib, 'net_server_tick').value
        local_tick = ctypes.c_uint.in_dll(lib, 'sim_tick_count').value
        assert server_tick==final_tick,'completed server final snapshots not received'
        for _ in range(4):
            lib.net_client_poll()
        assert ctypes.c_uint.in_dll(lib, 'sim_tick_count').value == local_tick == server_tick
        lib.net_client_close()
    finally:
        lib.net_client_close()
        if process.poll() is None:
            process.kill()
            process.communicate()


def verify_fourth_adapter(server, library):
    # Three actual UDP joins reserve slots0..2; the production NASM adapter is
    # the fourth player and must submit/receive an accepted own-company order.
    lib=ctypes.CDLL(str(library.resolve()))
    lib.net_client_open.argtypes=[ctypes.c_char_p,ctypes.c_uint]
    lib.net_client_order.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_float,ctypes.c_float]
    process=subprocess.Popen([str(server),'--port','0','--ticks','90','--units','8192'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    peers=[]
    try:
        ready=json.loads(process.stdout.readline());address=('127.0.0.1',ready['port'])
        for expected in range(3):
            peer=Peer(address);peers.append(peer)
            assert peer.request(1)[0]==0 and peer.id==expected
        assert lib.net_client_open(b'127.0.0.1',ready['port'])==0
        connected=ctypes.c_uint.in_dll(lib,'net_connected');pending=ctypes.c_uint.in_dll(lib,'net_pending')
        tick=ctypes.c_uint.in_dll(lib,'net_server_tick');deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            lib.net_client_poll()
            if connected.value and tick.value>=15:break
            time.sleep(.01)
        assert connected.value and ctypes.c_uint.in_dll(lib,'net_player_id').value==3
        assert ctypes.c_uint.in_dll(lib,'net_front').value==0
        assert lib.net_client_order(1,0,3900.,1400.)==-1
        assert lib.net_client_order(0,0,3900.,1400.)==0,'fourth-player adapter denied own company'
        deadline=time.monotonic()+1
        while pending.value and time.monotonic()<deadline:lib.net_client_poll();time.sleep(.01)
        assert not pending.value and ctypes.c_uint.in_dll(lib,'net_last_status').value==0
        print(json.dumps({'suite':'fourth-player-company-adapter','passed':True,'actual_player_id':3,'own_order_ACK':0,'foreign_front_rejected':True}))
    finally:
        lib.net_client_close()
        for peer in peers:peer.socket.close()
        if process.poll() is None:process.kill()
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
    return {name: base+symbols[name] for name in ('sim_entities', 'sim_players', 'sim_count', 'infantry_weapons')}


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
                memory.seek(addresses['infantry_weapons'])
                stocks = memory.read(8192*32)
                enemy = None
                for index in range(8192):
                    x, z, hp, side, kind, front, target, generation = struct.unpack_from('<2f4IiI', records, index*32)
                    if side == 0:
                        # Translate the formation intact: unrelated allied fire
                        # cannot kill the fixture threat, and rear deployment
                        # sites stay clear of bodies instead of stacking an army
                        # on every fallback site.
                        memory.seek(addresses['sim_entities']+index*32)
                        memory.write(struct.pack('<f', x-1800.0))
                    elif hp > 0 and kind == 0 and enemy is None:
                        stock = struct.unpack_from('<8I', stocks, index*32)
                        if stock[0] == generation and stock[1]+stock[2] >= 10:
                            enemy = index
                            initial_stock = stock
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
        return {'death': True, 'safe_redeployment': True, 'fixture_writes': 'entity positions only', 'actual_infantry_id': enemy, 'initial_finite_weapon': initial_stock, 'HP_kind_generation_stores_preserved': True}
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
        self.hold_acks = False  # Explicit graphical queue fixture; default faults unchanged.
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
            held_acks=self.hold_acks
            def deliverable(item):
                return item[0]<=now and not(held_acks and len(item[1])>=HEADER.size and HEADER.unpack_from(item[1])[4]==2)
            ready = [item for item in queue if deliverable(item)]
            queue = [item for item in queue if not deliverable(item)]
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
    # Compatibility includes assets, canonical roads and resolved hull policy.
    # Reconstruct it independently of the build-time fingerprint tool.
    definitions = dict(re.findall(r'^%define ([A-Z_]+) ([-+A-Za-z0-9_.]+)$',
        (root/'schemas/infantry_aim.inc').read_text()+'\n'+(root/'schemas/player_blast.inc').read_text()+'\n'+(root/'schemas/player_ammunition.inc').read_text()+'\n'+(root/'schemas/infantry_supply_route.inc').read_text()+'\n'+(root/'schemas/depot_supply.inc').read_text()+'\n'+(root/'schemas/company_supply.inc').read_text()+'\n'+(root/'schemas/depot_ammunition.inc').read_text()+'\n'+(root/'schemas/infantry_weapon.inc').read_text()+'\n'+(root/'schemas/company_transfer.inc').read_text()+'\n'+(root/'schemas/company_remote.inc').read_text()+'\n'+(root/'schemas/company_control.inc').read_text()+'\n'+(root/'schemas/air_crash.inc').read_text()+'\n'+(root/'schemas/air_recovery.inc').read_text()+'\n'+(root/'schemas/air_observation.inc').read_text()+'\n'+(root/'schemas/air_evasion.inc').read_text()+'\n'+(root/'schemas/air_flight.inc').read_text()+'\n'+(root/'schemas/air_escort.inc').read_text()+'\n'+(root/'schemas/acquisition.inc').read_text()+'\n'+(root/'schemas/company_assault.inc').read_text()+'\n'+(root / 'schemas/player.inc').read_text() + '\n' + (root / 'schemas/world_body.inc').read_text() + '\n' + (root / 'schemas/wreck_nav.inc').read_text() + '\n' + (root / 'schemas/projectile_remote.inc').read_text() + '\n' + (root / 'schemas/aircraft.inc').read_text() + '\n' + (root / 'schemas/ground_surfaces.inc').read_text() + '\n' +
        (root / 'schemas/terrain_body.inc').read_text() + '\n' +
        (root / 'schemas/terrain_grade.inc').read_text() + '\n' +
        (root / 'schemas/ground_support.inc').read_text() + '\n' +
        (root / 'schemas/ground_contact.inc').read_text() + '\n' +
        (root / 'schemas/suspension.inc').read_text() + '\n' +
        (root / 'schemas/ground_visual.inc').read_text() + '\n' +
        (root / 'schemas/ground_eye.inc').read_text() + '\n' +
        (root / 'schemas/wreck.inc').read_text() + '\n' + (root / 'schemas/wreck_remote.inc').read_text() + '\n' + (root / 'schemas/shell_contact.inc').read_text() + '\n' + (root / 'schemas/world_contact.inc').read_text() + '\n' + (root / 'schemas/world_los.inc').read_text() + '\n' + (root / 'schemas/terrain_ground_query.inc').read_text() + '\n' + (root / 'schemas/terrain_height.inc').read_text(), re.M))
    policy = {}
    for name in ('GROUND_SURFACE_VERSION', 'GROUND_TANK_OFFROAD',
                 'GROUND_ARTILLERY_OFFROAD', 'GROUND_TANK_RADIUS',
                 'GROUND_ARTILLERY_RADIUS'):
        value, seen = definitions[name], {name}
        while value in definitions:
            assert value not in seen, 'Circular ground policy'
            seen.add(value)
            value = definitions[value]
        policy[name] = value
    payload = {
        'previous_content': hashlib.sha256(
            (root / 'content/asset-manifest.json').read_bytes()).hexdigest()[:8],
        'terrain_surface_abi': 1,
        'roads': json.loads((root / 'content/terrain/roads.json').read_text()),
        'tracked_policy': policy,
    }
    payload.update(air_crash={name:definitions[name] for name in ('AIR_CRASH_VERSION','AIR_CRASH_CAPACITY','AIR_CRASH_STRIDE','AIR_CRASH_LIFETIME','AIR_CRASH_PITCH_RATE','AIR_CRASH_BANK_RATE','AIR_CRASH_PITCH_FLOOR')})
    payload.update(air_recovery={name:definitions[name] for name in ('AIR_RECOVERY_VERSION','AIR_RECOVERY_CRITICAL_HP','AIR_RECOVERY_HOME_X','AIR_RECOVERY_FRONT_SPACING')})
    payload.update(air_observation={name:definitions[name] for name in ('AIR_OBSERVATION_VERSION', 'AIR_OBSERVATION_STRIDE', 'AIR_OBSERVATION_RANGE_SQ', 'AIR_OBSERVATION_REAR_COS_SQ', 'AIR_OBSERVATION_MAX_AGE', 'AIR_OBSERVATION_PREDICT_TICKS')},air_evasion={name:definitions[name] for name in ('AIR_EVADE_VERSION', 'AIR_EVADE_RANGE_SQ', 'AIR_EVADE_VIEW_COS_SQ', 'AIR_EVADE_PREDICT_TICKS', 'AIR_EVADE_MISS_SQ', 'AIR_EVADE_CANDIDATES', 'AIR_EVADE_LOS_CALLS', 'AIR_EVADE_CELL_RADIUS')},infantry_aim={name:definitions[name] for name in ('INFANTRY_AIM_VERSION','INFANTRY_AIM_STRIDE','INFANTRY_AIM_MAX_AGE','INFANTRY_AIM_REMOTE_MAX_AGE','INFANTRY_AIM_WIRE_STRIDE','INFANTRY_AIM_WIRE_MAX')},player_blast={name:definitions[name] for name in ('PLAYER_BLAST_VERSION','PLAYER_BLAST_MAX_DAMAGE','PLAYER_BLAST_MAX_RADIUS','PLAYER_BLAST_MAX_Y','PLAYER_BLAST_SUPPRESSION')},player_ammunition={name:definitions[name] for name in ('PLAYER_AMMUNITION_VERSION', 'PLAYER_AMMUNITION_REPORT_VERSION', 'PLAYER_AMMUNITION_REPORT_BYTES', 'PLAYER_AMMUNITION_REPORT_MAX_AGE', 'PLAYER_AMMUNITION_KNOWN', 'PLAYER_AMMUNITION_STRIDE', 'PLAYER_AMMUNITION_MAGAZINE', 'PLAYER_AMMUNITION_RESERVE', 'PLAYER_AMMUNITION_INITIAL', 'PLAYER_AMMUNITION_RELOAD_TICKS', 'PLAYER_AMMUNITION_RECEIVED_LIMIT', 'PLAYER_AMMUNITION_SUPPLY_PERIOD', 'PLAYER_AMMUNITION_SUPPLY_RADIUS_SQ')},infantry_supply_route={name:definitions[name] for name in ('INFANTRY_SUPPLY_ROUTE_VERSION','INFANTRY_SUPPLY_ROUTE_LOW','INFANTRY_SUPPLY_ROUTE_RADIUS_SQ','INFANTRY_SUPPLY_ROUTE_COHORTS','INFANTRY_SUPPLY_ROUTE_SLOTS')},depot_supply={name:definitions[name] for name in ('DEPOT_SUPPLY_VERSION','DEPOT_SUPPLY_HEADER','DEPOT_SUPPLY_RECORD','DEPOT_SUPPLY_COUNT','DEPOT_SUPPLY_BYTES','DEPOT_SUPPLY_MAX_AGE','DEPOT_SUPPLY_KNOWN','DEPOT_SUPPLY_CONNECTED','DEPOT_SUPPLY_CONTESTED','DEPOT_SUPPLY_DESTROYED','DEPOT_SUPPLY_AVAILABLE')},company_supply={name:definitions[name] for name in ('COMPANY_SUPPLY_VERSION','COMPANY_SUPPLY_STRIDE','COMPANY_SUPPLY_LOW_ROUNDS','COMPANY_SUPPLY_MAX_AGE')},depot_ammunition={name:definitions[name] for name in ('DEPOT_AMMUNITION_VERSION','DEPOT_AMMUNITION_SITES','DEPOT_AMMUNITION_STRIDE','DEPOT_AMMUNITION_INITIAL','DEPOT_AMMUNITION_MAX_TAKE')},infantry_weapon={name:definitions[name] for name in ('INFANTRY_WEAPON_VERSION','INFANTRY_WEAPON_STRIDE','INFANTRY_SHOT_TICKS','INFANTRY_HUMAN_RANGE_SQ','INFANTRY_HUMAN_DAMAGE','INFANTRY_MAGAZINE','INFANTRY_RESERVE','INFANTRY_RELOAD_TICKS','INFANTRY_RECEIVED_LIMIT','INFANTRY_RESUPPLY_PERIOD','INFANTRY_RESUPPLY_RADIUS_SQ','INFANTRY_RESUPPLY_EYE')},company_transfer={name:definitions[name] for name in ('COMPANY_TRANSFER_VERSION','COMPANY_TRANSFER_PLAYERS','COMPANY_TRANSFER_STRIDE','COMPANY_TRANSFER_LIFETIME')},company_remote={name:definitions[name] for name in ('COMPANY_REMOTE_VERSION','COMPANY_REMOTE_COUNT','COMPANY_REMOTE_STRIDE','COMPANY_REMOTE_KEY_LIMIT')},company_control={name:definitions[name] for name in ('COMPANY_CONTROL_VERSION','COMPANY_CONTROL_SLOTS','COMPANY_CONTROL_STRIDE','COMPANY_CONTROL_PLAYERS','COMPANY_CONTROL_COST','COMPANY_CONTROL_MAX_MODE','COMPANY_FOLLOW_SPACING','COMPANY_FOLLOW_TRAIL','COMPANY_FOLLOW_MARGIN','COMPANY_FOLLOW_MAX_ANCHOR','COMPANY_FOLLOW_PROJECT_TRIES','COMPANY_FOLLOW_PROJECT_STEP','COMPANY_DEFEND_RADIUS','COMPANY_DEFEND_SPACING','COMPANY_DEFEND_ARTY_BACK','COMPANY_DEFEND_MARGIN','COMPANY_DEFEND_MAX_ANCHOR')},air_flight={name:definitions[name] for name in ('AIR_FLIGHT_VERSION', 'AIR_FLIGHT_GRAVITY', 'AIR_FLIGHT_MIN_SPEED', 'AIR_FLIGHT_MAX_SPEED', 'AIR_FLIGHT_VERTICAL_LIMIT', 'AIR_FLIGHT_BOMBER_VERTICAL_ACCEL', 'AIR_FLIGHT_FIGHTER_VERTICAL_ACCEL', 'AIR_FLIGHT_HEADING_GAIN', 'AIR_FLIGHT_BOMBER_BANK', 'AIR_FLIGHT_FIGHTER_BANK', 'AIR_FLIGHT_BOMBER_EMERGENCY_BANK', 'AIR_FLIGHT_FIGHTER_EMERGENCY_BANK', 'AIR_FLIGHT_BOMBER_ROLL', 'AIR_FLIGHT_FIGHTER_ROLL', 'AIR_FLIGHT_BOMBER_YAW_BOUND', 'AIR_FLIGHT_FIGHTER_YAW_BOUND', 'AIR_FLIGHT_CORNER_MARGIN', 'AIR_FLIGHT_STRIKE_MEMORY', 'AIR_FLIGHT_STRIKE_STRIDE', 'AIR_FLIGHT_STRIKE_APPROACH', 'AIR_FLIGHT_STRIKE_REACHED_SQ')},air_escort={name:definitions[name] for name in ('AIR_ESCORT_VERSION', 'AIR_ACQUIRE_VERSION', 'AIR_ACQUIRE_CELLS', 'AIR_ESCORT_REVIEW', 'AIR_ESCORT_COMMITMENT', 'AIR_ESCORT_RANGE_SQUARED', 'AIR_ESCORT_BREAK_SQUARED', 'AIR_ESCORT_THREAT_SQUARED', 'AIR_ESCORT_TRAIL_TICKS', 'AIR_ESCORT_LATERAL', 'AIR_ESCORT_THREAT_WEIGHT')},acquisition={name:definitions[name] for name in ('ACQUIRE_VERSION','ACQUIRE_INF_CELLS','ACQUIRE_TANK_CELLS','ACQUIRE_ARTY_CELLS')},company_assault={name:definitions[name] for name in ('COMPANY_ASSAULT_VERSION', 'COMPANY_SLOTS', 'COMPANY_STRIDE', 'COMPANY_MIN_GROUND', 'COMPANY_NEAR_SQ', 'COMPANY_STAGE_DISTANCE', 'COMPANY_ARTY_BACK', 'COMPANY_ARMOUR_FORWARD', 'COMPANY_READY_SQ', 'COMPANY_STAGE_TIMEOUT', 'COMPANY_PREP_TIMEOUT', 'COMPANY_LOSS_PERCENT', 'COMPANY_INF_SPACING', 'COMPANY_INF_ROW', 'COMPANY_HULL_ROW', 'COMPANY_INF_LANE', 'COMPANY_ARMOUR_LANE', 'COMPANY_ARTY_LANE', 'COMPANY_WITHDRAW_DISTANCE')},player_deploy={name:definitions[name] for name in ('PLAYER_DEPLOY_POLICY_VERSION',)},world_body={name:definitions[name] for name in ('WORLD_BODY_VERSION',)},wreck_navigation={name:definitions[name] for name in ('WRECK_NAV_VERSION', 'WRECK_NAV_QUEUE', 'WRECK_NAV_BUILDS_PER_TICK', 'WRECK_NAV_LOOKAHEAD', 'WRECK_NAV_PLAN_DISTANCE', 'WRECK_NAV_ENDPOINT_INCREMENT', 'WRECK_NAV_ENDPOINT_MAX_DISTANCE', 'WRECK_NAV_LOOKAHEAD_SQUARED', 'WRECK_NAV_PLAN_DISTANCE_SQUARED', 'WRECK_NAV_MAX_WRECKS', 'WRECK_NAV_MAX_NODES', 'WRECK_NAV_MAX_PATH', 'WRECK_NAV_WINDOW_MARGIN', 'WRECK_NAV_CORNER_MARGIN', 'WRECK_NAV_MAX_LEG_SQUARED', 'WRECK_NAV_GOAL_CHANGE_SQUARED', 'WRECK_NAV_REACHED_SQUARED', 'WRECK_NAV_SOURCE_DISTANCE_WEIGHT')},projectile_remote={name:definitions[name] for name in ('PROJECTILE_REMOTE_POLICY_VERSION','PROJECTILE_OWNED_PRIORITY_MAX','PROJECTILE_WIRE_MAX')},bomb_release={name:definitions[name] for name in ('AIR_BOMB_RELEASE_VERSION',)},world_los={name:definitions[name] for name in ('WORLD_LOS_VERSION',)},world_contact={name:definitions[name] for name in ('WORLD_CONTACT_VERSION', 'WORLD_CONTACT_GROUND', 'WORLD_CONTACT_SOLID', 'WORLD_CONTACT_WRECK', 'WORLD_CONTACT_ACTOR', 'WORLD_CONTACT_BLAST_SKIN', 'TERRAIN_GROUND_QUERY_VERSION', 'TERRAIN_GROUND_QUERY_SKIN', 'TERRAIN_HEIGHT_CENTER', 'TERRAIN_HEIGHT_X_SCALE', 'TERRAIN_HEIGHT_Z_SCALE', 'TERRAIN_HEIGHT_RIDGE_SCALE', 'TERRAIN_HEIGHT_RIDGE_HEIGHT', 'TERRAIN_HEIGHT_BASE')},shell_contact={name:definitions[name] for name in ('SHELL_CONTACT_VERSION','SHELL_CONTACT_RADIUS','SHELL_CONTACT_MAX_SAMPLES')},wreck_presentation={name:definitions[name] for name in ('WRECK_REMOTE_VERSION','WRECK_WIRE_STRIDE','WRECK_WIRE_MAX','WRECK_PRESENTATION_VERSION','WRECK_PRESENTATION_FRAME','WRECK_PRESENTATION_LOD')},wreck_registry={name:definitions[name] for name in ('WRECK_VERSION','WRECK_CAPACITY','WRECK_LIFETIME_TICKS')},ground_eye={name:definitions[name] for name in ('EYE_VERSION','EYE_LOCAL_HEIGHT')},ground_visual={name:definitions[name] for name in ('CONTACT_VERSION','SUSPENSION_VERSION','SUSPENSION_Y_OMEGA','SUSPENSION_PITCH_OMEGA','SUSPENSION_BANK_OMEGA','SUSPENSION_Y_LIMIT','SUSPENSION_ANGLE_LIMIT','SUSPENSION_Y_VELOCITY_LIMIT','SUSPENSION_ANGLE_VELOCITY_LIMIT','VISUAL_VERSION','VISUAL_MAX_DT','VISUAL_JUMP_SQ')},
        relief_abi=1,grade_abi=1,
        relief=json.loads((root/'content/terrain/relief.json').read_text()),
        grade_policy={name:definitions[name] for name in ('TERRAIN_GRADE_VERSION','GRADE_INF_LIMIT_SQ','GRADE_TANK_LIMIT_SQ','GRADE_ARTY_LIMIT_SQ','GRADE_GUARD_SQ','GRADE_BASE_X','GRADE_BASE_Z','BODY_INF_SWEEP_RADIUS','BODY_TANK_SWEEP_RADIUS','BODY_ARTY_SWEEP_RADIUS')},
        render_patch={'x':[5375,5875],'z':[4750,5625],'spacing':5,'max_height_error':0.027,'route_margin':6,'node_limit':27},
        ground_support={name:definitions[name] for name in ('SUPPORT_VERSION','SUPPORT_TANK_HALF_WIDTH','SUPPORT_TANK_HALF_LENGTH','SUPPORT_TANK_CENTER_Z','SUPPORT_ARTY_HALF_WIDTH','SUPPORT_ARTY_HALF_LENGTH','SUPPORT_ARTY_CENTER_Z')})
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    assert int(hashlib.sha256(encoded).hexdigest()[:8], 16) == CONTENT
    constants = (root / "src/net/protocol.inc").read_text()
    assert f"%define NET_SCHEMA 0x{SCHEMA:08x}" in constants
    assert f"%define NET_CONTENT 0x{CONTENT:08x}" in constants
    report = verify(args.server.resolve())
    if args.client_lib:
        verify_adapter(args.server.resolve(), args.client_lib)
        verify_fourth_adapter(args.server.resolve(), args.client_lib)
    extra = {}
    if args.extended:
        extra['combat'] = verify_death_redeployment(args.server.resolve())
        extra['faults'] = [verify_faults(args.server.resolve(), delay) for delay in (0, 50, 100, 150)]
    print(json.dumps({'suite': 'cooperative-world', 'passed': True, 'server': report, **extra}))


if __name__ == '__main__':
    main()
