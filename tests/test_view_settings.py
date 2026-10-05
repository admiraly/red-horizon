#!/usr/bin/env python3
"""Strict client startup CLI and real private-Xvfb framebuffer verification."""
import json, os, pathlib, select, subprocess, sys, tempfile
exe = pathlib.Path(sys.argv[1]).resolve()
invalid = [('--width','0'),('--width','319'),('--width','3841'),('--width','1280.5'),('--height','239'),('--height','2161'),('--fov','34.9'),('--fov','110.1'),('--fov','NaN'),('--fov','inf'),('--fov','1e999'),('--fov','60junk'),('--fov',' 60'),('--fov','60 '),('--fov','0x40'),('--sensitivity','0'),('--sensitivity','-0.002'),('--sensitivity','0.051'),('--height','')]
for flag,value in invalid:
 p=subprocess.run([str(exe),flag,value],cwd=exe.parent,capture_output=True,timeout=10)
 assert p.returncode != 0,(flag,value)
for args in [ ['--width'], ['--fov','60','--fov','65'],['--height','720','--height','720'], ['--sensitivity','0.002','--sensitivity','0.003'] ]:
 p=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,timeout=10)
 assert p.returncode!=0,args
r,w=os.pipe(); server=None
try:
 server=subprocess.Popen(['Xvfb','-displayfd',str(w),'-screen','0','1920x1080x24','-nolisten','tcp'],pass_fds=(w,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 os.close(w);w=None
 assert select.select([r],[],[],10)[0]
 number=os.read(r,32).decode().strip();assert number.isdigit()
 env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
 with tempfile.TemporaryDirectory(prefix='rh-view-') as directory:
  folder=pathlib.Path(directory)
  def render(name,args,dimensions):
   path=folder/(name+'.ppm')
   p=subprocess.run([str(exe),*args,'--frames','1','--screenshot',str(path)],cwd=exe.parent,env=env,capture_output=True,text=True,timeout=30)
   assert p.returncode==0,p.stderr+p.stdout
   blob=path.read_bytes();header,body=blob.split(b'\n255\n',1)
   assert header==f'P6\n{dimensions[0]} {dimensions[1]}'.encode(),header
   assert len(body)==dimensions[0]*dimensions[1]*3
   assert 'submitted_entities=8192' in p.stdout,p.stdout
   # All four corners must be rendered (not an unpainted enlarged window).
   corners=[tuple(body[i:i+3]) for i in [0,(dimensions[0]-1)*3,(dimensions[1]-1)*dimensions[0]*3,len(body)-3]]
   assert all(c!=(0,0,0) for c in corners),corners
   return body,p.stdout,corners
  default,log,corners=render('default',[],(1280,720))
  explicit,_,_=render('explicit',['--width','1.28e3','--height','7.2e2','--sensitivity','2e-3'],(1280,720))
  default_difference=sum(default[i:i+3]!=explicit[i:i+3] for i in range(0,len(default),3))
  # Separate startup runs can advance different ticks during shader compilation;
  # exact default projection is checked in the kernel/frozen-pose regressions.
  large,_,large_corners=render('1080p',['--width','1920','--height','1080'],(1920,1080))
  square,_,_=render('800x600',['--width','800','--height','600'],(800,600))
  narrow,_,_=render('fov45',['--fov','45'],(1280,720))
  wide,_,_=render('fov90',['--fov','90'],(1280,720))
  difference=sum(narrow[i:i+3]!=wide[i:i+3] for i in range(0,len(narrow),3))
  assert difference>10000,difference
  render('tactical1080p',['--width','1920','--height','1080','--tactical'],(1920,1080))
  result={'invalid_cases':len(invalid)+4,'resolutions':[[1280,720],[1920,1080],[800,600]],'default_dimension_changed_pixels':default_difference,'fov45_vs90_changed_pixels':difference,'1080p_corners':large_corners,'context':'private Xvfb, software OpenGL, one render frame, full 8192 actors; no target-GPU performance claim'}
  print(json.dumps(result))
finally:
 os.close(r)
 if w is not None:os.close(w)
 if server is not None:
  server.terminate()
  try:server.wait(timeout=5)
  except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
