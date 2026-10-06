#!/usr/bin/env python3
"""Malformed/reordered real UDP packets and actual four-player company snapshots.
One declared initial far-company infantry birth precedes all player joins.
After that, tests observe only; no live pose, health, clock or economic renewal.
"""
import ctypes as C,hashlib,json,math,os,pathlib,signal,socket,struct,subprocess,sys,tempfile,time
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT,Peer
library,server=map(lambda s:pathlib.Path(s).resolve(),sys.argv[1:3])
# Private copy: a later development rebuild must not replace this mapped file.
with tempfile.TemporaryDirectory(prefix='rh-company-remote-') as td:
 private=pathlib.Path(td)/'client.so';private.write_bytes(library.read_bytes());lib=C.CDLL(str(private))
 lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
 lib.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
 remote=(C.c_ubyte*160).in_dll(lib,'net_company_records');players=(C.c_uint*64).in_dll(lib,'sim_players')
 valid=C.c_uint.in_dll(lib,'net_company_valid');clock=C.c_uint.in_dll(lib,'net_company_tick')
 def record(i,key=0xffffffff,generation=0,serial=0,mode=0,ordered=0,x=0,z=0,sequence=0,tick=0):
  return struct.pack('<6I2f2I',i,key,generation,serial,mode,ordered,x,z,sequence,tick)
 def packet(records):return struct.pack('<I',4)+b''.join(records)+bytes(192)
 rows=[record(0,19,1,1,3,1,2200,1300,1,5),record(1,285,1,1),record(2,534,1,1),record(3,0,1,1,0,1,2400,1300,1,5)]
 sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('127.0.0.1',0));sock.settimeout(1)
 try:
  assert lib.net_client_open(b'127.0.0.1',sock.getsockname()[1])==0
  _,destination=sock.recvfrom(1200)
  def send(payload,tick=10,kind=107,session=1,version=VERSION,schema=SCHEMA,content=CONTENT):
   sock.sendto(HEADER.pack(MAGIC,version,schema,content,kind,0,1 if kind==2 else 0,tick,len(payload),session)+payload,destination)
   return lib.net_client_poll()
  send(struct.pack('<4I',0,0,8192,100),kind=2,tick=0)
  authority=lib.sim_checksum();initial=bytes(remote);rejected=0
  malformed=[packet(rows)[:-1],struct.pack('<I',3)+b''.join(rows)+bytes(192),packet(rows)+b'X']
  for index,kw in [(0,dict(i=1)),(1,dict(key=768,generation=1)),(2,dict(key=534,generation=0)),(3,dict(key=19,generation=1)),(3,dict(key=0,generation=1,mode=5)),(3,dict(key=0,generation=1,ordered=2)),(3,dict(key=0,generation=1,ordered=1,x=math.nan)),(3,dict(key=0,generation=1,ordered=1,z=math.inf)),(3,dict(key=0,generation=1,ordered=1,x=-1)),(3,dict(key=0,generation=1,ordered=1,z=8001)),(3,dict(key=0,generation=1,ordered=1,tick=11)),(3,dict(key=0,generation=1,mode=1)),(3,dict(key=0,generation=1,sequence=1)),(3,dict(generation=1)),(3,dict(ordered=1)),(3,dict(x=1)),(3,dict(tick=1))]:
   changed=rows.copy();kw.setdefault('i',index);changed[index]=record(**kw);malformed.append(packet(changed))
  for payload in malformed:
   send(payload);assert bytes(remote)==initial and not valid.value and lib.sim_checksum()==authority;rejected+=1
  for kw in ({'version':VERSION-1},{'schema':SCHEMA^1},{'content':CONTENT^1},{'session':2}):
   send(packet(rows),**kw);assert bytes(remote)==initial;rejected+=1
  # Direct receive is read-only with respect to all authoritative state.
  raw=C.create_string_buffer(b''.join(rows)+bytes(192));lib.net_company_receive.argtypes=[C.c_void_p,C.c_uint,C.c_uint]
  assert lib.net_company_receive(raw,4,10)==0 and lib.sim_checksum()==authority
  lib.net_company_reset()
  core=(bytes(players),bytes((C.c_ubyte*(32768*32)).in_dll(lib,'sim_entities')),bytes((C.c_ubyte*(1536*32)).in_dll(lib,'company_controls')))
  send(packet(rows));assert bytes(remote)==b''.join(rows) and valid.value==1 and clock.value==10
  # Company metadata alone never fabricates player state or enables commands.
  assert core==(bytes(players),bytes((C.c_ubyte*(32768*32)).in_dll(lib,'sim_entities')),bytes((C.c_ubyte*(1536*32)).in_dll(lib,'company_controls')))
  assert lib.net_company_for_player(0)==-1
  for i,front in enumerate((0,1,2,0)):
   players[i*16+10]=front;players[i*16+11]=1;players[i*16+15]=1
  assert [lib.net_company_for_player(i)for i in range(4)]==[19,285,534,0]
  players[15]=2;assert lib.net_company_for_player(0)==-1;players[15]=1
  players[10]=1;assert lib.net_company_for_player(0)==-1;players[10]=0
  players[11]=0;assert lib.net_company_for_player(0)==-1;players[11]=1
  proposals=(C.c_ubyte*192).in_dll(lib,'net_company_transfers')
  offer=[1,1,19,285,1,1,1,1,100,1,0,0]
  def offer_packet(values):return struct.pack('<I',4)+b''.join(rows)+struct.pack('<12I',*values)+bytes(144)
  offer_rejected=0
  for field,value in [(0,2),(1,4),(1,0),(2,768),(2,20),(3,534),(4,2),(5,2),(6,2),(7,2),(8,11),(8,462),(9,0),(9,0xffffffff),(10,1),(11,1)]:
   bad=offer.copy();bad[field]=value;send(offer_packet(bad),tick=11)
   assert bytes(remote)==b''.join(rows) and not any(proposals) and clock.value==10
   offer_rejected+=1
  bad=offer.copy();bad[0]=0;send(offer_packet(bad),tick=11);assert not any(proposals);offer_rejected+=1
  send(offer_packet(offer),tick=11);assert bytes(proposals[:48])==struct.pack('<12I',*offer)
  assert lib.net_company_offer(1,0)==1 and lib.net_company_offer(2,0)==-1
  players[31]=2;assert lib.net_company_offer(1,0)==-1;players[31]=1
  players[26]=0;assert lib.net_company_offer(1,0)==-1;players[26]=1
  players[27]=0;assert lib.net_company_offer(1,0)==-1;players[27]=1
  saved=bytes(remote);changed=rows.copy();changed[0]=record(0,20,1,1)
  for tick in (9,10):send(packet(changed),tick=tick);assert bytes(remote)==saved and clock.value==11
  changed=rows.copy();changed[0]=record(0,serial=2);send(packet(changed),tick=12)
  assert lib.net_company_for_player(0)==-1 and bytes(remote)==b''.join(changed)
  send(packet(rows),tick=10);assert lib.net_company_for_player(0)==-1
  changed[0]=record(0,19,2,3);send(packet(changed),tick=13);assert lib.net_company_for_player(0)==-1
  players[15]=2;assert lib.net_company_for_player(0)==19
  lib.net_client_close();assert not valid.value and clock.value==0 and lib.net_company_for_player(0)==-1
  assert all(struct.unpack_from('<I',remote,i*40+4)[0]==0xffffffff for i in range(4))
  # Timeout must invalidate metadata even when no final tombstone arrives.
  assert lib.net_client_open(b'127.0.0.1',sock.getsockname()[1])==0
  _,destination=sock.recvfrom(1200);send(struct.pack('<4I',0,0,8192,100),kind=2,tick=0);send(packet(rows))
  time.sleep(3.05);lib.net_client_poll();assert not valid.value and not C.c_uint.in_dll(lib,'net_connected').value
 finally:lib.net_client_close();sock.close()
 print(json.dumps({'suite':'company-remote-parser','passed':True,'malformed_or_foreign_packets':rejected,'malformed_proposals':offer_rejected,'proposal_whole_batch_atomic':True,'offer_current_participant_generation_front_connected_gates':True,'whole_batch_atomic':True,'follow_mode_accepted_invalid_mode5_rejected':True,'direct_receive_authority_checksum_preserved':True,'transport_players_entities_companies_preserved':True,'transport_advances_existing_remote_clock':True,'stale_equal_tick_rejected':True,'body_generation_front_disconnect_gates':True,'tombstone_no_resurrection':True,'close_timeout_reset':True,'library_sha256':hashlib.sha256(private.read_bytes()).hexdigest()}))
 # Actual world, three observer peers and production NASM adapter as player3.
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','420'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
 try:
  ready=json.loads(host.stdout.readline());address=('127.0.0.1',ready['port'])
  symbols={line.split()[2]:int(line.split()[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(line.split())==3}
  # Initial encounter construction only: one generation71 infantry birth in
  # front0 cohort0, far from all deployment positions. No later state writes.
  os.kill(host.pid,signal.SIGSTOP)
  try:
   _,status=os.waitpid(host.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
   birth=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
   try:
    birth_tick=struct.unpack('<I',os.pread(birth,4,symbols['sim_tick_count']))[0];assert birth_tick<5
    os.pwrite(birth,struct.pack('<2f6I',7500.,1300.,100,0,0,0,0xffffffff,71),symbols['sim_entities']+32)
   finally:os.close(birth)
  finally:os.kill(host.pid,signal.SIGCONT)
  memory=os.open(f'/proc/{host.pid}/mem',os.O_RDONLY)
  def controls():return os.pread(memory,1536*32,symbols['company_controls'])
  def assignments():return [struct.unpack_from('<4I',os.pread(memory,64,symbols['player_companies']),i*16)for i in range(4)]
  for _ in range(3):
   p=Peer(address);assert p.request(1)[0]==0;peers.append(p)
  assert lib.net_client_open(b'127.0.0.1',ready['port'])==0
  last_input=0
  departed=set()
  def until(predicate,seconds=4):
   global last_input
   deadline=time.monotonic()+seconds
   while time.monotonic()<deadline:
    lib.net_client_poll()
    for p in peers:p.receive(0)
    if time.monotonic()-last_input>.3:
     for p in peers:
      if p.id not in departed:p.input()
     if C.c_uint.in_dll(lib,'net_connected').value:lib.net_client_input(0,0,C.c_float(0),C.c_float(0),C.c_float(0),C.c_float(0))
     last_input=time.monotonic()
    result=predicate()
    if result:return result
    assert host.poll() is None
    time.sleep(.002)
   raise AssertionError('actual company replication timed out')
  until(lambda:C.c_uint.in_dll(lib,'net_connected').value and valid.value and lib.net_company_for_player(3)>=0)
  keys=[a[0]for a in assignments()];assert len(set(keys))==4
  until(lambda:[lib.net_company_for_player(i)for i in range(4)]==keys)
  assert C.c_uint.in_dll(lib,'net_player_id').value==3
  # Company soldiers outside the local region remain real replicated actors.
  entity_bytes=os.pread(memory,8192*32,symbols['sim_entities'])
  player_bytes=os.pread(memory,256,symbols['sim_players'])
  far_owned={}
  for i in range(4):
   px,_,pz=struct.unpack_from('<3f',player_bytes,i*64)
   far_owned[i]=[actor for actor in range(8192)if (e:=struct.unpack_from('<2f6I',entity_bytes,actor*32))[2] and e[3]==0 and e[4]<3 and e[5]*256+(actor>>7)==keys[i] and math.hypot(e[0]-px,e[1]-pz)>1200]
  assert any(far_owned.values()),'fixture lacks outside-region company members'
  adapter_entities=(C.c_uint*(32768*8)).in_dll(lib,'sim_entities')
  until(lambda:all(all((actor in peers[i].entities)if i<3 else adapter_entities[actor*8+7]==struct.unpack_from('<I',entity_bytes,actor*32+28)[0] for actor in actors)for i,actors in far_owned.items()),5)
  assert all(all((peers[i].entities[actor][3]==0)if i<3 else adapter_entities[actor*8+3]==0 for actor in actors)for i,actors in far_owned.items())
  # The adapter sees another owner's command without issuing it itself.
  status,balance,_=peers[0].command(4,struct.pack('<IIff',0,1,2200,1300),lose_ack=True);assert status==0
  until(lambda:struct.unpack_from('<I',remote,32)[0]==1)
  wire=struct.unpack_from('<6I2f2I',remote,0);assert wire[4:]==(1,1,2200.,1300.,1,wire[9])
  before=controls();a=assignments();exact=0
  for i in range(4):
   r=struct.unpack_from('<6I2f2I',remote,i*40);c=struct.unpack_from('<4I2f2I',before,keys[i]*32)
   assert r[:4]==(i,keys[i],a[i][1],a[i][2])
   assert r[4:]==c[2:];exact+=1
  lib.net_client_order.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
  assert lib.net_client_order(0,0,2400.,1300.)==0
  until(lambda:struct.unpack_from('<I',remote,3*40+32)[0]==1)
  assert struct.unpack_from('<2f',remote,3*40+24)==(2400.,1300.)
  # Release is a complete snapshot tombstone; older metadata cannot revive it.
  old=bytes(remote);assert peers[0].command(5)[0]==0;departed.add(0)
  until(lambda:struct.unpack_from('<I',remote,4)[0]==0xffffffff)
  assert lib.net_company_for_player(0)==-1
  serial=struct.unpack_from('<I',remote,12)[0]
  peers[0].id=0xffffffff;peers[0].generation=0;peers[0].sequence=1
  assert peers[0].request(1)[0]==0;departed.clear()
  until(lambda:lib.net_company_for_player(0)>=0 and struct.unpack_from('<I',remote,12)[0]>serial)
  assert struct.unpack_from('<I',remote,20)[0]==0,'released intent leaked into fresh lease'
  for p in peers:p.command(5);p.socket.close()
  peers=[];lib.net_client_close()
  stdout,stderr=host.communicate(timeout=20);assert host.returncode==0,(stdout,stderr)
  print(json.dumps({'suite':'company-remote-actual-four-player','passed':True,'units':8192,'keys':keys,'exact_server_records':exact,'outside_local_region_owned_actors':{str(i):len(v)for i,v in far_owned.items()},'production_adapter_player':3,'remote_owner_intent_observed':True,'lost_ack_single_sequence':True,'adapter_own_order_observed':True,'disconnect_tombstone_rejoin_fresh_intent':True,'observer_writes_after_initial_birth':False,'initial_birth':{'entity':1,'generation':71,'tick':birth_tick,'position':[7500.,1300.]},'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'server':json.loads(stdout.strip().splitlines()[-1]),'limits':['GL ownership tint and map display verified separately; transfer and assistance remain unfinished.']}))
 finally:
  lib.net_client_close()
  if memory is not None:os.close(memory)
  for p in peers:p.socket.close()
  if host.poll() is None:host.kill();host.communicate()
