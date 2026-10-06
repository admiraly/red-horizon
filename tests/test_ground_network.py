#!/usr/bin/env python3
"""Real assembled parser; independent ground64 warmup and hostile batch tests.
Optional second argument exercises real dedicated-server ground motion records.
"""
import ctypes as C, json, math, os, pathlib, signal, socket, struct, subprocess, sys, time
from test_coop import HEADER, MAGIC, VERSION, SCHEMA, CONTENT, Peer, server_addresses
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()))
lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
e=(C.c_ubyte*(32768*32)).in_dll(lib,'sim_entities')
g=(C.c_ubyte*(32768*32)).in_dll(lib,'sim_ground_motion')
def record(index=7,generation=1,hp=400,kind=1,flags=None,reserved=0,**kw):
    fields=dict(x=100.,z=100.,heading=.4,speed=.2,turn=.03,vx=.1,vz=.17)
    fields.update(kw)
    flags=int(hp!=0) if flags is None else flags
    return struct.pack('<I2f6I5f2I',index,fields['x'],fields['z'],hp,0,kind,0,0xffffffff,generation,*(fields[k]for k in('heading','speed','turn','vx','vz')),flags,reserved)
def batch(*rows):return struct.pack('<I',len(rows))+b''.join(rows)
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));s.settimeout(1)
rejected=0
try:
    assert lib.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
    _,address=s.recvfrom(1200)
    def send(data,tick=10,kind=105,session=1,version=VERSION,schema=SCHEMA,content=CONTENT):
        s.sendto(HEADER.pack(MAGIC,version,schema,content,kind,0,1 if kind==2 else 0,tick,len(data),session)+data,address)
        return lib.net_client_poll()
    send(struct.pack('<4I',0,0,64,100),kind=2)
    initial=(bytes(e),bytes(g))
    bad=[batch(record(index=64)),batch(record(generation=0)),batch(record(hp=401)),batch(record(kind=2,hp=161)),batch(record(kind=0)),batch(record(kind=3)),batch(record(flags=0)),batch(record(hp=0,flags=1)),batch(record(flags=2)),batch(record(reserved=1)),batch(record(x=-1)),batch(record(z=8001)),batch(record(heading=float('nan'))),batch(record(speed=float('inf'))),batch(record(turn=-.101)),batch(record(heading=6.41)),batch(record(speed=-.611)),batch(record(vx=.5,vz=.5)),batch(record(),record()),batch(record(),record(index=8,z=float('nan'))),struct.pack('<I',19)+record()*19,struct.pack('<I',1)]
    for data in bad:
        send(data,tick=100);assert (bytes(e),bytes(g))==initial,'invalid batch partially mutated state';rejected+=1
    for change in ({'version':VERSION-1},{'schema':SCHEMA^1},{'content':CONTENT^1},{'session':2}):
        send(batch(record()),tick=100,**change);assert (bytes(e),bytes(g))==initial;rejected+=1
    # Rejection of tick100 must not poison timestamps for a valid tick10 warmup.
    send(batch(record()))
    assert bytes(e[7*32:8*32])==record()[4:36]
    pose=struct.unpack_from('<5f3I',g,7*32)
    assert abs(pose[0]-.4)<1e-6 and pose[5:]==(1,1,1),pose
    accepted=(bytes(e),bytes(g))
    send(batch(record(x=150)),9);assert (bytes(e),bytes(g))==accepted
    # Same/older-tick sparse chunks must not clobber a hull's independent pose/XZ.
    for tick in (9,10):
        send(struct.pack('<I',1)+record(x=150)[:36],tick,kind=101)
        assert (bytes(e),bytes(g))==accepted
    send(batch(record(generation=2,x=200)),11)
    accepted=(bytes(e),bytes(g));send(batch(record(generation=1)),12)
    assert (bytes(e),bytes(g))==accepted
    send(batch(record(generation=2,hp=0,speed=0,vx=0,vz=0,turn=0)),13)
    accepted=(bytes(e),bytes(g));send(batch(record(generation=2)),14)
    assert (bytes(e),bytes(g))==accepted and struct.unpack_from('<I',g,7*32+28)[0]==0
    send(struct.pack('<I',1)+record(generation=2)[:36],14,kind=101)
    assert (bytes(e),bytes(g))==accepted,'sparse equal-generation record revived a tombstone'
    send(batch(record(generation=3,kind=2,hp=160)),15)
    assert struct.unpack_from('<3I',g,7*32+20)==(3,2,1)
    # Interest hiding is not a death tombstone: the same living generation can return.
    players=(C.c_ubyte*256).in_dll(lib,'sim_players')
    C.memmove(C.addressof(players),struct.pack('<f',7000.),4)
    lib.net_client_poll()
    assert struct.unpack_from('<I',e,7*32+8)[0]==0
    C.memmove(C.addressof(players),struct.pack('<f',0.),4)
    send(batch(record(generation=3,kind=2,hp=160)),16)
    assert struct.unpack_from('<I',e,7*32+8)[0]==160,'interest return mistaken for dead-generation revival'
    # A sparse wire death also blocks ground-only revival before any pose warmup.
    send(struct.pack('<I',1)+record(index=8,hp=0)[:36],17,kind=101)
    send(batch(record(index=8)),18)
    assert struct.unpack_from('<I',e,8*32+8)[0]==0 and not any(g[8*32:9*32])
    send(batch(record(index=9,hp=0)),0)
    send(batch(record(index=9)),1)
    assert struct.unpack_from('<I',e,9*32+8)[0]==0,'tick-zero tombstone revived'
    # Arbitrary client poll/render time cannot advance authoritative actuator state.
    accepted=bytes(g)
    for _ in range(10):lib.net_client_poll()
    assert bytes(g)==accepted
    lib.net_client_close();assert not any(g),'disconnect retained hull pose'
    assert lib.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
    _,address=s.recvfrom(1200);send(struct.pack('<4I',0,0,64,100),kind=2)
    send(batch(record()));time.sleep(3.05);lib.net_client_poll()
    assert not C.c_uint.in_dll(lib,'net_connected').value and not any(g),'timeout retained hull pose'
finally:lib.net_client_close();s.close()
print(json.dumps(dict(suite='ground-network-parser',passed=True,malformed_batches_rejected=rejected,warmup_without_sparse_entities=True,whole_batch_atomic=True,sparse_same_tick_precedence=True,generation_reuse_and_no_revival=True,disconnect_and_timeout_clear=True)))

if len(sys.argv)>2:
    server=pathlib.Path(sys.argv[2]).resolve()
    host=subprocess.Popen([str(server),'--port','0','--units','2048','--ticks','240'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    peer=None;memory=None
    try:
        ready=json.loads(host.stdout.readline());peer=Peer(('127.0.0.1',ready['port']))
        assert peer.request(1)[0]==0
        addresses=server_addresses(host,server)
        symbols={line.split()[2]:int(line.split()[0],16) for line in subprocess.check_output(['nm','-g','--defined-only',str(server)],text=True).splitlines() if len(line.split())==3}
        base=addresses['sim_entities']-symbols['sim_entities']
        addresses['sim_ground_motion']=base+symbols['sim_ground_motion']
        memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
        os.kill(host.pid,signal.SIGSTOP)
        try:
            data=os.pread(memory,2048*32,addresses['sim_entities'])
            tanks=[i for i in range(2048) if struct.unpack_from('<4I',data,i*32+8)[1:]==(0,1,0) and struct.unpack_from('<I',data,i*32+8)[0]>0]
            armor=tanks[-1]
            x,z=struct.unpack_from('<2f',data,armor*32)
            # Only player position is a fixture; normal input creates ownership.
            os.pwrite(memory,struct.pack('<f',x),addresses['sim_players'])
            os.pwrite(memory,struct.pack('<f',z+6),addresses['sim_players']+8)
        finally:os.kill(host.pid,signal.SIGCONT)
        assert peer.input(8)[0]==0
        deadline=time.monotonic()+2
        while time.monotonic()<deadline and (not peer.state or peer.state['player_vehicle'][0]!=armor):peer.receive(.05)
        assert peer.state and peer.state['player_vehicle'][0]==armor,'real boarding did not establish priority hull'
        assert peer.input()[0]==0
        owned_priority_packets=0;authority_matches=0;moving_authority_matches=0
        captured=[];traces={};deadline=time.monotonic()+5;next_keepalive=0
        while time.monotonic()<deadline:
            if time.monotonic()>=next_keepalive:peer.input();next_keepalive=time.monotonic()+.3
            row=peer.receive(.03)
            if not row or row[0][4]!=105:continue
            header,data=row;n=struct.unpack_from('<I',data)[0]
            assert n<=18 and len(data)==4+n*64
            indices=[]
            for offset in range(4,len(data),64):
                r=struct.unpack_from('<I2f6I5f2I',data,offset)
                index,x,z,hp,side,kind,front,target,generation,heading,speed,turn,vx,vz,flags,reserved=r
                assert index<2048 and generation and side<=1 and kind in (1,2) and front<=2
                assert hp<=(400 if kind==1 else 160) and flags==int(hp!=0) and reserved==0
                assert all(map(math.isfinite,(x,z,heading,speed,turn,vx,vz)))
                assert abs(heading)<=6.4 and abs(speed)<=.61001 and abs(turn)<=.10001 and math.hypot(vx,vz)<=.61101
                actual_entity=os.pread(memory,32,addresses['sim_entities']+index*32)
                actual_pose=os.pread(memory,32,addresses['sim_ground_motion']+index*32)
                actual_record=struct.pack('<I',index)+actual_entity+actual_pose[:20]+actual_pose[28:32]+bytes(4)
                if data[offset:offset+64]==actual_record:
                    authority_matches+=1
                    moving_authority_matches+=int(math.hypot(vx,vz)>.001)
                indices.append(index);traces.setdefault(index,[]).append((header[7],x,z,heading,speed,generation))
            assert len(indices)==len(set(indices))
            if peer.state and peer.state['player_vehicle'][0]==armor and header[7]>=peer.state['tick']:
                assert indices and indices[0]==armor,'legitimate owned hull did not lead bounded packet'
                owned_priority_packets+=1
            captured.append((header[7],data))
        moved=[i for i,rows in traces.items() if len(rows)>3 and math.dist(rows[0][1:3],rows[-1][1:3])>.25]
        assert captured and moved,('no authentic ground movement',traces)
        assert len(traces)>18,'fair cursor never refreshed beyond one packet of hulls'
        assert peer.max_packet<=1196,peer.max_packet
        assert owned_priority_packets>3,'owned priority never observed over real snapshots'
        assert authority_matches>3 and moving_authority_matches>0,'wire records never matched real moving server state'
        # Re-deliver authentic ground packets alone through a controlled UDP relay.
        # No NET_ENTITIES packet is forwarded. Delay/drop/reorder reproduce faults.
        relay=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);relay.bind(('127.0.0.1',0));relay.settimeout(1)
        try:
            assert lib.net_client_open(b'127.0.0.1',relay.getsockname()[1])==0
            _,destination=relay.recvfrom(1200)
            def replay(kind,data,tick):
                relay.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(data),9)+data,destination)
                lib.net_client_poll()
            replay(2,struct.pack('<4I',0,0,2048,100),0)
            # Client observer placement only, to keep captured front in interest.
            players=(C.c_ubyte*256).in_dll(lib,'sim_players')
            C.memmove(C.addressof(players),struct.pack('<f',x),4)
            C.memmove(C.addressof(players)+8,struct.pack('<f',z+6),4)
            for number,(tick,data) in enumerate(captured):
                if number!=2:replay(105,data,tick) # one deliberate dropped snapshot
            assert any(g),'authentic ground-only warmup failed'
            accepted=(bytes(e),bytes(g))
            for tick,data in (captured[0],captured[-1],captured[len(captured)//2]):
                replay(105,data,tick)
                assert (bytes(e),bytes(g))==accepted,'reordered authentic hull replaced latest sample'
            lib.net_client_close();assert not any(g)
        finally:relay.close();lib.net_client_close()
        print(json.dumps(dict(suite='ground-network-server',passed=True,authentic_ground_packets=len(captured),owned_priority_packets=owned_priority_packets,authority_matches=authority_matches,moving_authority_matches=moving_authority_matches,moving_hulls=moved,max_packet=peer.max_packet,ground_only_warmup_with_reorder_duplicate_drop=True)))
    finally:
        if peer:peer.socket.close()
        if memory is not None:os.close(memory)
        if host.poll() is None:
            host.terminate()
            try:host.wait(timeout=3)
            except subprocess.TimeoutExpired:host.kill();host.wait(timeout=3)
