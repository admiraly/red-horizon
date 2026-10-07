#!/usr/bin/env python3
"""Four real UDP endpoints: explicit consent, lost ACK, swapped front authority.
Read-only observer, original8192-unit world, no pose/health/store/clock writes.
"""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,sys,tempfile,time
from test_coop import Peer
server,library=map(lambda x:pathlib.Path(x).resolve(),sys.argv[1:3])
with tempfile.TemporaryDirectory(prefix='rh-transfer-udp-')as temporary:
 copied=pathlib.Path(temporary)/'adapter.so';copied.write_bytes(library.read_bytes());l=C.CDLL(str(copied));l.net_client_open.argtypes=[C.c_char_p,C.c_uint]
 l.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;l.net_client_transfer.argtypes=[C.c_uint]*3;l.net_client_order.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','450'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
 try:
  ready=json.loads(host.stdout.readline());address=('127.0.0.1',ready['port']);symbols={r[2]:int(r[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(r:=line.split())==3};memory=os.open(f'/proc/{host.pid}/mem',os.O_RDONLY)
  def read(name,n,offset=0):return os.pread(memory,n,symbols[name]+offset)
  def leases():return [struct.unpack_from('<4I',read('player_companies',64),i*16)for i in range(4)]
  def controls(keys):return [struct.unpack('<4I2f2I',read('company_controls',32,k*32))for k in keys]
  for _ in range(3):
   p=Peer(address);assert p.request(1)[0]==0;peers.append(p)
  assert l.net_client_open(b'127.0.0.1',ready['port'])==0
  last_input=0
  def until(predicate,seconds=4):
   global last_input
   deadline=time.monotonic()+seconds
   while time.monotonic()<deadline:
    l.net_client_poll()
    for p in peers:p.receive(0)
    if time.monotonic()-last_input>.3:
     for p in peers:p.input()
     if C.c_uint.in_dll(l,'net_connected').value:l.net_client_input(0,0,C.c_float(0),C.c_float(0),C.c_float(0),C.c_float(0))
     last_input=time.monotonic()
    result=predicate()
    if result:return result
    assert host.poll() is None
    time.sleep(.003)
   raise AssertionError('transfer network condition timed out')
  until(lambda:C.c_uint.in_dll(l,'net_connected').value and l.net_company_for_player(3)>=0)
  initial=leases();keys=[a[0]for a in initial];assert len(set(keys))==4
  # Preserve real accepted intents in two companies, without global front orders.
  assert peers[0].command(4,struct.pack('<IIff',0,1,2200.,1300.))[0]==0
  assert peers[1].command(4,struct.pack('<IIff',1,0,2400.,3900.))[0]==0
  original=controls(keys)
  def request(peer,action,other,seq=0,**kw):return peer.command(6,struct.pack('<3I',action,other,seq),**kw)
  assert request(peers[0],0,1,lose_ack=True)[0]==0
  until(lambda:peers[1].company_transfers and peers[1].company_transfers[0][0]==1)
  offer=peers[1].company_transfers[0];sequence=offer[9];assert sequence==1 and offer[1:4]==(1,keys[0],keys[1])
  assert leases()==initial and controls(keys)==original,'request silently changed ownership'
  # Third party cannot accept; wrong request ID cannot accept.
  assert request(peers[2],1,0,sequence)[0]==5
  assert request(peers[1],1,0,sequence+1)[0]==5
  assert leases()==initial and controls(keys)==original
  before_players=read('sim_players',256)
  assert request(peers[1],1,0,sequence,lose_ack=True)[0]==0
  until(lambda:l.net_company_for_player(0)==keys[1] and l.net_company_for_player(1)==keys[0])
  after=leases();assert [a[0]for a in after]==[keys[1],keys[0],keys[2],keys[3]]
  assert after[0][2]==initial[0][2]+1 and after[1][2]==initial[1][2]+1
  transferred=controls(keys);assert transferred[0][:2]==(1,after[1][1]) and transferred[1][:2]==(0,after[0][1])
  assert all(a[2:]==b[2:]for a,b in zip(original,transferred))
  after_players=read('sim_players',256)
  assert all(before_players[i*64:i*64+12]==after_players[i*64:i*64+12]for i in (0,1)),'exchange teleported a human'
  assert all(not struct.unpack_from('<I',read('company_transfers',192),i*48)[0]for i in range(4))
  until(lambda:peers[0].front==1 and peers[1].front==0)
  # Old front denied; new owner's command accepted and confined to their cohort.
  assert peers[0].command(4,struct.pack('<IIff',0,0,2600.,1300.))[0]==5
  # Consent exchange does not reset the original15-tick order rate gate.
  # Wait on real authoritative ticks; no clock writes or deadline changes.
  until(lambda:struct.unpack('<I',read('sim_tick_count',4))[0]-original[0][7]>=15)
  new_order=peers[0].command(4,struct.pack('<IIff',1,1,2200.,3900.))
  assert new_order[0]==0,('new-owner order ACK',new_order,original[0][7],leases())
  assert controls(keys)[0][2:]==transferred[0][2:]
  assert request(peers[1],1,0,sequence)[0]==5,'old consent revived an accepted proposal'
  # Production NASM adapter exercises proposal and cancel over the same endpoint.
  until(lambda:C.c_uint.in_dll(l,'net_pending').value==0)
  assert l.net_client_transfer(0,2,0)==0
  remote=(C.c_uint*48).in_dll(l,'net_company_transfers')
  until(lambda:remote[36]==1)
  adapter_sequence=remote[45]
  assert l.net_client_transfer(3,2,adapter_sequence)==0
  until(lambda:remote[36]==0 and C.c_uint.in_dll(l,'net_pending').value==0)
  for p in peers:p.command(5);p.socket.close()
  peers=[];l.net_client_close();stdout,stderr=host.communicate(timeout=20);assert host.returncode==0,(stdout,stderr)
  print(json.dumps({'suite':'company-transfer-actual-udp','passed':True,'units':8192,'before_keys':keys,'after_keys':[a[0]for a in after],'explicit_recipient_consent':True,'lost_propose_and_accept_ACK_no_duplicate_swap':True,'source_generations_and_leases_bound':True,'preserved_company_intents':True,'body_positions_preserved':True,'authoritative_fronts_updated':True,'post_transfer_order_elapsed_server_ticks':new_order[2]-original[0][7],'old_front_and_old_consent_rejected':True,'production_adapter_propose_cancel':True,'observer_writes':False,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'library_sha256':hashlib.sha256(copied.read_bytes()).hexdigest(),'server':json.loads(stdout.strip().splitlines()[-1]),'limits':['Rendered keyboard/feedback and broader fault/full acceptance are separate; exchange is not squad splitting or assistance.']}))
 finally:
  l.net_client_close()
  if memory is not None:os.close(memory)
  for p in peers:p.socket.close()
  if host.poll() is None:host.kill();host.communicate()
