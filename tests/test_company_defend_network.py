#!/usr/bin/env python3
"""Actual8192 authority, three UDP peers + production NASM fourth adapter.
Read-only observer; no pose/health/ammo/tick/economic writes.
"""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,sys,tempfile,time
from test_coop import Peer
server,library=map(lambda s:pathlib.Path(s).resolve(),sys.argv[1:3])
with tempfile.TemporaryDirectory(prefix='rh-defend-udp-')as directory:
 private=pathlib.Path(directory)/'adapter.so';private.write_bytes(library.read_bytes());l=C.CDLL(str(private))
 l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_client_input.argtypes=[C.c_uint]+[C.c_float]*4;l.net_client_order.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','450'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
 try:
  ready=json.loads(host.stdout.readline());address=('127.0.0.1',ready['port'])
  symbols={r[2]:int(r[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(r:=line.split())==3}
  memory=os.open(f'/proc/{host.pid}/mem',os.O_RDONLY)
  def read(name,n,offset=0):return os.pread(memory,n,symbols[name]+offset)
  def u32(name,offset=0):return struct.unpack('<I',read(name,4,offset))[0]
  def body(i):return struct.unpack('<5f11I',read('sim_players',64,i*64))
  def control(key):return struct.unpack('<4I2f2I',read('company_controls',32,key*32))
  for _ in range(3):
   peer=Peer(address);assert peer.request(1)[0]==0;peers.append(peer)
  assert l.net_client_open(b'127.0.0.1',ready['port'])==0
  moving=False;last_input=0
  def until(predicate,seconds=5):
   global last_input
   deadline=time.monotonic()+seconds
   while time.monotonic()<deadline:
    l.net_client_poll()
    for p in peers:p.receive(0)
    if time.monotonic()-last_input>.2:
     for i,p in enumerate(peers):p.input(x=.1 if moving and i==0 else 0.)
     if C.c_uint.in_dll(l,'net_connected').value:l.net_client_input(0,0.,0.,0.,0.)
     last_input=time.monotonic()
    value=predicate()
    if value:return value
    assert host.poll() is None,'authority ended before defend observations'
    time.sleep(.003)
   raise AssertionError('defend network condition timed out')
  until(lambda:C.c_uint.in_dll(l,'net_connected').value and all(l.net_company_for_player(i)>=0 for i in range(4)))
  keys=[u32('player_companies',i*16)for i in range(4)];assert len(set(keys))==4
  before=body(0);_,funds,tick=peers[0].input()
  status,balance,accepted_tick=peers[0].command(4,struct.pack('<IIff',0,4,before[0],before[2]),lose_ack=True)
  assert status==0 and balance==funds+39*(accepted_tick//30-tick//30)-5
  original=control(keys[0]);assert original[2:4]==(4,1) and original[6]==1
  assert peers[0].command(4,struct.pack('<IIff',0,5,before[0],before[2]))[0]==1
  assert peers[1].command(4,struct.pack('<IIff',0,4,before[0],before[2]))[0]==5
  assert control(keys[0])==original
  remote=(C.c_ubyte*160).in_dll(l,'net_company_records')
  until(lambda:struct.unpack_from('<I',remote,16)[0]==4)
  # Production assembly sender and whole-batch receiver also execute mode4.
  until(lambda:C.c_uint.in_dll(l,'net_pending').value==0)
  adapter=(C.c_float*64).in_dll(l,'sim_players');front=C.c_uint.in_dll(l,'net_front').value
  assert l.net_client_order(front,4,adapter[48],adapter[50])==0
  until(lambda:C.c_uint.in_dll(l,'net_pending').value==0 and control(keys[3])[2]==4)
  until(lambda:struct.unpack_from('<I',remote,3*40+16)[0]==4)
  assert control(keys[3])[6]==1
  base=(keys[0]%256)*128
  def members():
   raw=read('sim_entities',128*32,base*32);hazards=read('hazard_states',128*32,base*32)
   return {base+j:struct.unpack_from('<2f6I',raw,j*32)for j in range(128)
           if (r:=struct.unpack_from('<2f6I',raw,j*32))[2] and r[3]==0 and r[4]==0 and r[5]==0
           and struct.unpack_from('<I',hazards,j*32+4)[0]==0}
  initial=members();assert len(initial)>=8
  owner_initial=body(0);start_tick=u32('sim_tick_count');moving=True
  until(lambda:u32('sim_tick_count')>=start_tick+120,6);moving=False
  final=members();owner_final=body(0)
  assert owner_final[15]==owner_initial[15],('walking trace changed body generation',owner_initial,owner_final)
  assert owner_final[0]-owner_initial[0]>8 and abs(owner_final[2]-owner_initial[2])<.1
  retained=set(initial)&set(final);assert len(retained)>=8
  progressing=[]
  for i in retained:
   if initial[i][7]!=final[i][7]:continue
   radius=24+((i&127)>>3)*12;angle=(i&7)*math.pi/4
   gx=max(480,min(7520,before[0]))+radius*math.cos(angle)
   gz=max(480,min(7520,before[2]))+radius*math.sin(angle)
   displacement=(final[i][0]-initial[i][0],final[i][1]-initial[i][1]);direction=(gx-initial[i][0],gz-initial[i][1])
   if math.hypot(*displacement)>.5 and sum(a*b for a,b in zip(displacement,direction))>0:progressing.append(i)
  assert len(progressing)>=4,('quiet cohort did not progress toward defend slots',len(retained),progressing)
  assert control(keys[0])==original,'movement rewrote or recharged the command'
  for p in peers:p.command(5);p.socket.close()
  peers=[];l.net_client_close();stdout,stderr=host.communicate(timeout=20);assert host.returncode==0,(stdout,stderr)
  print(json.dumps({'suite':'company-defend-actual-udp','passed':True,'units':8192,'four_exclusive_keys':keys,
                   'lost_defend_ACK_one_cost_one_sequence':True,'production_adapter_defend_mode4':True,'invalid_mode_and_foreign_ownership_rejected':True,
                   'owner_walk_m':owner_final[0]-owner_initial[0],'retained_quiet_infantry':len(retained),
                   'quiet_infantry_progress_toward_initial_defend_slots':progressing,'accepted_command_preserved':True,
                   'observer_writes':False,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),
                   'library_sha256':hashlib.sha256(private.read_bytes()).hexdigest(),
                   'limits':['Read-only real original8192/four-endpoint transport and120-tick movement observation.',
                             'Mixed-role distinct-slot convergence is verified by separate causal API traces; no whole-operation traffic/graphics/performance claim.']}))
 finally:
  l.net_client_close()
  if memory is not None:os.close(memory)
  for p in peers:p.socket.close()
  if host.poll() is None:host.kill();host.communicate()
