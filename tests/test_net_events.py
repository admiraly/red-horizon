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
    def send(kind,payload,tick=10,session=1,player=0):
        s.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,player,1 if kind==2 else 0,tick,len(payload),session)+payload,address)
        return lib.net_client_poll()
    send(2,struct.pack('<4I',0,0,128,100))
    assert C.c_uint.in_dll(lib,'net_connected').value==1 and seq.value==0
    def event(n,x=3800.0,y=20.0,z=1300.0,kind=3,side=0,tick=5,radius=12.0):
        return struct.pack('<3f3IfI',x,y,z,kind,side,tick,radius,n)
    def packet(*records):return struct.pack('<I',len(records))+b''.join(records)
    initial=bytes(ring)
    bad=[packet(event(1,x=float('nan'))),packet(event(1,y=float('inf'))),
         packet(event(1,z=-1)),packet(event(1,kind=11)),packet(event(1,side=2)),
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
    # Self-contained aircraft packets exercise actual entity and sidecar arrays.
    aircraft=(C.c_ubyte*(32768*64)).in_dll(lib,'sim_aircraft')
    entities=(C.c_ubyte*(32768*32)).in_dll(lib,'sim_entities')
    def air(index=12,generation=5,x=100.,z=100.,hp=120,side=0,kind=3,front=0,target=-1,
            y=130.0,heading=.3,pitch=.05,bank=.7,speed=7.0,role=1,mode=1):
        return struct.pack('<I2f4IiI5fII',index,x,z,hp,side,kind,front,target,generation,
                           y,heading,pitch,bank,speed,role,mode)
    def entity(index=12,generation=5,kind=3):
        return struct.pack('<I2f6I',index,100.,100.,120,0,kind,0,0xffffffff,generation)
    air_before=bytes(aircraft);entity_before=bytes(entities)
    bad_air=[packet(air(y=float('nan'))),packet(air(speed=float('inf'))),
             packet(air(heading=float('nan'))),packet(air(pitch=float('inf'))),
             packet(air(bank=float('nan'))),packet(air(x=float('nan'))),
             packet(air(z=float('inf'))),packet(air(x=-1)),packet(air(z=8001)),
             packet(air(hp=201)),packet(air(side=2)),
             packet(air(kind=0)),packet(air(front=3)),packet(air(target=-2)),
             packet(air(target=128)),packet(air(index=128)),packet(air(generation=0)),
             packet(air(y=-101)),packet(air(y=1201)),packet(air(heading=6.5)),
             packet(air(pitch=1.7)),packet(air(bank=-1.7)),packet(air(speed=-1)),
             packet(air(speed=11)),packet(air(role=2)),packet(air(mode=4)),
             struct.pack('<I',19)+air()*19,struct.pack('<I',1),
             packet(air(),air(index=13,role=2)),packet(air(),air(index=128)),
             packet(air(),air(index=13,x=float('nan'))),packet(air(),air(index=13,hp=201))]
    for data in bad_air:
        send(103,data,13)
        assert bytes(aircraft)==air_before and bytes(entities)==entity_before, 'malformed air64 packet partially applied'
    # Unknown aircraft warm up solely from type103; no entity101 chunk needed.
    send(103,packet(*([air()]*18)),14)
    assert bytes(entities[12*32:13*32])==air()[4:36]
    expected=struct.pack('<5fII',130.,.3,.05,.7,7.,1,1)
    assert bytes(aircraft[12*64:12*64+28])==expected
    assert struct.unpack_from('<I',aircraft,12*64+40)[0]==5
    assert struct.unpack_from('<I',aircraft,12*64+60)[0]==1
    # Successive type103-only snapshots refresh X/Z and pose together.
    send(103,packet(air(x=121.,z=105.,heading=.4)),17)
    assert bytes(entities[12*32:13*32])==air(x=121.,z=105.,heading=.4)[4:36]
    accepted=bytes(aircraft);accepted_entities=bytes(entities)
    for data,tick in [(packet(air(x=200)),16),(packet(air(generation=4)),18)]:
        send(103,data,tick)
        assert bytes(aircraft)==accepted and bytes(entities)==accepted_entities,'stale aircraft applied'
    send(103,packet(air(y=180)),18,session=2)
    send(103,packet(air(y=180)),18,player=1)
    assert bytes(aircraft)==accepted and bytes(entities)==accepted_entities,'unmatched session/player aircraft applied'
    # A newer generation replaces a stale known entity and keeps both arrays coherent.
    send(103,packet(air(generation=6,x=128)),18)
    assert struct.unpack_from('<I',entities,12*32+28)[0]==6
    assert struct.unpack_from('<I',aircraft,12*64+40)[0]==6
    accepted=bytes(aircraft);accepted_entities=bytes(entities)
    send(103,packet(air(generation=5,x=300)),19)
    assert bytes(aircraft)==accepted and bytes(entities)==accepted_entities
    # Same-generation known ground actor never changes kind from an air packet.
    send(101,packet(entity(index=14,kind=0)),18)
    accepted_entities=bytes(entities)
    send(103,packet(air(index=14)),19)
    assert bytes(aircraft)==accepted and bytes(entities)==accepted_entities
    send(101,packet(entity(generation=6)),20)
    accepted_entities=bytes(entities)
    send(103,packet(air(generation=6,y=150)),19)
    assert bytes(aircraft)==accepted and bytes(entities)==accepted_entities,'pose older than entity chunk applied'
    # Death is self-contained; an older/same-tick sparse packet cannot resurrect it.
    send(103,packet(air(generation=6,hp=0)),22)
    assert struct.unpack_from('<I',entities,12*32+8)[0]==0
    assert struct.unpack_from('<I',aircraft,12*64+60)[0]==0
    dead_entities=bytes(entities);dead_aircraft=bytes(aircraft)
    send(101,packet(entity(generation=6)),22)
    send(103,packet(air(generation=6)),21)
    assert bytes(entities)==dead_entities and bytes(aircraft)==dead_aircraft,'stale/same-tick packet resurrected dead aircraft'
    # Expanded actual-air events preserve whole-packet validation and dedup.
    send(102,packet(event(259,kind=6,tick=14),event(260,kind=7,tick=14),
                    event(261,kind=8,tick=14),event(262,kind=9,tick=14)),16)
    assert seq.value==262
    rifle=event(263,kind=10,tick=14,radius=.25)
    send(102,packet(rifle),16)
    assert seq.value==263 and bytes(ring[224:256])==rifle
    before=bytes(ring);send(102,packet(rifle),16)
    assert bytes(ring)==before and seq.value==263,'NPC rifle packet replayed'
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
    send(100,payload,23)
    assert C.c_uint.in_dll(lib,'sim_tick_count').value==23,'malformed snapshot changed stale-tick guard'
    print(json.dumps({'suite':'network-events','passed':True,'malformed_cases':len(bad)+len(bad_air)+3,'whole_packet_validation':True,'deduplication':True,'pool_wrap':True,'vehicle_state_validation':True,'aircraft_whole_packet_validation':True,'aircraft_generation_and_reordering':True,'aircraft_independent_warmup_and_xz':True,'fixtures':'wire payloads; real assembly adapter'}))
finally:
    lib.net_client_close();s.close()
