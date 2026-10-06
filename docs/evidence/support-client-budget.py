#!/usr/bin/env python3
"""Private software-GL dense client observation; no hardware budget acceptance."""
from pathlib import Path
import hashlib,json,os,select,subprocess,sys,tempfile,time
root=Path(__file__).resolve().parents[2];exe=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
read,write=os.pipe();server=None
try:
 with (out/'xvfb.log').open('wb') as log:server=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','1280x720x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log)
 os.close(write);write=-1;assert select.select([read],[],[],10)[0];number=os.read(read,32).decode().strip();assert number.isdigit();os.close(read);read=-1
 env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
 context=subprocess.run(['glxinfo','-B'],env=env,capture_output=True,text=True,check=True,timeout=15).stdout
 assert 'llvmpipe' in context.lower() or 'softpipe' in context.lower(),context
 cmd=[str(exe),'--scenario','scale-hotspot','--frames','120','--width','1280','--height','720','--census','--screenshot',str(out/'client.ppm')]
 start=time.monotonic();run=subprocess.run(cmd,cwd=exe.parent,env=env,capture_output=True,text=True,check=True,timeout=90);elapsed=time.monotonic()-start
 (out/'client.log').write_text(run.stdout+run.stderr);reports=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{')];names=('client_metrics','battle_metrics','visibility_census');assert all(sum(bool(r.get(name)) for r in reports)==1 for name in names)
 result={'command':cmd,'client_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'wall_seconds':elapsed,'context':context,'reports':reports,'coverage':{'initial_army':8192,'seed':42,'resolution':[1280,720],'frames':120,'replicated':0,'audio':'ALSA null; physical listening unverified','threads':'single simulation thread','scope':'Software GL actual client with live combat and final pixel census. Timings include concurrent verification, initialization and final census drawing. No hardware FPS goal or isolated support-overhead/speedup claim.'}}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
 if read>=0:os.close(read)
 if write>=0:os.close(write)
 if server is not None:server.terminate();server.wait(timeout=5)
