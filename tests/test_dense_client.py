#!/usr/bin/env python3
"""Real GL dense fixture smoke; submitted instances never imply pixel visibility."""
import json,os,pathlib,select,subprocess,sys,tempfile
exe=pathlib.Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as folder:
 root=pathlib.Path(folder);read_fd,write_fd=os.pipe();server=None
 try:
  with (root/'xvfb.log').open('w') as log:
   server=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1280x720x24','-nolisten','tcp'],pass_fds=(write_fd,),stdout=subprocess.DEVNULL,stderr=log)
   os.close(write_fd);write_fd=None
   assert select.select([read_fd],[],[],10)[0],'Xvfb startup timeout'
   number=os.read(read_fd,32).decode().strip();assert number.isdigit()
   env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
   results={}
   for scenario in ('scale-front','scale-hotspot'):
    image=root/(scenario+'.ppm')
    run=subprocess.run([str(exe),'--scenario',scenario,'--frames','120','--screenshot',str(image)],cwd=exe.parent,env=env,capture_output=True,text=True,timeout=60)
    assert run.returncode==0,(scenario,run.stdout,run.stderr)
    metrics=[json.loads(row)for row in run.stdout.splitlines()if row.startswith('{"battle_metrics"')]
    assert len(metrics)==1,(scenario,run.stdout)
    m=metrics[0]
    assert m['samples']==120 and m['initial_living']==8192,m
    assert 0<m['peak_living']<=m['initial_living'],m
    assert m['peak_engaged']>=2048 and m['peak_projectiles']>0,m
    assert m['peak_submitted_high']+m['peak_submitted_low']>=1024,m
    assert m['peak_effect_records']>0 and m['peak_trail_records']>0 and m['peak_audio_voices']>0,m
    assert m['simultaneous_projectiles_effects_audio_frames']>0,m
    assert m['visible_individual_count']=='unmeasured',m
    header,data=image.read_bytes().split(b'\n255\n',1)
    assert b'1280 720' in header and len(data)==1280*720*3
    assert len(set(data[i:i+3]for i in range(0,len(data),3)))>100,'empty/unvaried scene'
    results[scenario]=m
   print(json.dumps({'suite':'dense-client','passed':True,'actual_GL':True,'runtime_pose_or_damage_writes':False,'frame_peaks':results,'pixel_visible_actor_count':'unmeasured','audio_device':'null; waveform routing only'}))
 finally:
  os.close(read_fd)
  if write_fd is not None:os.close(write_fd)
  if server is not None:
   server.terminate()
   try:server.wait(timeout=5)
   except subprocess.TimeoutExpired:server.kill();server.wait()
