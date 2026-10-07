#!/usr/bin/env python3
"""Development-only paired whole-client light controls; frozen presentation clocks.
Real separate cannon-impact producer, original client8192 army retained.
"""
import ctypes as C,ctypes.util,hashlib,json,os,pathlib,select,signal,struct,subprocess,sys,tempfile,time
EXE=pathlib.Path(sys.argv[1]).resolve();LIB=pathlib.Path(sys.argv[2]).resolve()
X=C.CDLL(ctypes.util.find_library('X11'));D=C.c_void_p;W=C.c_ulong
X.XOpenDisplay.argtypes=[C.c_char_p];X.XOpenDisplay.restype=D
X.XDefaultRootWindow.argtypes=[D];X.XDefaultRootWindow.restype=W
X.XQueryTree.argtypes=[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)]
X.XFetchName.argtypes=[D,W,C.POINTER(C.c_char_p)];X.XFree.argtypes=[D]
X.XGetImage.argtypes=[D,W,C.c_int,C.c_int,C.c_uint,C.c_uint,W,C.c_int];X.XGetImage.restype=D
X.XGetPixel.argtypes=[D,C.c_int,C.c_int];X.XGetPixel.restype=W
X.XDestroyImage.argtypes=[D];X.XCloseDisplay.argtypes=[D]

world=C.CDLL(str(LIB));world.effects_update.argtypes=[C.c_uint,C.c_float]
assert world.sim_init(32,1)==0
entities=(C.c_uint*(32768*8)).in_dll(world,'sim_entities')
for i in range(32):entities[i*8+2]=0
floats=C.cast(entities,C.POINTER(C.c_float))
for i,x,hp in ((12,3500.,400),(16,3700.,100)):
 floats[i*8]=x;floats[i*8+1]=2000.;entities[i*8+2]=hp
for side in (0,1):
 for front in range(3):assert world.sim_order(side,front,1)==0
assert world.player_join(0,0)==0
player=(C.c_float*16).in_dll(world,'sim_players');player[0],player[1],player[2]=3500,22.8,2000
cooldown=(C.c_uint*32768).in_dll(world,'sim_shell_cooldown');cooldown[12]=1
world.sim_tick();world.effects_update(0,0);assert world.projectile_spawn(12,16)==0
for _ in range(25):world.sim_tick()
world.effects_update(0,0)
pool=bytes((C.c_ubyte*2048).in_dll(world,'effects_records'))
records=[struct.unpack_from('<5f3I',pool,i*32)for i in range(64)]
flash=next(r for r in records if r[7]==2 and r[3]>0)
read,write=os.pipe();server=process=display=memory=None
try:
 with tempfile.TemporaryFile()as log:
  server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x360x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log);os.close(write);write=-1
  assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
  display=X.XOpenDisplay(env['DISPLAY'].encode());assert display
  process=subprocess.Popen([str(EXE),'--width','640','--height','360'],cwd=EXE.parent,env=env,stdout=log,stderr=log)
  symbols={line.split()[2]:int(line.split()[0],16)for line in subprocess.check_output(['nm','-n',str(EXE)],text=True).splitlines()if len(line.split())==3}
  memory=os.open(f'/proc/{process.pid}/mem',os.O_RDWR)
  def get(name,size):return os.pread(memory,size,symbols[name])
  def u32(name):return struct.unpack('<I',get(name,4))[0]
  def put(name,data):os.pwrite(memory,data,symbols[name])
  def until(predicate):
   deadline=time.monotonic()+15
   while time.monotonic()<deadline:
    if predicate():return
    if process.poll()is not None:
     log.seek(0);raise AssertionError(log.read().decode(errors='replace'))
    time.sleep(.02)
   raise AssertionError('client frame timeout')
  def stop():os.kill(process.pid,signal.SIGSTOP);_,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
  until(lambda:u32('frame_count')>=4);stop();put('thirty',struct.pack('<d',1e30));put('accum',struct.pack('<d',0));put('maxdt',struct.pack('<d',0))
  put('sim_players',struct.pack('<5f',flash[0],flash[1]+4,flash[2]-40,0,.08));put('yaw',struct.pack('<f',0));put('pitch',struct.pack('<f',.08))
  # Consume any real initial events, then substitute genuine immutable separate impact samples.
  frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+3);stop();put('effects_records',pool)
  count=C.c_uint();root=W();parent=W();children=C.POINTER(W)();X.XQueryTree(display,X.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count));window=0
  for win in list(children[:count.value]):
   name=C.c_char_p()
   if X.XFetchName(display,win,C.byref(name))and name:
    if name.value.startswith(b'RED HORIZON'):window=win
    X.XFree(C.cast(name,D))
  if children:X.XFree(children)
  assert window and u32('sim_count')==8192
  def digest():return hashlib.sha256(b''.join(get(name,size)for name,size in (('sim_entities',8192*32),('sim_aircraft',8192*64),('sim_players',256),('sim_events',8192),('sim_projectiles',32768),('sim_tick_count',4)))).hexdigest()
  authority=digest();ticks=u32('local_sim_ticks')
  def capture(on,tactical=0):
   put('event_lights_enabled',struct.pack('<I',on));put('tactical',struct.pack('<I',tactical));frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+5);stop()
   assert digest()==authority and u32('local_sim_ticks')==ticks and get('effects_records',2048)==pool
   assert u32('event_light_count')==(1 if on else 0)
   image=X.XGetImage(display,window,0,0,640,360,W(-1).value,2);assert image;pixels=bytearray()
   for y in range(360):
    for x in range(640):
     value=X.XGetPixel(image,x,y);pixels.extend(((value>>16)&255,(value>>8)&255,value&255))
   X.XDestroyImage(image);return pixels
  off=capture(0);on=capture(1);repeat=capture(1);map_off=capture(0,1);map_on=capture(1,1)
  changed=lambda a,b:sum(max(abs(a[i+k]-b[i+k])for k in range(3))>2 for i in range(0,len(a),3))
  pixels=changed(off,on);assert pixels>50,pixels
  assert changed(on,repeat)==0 and changed(map_off,map_on)==0
  path=pathlib.Path(sys.argv[3]);path.write_bytes(b'P6\n640 360\n255\n'+on)
  print(json.dumps(dict(suite='event-lights-whole-client',passed=True,changed_surface_pixels=pixels,repeat_delta_pixels=0,tactical_delta_pixels=0,original_army_count=8192,authority_sha256=authority,authority_and_effect_records_unchanged=True,actual_flash=flash,client_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),screenshot=str(path),scope='Actual full-client terrain/model/effect/HDR/bloom/HUD pipeline. Frozen development clock and camera fixture; genuine separate real cannon-impact effects copied unchanged. Paired only event_lights_enabled. No live synchronisation/shadow/target-GPU performance or artistic acceptance.')))
finally:
 if process is not None:
  if process.poll()is None:os.kill(process.pid,signal.SIGCONT);process.terminate()
  process.wait(timeout=5)
 if memory is not None:os.close(memory)
 if display:X.XCloseDisplay(display)
 if server:server.terminate();server.wait(timeout=5)
 if read>=0:os.close(read)
 if write>=0:os.close(write)
