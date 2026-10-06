#!/usr/bin/env python3
"""Actual client UDP parser plus genuine server-death/global late-join stream."""
import ctypes as C,hashlib,json,math,os,pathlib,signal,socket,struct,subprocess,sys,time
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT,Peer,server_addresses
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()));lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
remote=(C.c_ubyte*65536).in_dll(lib,'net_wrecks');count=C.c_uint.in_dll(lib,'net_wreck_count');authority=(C.c_ubyte*196620).in_dll(lib,'sim_wrecks')
def record(slot=0,seq=1,birth=0,flags=1,**kw):
 p=dict(x=100.,y=30.,z=100.,heading=.4,pitch=.1,bank=-.2,kind=1,side=0,entity=12,generation=1,birth=birth,expiry=(birth+1800)&0xffffffff,sequence=seq,flags=flags,reserved0=0,reserved1=0);p.update(kw)
 return struct.pack('<I6f10I',slot,*(p[k] for k in ('x','y','z','heading','pitch','bank','kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')))
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));s.settimeout(1);rejected=0
try:
 assert lib.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
 _,destination=s.recvfrom(1200)
 def send(payload,tick=10,kind=106,session=1,version=VERSION,schema=SCHEMA,content=CONTENT):
  s.sendto(HEADER.pack(MAGIC,version,schema,content,kind,0,1 if kind==2 else 0,tick,len(payload),session)+payload,destination);return lib.net_client_poll()
 send(struct.pack('<4I',0,0,8192,100),kind=2,tick=0);initial=bytes(remote);original=bytes(authority)
 for payload in (record(slot=1024),record()+record(),record()+record(slot=1,y=math.nan),record()[:-1],record()*18,record(flags=0),record(flags=3),record(birth=11)):
  send(payload);assert bytes(remote)==initial and bytes(authority)==original;rejected+=1
 for change in ({'version':VERSION-1},{'schema':SCHEMA^1},{'content':CONTENT^1},{'session':2}):send(record(),**change);assert bytes(remote)==initial;rejected+=1
 send(record());assert bytes(remote[:64])==record()[4:] and count.value==1
 saved=bytes(remote);send(record(x=200),tick=11);assert bytes(remote)==saved
 send(record(slot=0,seq=2,birth=11,x=200,generation=2),tick=11);saved=bytes(remote)
 for payload,tick in ((record(),12),(record(seq=3,birth=0),9)):
  send(payload,tick);assert bytes(remote)==saved
 # Unrelated accepted record advances authoritative clock, expires missed tombstone.
 send(record(slot=1,seq=4,birth=1811,x=400),tick=1811);assert count.value==1 and not struct.unpack_from('<I',remote,52)[0]&1
 saved=bytes(remote);send(record(seq=2,birth=11,x=200,generation=2),tick=1800);assert bytes(remote)==saved
 assert bytes(authority)==original,'remote transport mutated authoritative registry'
 lib.net_client_close();assert not any(remote)
 assert lib.net_client_open(b'127.0.0.1',s.getsockname()[1])==0
 _,destination=s.recvfrom(1200);send(struct.pack('<4I',0,0,8192,100),kind=2,tick=0);send(record());time.sleep(3.05);lib.net_client_poll();assert not any(remote) and not C.c_uint.in_dll(lib,'net_connected').value
finally:lib.net_client_close();s.close()
print(json.dumps({'suite':'wreck-network-parser','passed':True,'malformed_packets_rejected':rejected,'whole_batch_atomic':True,'remote_only_warmup':True,'retirement_stale_and_no_revival':True,'authority_unchanged':True,'clock_expiry_disconnect_timeout':True}))
if len(sys.argv)<3:sys.exit(0)
server=pathlib.Path(sys.argv[2]).resolve();extended='--extended' in sys.argv;limit=1890 if extended else 240
host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks',str(limit)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
try:
 ready=json.loads(host.stdout.readline());symbols={line.split()[2]:int(line.split()[0],16) for line in subprocess.check_output(['nm','-g','--defined-only',str(server)],text=True).splitlines() if len(line.split())==3};addresses=server_addresses(host,server);base=addresses['sim_entities']-symbols['sim_entities'];wreck_address=base+symbols['sim_wrecks'];memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
 os.kill(host.pid,signal.SIGSTOP)
 try:
  # Declared births only, then genuine ordinary combat. No later HP/pose/clock writes.
  os.pwrite(memory,struct.pack('<2f6I',7000.,6500.,1,1,1,0,0xffffffff,42),addresses['sim_entities']+12*32)
  os.pwrite(memory,struct.pack('<2f6I',6994.,6500.,100,0,0,0,0xffffffff,42),addresses['sim_entities']+13*32)
 finally:os.kill(host.pid,signal.SIGCONT)
 first=Peer(('127.0.0.1',ready['port']));peers.append(first);assert first.request(1)[0]==0
 captured=[];matched=0;deadline=time.monotonic()+5;first_identity=None;next_input=0
 while time.monotonic()<deadline and first_identity is None:
  if time.monotonic()>=next_input:first.input();next_input=time.monotonic()+.3
  row=first.receive(.03)
  if not row or row[0][4]!=106:continue
  header,payload=row;assert len(payload)%68==0 and len(payload)<=1156
  for offset in range(0,len(payload),68):
   slot=struct.unpack_from('<I',payload,offset)[0];w=payload[offset+4:offset+68];actual=os.pread(memory,64,wreck_address+slot*64)
   if actual==w:matched+=1
   values=struct.unpack('<6f10I',w)
   if values[8]==12 and values[9]==42 and values[13]&1:
    first_identity=(slot,values[12],w,header[7]);assert values[6:10]==(1,1,12,42)
  captured.append((header[7],payload))
 assert first_identity and matched,'real infantry fire never produced/replicated a canonical vehicle death'
 # Global state is present even for a client joining after the source died.
 second=Peer(('127.0.0.1',ready['port']));peers.append(second);assert second.request(1)[0]==0
 late_match=False;expiry_match=False;max_packet=0;deadline=time.monotonic()+(64 if extended else 3);next_input=0
 while time.monotonic()<deadline and not (late_match and (expiry_match or not extended)):
  if time.monotonic()>=next_input:
   for peer in peers:peer.input()
   next_input=time.monotonic()+.3
  for peer in peers:
   row=peer.receive(.02)
   if not row or row[0][4]!=106:continue
   header,payload=row;assert len(payload)%68==0 and len(payload)<=1156;max_packet=max(max_packet,len(payload)+40)
   assert len({struct.unpack_from('<I',payload,i)[0] for i in range(0,len(payload),68)})==len(payload)//68
   for offset in range(0,len(payload),68):
    slot=struct.unpack_from('<I',payload,offset)[0];w=payload[offset+4:offset+68];values=struct.unpack('<6f10I',w)
    if slot==first_identity[0] and values[12]==first_identity[1]:
     assert w[:52]==first_identity[2][:52] and w[56:]==first_identity[2][56:],'death pose/identity changed'
     if peer is second:late_match=True
     if not values[13]&1:expiry_match=True;assert (header[7]-values[10])&0xffffffff>=1800
   captured.append((header[7],payload))
 assert late_match,'late join never recovered existing distant wreck'
 if extended:assert expiry_match,'real1800 world-tick expiry never reached the wire'
 # Replay authentic packets alone into real assembly adapter, with drops/reorder.
 relay=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);relay.bind(('127.0.0.1',0));relay.settimeout(1)
 try:
  assert lib.net_client_open(b'127.0.0.1',relay.getsockname()[1])==0
  _,target=relay.recvfrom(1200)
  def replay(kind,payload,tick):relay.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(payload),9)+payload,target);lib.net_client_poll()
  replay(2,struct.pack('<4I',0,0,8192,100),0)
  for number,(tick,payload) in enumerate(captured):
   if number%7!=3:replay(106,payload,tick)
  assert any(remote),'authentic wreck-only stream never warmed up'
  saved=bytes(remote)
  for tick,payload in (captured[0],captured[len(captured)//2],captured[-1]):replay(106,payload,tick);assert bytes(remote)==saved
 finally:relay.close();lib.net_client_close()
 print(json.dumps({'suite':'wreck-network-server','passed':True,'units':8192,'declared_births':2,'genuine_casualty_identity':list(first_identity[:2]),'actual_wire_authority_matches':matched,'authentic_packets':len(captured),'late_join_recovered':True,'actual_world_expiry_tombstone':expiry_match,'max_wreck_packet':max_packet,'authentic_wreck_only_replay_with_drop_reorder_duplicate':True,'scope':'Actual NASM server combat/registry/global stream and adapter; two initial births only, no in-flight HP/pose/clock refresh. Expiry proven only with --extended; visible graphics separate.'}))
finally:
 for peer in peers:peer.socket.close()
 if memory is not None:os.close(memory)
 if host.poll() is None:
  host.terminate()
  try:host.wait(timeout=3)
  except subprocess.TimeoutExpired:host.kill();host.wait(timeout=3)
