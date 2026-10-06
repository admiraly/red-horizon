#!/usr/bin/env python3
"""Original8192/four-endpoint server, production adapter and own-stock reports.
Entire scene is unchanged; /proc observations are read-only, never freeze/write.
"""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,sys,tempfile,time
from test_coop import Peer
server,library=[pathlib.Path(p).resolve()for p in sys.argv[1:3]]
with tempfile.TemporaryDirectory(prefix='rh-player-ammo-udp-')as directory:
 private=pathlib.Path(directory)/'adapter.so';private.write_bytes(library.read_bytes());l=C.CDLL(str(private))
 l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;l.net_player_ammunition_report.argtypes=[C.c_uint,C.c_void_p,C.c_uint]
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','900'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
 try:
  ready=json.loads(host.stdout.readline());symbols={r[2]:int(r[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(r:=line.split())==3}
  memory=os.open(f'/proc/{host.pid}/mem',os.O_RDONLY)
  for _ in range(3):
   p=Peer(('127.0.0.1',ready['port']));assert p.request(1)[0]==0;peers.append(p)
  assert l.net_client_open(b'127.0.0.1',ready['port'])==0
  connected=C.c_uint.in_dll(l,'net_connected');owner=C.c_uint.in_dll(l,'net_player_id');stamp=C.c_uint.in_dll(l,'net_player_ammunition_tick');client_record=(C.c_uint*10).in_dll(l,'net_player_ammunition_record');last_input=0;desired=0;comparisons={};samples=[];retries=0;depleted=False;reloading=False;body_generations=set()
  def pump():
   global last_input
   l.net_client_poll()
   for p in peers:
    for _ in range(12):
     if p.receive(0)is None:break
   if time.monotonic()-last_input>.15:
    for p in peers:p.input()
    if connected.value:l.net_client_input(0,desired|4,-1.,0.,0.,0.)
    last_input=time.monotonic()
  def native():
   global retries
   if not connected.value:return None
   ident=owner.value;assert ident==3
   tick=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0];pb=symbols['sim_players']+ident*64;sb=symbols['player_ammunition']+ident*32
   player=os.pread(memory,64,pb);stock=os.pread(memory,32,sb)
   if player!=os.pread(memory,64,pb)or stock!=os.pread(memory,32,sb)or tick!=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0]:retries+=1;return None
   p=struct.unpack('<5f11I',player);s=struct.unpack('<8I',stock)
   if p[6]+s[1]+s[2]!=120+s[3]:retries+=1;return None
   if p[15]!=s[0]:retries+=1;return None
   assert 0<=p[5]<=100 and p[15]>0 and p[11]==1 and s[3]==0 and s[5:]==(120,0,0),(p,s)
   actual=(ident,p[15],p[6],s[1],s[2],s[3],s[4],s[5],1,0)if p[5]else(ident,p[15],0,0,0,0,0,0,0,0)
   out=(C.c_uint*10)()
   if l.net_player_ammunition_report(ident,out,40)==0:
    assert tuple(out)==tuple(client_record)
    if stamp.value==tick:
     assert tuple(out)==actual,(tick,tuple(out),actual);comparisons[tick]=actual
   return tick,p,s
  def until(fn,seconds=12):
   deadline=time.monotonic()+seconds
   while time.monotonic()<deadline:
    pump();row=native()
    if row and fn(row):return row
    assert host.poll()is None,'server ended before weapon observations'
    time.sleep(.003)
   raise AssertionError('own player stock transport observation timed out')
  row=until(lambda row:connected.value and len(comparisons)>0);assert row[1][6]==30 and row[2][1]==90 and row[1][12]==0
  # Genuine public sprint toward the rear while exercising the rifle. Follow
  # the real battlefield's damage/deployment, never renew HP or inventory.
  deadline=time.monotonic()+50;previous_sample=-1
  while time.monotonic()<deadline:
   pump();row=native()
   if row:
    t,p,s=row;body_generations.add(p[15]);depleted|=p[6]==0;reloading|=p[7]>0
    desired=0 if p[7]or not p[5]else(1 if p[6]else(2 if s[1]else 3))
    if t>=previous_sample+60:samples.append([t,p[15],p[5],p[6],s[1],s[2],p[12]]);previous_sample=t
    if t>=720:break
   assert host.poll()is None,'server ended during actual player stock observation'
   time.sleep(.003)
  else:raise AssertionError('own-stock battlefield observations timed out')
  assert depleted and reloading and row[1][12]>=30 and len(comparisons)>=20,(depleted,reloading,row,len(comparisons))
  assert any(r[3]<90 for r in comparisons.values()if r[8])
  assert C.c_uint.in_dll(l,'sim_tick_count').value>0
  l.net_client_close()
  for p in peers:p.command(5);p.socket.close()
  peers=[];stdout,stderr=host.communicate(timeout=30);assert host.returncode==0,(stdout,stderr)
  print(json.dumps({'suite':'player-ammunition-original-four-endpoint-udp','passed':True,'units':8192,'production_adapter_owner':3,'endpoints':4,'unchanged_initial_world':True,'observer_writes':False,'actual_lifetime_rifle_shots':row[1][12],'observed_depleted_magazine':depleted,'observed_reload':reloading,'actual_body_generations':sorted(body_generations),'public_sprint_rearward_input':True,'same_tick_exact_authority_report_comparisons':len(comparisons),'reserve_levels':sorted({r[3]for r in comparisons.values()if r[8]}),'magazine_samples':samples,'stable_read_retries':retries,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'adapter_sha256':hashlib.sha256(private.read_bytes()).hexdigest(),'limits':['Own player report correlated exactly at observed native snapshot ticks; not every packet or whole-army stock replication.','Original8192/world and real public inputs, no setup/live pose/HP/stock/clock writes.','Tracks real damage/new bodies in the original battlefield. Single-body120-round depletion and finite-store exhaustion are separate genuine CPU traces.','Rendered reserve/empty/timeout feedback and broad faults are separate.']}))
 finally:
  l.net_client_close()
  for p in peers:p.socket.close()
  if memory is not None:os.close(memory)
  if host.poll()is None:host.kill();host.communicate()
