#!/usr/bin/env python3
"""Real UDP parser plus actual finite-store server cannon casualty and late join."""
import ctypes as C,hashlib,json,math,os,pathlib,signal,socket,struct,subprocess,sys,time
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT,server_addresses
from wreck_stream_observer import RecordingPeer as Peer
l=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()));l.net_client_open.argtypes=[C.c_char_p,C.c_uint]
remote=(C.c_ubyte*(128*96)).in_dll(l,'net_air_crashes');count=C.c_uint.in_dll(l,'net_air_crash_count');authority=(C.c_ubyte*(128*96+32768*4+16)).in_dll(l,'sim_air_crashes')
def record(slot=0,sequence=1,birth=0,state=1,x=100.,**kw):
 f=dict(y=200.,z=100.,vx=0.,vy=-1.,vz=7.,heading=.4,pitch=.1,bank=-.2,role=0,side=0,entity=12,generation=1);f.update(kw)
 return struct.pack('<I9f7I8I',slot,x,*(f[n] for n in ('y','z','vx','vy','vz','heading','pitch','bank','role','side','entity','generation')),birth,sequence,state,*([0]*8))
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));s.settimeout(1);rejected=0
try:
 assert l.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
 _,destination=s.recvfrom(1200)
 def send(payload,tick=10,kind=119,session=1,version=VERSION,schema=SCHEMA,content=CONTENT):
  s.sendto(HEADER.pack(MAGIC,version,schema,content,kind,0,1 if kind==2 else 0,tick,len(payload),session)+payload,destination);l.net_client_poll()
 send(struct.pack('<4I',0,0,8192,100),kind=2,tick=0);initial=bytes(remote);original=bytes(authority)
 for p in (record(slot=128),record()+record(),record()+record(slot=1,y=math.nan),record()[:-1],record()*12,record(state=0),record(state=2),record(birth=11)):
  send(p);assert bytes(remote)==initial;rejected+=1
 for c in ({'version':VERSION-1},{'schema':SCHEMA^1},{'content':CONTENT^1},{'session':2}):send(record(),**c);assert bytes(remote)==initial;rejected+=1
 send(record());assert bytes(remote[:96])==record()[4:] and count.value==1
 send(record(x=107,y=199),tick=11);saved=bytes(remote);assert saved[:96]==record(x=107,y=199)[4:]
 send(record(x=108,y=199),tick=11);assert bytes(remote)==saved
 send(record(),tick=9);assert bytes(remote)==saved
 send(record(slot=1,sequence=2,birth=1810),tick=1810);assert count.value==1 and struct.unpack_from('<I',remote,60)[0]==0
 assert bytes(authority)==original
 l.net_client_close();assert not any(remote)
 assert l.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
 _,destination=s.recvfrom(1200);send(struct.pack('<4I',0,0,8192,100),kind=2,tick=0);send(record());time.sleep(3.05);l.net_client_poll();assert not any(remote) and not C.c_uint.in_dll(l,'net_connected').value
finally:l.net_client_close();s.close()
print(json.dumps(dict(suite='air-crash-network-parser',passed=True,malformed_packets_rejected=rejected,whole_batch_atomic=True,remote_only_warmup=True,authority_unchanged=True,clock_expiry_disconnect_timeout=True)))
if len(sys.argv)<3:sys.exit(0)
server=pathlib.Path(sys.argv[2]).resolve();extended='--extended' in sys.argv
host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks',str(2160 if extended else 420)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
try:
 ready=json.loads(host.stdout.readline());symbols={v.split()[2]:int(v.split()[0],16) for v in subprocess.check_output(['nm','-g','--defined-only',str(server)],text=True).splitlines() if len(v.split())==3};addresses=server_addresses(host,server);base=addresses['sim_entities']-symbols['sim_entities'];memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
 os.kill(host.pid,signal.SIGSTOP)
 try:
  # Declared births only. Real aircraft FSM acquires/shoots/debits its own store.
  for i,x,hp,side in ((31,4000.,24,1),(63,3900.,200,0)):
   os.pwrite(memory,struct.pack('<2f6I',x,4000.,hp,side,3,1,0xffffffff,42),addresses['sim_entities']+i*32)
   os.pwrite(memory,struct.pack('<5f2Ii3I3f2I',200.,math.pi/2,0.,0.,7.,1,0,-1,0,180,42,7.,0.,0.,0,1),base+symbols['sim_aircraft']+i*64)
 finally:os.kill(host.pid,signal.SIGCONT)
 first=Peer(('127.0.0.1',ready['port']));peers.append(first);assert first.request(1)[0]==0
 captured=[];identity=None;second=None;late=False;landed=False;expired=False;next_input=0;deadline=time.monotonic()+(75 if extended else 12);maxpacket=0;phases=set();authority_matches=0
 while time.monotonic()<deadline and not (late and landed and (expired or not extended)):
  if time.monotonic()>=next_input:
   for peer in peers:peer.input()
   next_input=time.monotonic()+.25
  for peer in list(peers):
   row=peer.receive(.01)
   if not row or row[0][4]!=119:continue
   header,payload=row;assert len(payload)%100==0 and len(payload)<=1100;maxpacket=max(maxpacket,len(payload)+40)
   assert len({struct.unpack_from('<I',payload,o)[0] for o in range(0,len(payload),100)})==len(payload)//100
   captured.append((header[7],payload))
   for offset in range(0,len(payload),100):
    slot=struct.unpack_from('<I',payload,offset)[0];wire=payload[offset+4:offset+100];f=struct.unpack('<9f7I8I',wire)
    if f[11:13]!=(31,42):continue
    if identity is None:identity=(slot,f[14]);second=Peer(('127.0.0.1',ready['port']));assert second.request(1)[0]==0;peers.append(second)
    assert (slot,f[14])==identity and f[9:13]==(1,1,31,42)
    actual=os.pread(memory,96,base+symbols['sim_air_crashes']+slot*96)
    if wire==actual:authority_matches+=1
    if peer is second:late=True
    phases.add(f[15]);landed |= f[15]==2;expired |= f[15]==0
    assert ((header[7]-f[13])&0xffffffff<1800)==bool(f[15])
 assert identity and late and landed and authority_matches,(identity,late,landed,authority_matches,phases)
 if extended:assert expired
 shooter=os.pread(memory,64,base+symbols['sim_aircraft']+63*64);assert struct.unpack_from('<I',shooter,36)[0]<180,'FSM did not debit actual cannon store'
 assert struct.unpack('<I',os.pread(memory,4,addresses['sim_entities']+31*32+8))[0]==0
 # Authentic stream only, simulated drops and out-of-order duplicate deliveries.
 relay=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);relay.bind(('127.0.0.1',0));relay.settimeout(1)
 try:
  assert l.net_client_open(b'127.0.0.1',relay.getsockname()[1])==0
  _,target=relay.recvfrom(1200)
  def replay(kind,payload,tick):relay.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(payload),9)+payload,target);l.net_client_poll()
  replay(2,struct.pack('<4I',0,0,8192,100),0);delivered=[]
  for n,(tick,payload) in enumerate(captured):
   if n%7!=3:replay(119,payload,tick);delivered.append((tick,payload))
  assert delivered and any(remote)
  saved=bytes(remote)
  for tick,payload in (delivered[0],delivered[len(delivered)//2],delivered[-1]):replay(119,payload,tick);assert bytes(remote)==saved
  tick,payload=captured[-1];replay(119,payload,tick);saved=bytes(remote);replay(119,payload,tick);assert bytes(remote)==saved
 finally:l.net_client_close();relay.close()
 print(json.dumps(dict(suite='air-crash-network-server',passed=True,units=8192,declared_births=2,genuine_casualty_identity=identity,actual_wire_authority_matches=authority_matches,authentic_packets=len(captured),late_join_recovered=True,phases=sorted(phases),actual_world_expiry_tombstone=expired,max_packet=maxpacket,authentic_replay_drop_reorder_duplicate=True,finite_FSM_ammunition=True,scope='Real authoritative FSM casualty/global crash stream/two peers/adapter; two initial births only, no later body/HP/ammo/gen/clock writes. TTL only covered with extended; visible client separately tested.')))
finally:
 for p in peers:p.socket.close()
 if memory is not None:os.close(memory)
 if host.poll() is None:host.terminate()
 host.wait(timeout=5)
