#!/usr/bin/env python3
"""Real8192 authority induced-turn energy loss replicated through the assembly UDP adapter."""
import ctypes as C,json,math,os,pathlib,signal,struct,subprocess,sys,time
library=pathlib.Path(sys.argv[1]).resolve();server=pathlib.Path(sys.argv[2]).resolve()
l=C.CDLL(str(library));l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_client_poll.restype=C.c_int
connected=C.c_uint.in_dll(l,'net_connected');a=(C.c_ubyte*(32768*64)).in_dll(l,'sim_aircraft');e=(C.c_ubyte*(32768*32)).in_dll(l,'sim_entities')
p=subprocess.Popen([str(server),'--port','0','--ticks','600','--units','8192'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);memory=None
try:
 ready=json.loads(p.stdout.readline());assert ready['units']==8192
 assert l.net_client_open(b'127.0.0.1',ready['port'])==0
 deadline=time.monotonic()+3
 while not connected.value and time.monotonic()<deadline:l.net_client_poll();time.sleep(.01)
 assert connected.value
 symbols={v.split()[2]:int(v.split()[0],16)for v in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(v.split())==3}
 memory=os.open(f'/proc/{p.pid}/mem',os.O_RDWR)
 def u32(name):return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]
 deadline=time.monotonic()+3
 while u32('sim_tick_count')<3 and time.monotonic()<deadline:l.net_client_poll();time.sleep(.01)
 os.kill(p.pid,signal.SIGSTOP);_,status=os.waitpid(p.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
 try:
  assert u32('sim_count')==8192;ident=None
  for i in range(8192):
   body=struct.unpack('<2f6I',os.pread(memory,32,symbols['sim_entities']+i*32));air=struct.unpack('<5f11I',os.pread(memory,64,symbols['sim_aircraft']+i*64));fuel=struct.unpack('<4I',os.pread(memory,16,symbols['sim_air_fuel']+i*16))
   if body[2]>0 and body[3]==0 and body[4]==3 and air[5]==1 and air[10]==body[7] and air[15]&1 and fuel[0]==body[7] and fuel[1]>0:ident=i;break
  assert ident is not None
  before=dict(hp=body[2],generation=body[7],ammo=air[9],role=air[5],front=body[5]);z=2000.*(body[5]+1)
  own=C.c_uint.in_dll(l,'net_player_id').value
  z=6900.
  os.pwrite(memory,struct.pack('<3f',6900.,17.8,z+100),symbols['sim_players']+own*64)
  os.pwrite(memory,struct.pack('<2f',6900.,z),symbols['sim_entities']+ident*32)
  os.pwrite(memory,struct.pack('<5f',180.,math.pi/4,0.,-math.acos(1/8),6.8),symbols['sim_aircraft']+ident*64)
  os.pwrite(memory,struct.pack('<3f',6.8/math.sqrt(2),0.,6.8/math.sqrt(2)),symbols['sim_aircraft']+ident*64+44)
  # Existing finite fuel is retained; the real boundary maneuver spends energy.
  initial_fuel=fuel[1]
 finally:os.kill(p.pid,signal.SIGCONT)
 samples=[];deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  assert p.poll()is None,'server exited before speed capture'
  l.net_client_poll();pose=struct.unpack_from('<5fII',a,ident*64);body=struct.unpack_from('<2f6I',e,ident*32)
  if pose[4]<=6.8 and body[2]>0 and (not samples or pose[4]!=samples[-1]['speed']):
   samples.append(dict(x=body[0],z=body[1],y=pose[0],speed=pose[4],mode=pose[6],hp=body[2],generation=body[7]))
   if len(samples)>=4 and samples[-1]['speed']<samples[0]['speed']-.1:break
  time.sleep(.01)
 assert len(samples)>=4 and samples[-1]['speed']<samples[0]['speed']-.1 and all(5<=v['speed']<=7 and v['generation']==before['generation']for v in samples),samples
 assert all(v['speed']<u['speed'] for u,v in zip(samples,samples[1:])),samples
 actual=struct.unpack('<5f11I',os.pread(memory,64,symbols['sim_aircraft']+ident*64));assert actual[9]==before['ammo'] and actual[10]==before['generation']
 remaining=struct.unpack('<I',os.pread(memory,4,symbols['sim_air_fuel']+ident*16+4))[0];assert 0<remaining<initial_fuel
 print(json.dumps(dict(suite='air-energy-actual-UDP',passed=True,original_army_count=8192,source=ident,preserved_source=before,received_real_turn_deceleration=samples,initial_finite_fuel=initial_fuel,remaining_finite_fuel=remaining,server_tick=u32('sim_tick_count'),scope='Actual separate8192 authority sim_tick and full type103 NASM UDP adapter. One-time player/plane staging, existing finite fuel, no HP/gen/ammo or live clock/fuel renewal. Not low-speed/stall/landing, full operation, graphics/audio or bandwidth/performance acceptance.')))
finally:
 l.net_client_close()
 if memory is not None:os.close(memory)
 if p.poll()is None:os.kill(p.pid,signal.SIGCONT);p.terminate()
 p.communicate(timeout=5)
