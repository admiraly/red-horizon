#!/usr/bin/env python3
"""Actual whole-client sunlight controls, frozen camera/clocks, full8192 retained.
No HP/kind/generation/stock/event/pose writes to army. Dev GL checksum observer.
"""
import ctypes as C,ctypes.util,hashlib,json,os,pathlib,select,signal,struct,subprocess,sys,tempfile,time
EXE=pathlib.Path(sys.argv[1]).resolve()
X=C.CDLL(ctypes.util.find_library('X11'));D=C.c_void_p;W=C.c_ulong
X.XOpenDisplay.argtypes=[C.c_char_p];X.XOpenDisplay.restype=D
X.XDefaultRootWindow.argtypes=[D];X.XDefaultRootWindow.restype=W
X.XQueryTree.argtypes=[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)]
X.XFetchName.argtypes=[D,W,C.POINTER(C.c_char_p)];X.XFree.argtypes=[D]
X.XGetImage.argtypes=[D,W,C.c_int,C.c_int,C.c_uint,C.c_uint,W,C.c_int];X.XGetImage.restype=D
X.XGetPixel.argtypes=[D,C.c_int,C.c_int];X.XGetPixel.restype=W
X.XDestroyImage.argtypes=[D];X.XCloseDisplay.argtypes=[D]


SHIM=r'''#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
static uint64_t before;static int armed;
static uintptr_t address(const char *name){return (uintptr_t)strtoull(getenv(name),0,10);}
void glBindFramebuffer(unsigned target,unsigned object){
 static void(*real)(unsigned,unsigned);if(!real)real=dlsym(RTLD_NEXT,"glBindFramebuffer");
 unsigned fbo=*(volatile unsigned *)address("RH_SHADOW_FBO");
 unsigned frame=*(volatile unsigned *)address("RH_FRAME_COUNT");
 uint64_t(*checksum)(void)=(void *)address("RH_CHECKSUM");
 if(fbo&&frame&&object==fbo&&!armed){before=checksum();armed=1;}
 if(armed&&object!=fbo){uint64_t after=checksum();FILE *f=fopen(getenv("RH_SHADOW_CAPTURE"),"a");if(f){fprintf(f,"{\"before\":\"%016llx\",\"after\":\"%016llx\",\"frame\":%u}\n",(unsigned long long)before,(unsigned long long)after,frame);fclose(f);}armed=0;}
 real(target,object);
}
void glfwSwapBuffers(void *window){
 static void(*real)(void *);if(!real)real=dlsym(RTLD_NEXT,"glfwSwapBuffers");real(window);
 const char *path=getenv("RH_SHADOW_REQUEST");FILE *f=fopen(path,"r");
 if(f){unsigned wanted=0;int ok=fscanf(f,"%u",&wanted);fclose(f);unsigned frame=*(volatile unsigned *)address("RH_FRAME_COUNT");
 if(ok==1&&frame>=wanted){unlink(path);raise(SIGSTOP);}}
}
'''
read,write=os.pipe();server=process=display=memory=None
try:
 with tempfile.TemporaryDirectory(prefix='rh-shadow-client-')as tmp:
  folder=pathlib.Path(tmp);log=(folder/'client.log').open('w+b');(folder/'shim.c').write_text(SHIM)
  subprocess.run(['cc','-shared','-fPIC','-O2',str(folder/'shim.c'),'-ldl','-o',str(folder/'shim.so')],check=True,capture_output=True)
  server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x360x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log);os.close(write);write=-1
  assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
  symbols={line.split()[2]:int(line.split()[0],16)for line in subprocess.check_output(['nm','-n',str(EXE)],text=True).splitlines()if len(line.split())==3}
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null',LD_PRELOAD=str(folder/'shim.so'),RH_SHADOW_FBO=str(symbols['sun_shadow_fbo']),RH_FRAME_COUNT=str(symbols['frame_count']),RH_CHECKSUM=str(symbols['sim_checksum']),RH_SHADOW_CAPTURE=str(folder/'hashes.jsonl'),RH_SHADOW_REQUEST=str(folder/'capture.request'));env.pop('WAYLAND_DISPLAY',None)
  display=X.XOpenDisplay(env['DISPLAY'].encode());assert display
  process=subprocess.Popen([str(EXE),'--width','640','--height','360'],cwd=EXE.parent,env=env,stdout=log,stderr=log)
  memory=os.open(f'/proc/{process.pid}/mem',os.O_RDWR)
  def get(name,size):return os.pread(memory,size,symbols[name])
  def u32(name):return struct.unpack('<I',get(name,4))[0]
  def put(name,data):os.pwrite(memory,data,symbols[name])
  def until(predicate):
   deadline=time.monotonic()+20
   while time.monotonic()<deadline:
    if predicate():return
    if process.poll()is not None:
     log.seek(0);raise AssertionError(log.read().decode(errors='replace'))
    time.sleep(.02)
   raise AssertionError('client frame timeout')
  def stop():os.kill(process.pid,signal.SIGSTOP);_,status=os.waitpid(process.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
  until(lambda:u32('frame_count')>=4);stop();put('thirty',struct.pack('<d',1e30));put('accum',struct.pack('<d',0));put('maxdt',struct.pack('<d',0))
  army=get('sim_entities',8192*32);entities=[struct.unpack_from('<ff6I',army,i*32)for i in range(8192)]
  candidates=[(i,e)for i,e in enumerate(entities)if e[2]>0 and e[3]==0 and e[4]==1 and 1000<e[0]<4500 and 1000<e[1]<7000]
  assert candidates;i,e=min(candidates,key=lambda row:(row[1][0]-3780)**2+(row[1][1]-3900)**2);x,z=e[:2]
  ground=12+(x-4000)**2*.000001+(z-4000)**2*.0000005+max(0,1-abs(x-4000)/800)*18
  put('sim_players',struct.pack('<5f',x,ground+8,z-30,0,.18));put('yaw',struct.pack('<f',0));put('pitch',struct.pack('<f',.18))
  put('effects_records',bytes(2048));put('air_trails_visible',struct.pack('<I',0));put('air_crash_plumes_visible',struct.pack('<I',0))
  frame=u32('frame_count');os.kill(process.pid,signal.SIGCONT);until(lambda:u32('frame_count')>=frame+3);stop()
  # Freeze only the cosmetic minimum delta after motion observations settle.
  # Validate the exact production maxss instruction and original constant.
  instruction=get('meshes_draw.advance_clock',8);assert instruction[:4]==bytes.fromhex('f30f5f2d'),instruction.hex()
  delta_address=symbols['meshes_draw.advance_clock']+8+struct.unpack('<i',instruction[4:])[0]
  original=os.pread(memory,4,delta_address);assert original==struct.pack('<f',.001)
  os.pwrite(memory,struct.pack('<f',0),delta_address)
  count=C.c_uint();root=W();parent=W();children=C.POINTER(W)();X.XQueryTree(display,X.XDefaultRootWindow(display),C.byref(root),C.byref(parent),C.byref(children),C.byref(count));window=0
  for win in list(children[:count.value]):
   name=C.c_char_p()
   if X.XFetchName(display,win,C.byref(name))and name:
    if name.value.startswith(b'RED HORIZON'):window=win
    X.XFree(C.cast(name,D))
  if children:X.XFree(children)
  assert window and u32('sim_count')==8192
  def digest():return hashlib.sha256(b''.join(get(name,size)for name,size in(('sim_entities',8192*32),('sim_aircraft',8192*64),('sim_players',256),('sim_events',8192),('sim_projectiles',32768),('sim_tick_count',4)))).hexdigest()
  authority=digest();ticks=u32('local_sim_ticks');observed=[]
  def capture(on,tactical=0):
   put('sun_shadows_enabled',struct.pack('<I',on));put('tactical',struct.pack('<I',tactical))
   frame=u32('frame_count');(folder/'capture.request').write_text(str(frame+5))
   os.kill(process.pid,signal.SIGCONT)
   def presented_stop():
    pid,status=os.waitpid(process.pid,os.WNOHANG|os.WUNTRACED)
    if not pid:return False
    assert os.WIFSTOPPED(status),'client exited while awaiting presented frame'
    return True
   until(presented_stop)
   assert u32('sun_shadow_pass')==0 and u32('mesh_counts_complete')==1
   assert digest()==authority and u32('local_sim_ticks')==ticks
   assert 0<=u32('mesh_frame')-u32('frame_count')<=1,'animation advanced twice'
   casters=u32('sun_shadow_casters');assert casters<=1024
   assert u32('sun_shadow_budget')+casters==1024
   assert u32('sun_shadow_ready')==int(on and not tactical)
   observed.append(dict(enabled=on,tactical=tactical,casters=casters,frame=u32('frame_count'),mesh_frame=u32('mesh_frame')))
   image=X.XGetImage(display,window,0,0,640,360,W(-1).value,2);assert image;pixels=bytearray()
   for y in range(360):
    for x in range(640):
     value=X.XGetPixel(image,x,y);pixels.extend(((value>>16)&255,(value>>8)&255,value&255))
   X.XDestroyImage(image);return pixels
  off=capture(0);on=capture(1);repeat=capture(1);map_off=capture(0,1);map_on=capture(1,1)
  changed=lambda a,b:sum(max(abs(a[i+k]-b[i+k])for k in range(3))>2 for i in range(0,len(a),3))
  pixels=changed(off,on);assert pixels>100,pixels
  assert changed(on,repeat)==0 and changed(map_off,map_on)==0
  assert any(o['casters']>0 for o in observed)
  path=pathlib.Path(sys.argv[2]);path.write_bytes(b'P6\n640 360\n255\n'+on)
  hashes=[json.loads(row)for row in(folder/'hashes.jsonl').read_text().splitlines()];assert hashes and all(row['before']==row['after']for row in hashes),'shadow pass mutated full authority hash'
  print(json.dumps(dict(suite='sun-shadows-whole-client',passed=True,shadow_changed_pixels=pixels,repeat_delta_pixels=0,tactical_delta_pixels=0,original_army_count=8192,camera_source_actor=i,observed=observed,full_authority_checksum_samples=len(hashes),shadow_pass_full_hash_unchanged=True,authority_sha256=authority,client_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),screenshot=str(path),scope='Actual whole-client current-frame terrain and animated source casters, HDR/bloom/HUD. Frozen development camera/simulation/cosmetic clocks after settling, actual8192 army unchanged; full production checksum observed before/after depth via dev GL shim. Budget and one animation advance proved. No target-GPU performance/final art/cascade/all-body casting acceptance.')))
finally:
 if process is not None:
  if process.poll()is None:os.kill(process.pid,signal.SIGCONT);process.terminate()
  process.wait(timeout=5)
 if memory is not None:os.close(memory)
 if display:X.XCloseDisplay(display)
 if server:server.terminate();server.wait(timeout=5)
 if read>=0:os.close(read)
 if write>=0:os.close(write)
