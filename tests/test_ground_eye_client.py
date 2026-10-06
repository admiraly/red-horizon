#!/usr/bin/env python3
"""Actual local and UDP graphical driver's terrain-supported eye observer.
Initial positions only are fixtures. Frozen network preview is labelled cosmetic.
"""
import ctypes as C,ctypes.util,json,math,os,pathlib,select,signal,struct,subprocess,sys,tempfile,time
CLIENT,SERVER=(pathlib.Path(x).resolve() for x in sys.argv[1:3]);ROOT=pathlib.Path(__file__).resolve().parents[1]
X=C.CDLL(ctypes.util.find_library('X11'));XT=C.CDLL(ctypes.util.find_library('Xtst'));D,W=C.c_void_p,C.c_ulong
for name,args,rest in [('XOpenDisplay',[C.c_char_p],D),('XDefaultRootWindow',[D],W),('XQueryTree',[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)],C.c_int),('XFetchName',[D,W,C.POINTER(C.c_char_p)],C.c_int),('XKeysymToKeycode',[D,W],C.c_uint),('XGetImage',[D,W,C.c_int,C.c_int,C.c_uint,C.c_uint,W,C.c_int],D),('XGetPixel',[D,C.c_int,C.c_int],W)]:
 fn=getattr(X,name);fn.argtypes=args;fn.restype=rest
X.XFree.argtypes=[D];X.XRaiseWindow.argtypes=[D,W];X.XSetInputFocus.argtypes=[D,W,C.c_int,W];X.XFlush.argtypes=[D];X.XCloseDisplay.argtypes=[D];X.XDestroyImage.argtypes=[D]
XT.XTestFakeKeyEvent.argtypes=[D,C.c_uint,C.c_int,W];XT.XTestFakeButtonEvent.argtypes=[D,C.c_uint,C.c_int,W];XT.XTestFakeMotionEvent.argtypes=[D,C.c_int,C.c_int,C.c_int,W]
processes=[];memories=[];display=None;read_fd,write_fd=os.pipe()
def syms(exe):return {s[2]:int(s[0],16) for line in subprocess.check_output(['nm','-n',str(exe)],text=True).splitlines() if len(s:=line.split())==3}
def wait(fn,seconds=6):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  value=fn()
  if value:return value
  assert all(p.poll() is None for p in processes),'private process exited'
  time.sleep(.02)
 raise AssertionError('ground eye client condition timed out')
def stop(p):
 os.kill(p.pid,signal.SIGSTOP);_,status=os.waitpid(p.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
def run(p):os.kill(p.pid,signal.SIGCONT)
def title(w):
 n=C.c_char_p()
 if not X.XFetchName(display,w,C.byref(n)) or not n:return ''
 s=n.value.decode(errors='replace');X.XFree(C.cast(n,D));return s
def window(network=False):
 r,p,ch,n=W(),W(),C.POINTER(W)(),C.c_uint();X.XQueryTree(display,X.XDefaultRootWindow(display),C.byref(r),C.byref(p),C.byref(ch),C.byref(n))
 found=next((w for w in ch[:n.value] if 'RED HORIZON' in title(w) and ('CO-OP P0' in title(w) if network else 'HP 100 ' in title(w))),0)
 if ch:X.XFree(ch)
 return found
def focus(w):
 X.XRaiseWindow(display,w);X.XSetInputFocus(display,w,2,0);XT.XTestFakeMotionEvent(display,0,640,360,0);X.XFlush(display);time.sleep(.1)
def key(k,down):XT.XTestFakeKeyEvent(display,X.XKeysymToKeycode(display,ord(k)),int(down),0);X.XFlush(display)
def tap(k,duration=.12):key(k,True);time.sleep(duration);key(k,False);time.sleep(.08)
def button(down):XT.XTestFakeButtonEvent(display,1,int(down),0);X.XFlush(display)
def read(mem,sym,name,fmt,off=0):return struct.unpack(fmt,os.pread(mem,struct.calcsize(fmt),sym[name]+off))
def put(mem,sym,name,fmt,*values,off=0):os.pwrite(mem,struct.pack(fmt,*values),sym[name]+off)
def player(mem,sym):return read(mem,sym,'sim_players','<5f11I')
def pose(mem,sym,i):return read(mem,sym,'sim_ground_motion','<5f3I',i*32)
def entity(mem,sym,i):return read(mem,sym,'sim_entities','<2f6I',i*32)
def mapping(mem,sym):return read(mem,sym,'sim_player_vehicle','<i')[0]
with tempfile.TemporaryDirectory(prefix='rh-eye-client-') as td:
 td=pathlib.Path(td);objs=[]
 for i,name in enumerate(('terrain','terrain_relief','ground_support','ground_contact','ground_eye')):
  obj=td/f'{i}.o';subprocess.run([os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm'),'-f','elf64','-I',str(ROOT)+'/',str(ROOT/f'src/nav/{name}.asm'),'-o',str(obj)],check=True);objs.append(str(obj))
 library=td/'eye.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-lm','-o',str(library)],check=True);lib=C.CDLL(str(library))
 lib.ground_eye.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*3;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
 def expected(e,g):
  out=(C.c_float*3)();assert lib.ground_eye(out,1,12,e[0],e[1],g[0])==0;return tuple(out)
 def birth(p,mem,sym,count):
  stop(p)
  try:
   army=os.pread(mem,count*32,sym['sim_entities']);armor=next(i for i in range(count) if struct.unpack_from('<4I',army,i*32+8)[1:]==(0,1,0) and struct.unpack_from('<I',army,i*32+8)[0]>0)
   for i in range(count):
    x,z=struct.unpack_from('<2f',army,i*32);side=struct.unpack_from('<I',army,i*32+12)[0]
    put(mem,sym,'sim_entities','<2f',x+(-2500 if side==0 else 2500),z,off=i*32)
   put(mem,sym,'sim_entities','<2f',5795.,5250.,off=armor*32)
   put(mem,sym,'sim_players','<5f',5801.,lib.terrain_height(5801.,5250.)+1.8,5250.,0.,0.)
  finally:run(p)
  return armor
 def observe(mem,sym,i):
  # Retry transient in-tick reads; require coherent entity/motion stamps and eye.
  e,g,p=entity(mem,sym,i),pose(mem,sym,i),player(mem,sym)
  if e[7]!=g[5] or g[6:]!=(1,1) or mapping(mem,sym)!=i:return None
  want=expected(e,g);error=max(abs(a-b) for a,b in zip(p[:3],want))
  return (e,g,p,want,error)
 try:
  xvfb=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1280x720x24','-nolisten','tcp'],pass_fds=(write_fd,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);processes.append(xvfb)
  os.close(write_fd);write_fd=None;assert select.select([read_fd],[],[],10)[0];number=os.read(read_fd,32).decode().strip();os.close(read_fd);read_fd=None
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None);display=X.XOpenDisplay(env['DISPLAY'].encode());assert display
  sym=syms(CLIENT);local=subprocess.Popen([str(CLIENT)],cwd=CLIENT.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);processes.append(local)
  win=wait(window);focus(win);mem=os.open(f'/proc/{local.pid}/mem',os.O_RDWR);memories.append(mem);armor=birth(local,mem,sym,8192)
  tap('e');wait(lambda:mapping(mem,sym)==armor)
  rows=[]
  def sample():
   row=observe(mem,sym,armor)
   if row and row[4]<.002:rows.append(row);return row
  try:initial=wait(sample)
  except AssertionError as exc:raise AssertionError(('supported driver eye did not match live hull',observe(mem,sym,armor))) from exc
  legacy_gap=math.dist(initial[2][:3],(initial[0][0],lib.terrain_height(*initial[0][:2])+3,initial[0][1]));assert legacy_gap>.25,legacy_gap
  key('w',True)
  try:
   end=time.monotonic()+1.1
   while time.monotonic()<end:sample();time.sleep(.025)
  finally:key('w',False)
  assert len(rows)>8 and math.dist(rows[0][0][:2],rows[-1][0][:2])>.3,'GUI drive did not move supported hull'
  assert all(abs(r[1][1])<=.6001 and math.hypot(r[1][3],r[1][4])<=.601 for r in rows)
  wait(lambda:(r:=sample()) and abs(r[1][1])<.001)
  # Real held right input causes bounded tracked turn; reverse is real S input.
  key('d',True);time.sleep(.5);key('d',False);turned=wait(sample)
  key('a',True);time.sleep(.5);key('a',False)
  key('s',True)
  try:reversed_row=wait(lambda:(r:=sample()) and r[1][1]<-.001 and r,2)
  finally:key('s',False)
  assert abs(turned[1][0]-initial[1][0])>.05,'GUI turn did not change hull axis'
  assert all(abs(v)<1e5 and math.isfinite(v) for v in reversed_row[2][:5])
  before=read(mem,sym,'vehicle_shots','<I')[0];button(True);time.sleep(.35);button(False);wait(lambda:read(mem,sym,'vehicle_shots','<I')[0]>before)
  wait(lambda:(r:=sample()) and abs(r[1][1])<.001)
  stationary=wait(sample);wait(lambda:math.dist(read(mem,sym,'camera','<3f'),stationary[3])<.08)
  assert math.dist(read(mem,sym,'visual_target','<3f'),stationary[2][:3])<.002
  aim=read(mem,sym,'sim_players','<2f',12);assert math.dist(aim,read(mem,sym,'yaw','<f')+read(mem,sym,'pitch','<f'))<.002
  image=X.XGetImage(display,win,0,0,1280,720,W(-1).value,2);assert image
  rgb=bytearray()
  for yy in range(720):
   for xx in range(1280):
    pixel=X.XGetPixel(image,xx,yy);rgb.extend(((pixel>>16)&255,(pixel>>8)&255,pixel&255))
  X.XDestroyImage(image)
  screenshot=pathlib.Path(tempfile.gettempdir())/'red-horizon-supported-driver-eye.ppm';screenshot.write_bytes(b'P6\n1280 720\n255\n'+rgb)
  tap('q');wait(lambda:mapping(mem,sym)==-1)
  assert read(mem,sym,'vehicle_entity_driver','<i',armor*4)[0]==-1
  assert read(mem,sym,'vehicle_driver_generation','<I')[0]==0
  local.terminate();local.wait(timeout=3);processes.remove(local)
  # Actual UDP client receives supported eye and mapping from an assembly server.
  host=subprocess.Popen([str(SERVER),'--port','0','--units','512'],cwd=SERVER.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);processes.append(host);ready=json.loads(host.stdout.readline());ss=syms(SERVER)
  net=subprocess.Popen([str(CLIENT),'--connect','127.0.0.1','--port',str(ready['port'])],cwd=CLIENT.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);processes.append(net)
  nw=wait(lambda:window(True));focus(nw);nm=os.open(f'/proc/{net.pid}/mem',os.O_RDWR);hm=os.open(f'/proc/{host.pid}/mem',os.O_RDWR);memories.extend((nm,hm));wait(lambda:player(hm,ss)[11]==1);ni=birth(host,hm,ss,512)
  wait(lambda:abs(player(nm,sym)[0]-5801)<1);tap('e');wait(lambda:mapping(hm,ss)==ni);wait(lambda:mapping(nm,sym)==ni)
  nr=wait(lambda:(r:=observe(hm,ss,ni)) and r[4]<.002 and r)
  wait(lambda:math.dist(player(nm,sym)[:3],nr[2][:3])<.05)
  # Cosmetic timing fixture only: freeze this own server after a real boarding
  # snapshot; hold W and extend preview age to isolate camera path before timeout.
  stop(host);stop(net)
  put(nm,sym,'net_predict_timeout','<d',10.)
  run(net);key('w',True)
  try:
   wait(lambda:math.hypot(read(nm,sym,'wish_x','<f')[0],read(nm,sym,'wish_z','<f')[0])>.2,1)
   assert read(nm,sym,'net_connected','<I')[0]==1
   target_samples=[];end=time.monotonic()+.7
   while time.monotonic()<end:
    p=player(nm,sym);target=read(nm,sym,'visual_target','<3f')
    assert math.dist(target,p[:3])<.002,('boarded network foot preview displaced XYZ',target,p[:3])
    target_samples.append(target);time.sleep(.02)
  finally:key('w',False);run(host)
  assert len(target_samples)>10
  print(json.dumps(dict(suite='ground-eye-client',passed=True,local_supported_samples=len(rows),legacy_upright_eye_gap=legacy_gap,observed_reverse_speed=reversed_row[1][1],exit_cleared_driver_generation=True,screenshot=str(screenshot),real_keyboard_board_drive_turn_reverse_fire_exit=True,camera_converges_and_world_aim_preserved=True,network_actual_boarding_supported_eye=True,network_preview_samples=len(target_samples),network_preview_fixture='own server frozen and client preview-age extended; cosmetic path only, not fault/latency acceptance',software_gl=True)))
 finally:
  if display:
   for k in ('e','w','a','s','d','q'):key(k,False)
   button(False)
   X.XCloseDisplay(display);display=None
  for p in reversed(processes):
   if p.poll() is None:
    os.kill(p.pid,signal.SIGCONT);p.terminate()
    try:p.wait(timeout=3)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)
  for m in memories:os.close(m)
  if display:X.XCloseDisplay(display)
  if read_fd is not None:os.close(read_fd)
  if write_fd is not None:os.close(write_fd)
