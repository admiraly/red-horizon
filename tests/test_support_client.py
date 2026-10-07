#!/usr/bin/env python3
"""Actual assembly client support instances/GL pixels; private frozen fixtures."""
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
read,write=os.pipe();server=process=display=memory=None
try:
 with tempfile.TemporaryFile() as log:
  server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x360x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log);os.close(write);write=-1
  assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
  display=X.XOpenDisplay(env['DISPLAY'].encode());assert display
  process=subprocess.Popen([str(EXE),'--width','640','--height','360'],cwd=EXE.parent,env=env,stdout=log,stderr=log)
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
  ticks=u32('local_sim_ticks');put('air_trails_visible',struct.pack('<I',0));put('effects_records',bytes(2048));put('sim_projectile_count',struct.pack('<I',0));put('sim_projectiles',bytes(32768))
  count=C.c_uint()
  root=W();parent=W();children=C.POINTER(W)();X.XQueryTree(display,X.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count));window=0
  for win in list(children[:count.value]):
   name=C.c_char_p()
   if X.XFetchName(display,win,C.byref(name)) and name:
    if name.value.startswith(b'RED HORIZON'):window=win
    X.XFree(C.cast(name,D))
  if children:X.XFree(children)
  assert window
  def capture(label):
   frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+5);stop()
   image=X.XGetImage(display,window,0,0,640,360,W(-1).value,2);assert image;pixels=bytearray()
   for y in range(360):
    for x in range(640):
     value=X.XGetPixel(image,x,y);pixels.extend(((value>>16)&255,(value>>8)&255,value&255))
   X.XDestroyImage(image);path=pathlib.Path(tempfile.gettempdir())/('red-horizon-support-'+label+'.ppm');path.write_bytes(b'P6\n640 360\n255\n'+pixels);return pixels,str(path),struct.unpack('<16f',get('mesh_ground_pose',64))
  rows=[]
  for role in (1,2):
   for mode,distance,tactical in (('near',32.,0),('mid',300.,0),('distant',2000.,0),('map',900.,1)):
    expected=(C.c_float*16)();assert world.ground_support(expected,role,64,5750,5200,math.pi/2)==0
    contact=(C.c_float*16)();assert world.ground_contact(contact,role,64,5750,5200,math.pi/2,expected[1],expected[2])==0
    expected[0]=max(expected[0],contact[0])
    # Exercise a true distant marker beyond both hull thresholds at640x360;
    # a900m low hull can have subpixel height despite its longer bounding span.
    # Keep this transform oracle above the ridge and off the crosshair.
    camera_x=5630 if mode=='distant' else 5750
    camera_y=expected[0]+(80 if mode=='distant' else 8)
    put('sim_players',struct.pack('<5f',camera_x,camera_y,5200-distance,0,-.05));put('yaw',struct.pack('<f',0));put('pitch',struct.pack('<f',-.05));put('tactical',struct.pack('<I',tactical));put('sim_count',struct.pack('<I',0));background,_,_=capture(f'{role}-{mode}-background')
    put('sim_count',struct.pack('<I',1));put('sim_entities',struct.pack('<2f6I',5750,5200,400 if role==1 else 160,0,role,0,0xffffffff,1));put('sim_ground_motion',struct.pack('<5f3I',math.pi/2,0,0,0,0,1,role,1));authority=tuple(get(name,size) for name,size in (('sim_entities',1048576),('sim_ground_motion',1048576),('sim_players',256)))
    pixels,path,pose=capture(f'{role}-{mode}');assert pose[0]==5750 and pose[2]==5200 and pose[14]==role
    assert abs(pose[1]-expected[0])<1e-5 and abs(pose[7]-expected[1])<1e-6 and abs(pose[11]-expected[2])<1e-6 and pose[15]==1,(role,mode,pose,tuple(expected))
    assert authority==tuple(get(name,size) for name,size in (('sim_entities',1048576),('sim_ground_motion',1048576),('sim_players',256))) and ticks==u32('local_sim_ticks'),'render changed authority'
    changed=sum(max(abs(pixels[i+k]-background[i+k]) for k in range(3))>20 for i in range(0,len(pixels),3));assert changed>(25 if mode=='near' else 0),(role,mode,changed,struct.unpack('<3f',get('camera',12)),tuple(u32(n)for n in ('mesh_high_instances','mesh_low_instances','mesh_marker_instances')))
    rows.append({'role':role,'mode':mode,'changed_source_pixels':changed,'pose_y_pitch_bank':(pose[1],pose[7],pose[11]),'screenshot':path})
  # Actual renderer spring after a changed authoritative hull axis at fixed XZ.
  # This is a stopped-clock observer fixture, not a claim about natural motion.
  dynamic=[]
  put('tactical',struct.pack('<I',0))
  for h in (0.,.7,-.5):
   before=struct.unpack('<6f2If3I',get('mesh_ground_cache',48))
   expected=(C.c_float*16)();assert world.ground_support(expected,2,64,5750,5200,h)==0
   put('sim_ground_motion',struct.pack('<5f3I',h,0,0,0,0,1,2,1))
   authority=tuple(get(name,size) for name,size in (('sim_entities',1048576),('sim_ground_motion',1048576),('sim_players',256)))
   _,path,pose=capture('dynamic-'+str(h));after=struct.unpack('<6f2If3I',get('mesh_ground_cache',48));elapsed=after[8]-before[8]
   assert elapsed>0 and after[6:8]==(1,2)
   for i,w in ((1,16),(2,18)):
    q=before[i]-expected[i];k=before[i+3]+w*q;e=math.exp(-w*elapsed)
    want=expected[i]+(q+k*elapsed)*e;velocity=(before[i+3]-w*k*elapsed)*e
    assert abs(after[i]-want)<4e-6 and abs(after[i+3]-velocity)<3e-5,('actual spring',i,after,want,velocity,elapsed)
   assert pose[1]==after[0] and pose[7]==after[1] and pose[11]==after[2]
   contact=(C.c_float*16)();assert world.ground_contact(contact,2,64,5750,5200,h,after[1],after[2])==0
   assert pose[1]>=contact[0]-2e-5 and max(abs(after[i]-expected[i]) for i in (1,2))>1e-4,'no intermediate pose/contact'
   assert authority==tuple(get(name,size) for name,size in (('sim_entities',1048576),('sim_ground_motion',1048576),('sim_players',256))) and ticks==u32('local_sim_ticks')
   dynamic.append({'heading':h,'elapsed_seconds':elapsed,'pitch_bank':after[1:3],'target_pitch_bank':tuple(expected[1:3]),'contact_floor':contact[0],'rendered_y':pose[1],'screenshot':path})
  # A recycled or inactive sidecar must keep upright relative-height fallback.
  put('tactical',struct.pack('<I',0));put('sim_players',struct.pack('<5f',5750,expected[0]+8,5168,0,-.05))
  for generation,flags in ((2,1),(1,0)):
   put('sim_ground_motion',struct.pack('<5f3I',math.pi/2,0,0,0,0,generation,2,flags));_,_,pose=capture('stale-'+str(generation)+'-'+str(flags));assert pose[1]==0 and pose[7]==0 and pose[11]==0 and pose[15]==0,pose
  print(json.dumps({'suite':'ground-support-client','passed':True,'client_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'cases':rows,'authority_unchanged':True,'stale_inactive_fallback':True,'dynamic_response':dynamic,'scope':'Actual sourced-client instance hooks, near/mid/distant/map GL and read-only frozen fixtures; analytical dynamic response on frozen observer fixtures; no natural gameplay or physical suspension acceptance'}))
finally:
 if process is not None:
  if process.poll() is None:os.kill(process.pid,signal.SIGCONT);process.terminate()
  process.wait(timeout=5)
 if memory is not None:os.close(memory)
 if display:X.XCloseDisplay(display)
 if server is not None:server.terminate();server.wait(timeout=5)
 if read>=0:os.close(read)
 if write>=0:os.close(write)
