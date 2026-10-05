#!/usr/bin/env python3
"""Real authoritative vehicle input and cosmetic events over UDP.
Fixtures move actors in this test's own paused server; never write health/ammo.
"""
import ctypes as C
import json
import os
import pathlib
import signal
import struct
import subprocess
import sys
import time
from test_coop import Peer, server_addresses, VERSION

server, library = (pathlib.Path(p).resolve() for p in sys.argv[1:3])
lib=C.CDLL(str(library))
lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
lib.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
for name in ('net_client_open','net_client_poll','net_client_input'):
    getattr(lib,name).restype=C.c_int
host=subprocess.Popen([str(server),'--port','0','--units','128'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
peer=None; memory=None
try:
    ready=json.loads(host.stdout.readline());assert ready['protocol']==VERSION
    peer=Peer(('127.0.0.1',ready['port']));assert peer.request(1)[0]==0
    assert lib.net_client_open(b'127.0.0.1',ready['port'])==0
    connected=C.c_uint.in_dll(lib,'net_connected')
    remote=(C.c_ubyte*128).in_dll(lib,'sim_vehicles')
    mapping=(C.c_int*4).in_dll(lib,'sim_player_vehicle')
    events=(C.c_ubyte*(256*32)).in_dll(lib,'sim_events')
    sequence=C.c_uint.in_dll(lib,'sim_event_sequence')
    addresses=server_addresses(host,server)
    memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
    def pump(seconds=.12,buttons=0,x=0,z=0):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            lib.net_client_poll()
            if connected.value:lib.net_client_input(0,0,0,0,0,0)
            time.sleep(.02)
        assert peer.input(buttons,x,z)[0]==0
        peer.receive(.02)
        lib.net_client_poll()
    def until(predicate,seconds=4,buttons=0,x=0,z=0):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            pump(.07,buttons,x,z)
            value=predicate()
            if value:return value
        raise AssertionError(('timeout',peer.state))
    until(lambda:connected.value and peer.state)
    assert C.c_uint.in_dll(lib,'net_player_id').value==1
    p=peer.state['players'][0];x,z=p[0],p[2]
    os.kill(host.pid,signal.SIGSTOP)
    try:
        data=os.pread(memory,128*32,addresses['sim_entities'])
        armor=next(i for i in range(128) if struct.unpack_from('<I',data,i*32+12)[0]==0 and struct.unpack_from('<I',data,i*32+16)[0]==1)
        for i in range(128):
            side=struct.unpack_from('<I',data,i*32+12)[0]
            os.pwrite(memory,struct.pack('<2f',1000.0 if side==0 else 7000.0,2000.0),addresses['sim_entities']+i*32)
        os.pwrite(memory,struct.pack('<2f',x+2,z),addresses['sim_entities']+armor*32)
        # Second human remains within8m boarding range, with clear hull/body
        # separation beside the lane rather than2m inside the driven tank.
        # Only positions are fixtures; ownership/damage/ammo stay authoritative.
        os.pwrite(memory,struct.pack('<f',x+2),addresses['sim_players']+64)
        os.pwrite(memory,struct.pack('<f',z+6),addresses['sim_players']+64+8)
    finally:os.kill(host.pid,signal.SIGCONT)
    until(lambda:peer.state['player_vehicle'][0]==armor,buttons=8)
    until(lambda:mapping[0]==armor and struct.unpack_from('<8I',remote,0)[3]==1)
    # Other player's valid ENTER intent cannot steal occupied armor.
    deadline=time.monotonic()+2
    pending=C.c_uint.in_dll(lib,'net_pending')
    while pending.value and time.monotonic()<deadline:
        lib.net_client_poll();time.sleep(.01)
    assert pending.value==0
    time.sleep(.05)
    assert lib.net_client_input(0,8,0,0,0,0)==0,'ownership fixture failed to queue ENTER'
    while pending.value and time.monotonic()<deadline:
        lib.net_client_poll();time.sleep(.01)
    assert pending.value==0 and C.c_uint.in_dll(lib,'net_last_status').value==0,'ENTER was not acknowledged'
    pump(.3)
    assert mapping[1]==-1 and mapping[0]==armor
    start=peer.state['players'][0][0]
    pump(.45,x=1)
    until(lambda:peer.state['players'][0][0]>start+1,seconds=2,x=1)
    # Place a living opposing infantry body in the cannon's real swept path.
    pump(.12)
    p=peer.state['players'][0]
    os.kill(host.pid,signal.SIGSTOP)
    try:os.pwrite(memory,struct.pack('<2f',p[0],p[2]+250),addresses['sim_entities']+64*32)
    finally:os.kill(host.pid,signal.SIGCONT)
    # Main weapon produces a real authoritative launch, not a client hit claim.
    until(lambda:any(e[3]==1 for e in peer.events.values()),seconds=5,buttons=1)
    until(lambda:any(struct.unpack_from('<3f3IfI',events,i*32)[3]==1 for i in range(256)),seconds=3)
    assert sequence.value>0
    until(lambda:any(e[3]==3 for e in peer.events.values()),seconds=6)
    until(lambda:peer.state['player_vehicle'][0]==-1,buttons=16)
    until(lambda:mapping[0]==-1)
    assert peer.max_packet<=1200
    print(json.dumps({'suite':'co-op-combat','passed':True,'board_drive_fire_exit':True,'exclusive_ownership':True,'replicated_launch_and_impact':True,'assembly_adapter_events':True,'max_packet':peer.max_packet,'fixture_writes':'positions only; own server'}))
finally:
    lib.net_client_close()
    if peer:peer.socket.close()
    if memory is not None:os.close(memory)
    if host.poll() is None:
        os.kill(host.pid,signal.SIGCONT);host.terminate()
    try:host.communicate(timeout=3)
    except subprocess.TimeoutExpired:host.kill();host.communicate()
