#!/usr/bin/env python3
"""Real8192/four-endpoint finite physical shell death through production UDP."""
import ctypes as C,hashlib,json,os,pathlib,signal,struct,subprocess,sys,tempfile,time
from test_coop import Peer
server,library=[pathlib.Path(p).resolve()for p in sys.argv[1:3]]
with tempfile.TemporaryDirectory(prefix='rh-blast-udp-')as directory:
 private=pathlib.Path(directory)/'adapter.so';private.write_bytes(library.read_bytes());l=C.CDLL(str(private))
 l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;l.net_player_ammunition_report.argtypes=[C.c_uint,C.c_void_p,C.c_uint]
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','300'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
 try:
  ready=json.loads(host.stdout.readline());symbols={r[2]:int(r[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(r:=line.split())==3}
  connected=C.c_uint.in_dll(l,'net_connected');owner=C.c_uint.in_dll(l,'net_player_id');wire_tick=C.c_uint.in_dll(l,'net_server_tick');wire=(C.c_ubyte*256).in_dll(l,'sim_players');stock_tick=C.c_uint.in_dll(l,'net_player_ammunition_tick')
  assert l.net_client_open(b'127.0.0.1',ready['port'])==0
  deadline=time.monotonic()+5
  while not connected.value and time.monotonic()<deadline:l.net_client_poll();time.sleep(.002)
  assert connected.value and owner.value==0
  for _ in range(3):
   p=Peer(('127.0.0.1',ready['port']));assert p.request(1)[0]==0;peers.append(p)
  memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
  def integer(name,offset=0):return struct.unpack('<I',os.pread(memory,4,symbols[name]+offset))[0]
  os.kill(host.pid,signal.SIGSTOP)
  try:
   _,status=os.waitpid(host.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
   os.pwrite(memory,struct.pack('<fff',2005.,17.8,3900.),symbols['sim_players'])
   generation=integer('sim_players',60)
   for ident,z,front,target in ((12,3900.,1,0xffffffff),(4108,4300.,0,12)):
    address=symbols['sim_entities']+ident*32;row=list(struct.unpack('<ff6I',os.pread(memory,32,address)))
    assert row[2]>0 and row[4]==1 and row[7]>0
    row[0],row[1],row[5],row[6]=2000.,z,front,target
    os.pwrite(memory,struct.pack('<ff6I',*row),address)
   for index in (1,3):
    os.pwrite(memory,struct.pack('<I',1),symbols['orders']+index*4)
    os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+index*64+24)
   shells_before=integer('sim_shell_ammo',4108*4);assert shells_before>0
   fixture_tick=integer('sim_tick_count');sequence=integer('sim_event_sequence')
  finally:os.kill(host.pid,signal.SIGCONT)
  # Reopen read-only; no writes or freezes after the one startup fixture.
  os.close(memory);memory=os.open(f'/proc/{host.pid}/mem',os.O_RDONLY)
  last_input=0;impacts=[];native_dead=wire_dead=unknown_dead=wire_new_body=False;comparisons=0;samples=[];retries=0
  deadline=time.monotonic()+12
  while time.monotonic()<deadline:
   l.net_client_poll()
   for p in peers:
    for _ in range(12):
     if p.receive(0)is None:break
   if time.monotonic()-last_input>.1:
    l.net_client_input(0,0,0.,0.,0.,0.)
    for p in peers:p.input()
    last_input=time.monotonic()
   wt=wire_tick.value;wp=struct.unpack('<5f11I',bytes(wire[:64]))
   wire_dead|=wp[5]==0 and wp[15]==generation and wp[9]>0
   out=(C.c_uint*10)()
   if l.net_player_ammunition_report(0,out,40)==0 and wp[5]==0 and wp[15]==generation and out[1]==generation and tuple(out[2:8])==(0,)*6 and out[8]==0:unknown_dead=True
   wire_new_body|=wp[5]==100 and wp[15]==generation+1
   tick=integer('sim_tick_count');completed=integer('sim_tick_completed');pb=os.pread(memory,64,symbols['sim_players']);sb=os.pread(memory,32,symbols['player_ammunition'])
   if tick!=completed or tick!=integer('sim_tick_count')or completed!=integer('sim_tick_completed')or pb!=os.pread(memory,64,symbols['sim_players'])or sb!=os.pread(memory,32,symbols['player_ammunition']):retries+=1;time.sleep(.002);continue
   body=struct.unpack('<5f11I',pb);stock=struct.unpack('<8I',sb)
   native_dead|=body[5]==0 and body[15]==generation
   if wt==tick:
    assert wp==body,(tick,wp,body);comparisons+=1
   now=integer('sim_event_sequence')
   for number in range(sequence+1,now+1):
    event=struct.unpack('<3f3IfI',os.pread(memory,32,symbols['sim_events']+(number&255)*32))
    if event[3]==3 and event[4]==1 and abs(event[0]-2005.)<18 and abs(event[2]-3900.)<18:impacts.append(event)
   sequence=now
   if not samples or body[5:10]!=tuple(samples[-1][1:6])or body[15]!=samples[-1][-1]:samples.append([tick,body[5],body[6],body[7],body[8],body[9],stock[1],body[15]])
   # Retain the original five exact same-tick comparisons before stopping.
   # Early completed lifecycle observation alone is not the full acceptance gate.
   if native_dead and wire_dead and unknown_dead and wire_new_body and comparisons>=5:
    assert body[5]==100 and body[15]==generation+1 and body[6]==30 and stock[1]==90
    break
   assert host.poll()is None,'server ended before physical blast/deployment observation'
   time.sleep(.002)
  else:raise AssertionError((native_dead,wire_dead,unknown_dead,wire_new_body,samples,impacts))
  shells_after=integer('sim_shell_ammo',4108*4);assert impacts and shells_after<shells_before and comparisons>=5,(impacts,shells_before,shells_after,comparisons)
  l.net_client_close()
  for p in peers:p.command(5);p.socket.close()
  peers=[];stdout,stderr=host.communicate(timeout=15);assert host.returncode==0,(stdout,stderr)
  print(json.dumps({'suite':'physical-human-blast-four-endpoint-UDP','passed':True,'units':8192,'endpoints':4,'startup_fixture_tick':fixture_tick,'production_adapter_owner':0,'native_and_wire_real_death':True,'dead_own_stock_explicit_unknown':True,'genuine_new_body30_plus90':True,'same_tick_exact_public_body_comparisons':comparisons,'finite_shells_before_after':[shells_before,shells_after],'real_hostile_impacts':impacts,'samples':samples,'stable_read_retries':retries,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'adapter_sha256':hashlib.sha256(private.read_bytes()).hexdigest(),'limits':['One startup pose/order fixture, retaining original8192 army HP/kind/generation/finite stores. Read-only and unfrozen afterward.','Production state/own report transport verified; dedicated rendered multiplayer blast pixel and bomber UDP traces separate.']}))
 finally:
  l.net_client_close()
  for p in peers:p.socket.close()
  if memory is not None:os.close(memory)
  if host.poll()is None:host.kill();host.communicate()
