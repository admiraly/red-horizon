#!/usr/bin/env python3
"""Actual assembly cosmetic parser + dedicated-server authentic bombing fixture."""
import ctypes as C, json, math, os, pathlib, signal, socket, struct, subprocess, sys, time
from test_coop import HEADER, MAGIC, VERSION, SCHEMA, CONTENT, Peer, server_addresses
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()))
lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
lib.terrain_height.argtypes=[C.c_float,C.c_float]
lib.terrain_height.restype=C.c_float
lib.net_projectiles_update.argtypes=[C.c_float]
lib.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
pool=(C.c_ubyte*(512*64)).in_dll(lib,'net_projectiles')
authority=(C.c_ubyte*(512*64)).in_dll(lib,'sim_projectiles')
count=C.c_uint.in_dll(lib,'net_projectile_count')
def batch(*rows):return struct.pack('<I',len(rows))+b''.join(rows)
def record(index=7,gen=1,active=1,kind=3,ttl=240,**changes):
    values=dict(x=2100.,y=92.,z=2000.,vx=5.,vy=0.,vz=0.,ttl=ttl,side=0,kind=kind,damage=140,radius=36.,source=15,generation=gen,active=active,source_generation=1)
    values.update(changes)
    return struct.pack('<I6f4If4I',index,*values.values())
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));s.settimeout(1)
try:
    assert lib.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
    _,address=s.recvfrom(1200)
    def send(data,tick=10,session=1,kind=104):
        s.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(data),session)+data,address)
        return lib.net_client_poll()
    send(struct.pack('<4I',0,0,64,100),kind=2)
    unchanged=bytes(authority)
    bad=[batch(record(index=512)),batch(record(gen=0)),batch(record(active=2)),batch(record(kind=0)),batch(record(kind=5)),batch(record(ttl=241)),batch(record(ttl=0)),batch(record(side=2)),batch(record(source=64)),batch(record(source_generation=0)),batch(record(x=-1)),batch(record(z=8001)),batch(record(y=2001)),batch(record(vy=float('nan'))),batch(record(vx=1001)),batch(record(radius=float('inf'))),batch(record(radius=-1)),batch(record(),record()),batch(record(),record(index=8,z=float('nan'))),struct.pack('<I',19)+record()*19,struct.pack('<I',1)]
    initial=bytes(pool)
    for row in bad:
        send(row)
        assert bytes(pool)==initial,'malformed batch partially applied'
    send(batch(record()))
    assert bytes(pool[7*64:7*64+60])==record()[4:]
    accepted=bytes(pool)
    for tick,session in ((9,1),(10,1),(11,2)):
        send(batch(record(x=2300)),tick,session)
        assert bytes(pool)==accepted,'stale/session record applied'
    lib.net_projectiles_update(.1)
    r=struct.unpack_from('<6f4If5I',pool,7*64)
    assert abs(r[0]-2115)<.001 and r[1]<92 and r[4]<0 and count.value==1
    # New generation accepts slot reuse; old generation cannot overwrite it.
    send(batch(record(gen=2,x=2500,kind=4,ttl=40)),11)
    accepted=bytes(pool);send(batch(record(gen=1,x=2400)),12)
    assert bytes(pool)==accepted
    lib.net_projectiles_update(.1)
    assert abs(struct.unpack_from('<f',pool,7*64)[0]-2515)<.001
    assert struct.unpack_from('<f',pool,7*64+4)[0]==92,'air gun gained gravity'
    # Tombstone stops it immediately; reordered live same generation cannot revive.
    send(batch(record(gen=2,active=0,kind=4,ttl=0)),13)
    accepted=bytes(pool);send(batch(record(gen=2,kind=4)),14)
    assert bytes(pool)==accepted and struct.unpack_from('<I',pool,7*64+52)[0]==0
    # Dropped death packet: wall elapsed / remaining TTL expire without authority.
    send(batch(record(index=8,ttl=2,kind=1)),15)
    lib.net_projectiles_update(.1)
    assert struct.unpack_from('<I',pool,8*64+52)[0]==0
    send(batch(record(index=9)),16)
    lib.net_projectiles_update(4.1)
    assert count.value==0
    # Delayed beyond server tick horizon rejected; tick source can be unrelated type.
    send(struct.pack('<I',0),200,kind=103)
    accepted=bytes(pool);send(batch(record(index=10)),20)
    assert bytes(pool)==accepted
    # A delayed sample within horizon still catches up to latest server tick,
    # and its remaining TTL may already have elapsed before rendering.
    send(batch(record(index=12,kind=1,ttl=240)),180)
    lib.net_projectiles_update(0.)
    assert abs(struct.unpack_from('<f',pool,12*64)[0]-2200)<.001
    send(batch(record(index=13,kind=4,ttl=10)),180)
    lib.net_projectiles_update(0.)
    assert struct.unpack_from('<I',pool,13*64+52)[0]==0
    send(batch(record(index=11)),201)
    assert any(pool)
    assert bytes(authority)==unchanged,'cosmetic trajectories mutated authority'
    lib.net_client_close();assert bytes(pool)==bytes(len(pool)) and count.value==0
    assert lib.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
    _,address=s.recvfrom(1200)
    send(struct.pack('<4I',0,0,64,100),kind=2)
    send(batch(record()),12)
    time.sleep(3.05);lib.net_client_poll()
    assert not C.c_uint.in_dll(lib,'net_connected').value and not any(pool),'disconnect ghosts'
finally:lib.net_client_close();s.close()

# Fixture places real initialized actors/poses. Launch, ammo, damage and projectile
# fields are never written; all records originate from actual server simulation.
server=pathlib.Path(sys.argv[2]).resolve()
host=subprocess.Popen([str(server),'--port','0','--units','64'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
peer=None;memory=None
try:
    ready=json.loads(host.stdout.readline());peer=Peer(('127.0.0.1',ready['port']))
    assert peer.request(1)[0]==0
    assert lib.net_client_open(b'127.0.0.1',ready['port'])==0
    deadline=time.monotonic()+2
    while not C.c_uint.in_dll(lib,'net_connected').value:
        lib.net_client_poll();time.sleep(.01);assert time.monotonic()<deadline
    addr=server_addresses(host,server)
    # Extra authority symbols retain the same ELF mapping offset as sim_entities.
    symbols={v[2]:int(v[0],16) for line in subprocess.check_output(['nm','-g','--defined-only',str(server)],text=True).splitlines() if len(v:=line.split())==3}
    base=addr['sim_entities']-symbols['sim_entities']
    addr.update({n:base+symbols[n] for n in ('sim_aircraft','sim_projectiles')})
    memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
    os.kill(host.pid,signal.SIGSTOP)
    try:
        data=os.pread(memory,64*32,addr['sim_entities'])
        assert struct.unpack_from('<I',data,15*32+16)[0]==3
        hp=struct.unpack_from('<I',data,32*32+8)[0]
        for i in range(64):
            side=struct.unpack_from('<I',data,i*32+12)[0]
            os.pwrite(memory,struct.pack('<2f',500 if side==0 else 7000,600),addr['sim_entities']+i*32)
        os.pwrite(memory,struct.pack('<2f',2000,2000),addr['sim_entities']+15*32)
        os.pwrite(memory,struct.pack('<2f',2900,2000),addr['sim_entities']+32*32)
        os.pwrite(memory,struct.pack('<2f',lib.terrain_height(2000.,2000.)+110,math.pi/2),addr['sim_aircraft']+15*64)
        for i in range(2):
            os.pwrite(memory,struct.pack('<f',2500),addr['sim_players']+i*64)
            os.pwrite(memory,struct.pack('<f',2000),addr['sim_players']+i*64+8)
    finally:os.kill(host.pid,signal.SIGCONT)
    launched=False;damaged=False;dead=False;positions=[];wire=[];adapter_samples=[];slot=None;generation=None
    deadline=time.monotonic()+9
    next_keepalive=0
    while time.monotonic()<deadline:
        lib.net_client_poll()
        lib.net_projectiles_update(.01)
        if time.monotonic()>next_keepalive:
            lib.net_client_input(0,0,0,0,0,0);peer.input();next_keepalive=time.monotonic()+.3
        row=peer.receive(.01)
        if row and row[0][4]==104:
            header,data=row
            n=struct.unpack_from('<I',data)[0];assert n<=18 and len(data)==4+n*64
            for offset in range(4,len(data),64):
                index=struct.unpack_from('<I',data,offset)[0]
                r=struct.unpack_from('<6f4If4I',data,offset+4)
                if r[8]==3 and r[11]==15:
                    wire.append((header[7],index,r))
                    if r[13]:
                        launched=True;slot=index;generation=r[12];positions.append(r[:3])
                        actual=struct.unpack('<6f4If5I',os.pread(memory,64,addr['sim_projectiles']+index*64))
                        assert actual[12]>=r[12] and r[14]>0 and r[9]==140
                    elif generation==r[12]:dead=True
        if slot is not None:
            cosmetic=struct.unpack_from('<6f4If5I',pool,slot*64)
            if cosmetic[13] and cosmetic[12]==generation:adapter_samples.append(cosmetic[:3])
        actual_hp=struct.unpack('<I',os.pread(memory,4,addr['sim_entities']+32*32+8))[0]
        damaged|=actual_hp<hp
        if launched and damaged and dead:break
    assert launched and damaged and dead,(launched,damaged,dead,wire[:2])
    assert len(adapter_samples)>3 and adapter_samples[-1][0]>adapter_samples[0][0], 'assembly adapter never moved actual bomb'
    assert len(positions)>3 and positions[-1][0]>positions[0][0] and positions[-1][1]<positions[0][1]
    # Real bomb tombstones reach the adapter and cannot keep drifting indefinitely.
    lib.net_client_poll();lib.net_projectiles_update(.01)
    assert struct.unpack_from('<I',pool,slot*64+52)[0]==0
    assert peer.max_packet<=1200
    # Replay authentic captured authority records through a controlled UDP peer:
    # delayed delivery, reordered/duplicated samples and a deliberately lost death.
    lib.net_client_close()
    relay=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    relay.bind(('127.0.0.1',0));relay.settimeout(1)
    try:
        assert lib.net_client_open(b'127.0.0.1',relay.getsockname()[1])==0
        _,destination=relay.recvfrom(1200)
        def replay(kind,data,tick):
            relay.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(data),9)+data,destination)
            lib.net_client_poll()
        replay(2,struct.pack('<4I',0,0,64,100),0)
        frozen_authority=bytes(authority)
        alive_rows=[v for v in wire if v[2][13] and v[2][12]==generation]
        first,last=alive_rows[0],alive_rows[-1]
        def authentic(row):return batch(struct.pack('<I6f4If4I',row[1],*row[2]))
        replay(104,authentic(last),last[0])
        before=bytes(pool)
        replay(104,authentic(first),first[0])
        replay(104,authentic(last),last[0])
        assert bytes(pool)==before,'authentic reordered/duplicated record replaced latest'
        lib.net_projectiles_update(.1)
        assert struct.unpack_from('<f',pool,slot*64)[0]>last[2][0]
        # The captured inactive packet is dropped: age/TTL still removes the shot.
        lib.net_projectiles_update(4.1)
        assert struct.unpack_from('<I',pool,slot*64+52)[0]==0
        before=bytes(pool);replay(104,authentic(last),last[0]+1)
        assert bytes(pool)==before,'delayed authentic live record resurrected expired shot'
        assert bytes(authority)==frozen_authority
    finally:relay.close()
    print(json.dumps({'suite':'network-projectiles','passed':True,'malformed_batches':len(bad),'whole_batch_immutability':True,'generation_reuse_reorder_and_loss_expiry':True,'authority_unchanged_by_cosmetics':True,'disconnect_clears':True,'actual_server_bomb_motion_damage_and_tombstone':True,'authentic_delayed_reordered_duplicate_and_lost_death_replay':True,'authentic_bomb_samples':len(positions),'adapter_bomb_samples':len(adapter_samples),'max_packet':peer.max_packet,'fixture_writes':'actor positions and bomber pose only'}))
finally:
    lib.net_client_close()
    if peer:peer.socket.close()
    if memory is not None:os.close(memory)
    if host.poll() is None:os.kill(host.pid,signal.SIGCONT);host.terminate()
    try:host.communicate(timeout=3)
    except subprocess.TimeoutExpired:host.kill();host.communicate()
