import json,os,sys,struct,signal,subprocess,tempfile,time,pathlib,hashlib
exe=pathlib.Path(sys.argv[1]).resolve();image=pathlib.Path(sys.argv[2]).resolve()
symbols={p[2]:int(p[0],16)for line in subprocess.check_output(['nm','-n',str(exe)],text=True).splitlines()if len(p:=line.split())==3}
with tempfile.TemporaryDirectory(prefix='rh-airbase-capture-')as d:
 td=pathlib.Path(d);(td/'shim.c').write_text('#define _GNU_SOURCE\n#include <dlfcn.h>\n#include <signal.h>\n#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\nvoid glfwSwapBuffers(void*w){static void(*f)(void*);if(!f)f=dlsym(RTLD_NEXT,"glfwSwapBuffers");f(w);uint64_t(*h)(void)=(void*)strtoull(getenv("RH_CAPTURE_CHECKSUM"),0,16);fprintf(stderr,"capture_authority=%016llx\\n",(unsigned long long)h());fflush(stderr);raise(SIGSTOP);}\n')
 subprocess.run(['cc','-shared','-fPIC',str(td/'shim.c'),'-o',str(td/'shim.so'),'-ldl'],check=True)
 (td/'alsa.conf').write_text('pcm.!default { type null }\n')
 env=dict(os.environ,LD_PRELOAD=str(td/'shim.so'),RH_CAPTURE_CHECKSUM=f'{symbols["sim_checksum"]:x}',ALSA_CONFIG_PATH=str(td/'alsa.conf'));env.pop('LIBGL_ALWAYS_SOFTWARE',None)
 command=[str(exe),'--frames','8','--hidden','--no-vsync','--width','1280','--height','720','--fov','70','--screenshot',str(image),'--census']
 with (td/'client.log').open('w+')as log:
  p=subprocess.Popen(command,cwd=exe.parent,env=env,stdout=log,stderr=log);memory=None
  try:
   memory=os.open(f'/proc/{p.pid}/mem',os.O_RDWR)
   def put(name,data):assert os.pwrite(memory,data,symbols[name])==len(data)
   for frame in range(1,8):
    deadline=time.monotonic()+20
    while True:
     got,status=os.waitpid(p.pid,os.WUNTRACED|os.WNOHANG)
     if got:
      assert os.WIFSTOPPED(status),(frame,status)
      break
     assert time.monotonic()<deadline,('presentation timeout',frame)
     time.sleep(.01)
    if frame==3:
     # Single paused-render fixture: inputs/camera sync disabled, authority never rewritten.
     put('update_input',b'\x31\xc0\xc3');put('sync_player',b'\xc3')
     put('thirty',struct.pack('<d',1e30));put('accum',struct.pack('<d',0))
     put('camera',struct.pack('<3f',2000,550,3790));put('yaw',struct.pack('<f',0));put('pitch',struct.pack('<f',-1.2))
    os.kill(p.pid,signal.SIGCONT)
   assert p.wait(timeout=20)==0
   log.seek(0);text=log.read();samples=[line.split('=')[1]for line in text.splitlines()if line.startswith('capture_authority=')]
   assert len(samples)==7 and len(set(samples[2:]))==1,samples
   assert 'Arc(tm) A770' in text and 'invalid_codes":0' in text
   print(json.dumps({'passed':True,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'command':command,'camera':[2000,550,3790],'yaw_pitch':[0,-1.2],'authority_samples':samples,'image':str(image),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'telemetry':text,'scope':'Actual8192 native Arc client terrain/runway render; one paused presentation fixture disables input and cosmetic camera sync and freezes simulation clock after settling. No authority body/HP/stores/generation writes. Actual sim_checksum unchanged across five paused rendered samples and final census read-only. Not live gameplay, runway flight/landing/performance/traffic/art acceptance.'}))
  finally:
   if memory is not None:os.close(memory)
   if p.poll() is None:os.kill(p.pid,signal.SIGCONT);p.terminate();p.wait(timeout=5)
