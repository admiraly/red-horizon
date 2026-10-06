#!/usr/bin/env python3
"""Original8192/four-endpoint authority; read-only finite-round observation."""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,sys,tempfile,time
from test_coop import Peer
server,library=[pathlib.Path(x).resolve()for x in sys.argv[1:3]]
with tempfile.TemporaryDirectory(prefix='rh-infantry-udp-')as directory:
 private=pathlib.Path(directory)/'adapter.so';private.write_bytes(library.read_bytes());l=C.CDLL(str(private))
 l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_client_input.argtypes=[C.c_uint]+[C.c_float]*4
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','390'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
 try:
  ready=json.loads(host.stdout.readline());symbols={r[2]:int(r[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(r:=line.split())==3}
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
   raw=os.pread(memory,8192*32,symbols['infantry_weapons']);again=os.pread(memory,len(raw),symbols['infantry_weapons'])
   if raw!=again:retries+=1;return None
   rows=[struct.unpack_from('<8I',raw,i*32)for i in range(8192)]
   if any(r[0]!=1 or r[1]+r[2]+r[4]!=120 or r[1]>30 or r[2]>90 or r[3]>60 or (r[3] and r[1]) for i,r in enumerate(rows)if (i&15)<12):retries+=1;return None
   assert all(r==(0,)*8 for i,r in enumerate(rows)if (i&15)>=12)
   tick=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0]
   return {'tick':tick,'infantry':6144,'rounds_remaining':sum(r[1]+r[2]for r in rows),'actual_shots':sum(r[4]for r in rows),'reload_records':sum(bool(r[3])for r in rows),'depleted_records':sum(r[4]==120 for r in rows)}
  samples=[until(snapshot)];start=samples[0]['tick']
  for delta in (90,180,270):
   until(lambda:struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0]>=start+delta)
   samples.append(until(snapshot))
  assert samples[-1]['actual_shots']>samples[0]['actual_shots']>0,samples
  assert all(s['rounds_remaining']+s['actual_shots']==6144*120 for s in samples)
  assert all(a['actual_shots']<=b['actual_shots'] for a,b in zip(samples,samples[1:]))
  for p in peers:p.command(5);p.socket.close()
  peers=[];l.net_client_close();stdout,stderr=host.communicate(timeout=20);assert host.returncode==0,(stdout,stderr)
  print(json.dumps({'suite':'infantry-ammunition-original-four-endpoint-udp','passed':True,'units':8192,'endpoints':4,'observer_writes':False,'stocks_conserved_across_real_combat':True,'stable_samples':samples,'transient_read_retries':retries,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'adapter_sha256':hashlib.sha256(private.read_bytes()).hexdigest(),'limits':['Original declared world, no fixture births or live pose/health/stock/clock changes. Stock records observed on authority only; not replicated NPC ammo or rendered reload acceptance.']}))
 finally:
  l.net_client_close()
  for p in peers:p.socket.close()
  if memory is not None:os.close(memory)
  if host.poll()is None:host.kill();host.communicate()
