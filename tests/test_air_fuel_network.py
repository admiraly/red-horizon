#!/usr/bin/env python3
"""Genuine8192 authority fuel exhaustion through UDP into the real NASM adapter.
One initial own player/aircraft pose and fuel fixture; no subsequent renewal.
"""
import ctypes as C,json,math,os,pathlib,signal,struct,subprocess,sys,time
library=pathlib.Path(sys.argv[1]).resolve();server=pathlib.Path(sys.argv[2]).resolve()
l=C.CDLL(str(library));l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_client_poll.restype=C.c_int
connected=C.c_uint.in_dll(l,'net_connected');a=(C.c_ubyte*(32768*64)).in_dll(l,'sim_aircraft');e=(C.c_ubyte*(32768*32)).in_dll(l,'sim_entities')
p=subprocess.Popen([str(server),'--port','0','--ticks','600','--units','8192'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);memory=None
try:
 line=p.stdout.readline();assert line,('server readiness missing',p.communicate(timeout=3),p.returncode)
 ready=json.loads(line);assert ready['units']==8192
 assert l.net_client_open(b'127.0.0.1',ready['port'])==0
 deadline=time.monotonic()+3
 while not connected.value and time.monotonic()<deadline:l.net_client_poll();time.sleep(.01)
 assert connected.value
 symbols={line.split()[2]:int(line.split()[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(line.split())==3}
 memory=os.open(f'/proc/{p.pid}/mem',os.O_RDWR)
 def read(name,n):return os.pread(memory,n,symbols[name])
 def u32(name):return struct.unpack('<I',read(name,4))[0]
 deadline=time.monotonic()+3
 while u32('sim_tick_count')<3 and time.monotonic()<deadline:l.net_client_poll();time.sleep(.01)
 os.kill(p.pid,signal.SIGSTOP);_,status=os.waitpid(p.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
 try:
  assert u32('sim_count')==8192
  ident=None
  for i in range(8192):
   body=struct.unpack('<2f6I',os.pread(memory,32,symbols['sim_entities']+i*32));air=struct.unpack('<5f11I',os.pread(memory,64,symbols['sim_aircraft']+i*64));fuel=struct.unpack('<4I',os.pread(memory,16,symbols['sim_air_fuel']+i*16))
   if body[2]>0 and body[4]==3 and air[5]==1 and air[10]==body[7] and air[15]&1 and fuel[0]==body[7] and fuel[1]>0:ident=i;break
  assert ident is not None
  before=dict(hp=body[2],generation=body[7],ammo=air[9],role=air[5])
  # Clear quiet supported terrain, actual source body's role/HP/gen/ammo retained.
  own=C.c_uint.in_dll(l,'net_player_id').value
  os.pwrite(memory,struct.pack('<3f',2000.,17.8,3900.),symbols['sim_players']+own*64)
  os.pwrite(memory,struct.pack('<2f',2200.,3900.),symbols['sim_entities']+ident*32)
  os.pwrite(memory,struct.pack('<4f',110.,math.pi/2,0.,0.),symbols['sim_aircraft']+ident*64)
  os.pwrite(memory,struct.pack('<3f',7.,0.,0.),symbols['sim_aircraft']+ident*64+44)
  os.pwrite(memory,struct.pack('<I',0),symbols['sim_air_fuel']+ident*16+4)
 finally:os.kill(p.pid,signal.SIGCONT)
 samples=[];deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  assert p.poll()is None,'server exited before mode capture'
  l.net_client_poll();pose=struct.unpack_from('<5fII',a,ident*64);body=struct.unpack_from('<2f6I',e,ident*32)
  if pose[6]==4 and body[2]>0 and (not samples or pose[0]!=samples[-1]['y']):
   samples.append(dict(y=pose[0],pitch=pose[2],mode=pose[6],hp=body[2],generation=body[7]))
   if len(samples)>=3:break
  time.sleep(.01)
 assert len(samples)>=3 and samples[-1]['y']<samples[0]['y'] and all(x['generation']==before['generation']for x in samples),samples
 actual=struct.unpack('<5f11I',os.pread(memory,64,symbols['sim_aircraft']+ident*64));assert actual[9]==before['ammo'] and actual[10]==before['generation']
 assert struct.unpack('<I',os.pread(memory,4,symbols['sim_air_fuel']+ident*16+4))[0]==0
 print(json.dumps(dict(suite='air-fuel-actual-UDP',passed=True,original_army_count=8192,source=ident,preserved_source=before,received_powerless_glide=samples,server_tick=u32('sim_tick_count'),scope='Actual separate8192 authority sim_tick and full type103 UDP adapter. One-time own player/plane/fuel staging, no HP/gen/ammo or live clock/fuel renewal. Confirms decreasing-height glide replication, not multiplayer operation/GPU/audio/performance/landing acceptance.')))
finally:
 l.net_client_close()
 if memory is not None:os.close(memory)
 if p.poll()is None:os.kill(p.pid,signal.SIGCONT);p.terminate()
 p.communicate(timeout=5)
