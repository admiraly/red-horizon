#!/usr/bin/env python3
"""Actual local/UDP client wreck draw hooks; stopped-clock geometry fixtures."""
import socket
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT
import ctypes as C,ctypes.util,hashlib,json,math,os,pathlib,select,signal,struct,subprocess,sys,tempfile,time
EXE=pathlib.Path(sys.argv[1]).resolve();LIB=pathlib.Path(sys.argv[2]).resolve();ROOT=pathlib.Path('/mnt/titan_nv3/projects/red-horizon-workers/air-world')
world=C.CDLL(str(LIB));world.ground_support.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_float,C.c_float,C.c_float];world.ground_support.restype=C.c_int
world.ground_contact.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*5;world.ground_contact.restype=C.c_int
X=C.CDLL(ctypes.util.find_library('X11'));D=C.c_void_p;W=C.c_ulong
X.XOpenDisplay.argtypes=[C.c_char_p];X.XOpenDisplay.restype=D
X.XDefaultRootWindow.argtypes=[D];X.XDefaultRootWindow.restype=W
X.XQueryTree.argtypes=[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)]
X.XFetchName.argtypes=[D,W,C.POINTER(C.c_char_p)];X.XFree.argtypes=[D]
X.XGetImage.argtypes=[D,W,C.c_int,C.c_int,C.c_uint,C.c_uint,W,C.c_int];X.XGetImage.restype=D
X.XGetPixel.argtypes=[D,C.c_int,C.c_int];X.XGetPixel.restype=W
X.XDestroyImage.argtypes=[D];X.XCloseDisplay.argtypes=[D]
network='--udp' in sys.argv;relay=socket.socket(socket.AF_INET,socket.SOCK_DGRAM) if network else None
if relay:relay.bind(('127.0.0.1',0));relay.settimeout(10)
read,write=os.pipe();server=process=display=memory=None
try:
 with tempfile.TemporaryFile() as log:
  server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x360x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log);os.close(write);write=-1
  assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
  # A display number does not prove this process opened an Xlib connection.
  # Bound connection retries before any game/graphics assertions.
  display_deadline=time.monotonic()+5;display_attempts=0
  while not display:
   display_attempts+=1;display=X.XOpenDisplay(env['DISPLAY'].encode())
   if display:break
   if server.poll() is not None or time.monotonic()>=display_deadline:
    log.seek(0);raise AssertionError({'private_display_unavailable':env['DISPLAY'],'Xvfb_exit':server.poll(),'connection_attempts':display_attempts,'Xvfb_log':log.read().decode(errors='replace')})
   time.sleep(.02)
  process=subprocess.Popen([str(EXE),'--width','640','--height','360',*(['--connect','127.0.0.1','--port',str(relay.getsockname()[1])] if network else [])],cwd=EXE.parent,env=env,stdout=log,stderr=log)
  if network:
   _,destination=relay.recvfrom(1200)
   def send(payload,tick,kind=119):relay.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(payload),9)+payload,destination)
   send(struct.pack('<4I',0,0,8192,100),0,2)
  symbols={line.split()[2]:int(line.split()[0],16) for line in subprocess.check_output(['nm','-n',str(EXE)],text=True).splitlines() if len(line.split())==3}
  memory=os.open(f'/proc/{process.pid}/mem',os.O_RDWR)
  def get(name,size):return os.pread(memory,size,symbols[name])
  def u32(name):
   try:return struct.unpack('<I',get(name,4))[0]
   except (OSError,struct.error):return 0
  def until(predicate):
   deadline=time.monotonic()+15
   while time.monotonic()<deadline:
    if predicate():return
    if process.poll() is not None:
     log.seek(0);raise AssertionError(dict(client_exit=process.returncode,client_log=log.read().decode(errors='replace')))
    time.sleep(.02)
   raise AssertionError('client frame timeout')
  def stop():os.kill(process.pid,signal.SIGSTOP);_,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
  def put(name,bytes):os.pwrite(memory,bytes,symbols[name])
  until(lambda:u32('frame_count')>=4);stop();put('thirty',struct.pack('<d',1e30));put('accum',struct.pack('<d',0));frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+3);stop()
  ticks=u32('local_sim_ticks');
  if network:
   os.pwrite(memory,struct.pack('<I',100),symbols['sim_players']+20);os.pwrite(memory,struct.pack('<I',1),symbols['sim_players']+44)
  put('air_trails_visible',struct.pack('<I',0));put('effects_records',bytes(2048));put('sim_projectile_count',struct.pack('<I',0));put('sim_projectiles',bytes(32768))
  count=C.c_uint()
  root=W();parent=W();children=C.POINTER(W)();X.XQueryTree(display,X.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count));window=0
  for win in list(children[:count.value]):
   name=C.c_char_p()
   if X.XFetchName(display,win,C.byref(name)) and name:
    if name.value.startswith(b'RED HORIZON'):window=win
    X.XFree(C.cast(name,D))
  if children:X.XFree(children)
  assert window
  def capture(label,source_record=None,instances=0,instance_bytes=None):
   deadline=time.monotonic()+15
   while True:
    os.kill(process.pid,signal.SIGCONT)
    if network and source_record is not None:
     until(lambda:get('net_air_crashes',96)==source_record)
    frame=u32('frame_count');until(lambda:u32('frame_count')>=frame+5);stop()
    # SIGSTOP can land between wreck submission and the later marker pass.
    # Require the completed-pass stamp before comparing any live counters.
    if u32('mesh_counts_complete')==1 and u32('mesh_air_crash_instances')==instances and (instance_bytes is None or get('mesh_air_crash_pose',64)==instance_bytes):break
    assert time.monotonic()<deadline,'completed wreck draw telemetry timeout'
   image=X.XGetImage(display,window,0,0,640,360,W(-1).value,2);assert image;pixels=bytearray()
   for y in range(360):
    for x in range(640):
     value=X.XGetPixel(image,x,y);pixels.extend(((value>>16)&255,(value>>8)&255,value&255))
   X.XDestroyImage(image);path=pathlib.Path(tempfile.gettempdir())/('red-horizon-air-crash-'+('udp' if network else 'local')+'-'+label+'.ppm');path.write_bytes(b'P6\n640 360\n255\n'+pixels);return pixels,str(path),struct.unpack('<16f',get('mesh_air_crash_pose',64))
  # Obtain immutable samples from a genuine public static-contact casualty in a separate
  # authority replay. The visible client is a frozen presentation fixture only.
  class Entity(C.Structure):
   _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
  class Air(C.Structure):
   _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
  e=(Entity*32768).in_dll(world,'sim_entities');air=(Air*32768).in_dll(world,'sim_aircraft');crashes=(C.c_ubyte*(128*96)).in_dll(world,'sim_air_crashes')
  rows=[]
  for role in (0,1):
   assert world.sim_init(64,42)==0
   for i in range(64):e[i].hp=0
   speed=5 if role==0 else 7
   e[31]=Entity(3980,1300,200,0,3,0,-1,1);air[31]=Air(46,math.pi/2,0,0,speed,role,0,-1,0,180,1,speed,0,0,0,1)
   living=(C.c_uint*2).in_dll(world,'sim_alive');living[0]=1;living[1]=0
   death=landing=None;samples=[]
   for tick in range(1,1808):
    world.sim_tick();record=bytes(crashes[:96]);fields=struct.unpack('<9f7I8I',record)
    if fields[15] and death is None:death=tick;samples.append(('death',tick,record))
    if death and tick==death+30:samples.append(('falling',tick,record))
    if fields[15]==2 and landing is None:landing=tick;samples.append(('landed',tick,record))
    if death and tick==death+1800:samples.append(('expired',tick,record));break
   assert death==1 and landing and len(samples)==4 and e[31].hp==0
   for label,tick,record in samples:
    if network:
     # Relocate only stream birth/sequence between independent role fixtures.
     transport=bytearray(record);struct.pack_into('<II',transport,52,death+role*2000,1+role);record=bytes(transport);tick+=role*2000
    f=struct.unpack('<9f7I8I',record)
    source='net_air_crashes' if network else 'sim_air_crashes'
    put('sim_players',struct.pack('<5f',f[0],f[1]+10,f[2]-100,0,-.05));put('yaw',struct.pack('<f',0));put('pitch',struct.pack('<f',-.05));put('tactical',struct.pack('<I',0));put('sim_count',struct.pack('<I',1 if network else 0))
    if network:os.pwrite(memory,struct.pack('<I',0),symbols['sim_entities']+8)
    put(source,bytes(128*96))
    background,_,_=capture(f'{role}-{label}-background');before_counts=tuple(u32(n) for n in ('mesh_high_instances','mesh_low_instances','mesh_marker_instances'))
    if network:send(struct.pack('<I',0)+record,tick)
    else:put(source,record)
    expected=struct.pack('<16f',f[0],f[1],f[2],f[6],0,0,0,f[7],1,1,1,f[8],-1,3,3 if role==0 else 8,1)
    active=int(f[15]!=0)
    pixels,path,pose=capture(f'{role}-{label}',source_record=record if network else None,instances=active,instance_bytes=expected if active else None)
    assert get(source,96)==record,'draw mutated crash authority sample'
    assert before_counts==tuple(u32(n) for n in ('mesh_high_instances','mesh_low_instances','mesh_marker_instances'))
    changed=sum(max(abs(pixels[i+k]-background[i+k]) for k in range(3))>20 for i in range(0,len(pixels),3))
    assert changed>25 if active else changed==0,(role,label,changed)
    assert ticks==u32('local_sim_ticks')
    rows.append(dict(role=role,phase=label,source_tick=tick,changed_pixels=changed,instances=active,screenshot=path))
  print(json.dumps(dict(suite='air-world-contact-client-draw',passed=True,network_transport=network,client_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),cases=rows,living_instance_counts_unchanged=True,source_unchanged=True,scope='Actual client GL draw of genuine separate public-static-contact authority samples, two initial role fixtures, no replay-body renewal. Frozen cosmetic paired background clears presentation cache; UDP case then receives genuine pose through actual parser before completed draw, relocating birth/sequence only between independent role fixtures. Live authority/client synchronisation separate. Software GL, no spectacle/timing acceptance.')))

finally:
 if relay:relay.close()
 if process is not None:
  if process.poll() is None:os.kill(process.pid,signal.SIGCONT);process.terminate()
  process.wait(timeout=5)
 if memory is not None:os.close(memory)
 if display:X.XCloseDisplay(display)
 if server is not None:server.terminate();server.wait(timeout=5)
 if read>=0:os.close(read)
 if write>=0:os.close(write)
