#!/usr/bin/env python3
"""Development private-X presentation flags, actual mapping/framebuffer and render."""
from xvfb_display import read_display_number
import ctypes as C,ctypes.util,json,os,pathlib,select,subprocess,sys,tempfile,time
exe=pathlib.Path(sys.argv[1]).resolve();root=pathlib.Path(__file__).resolve().parents[1]
class Attributes(C.Structure):
 _fields_=[('x',C.c_int),('y',C.c_int),('width',C.c_int),('height',C.c_int),('border_width',C.c_int),('depth',C.c_int),('visual',C.c_void_p),('root',C.c_ulong),('window_class',C.c_int),('bit_gravity',C.c_int),('win_gravity',C.c_int),('backing_store',C.c_int),('backing_planes',C.c_ulong),('backing_pixel',C.c_ulong),('save_under',C.c_int),('colormap',C.c_ulong),('map_installed',C.c_int),('map_state',C.c_int),('all_event_masks',C.c_long),('your_event_mask',C.c_long),('do_not_propagate_mask',C.c_long),('override_redirect',C.c_int),('screen',C.c_void_p)]
x=C.CDLL(ctypes.util.find_library('X11'));D,W=C.c_void_p,C.c_ulong
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=D;x.XCloseDisplay.argtypes=[D];x.XDefaultRootWindow.argtypes=[D];x.XDefaultRootWindow.restype=W
x.XQueryTree.argtypes=[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)];x.XFetchName.argtypes=[D,W,C.POINTER(C.c_char_p)];x.XFree.argtypes=[D];x.XGetWindowAttributes.argtypes=[D,W,C.POINTER(Attributes)]
read,write=os.pipe();server=None;display=None;child=None
try:
 env=dict(os.environ,RH_AUDIO_DEVICE='null');env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None)
 invalid=[['--hidden'],['--hidden','--frames','0'],['--hidden','--frames','10001'],['--hidden','--hidden','--frames','1'],['--no-vsync','--no-vsync'],['--hidden','--frames','bad'],['--frame-cap'],['--frame-cap','29'],['--frame-cap','241'],['--frame-cap','60','--frame-cap','60']]
 for args in invalid:
  run=subprocess.run([str(exe),*args],cwd=exe.parent,env=env,capture_output=True,text=True,timeout=5);assert run.returncode==1,(args,run.stdout,run.stderr)
 with tempfile.TemporaryDirectory(prefix='rh-presentation-') as temp:
  folder=pathlib.Path(temp)
  with (folder/'xvfb.log').open('wb') as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x480x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
  os.close(write);write=-1;number=read_display_number(read,10);assert number.isdigit();os.close(read);read=-1
  env.update(DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1');display=x.XOpenDisplay(env['DISPLAY'].encode());assert display
  rows=[]
  for hidden,no_vsync,cap in [(1,1,60),(0,0,0),(0,1,0)]:
   image=folder/f'{hidden}-{no_vsync}.ppm';args=[str(exe),'--frames','80','--width','320','--height','240','--screenshot',str(image)]
   if hidden:args.append('--hidden')
   if no_vsync:args.append('--no-vsync')
   if cap:args+=['--frame-cap',str(cap)]
   started=time.monotonic()
   child=subprocess.Popen(args,cwd=exe.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   window=0;deadline=time.monotonic()+10
   while not window and time.monotonic()<deadline:
    assert child.poll() is None,'client exited before mapping observation'
    parent,r=C.c_ulong(),C.c_ulong();children=C.POINTER(W)();count=C.c_uint();x.XQueryTree(display,x.XDefaultRootWindow(display),C.byref(r),C.byref(parent),C.byref(children),C.byref(count))
    for ident in children[:count.value]:
     name=C.c_char_p()
     if x.XFetchName(display,ident,C.byref(name)) and name:
      value=name.value.decode(errors='replace');x.XFree(C.cast(name,D))
      if value.startswith('RED HORIZON'):window=ident;break
    if children:x.XFree(children)
    if not window:time.sleep(.002)
   assert window,'GLFW window not found'
   attr=Attributes();assert x.XGetWindowAttributes(display,window,C.byref(attr));assert (attr.width,attr.height)==(320,240)
   # Visible creation can be observed between XCreateWindow and XMapWindow.
   while not hidden and attr.map_state!=2 and time.monotonic()<deadline:
    time.sleep(.002);assert x.XGetWindowAttributes(display,window,C.byref(attr))
   assert attr.map_state==(0 if hidden else 2),(hidden,attr.map_state)
   stdout,stderr=child.communicate(timeout=45);elapsed=time.monotonic()-started
   if cap:assert elapsed>=(80-2)/cap,('frame cap ran too quickly',elapsed)
   assert child.returncode==0,(stdout,stderr);child=None
   presentation=[json.loads(line) for line in stdout.splitlines() if line.startswith('{"client_presentation"')];assert len(presentation)==1,stdout
   settings=presentation[0];assert settings=={'client_presentation':True,'hidden':hidden,'swap_interval_requested':1-no_vsync,'viewport_width':320,'viewport_height':240,'framebuffer_width':320,'framebuffer_height':240},settings
   pacing=[json.loads(line) for line in stdout.splitlines() if line.startswith('{"client_pacing"')];assert len(pacing)==1 and pacing[0]['frame_cap_requested']==cap and pacing[0]['clock_errors']==0,pacing
   if cap:assert pacing[0]['waits']+pacing[0]['late_rebases']>0,pacing
   assert 'submitted_entities=8192' in stdout and 'client_render_device=llvmpipe' in stdout,stdout
   body=image.read_bytes();header=b'P6\n320 240\n255\n';assert body.startswith(header) and len(body)==len(header)+320*240*3;assert len(set(body[len(header):]))>20
   rows.append({'settings':settings,'frame_pacing':pacing[0],'actual_X_map_state':attr.map_state,'rendered_entities':8192,'nonblank_screenshot':True})
  print(json.dumps({'suite':'client-presentation-options','passed':True,'pre_context_invalid_cases':len(invalid),'real_GL_runs':rows,'scope':'Private Xvfb real assembled8192 client, actual X map state and framebuffer report; no target GPU/pacing/performance or hidden-vs-visible authority equivalence claim.'}))
finally:
 if child and child.poll() is None:child.terminate();child.wait(timeout=5)
 if display:x.XCloseDisplay(display)
 if read>=0:os.close(read)
 if write>=0:os.close(write)
 if server:server.terminate();server.wait(timeout=5)
