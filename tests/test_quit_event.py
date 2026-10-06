#!/usr/bin/env python3
"""Actual GLFW client: press/release queued within one event batch must quit."""
import ctypes as C,ctypes.util,json,os,pathlib,select,signal,subprocess,sys,tempfile,time,struct,hashlib
exe=pathlib.Path(sys.argv[1]).resolve();negative='--expect-missed' in sys.argv
X=C.CDLL(ctypes.util.find_library('X11'));XT=C.CDLL(ctypes.util.find_library('Xtst'));D=C.c_void_p;W=C.c_ulong
X.XOpenDisplay.argtypes=[C.c_char_p];X.XOpenDisplay.restype=D;X.XDefaultRootWindow.argtypes=[D];X.XDefaultRootWindow.restype=W
X.XQueryTree.argtypes=[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)];X.XFetchName.argtypes=[D,W,C.POINTER(C.c_char_p)];X.XFree.argtypes=[D]
X.XSetInputFocus.argtypes=[D,W,C.c_int,W];X.XFlush.argtypes=[D];X.XSync.argtypes=[D,C.c_int];X.XCloseDisplay.argtypes=[D]
X.XKeysymToKeycode.argtypes=[D,W];X.XKeysymToKeycode.restype=C.c_uint;XT.XTestFakeKeyEvent.argtypes=[D,C.c_uint,C.c_int,W]
symbols={p[2]:int(p[0],16) for line in subprocess.check_output(['nm','-n',str(exe)],text=True).splitlines() if len(p:=line.split())==3}
read,write=os.pipe();xvfb=process=display=memory=None
try:
 with tempfile.TemporaryFile() as log:
  xvfb=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x360x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log);os.close(write);write=-1
  assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();os.close(read);read=-1
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
  display=X.XOpenDisplay(env['DISPLAY'].encode());assert display
  process=subprocess.Popen([str(exe),'--tactical','--width','640','--height','360'],cwd=exe.parent,env=env,stdout=log,stderr=log)
  memory=os.open(f'/proc/{process.pid}/mem',os.O_RDONLY)
  def frames():return struct.unpack('<I',os.pread(memory,4,symbols['frame_count']))[0]
  deadline=time.monotonic()+15
  while frames()<4:
   assert process.poll() is None;assert time.monotonic()<deadline;time.sleep(.02)
  os.kill(process.pid,signal.SIGSTOP);_,state=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(state)
  count=C.c_uint();root=W();parent=W();children=C.POINTER(W)();X.XQueryTree(display,X.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count));window=0
  for win in list(children[:count.value]):
   name=C.c_char_p()
   if X.XFetchName(display,win,C.byref(name)) and name:
    if name.value.startswith(b'RED HORIZON'):window=win
    X.XFree(C.cast(name,D))
  if children:X.XFree(children)
  assert window;X.XSetInputFocus(display,window,2,0);code=X.XKeysymToKeycode(display,0xff1b);assert code
  XT.XTestFakeKeyEvent(display,code,1,0);XT.XTestFakeKeyEvent(display,code,0,0);X.XSync(display,0)
  initial=frames();os.kill(process.pid,signal.SIGCONT);started=time.monotonic();deadline=started+5
  if negative:
   while process.poll() is None and frames()<initial+3 and time.monotonic()<deadline:time.sleep(.01)
   assert process.poll() is None and frames()>=initial+3,'negative did not expose the missed delivered tap'
  else:
   process.wait(timeout=5);assert process.returncode==0
  print(json.dumps({'suite':'actual-client-quit-event','passed':True,'negative_missed_tap':negative,'queued_press_and_release_while_stopped':True,'elapsed_seconds':time.monotonic()-started,'exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'limits':['Private software GL/Xvfb; no physical desktop input or full game acceptance.','SIGSTOP controls event delivery only; no simulation/HP/pose/store/clock writes.']}))
finally:
 if process is not None and process.poll() is None:
  try:os.kill(process.pid,signal.SIGCONT)
  except ProcessLookupError:pass
  process.terminate()
  try:process.wait(timeout=5)
  except subprocess.TimeoutExpired:process.kill();process.wait()
 if memory is not None:os.close(memory)
 if display:X.XCloseDisplay(display)
 if xvfb is not None:
  xvfb.terminate();xvfb.wait(timeout=5)
 for fd in (read,write):
  if fd>=0:os.close(fd)
