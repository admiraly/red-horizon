#!/usr/bin/env python3
"""Original8192/four-endpoint authority; read-only finite-round observation."""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,sys,tempfile,time,signal
from test_coop import Peer
server,library=[pathlib.Path(x).resolve()for x in sys.argv[1:3]]
encounter='--resupply-encounter' in sys.argv
with tempfile.TemporaryDirectory(prefix='rh-infantry-udp-')as directory:
 private=pathlib.Path(directory)/'adapter.so';private.write_bytes(library.read_bytes());l=C.CDLL(str(private))
 l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_client_input.argtypes=[C.c_uint]+[C.c_float]*4
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','390'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
 try:
  ready=json.loads(host.stdout.readline());symbols={r[2]:int(r[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(r:=line.split())==3}
  initial_encounter=None
  if encounter:
   # One declared startup encounter only. Keep8192 actors, identities, health,
   # infantry stores and all other ammo intact; no observer writes after setup.
   os.kill(host.pid,signal.SIGSTOP)
   try:
    fixture=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
    try:
     t=struct.unpack('<I',os.pread(fixture,4,symbols['sim_tick_count']))[0]
     original_source=struct.unpack('<2f6I',os.pread(fixture,32,symbols['sim_entities']))
     original_target=struct.unpack('<2f6I',os.pread(fixture,32,symbols['sim_entities']+4108*32))
     assert original_source[2:6]==(100,0,0,0) and original_target[2:5]==(400,1,1),(original_source,original_target)
     original_weapon=os.pread(fixture,32,symbols['infantry_weapons'])
     assert struct.unpack('<8I',original_weapon)[:5]==(1,30,90,0,0)
     os.pwrite(fixture,struct.pack('<2f',1020.,3900.),symbols['sim_entities'])
     os.pwrite(fixture,struct.pack('<2f',1240.,3900.),symbols['sim_entities']+4108*32)
     # Independently declared unarmed target, not a renewing combat resource.
     os.pwrite(fixture,struct.pack('<I',0),symbols['sim_shell_ammo']+4108*4)
     for front in (0,3+original_target[5]):
      os.pwrite(fixture,struct.pack('<I',1),symbols['orders']+front*4)
      os.pwrite(fixture,struct.pack('<I',1),symbols['ai_fronts']+front*64+24)
     assert os.pread(fixture,32,symbols['infantry_weapons'])==original_weapon
     initial_encounter={'tick':t,'source':0,'target':4108,'source_position':[1020,3900],'target_position':[1240,3900],'target_declared_shell_ammo':0,'unchanged_count':8192,'unchanged_health_and_generations':True,'unchanged_infantry_stocks':True}
    finally:os.close(fixture)
   finally:os.kill(host.pid,signal.SIGCONT)
  memory=os.open(f'/proc/{host.pid}/mem',os.O_RDONLY)
  for _ in range(3):
   p=Peer(('127.0.0.1',ready['port']));assert p.request(1)[0]==0;peers.append(p)
  assert l.net_client_open(b'127.0.0.1',ready['port'])==0
  last_input=0;retries=0
  def until(fn,seconds=6):
   global last_input
   deadline=time.monotonic()+seconds
   while time.monotonic()<deadline:
    l.net_client_poll()
    for p in peers:p.receive(0)
    if time.monotonic()-last_input>.2:
     for p in peers:p.input()
     if C.c_uint.in_dll(l,'net_connected').value:l.net_client_input(0,0.,0.,0.,0.)
     last_input=time.monotonic()
    result=fn()
    if result:return result
    assert host.poll()is None,'server terminated before stock observation'
    time.sleep(.003)
   raise AssertionError('ammo authority observation timed out')
  until(lambda:C.c_uint.in_dll(l,'net_connected').value)
  def snapshot():
   global retries
   # Retry observations crossing the short multi-field authoritative update.
   # Read-only observers never rewrite or freeze stocks/poses/health/clocks.
   raw=os.pread(memory,8192*32,symbols['infantry_weapons']);stock=os.pread(memory,12*16,symbols['depot_ammunition']);again=os.pread(memory,len(raw),symbols['infantry_weapons'])
   stock_again=os.pread(memory,len(stock),symbols['depot_ammunition'])
   if raw!=again or stock!=stock_again:retries+=1;return None
   rows=[struct.unpack_from('<8I',raw,i*32)for i in range(8192)]
   if any(r[0]!=1 or r[1]+r[2]+r[4]!=120+r[6] or r[1]>30 or r[2]>90 or r[3]>60 or (r[3] and r[1]) for i,r in enumerate(rows)if (i&15)<12):retries+=1;return None
   assert all(r==(0,)*8 for i,r in enumerate(rows)if (i&15)>=12)
   stores=[struct.unpack_from('<4I',stock,i*16)for i in range(12)]
   received=sum(r[6]for r in rows);issued=sum(s[1]for s in stores)
   if received!=issued:retries+=1;return None
   assert all(s[0]+s[1]==s[2] and s[3]==0 for s in stores)
   assert sum(s[2]for s in stores)==48000
   tick=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0]
   return {'tick':tick,'infantry':6144,'rounds_remaining':sum(r[1]+r[2]for r in rows),'actual_shots':sum(r[4]for r in rows),'reload_records':sum(bool(r[3])for r in rows),'depleted_records':sum(r[1]==r[2]==0 for i,r in enumerate(rows)if (i&15)<12),'received':received,'depot_remaining':sum(s[0]for s in stores),'depot_issued':issued}
  samples=[until(snapshot)];start=samples[0]['tick']
  for delta in ((120,240,340)if encounter else (90,180,270)):
   until(lambda:struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0]>=start+delta)
   samples.append(until(snapshot))
  assert samples[-1]['actual_shots']>samples[0]['actual_shots']>0,samples
  assert all(s['rounds_remaining']+s['actual_shots']+s['depot_remaining']==6144*120+48000 for s in samples)
  assert all(a['actual_shots']<=b['actual_shots'] for a,b in zip(samples,samples[1:]))
  receiver=None
  if encounter:
   receiver=struct.unpack('<8I',os.pread(memory,32,symbols['infantry_weapons']))
   target_hp=struct.unpack('<I',os.pread(memory,4,symbols['sim_entities']+4108*32+8))[0]
   assert receiver[0]==1 and receiver[6]>=30 and receiver[4]>30 and target_hp<310,(receiver,target_hp)
   assert receiver[1]+receiver[2]+receiver[4]==120+receiver[6]
   receiver={'generation':receiver[0],'magazine':receiver[1],'reserve':receiver[2],'shots':receiver[4],'received':receiver[6],'last_supply_tick':receiver[7],'target_hp':target_hp}
  for p in peers:p.command(5);p.socket.close()
  peers=[];l.net_client_close();stdout,stderr=host.communicate(timeout=20);assert host.returncode==0,(stdout,stderr)
  print(json.dumps({'suite':('infantry-resupply-staged-four-endpoint-udp'if encounter else 'infantry-ammunition-original-four-endpoint-udp'),'passed':True,'units':8192,'endpoints':4,'observer_writes':False,'initial_encounter':initial_encounter,'actual_receiver':receiver,'stocks_conserved_across_real_combat':True,'finite_depot_conservation':True,'stable_samples':samples,'transient_read_retries':retries,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'adapter_sha256':hashlib.sha256(private.read_bytes()).hexdigest(),'limits':['One explicit startup encounter/target-ammo declaration; no HP/identity/infantry-stock writes. Read-only and no freeze/renewal after setup.'if encounter else 'Original declared world, no fixture births or live pose/health/stock/clock changes.','Stock records observed on authority only; not replicated NPC ammo or rendered reload acceptance.']}))
 finally:
  l.net_client_close()
  for p in peers:p.socket.close()
  if memory is not None:os.close(memory)
  if host.poll()is None:host.kill();host.communicate()
