#!/usr/bin/env python3
"""Wire fixtures exercise the real assembly adapter's bounded cosmetic parser."""
import ctypes as C
import json
import pathlib
import socket
import struct
import sys
from test_coop import HEADER, MAGIC, VERSION, SCHEMA, CONTENT
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()))
lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
lib.net_client_poll.restype=C.c_int
seq=C.c_uint.in_dll(lib,'sim_event_sequence')
ring=(C.c_ubyte*(256*32)).in_dll(lib,'sim_events')
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));s.settimeout(1)
try:
    assert lib.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
    join,address=s.recvfrom(1200)
    def send(kind,payload,tick=10):
        s.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(payload),1)+payload,address)
        return lib.net_client_poll()
    send(2,struct.pack('<4I',0,0,128,100))
    assert C.c_uint.in_dll(lib,'net_connected').value==1 and seq.value==0
    def event(n,x=3800.0,y=20.0,z=1300.0,kind=3,side=0,tick=5,radius=12.0):
        return struct.pack('<3f3IfI',x,y,z,kind,side,tick,radius,n)
    def packet(*records):return struct.pack('<I',len(records))+b''.join(records)
    initial=bytes(ring)
    bad=[packet(event(1,x=float('nan'))),packet(event(1,y=float('inf'))),
         packet(event(1,z=-1)),packet(event(1,kind=6)),packet(event(1,side=2)),
         packet(event(1,tick=11)),packet(event(1,radius=-1)),packet(event(0)),
         packet(event(2),event(1)),packet(event(1),event(2,radius=float('nan'))),
         struct.pack('<I',33)+event(1)*33,struct.pack('<I',1)]
    for data in bad:
        send(102,data)
        assert seq.value==0 and bytes(ring)==initial,'malformed packet partially published'
    send(102,packet(event(1),event(2,kind=4)))
    assert seq.value==2 and bytes(ring[32:64])==event(1) and bytes(ring[64:96])==event(2,kind=4)
    before=bytes(ring);send(102,packet(event(1),event(2,kind=4)))
    assert seq.value==2 and bytes(ring)==before,'duplicate ring event reapplied'
    send(102,packet(event(258,kind=5)))
    assert seq.value==258 and C.c_uint.in_dll(lib,'sim_event_count').value==1
    assert bytes(ring[64:96])==event(258,kind=5),'bounded wrap slot incorrect'
    # A malformed high-tick vehicle snapshot cannot suppress a later valid one.
    players=bytes((C.c_ubyte*256).in_dll(lib,'sim_players'))
    sites=bytes((C.c_ubyte*384).in_dll(lib,'sim_sites'))
    vehicles=b''.join(struct.pack('<8I',0xffffffff,0,i,0,0,0,0,0) for i in range(4))
    payload=struct.pack('<6I',128,0,100,100,600,600)+players+sites+vehicles+struct.pack('<4i',-1,-1,-1,-1)
    malformed=bytearray(payload);struct.pack_into('<i',malformed,792,0)
    send(100,malformed,50)
    malformed_operation=bytearray(payload);struct.pack_into('<I',malformed_operation,4,4)
    send(100,malformed_operation,51)
    duplicate=bytearray(payload)
    for i in range(2):
        struct.pack_into('<8I',duplicate,664+i*32,12,1,i,1,64,0,1,0)
        struct.pack_into('<i',duplicate,792+i*4,12)
    send(100,duplicate,52)
    send(100,payload,11)
    assert C.c_uint.in_dll(lib,'sim_tick_count').value==11,'malformed snapshot changed stale-tick guard'
    print(json.dumps({'suite':'network-events','passed':True,'malformed_cases':len(bad)+3,'whole_packet_validation':True,'deduplication':True,'pool_wrap':True,'vehicle_state_validation':True,'fixtures':'wire payloads; real assembly adapter'}))
finally:
    lib.net_client_close();s.close()
