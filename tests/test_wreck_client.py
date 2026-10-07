#!/usr/bin/env python3
"""Actual local/UDP client wreck draw hooks; stopped-clock geometry fixtures."""
import socket
from xvfb_display import read_display_number
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT
import ctypes as C,ctypes.util,hashlib,json,math,os,pathlib,select,signal,struct,subprocess,sys,tempfile,time
EXE=pathlib.Path(sys.argv[1]).resolve();LIB=pathlib.Path(sys.argv[2]).resolve();ROOT=pathlib.Path(__file__).resolve().parents[1]
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
  number=read_display_number(read,10);os.close(read);read=-1
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
   def send(payload,tick,kind=106):relay.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(payload),9)+payload,destination)
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
    assert process.poll() is None,'client exited';time.sleep(.02)
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
     until(lambda:get('net_wrecks',64)==source_record)
    frame=u32('frame_count');until(lambda:u32('frame_count')>=frame+5);stop()
    # SIGSTOP can land between wreck submission and the later marker pass.
    # Require the completed-pass stamp before comparing any live counters.
    if u32('mesh_counts_complete')==1 and u32('mesh_wreck_instances')==instances and (instance_bytes is None or get('mesh_wreck_pose',64)==instance_bytes):break
    assert time.monotonic()<deadline,'completed wreck draw telemetry timeout'
   image=X.XGetImage(display,window,0,0,640,360,W(-1).value,2);assert image;pixels=bytearray()
   for y in range(360):
    for x in range(640):
     value=X.XGetPixel(image,x,y);pixels.extend(((value>>16)&255,(value>>8)&255,value&255))
   X.XDestroyImage(image);path=pathlib.Path(tempfile.gettempdir())/('red-horizon-wreck-'+('udp' if network else 'local')+'-'+label+'.ppm');path.write_bytes(b'P6\n640 360\n255\n'+pixels);return pixels,str(path),struct.unpack('<16f',get('mesh_wreck_pose',64))
  rows=[];sequence=0;clock=0
  world.sim_init.argtypes=[C.c_uint,C.c_uint];assert world.sim_init(64,42)==0
  world.wreck_register.argtypes=[C.c_uint]
  entities=(C.c_ubyte*1048576).in_dll(world,'sim_entities');motion=(C.c_ubyte*1048576).in_dll(world,'sim_ground_motion');wrecks=(C.c_ubyte*65536).in_dll(world,'sim_wrecks')
  for role in (1,2):
   for mode,distance,tactical in (('near',32.,0),('mid',300.,0),('far',900.,0),('map',900.,1)):
    world.wreck_init();C.memmove(C.addressof(entities),struct.pack('<2f6I',5750,5200,0,0,role,0,0xffffffff,1),32);C.memmove(C.addressof(motion),struct.pack('<5f3I',.7,0,0,0,0,1,role,1),32);assert world.wreck_register(0)==0;record=bytes(wrecks[:64]);fields=struct.unpack('<6f10I',record)
    put('sim_players',struct.pack('<5f',5750,fields[1]+8,5200-distance,0,-.05));put('yaw',struct.pack('<f',0));put('pitch',struct.pack('<f',-.05));put('tactical',struct.pack('<I',tactical));put('sim_count',struct.pack('<I',1 if network else 0))
    if network:
     # Source-clock tombstone removes prior fixture, then a new immutable slot.
     background_record=None
     if sequence:
      clock+=1800;old=bytearray(last_record);struct.pack_into('<I',old,52,fields_flags&2);send(struct.pack('<I',0)+old,clock);background_record=bytes(old)
    else:put('sim_wrecks',bytes(65536));put('sim_wreck_count',struct.pack('<I',0))
    background,_,_=capture(f'{role}-{mode}-background',background_record if network else None);before_counts=tuple(u32(n) for n in ('mesh_high_instances','mesh_low_instances','mesh_marker_instances'));assert u32('mesh_wreck_instances')==0
    sequence+=1;record=bytearray(record);struct.pack_into('<III',record,40,clock,(clock+1800)&0xffffffff,sequence);record=bytes(record);last_record=record;fields_flags=struct.unpack_from('<I',record,52)[0]
    if network:send(struct.pack('<I',0)+record,clock)
    else:put('sim_wrecks',record);put('sim_wreck_count',struct.pack('<I',1))
    expected=struct.pack('<16f',fields[0],fields[1],fields[2],fields[3],0,0,0,fields[4],1,1,1,fields[5],-1,3,role,1)
    pixels,path,pose=capture(f'{role}-{mode}',record if network else None,0 if mode=='far' else 1,None if mode=='far' else expected)
    assert u32('mesh_wreck_instances')==(0 if mode=='far' else 1),(role,mode,u32('net_connected'),u32('net_wreck_count'),get('camera',12),pose)
    if mode!='far':assert struct.pack('<16f',*pose)==expected,(role,mode,pose)
    source='net_wrecks' if network else 'sim_wrecks';assert get(source,64)==record,'renderer changed death pose'
    assert before_counts==tuple(u32(n) for n in ('mesh_high_instances','mesh_low_instances','mesh_marker_instances')),('wreck inflated live mesh counters',role,mode,before_counts,tuple(u32(n) for n in ('mesh_high_instances','mesh_low_instances','mesh_marker_instances')),u32('frame_count'))
    changed=sum(max(abs(pixels[i+k]-background[i+k]) for k in range(3))>20 for i in range(0,len(pixels),3))
    if mode in ('near','mid'):assert changed>(25 if mode=='near' else 0),(role,mode,changed)
    rows.append({'role':role,'mode':mode,'changed_pixels':changed,'wreck_instances':u32('mesh_wreck_instances'),'screenshot':path})
    assert ticks==u32('local_sim_ticks'),'stopped-clock render ticked gameplay'
  print(json.dumps({'suite':'wreck-client-draw','passed':True,'network_transport':network,'private_display_connection_attempts':display_attempts,'client_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'cases':rows,'received_record_then_completed_draw_observed':True,'immutable_death_pose':True,'living_instance_counts_unchanged':True,'scope':'Actual local/realUDP client draw hooks, frame0 high source geometry, near/mid/map/cull and expiry replacement. Frozen cosmetic geometry fixture from actual registry helper; actual server casualty/expiry proven separately. SoftwareGL, not natural play or GPU budgets.'}))

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
