#!/usr/bin/env python3
"""Actual native listen lifecycle and cooperative join, in private software X."""
import json,os,pathlib,select,shutil,subprocess,sys,tempfile,time
from test_coop import VERSION
exe=pathlib.Path(sys.argv[1]).resolve(); processes=[]; evidence=[]
symbols={parts[2]:int(parts[0],16) for line in subprocess.check_output(['nm','-n',str(exe)],text=True).splitlines() if len(parts:=line.split())==3}
def await_host_join(p):
 deadline=time.monotonic()+15
 with open(f'/proc/{p.pid}/mem','rb',buffering=0) as memory:
  while time.monotonic()<deadline:
   assert p.poll() is None,'host exited before accepted join'
   connected=int.from_bytes(os.pread(memory.fileno(),4,symbols['net_connected']),'little')
   player=int.from_bytes(os.pread(memory.fileno(),4,symbols['net_player_id']),'little')
   if connected==1:
    assert player==0,player
    return
   time.sleep(.01)
 raise AssertionError('host join never accepted')
def run(args,env,cwd=None,expected=0,timeout=20):
 r=subprocess.run([str(exe),*args],cwd=cwd or exe.parent,env=env,capture_output=True,text=True,timeout=timeout)
 assert r.returncode==expected,(args,r.returncode,r.stdout[-1800:],r.stderr)
 return r

def rows(out):return [json.loads(l) for l in out.splitlines() if l.startswith('{"listen_host"')]
def state(pid):
 try:return pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
 except (FileNotFoundError,ProcessLookupError):return None

def child(parent,timeout=10):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  assert parent.poll() is None,'client exited before host readiness'
  try:ids=pathlib.Path(f'/proc/{parent.pid}/task/{parent.pid}/children').read_text().split()
  except FileNotFoundError:ids=[]
  for value in ids:
   pid=int(value)
   try:
    if pathlib.Path(f'/proc/{pid}/exe').resolve().name=='red-horizon-coop-server':return pid
   except FileNotFoundError:pass
  time.sleep(.01)
 raise AssertionError('owned server absent')

def port_of(pid):
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  try:
   inodes={p.readlink().name[8:-1] for p in pathlib.Path(f'/proc/{pid}/fd').iterdir() if p.readlink().name.startswith('socket:[')}
   for line in pathlib.Path(f'/proc/{pid}/net/udp').read_text().splitlines()[1:]:
    fields=line.split()
    if fields[9] in inodes:return int(fields[1].split(':')[1],16)
  except FileNotFoundError:pass
  time.sleep(.01)
 raise AssertionError('server did not bind UDP')

read,write=os.pipe();x=None
try:
 x=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x480x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(write);write=-1
 assert select.select([read],[],[],10)[0];display=os.read(read,32).decode().strip();os.close(read);read=-1
 env=dict(os.environ,DISPLAY=':'+display,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='null');env.pop('WAYLAND_DISPLAY',None)
 for args in (['--listen','--listen'],['--listen','--connect','127.0.0.1'],['--connect','127.0.0.1','--listen'],['--connect','127.0.0.1','--scenario','scale-hotspot'],['--listen','--port','7777'],['--port','7777','--listen']):
  r=run(args,env,expected=1);assert not rows(r.stdout) or rows(r.stdout)[0]['child_pid']==0,'invalid args spawned authority'
 base=['--hidden','--no-vsync','--frame-cap','60','--width','320','--height','240']
 # Owned host plus an independent actual graphical peer; no authority fixtures.
 p=subprocess.Popen([str(exe),'--listen','--frames','240',*base],cwd=exe.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);processes.append(p);pid=child(p);port=port_of(pid);await_host_join(p)
 peer=run(['--connect','127.0.0.1','--port',str(port),'--frames','60',*base],env)
 assert 'network connected=1 player=1 ' in peer.stdout and 'local_sim_ticks=0' in peer.stdout,peer.stdout[-2000:]
 out,err=p.communicate(timeout=30);assert p.returncode==0,(out,err)
 advertised=[json.loads(l) for l in out.splitlines() if l.startswith('{"listen_ready"')];assert len(advertised)==1 and advertised[0]['port']==port and advertised[0]['child_pid']==pid
 record=rows(out)[0];assert record['child_pid']==pid and record['port']==port and record['child_exited']==1 and record['startup_failed']==0
 assert state(pid) is None,'normal exit did not reap owned child'
 assert 'network connected=1 player=0 ' in out and 'local_sim_ticks=0' in out and '"initial_living":8192' in out
 evidence.append({'case':'actual host plus independent peer','host':record,'peer_player':1,'authority_initial':8192,'host_and_peer_local_sim_ticks':0,'owned_child_reaped':True})
 for mode,name in enumerate(('air-battle','scale-front','scale-hotspot'),1):
  r=run(['--listen','--scenario',name,'--frames','60',*base],env)
  advertised=[json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"listen_ready"')]
  record=rows(r.stdout)[0];assert len(advertised)==1 and advertised[0]['scenario']==mode and advertised[0]['units']==8192
  assert 'network connected=1' in r.stdout and 'local_sim_ticks=0' in r.stdout and state(record['child_pid']) is None
  evidence.append({'case':'actual listen authored '+name,'scenario':mode,'host':record,'source_clock_from_real_server':True})
 # Post-launch GL initialization failure must also stop and reap the army.
 failed_env=dict(env,DISPLAY=':65432');r=run(['--listen','--frames','1','--hidden'],failed_env,expected=1)
 record=rows(r.stdout)[0];assert record['child_pid']>0 and record['child_exited']==1 and record['startup_failed']==0 and state(record['child_pid']) is None
 evidence.append({'case':'GL failure cleanup','host':record})
 # Unexpected authority death is observed, returns failure and reaps own PID.
 p=subprocess.Popen([str(exe),'--listen','--frames','10000',*base],cwd=exe.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);processes.append(p);pid=child(p);port_of(pid);os.kill(pid,15)
 out,err=p.communicate(timeout=20);assert p.returncode==1,(out,err);assert rows(out)[0]['child_exited']==1 and state(pid) is None
 evidence.append({'case':'server death propagated','child_reaped':True})
 # Abrupt parent death kernel contract: no surviving live army process.
 p=subprocess.Popen([str(exe),'--listen','--frames','10000',*base],cwd=exe.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);processes.append(p);pid=child(p);port_of(pid);p.kill();p.communicate(timeout=10)
 deadline=time.monotonic()+3
 while state(pid) not in (None,'Z') and time.monotonic()<deadline:time.sleep(.01)
 assert state(pid) in (None,'Z'),'army survived parent death'
 evidence.append({'case':'abrupt parent death','server_state':state(pid),'scope':'Kernel terminates child; init owns orphan reaping after parent SIGKILL.'})
 # Missing sibling exercises exec failure before any rendering/content access.
 with tempfile.TemporaryDirectory(prefix='rh-listen-missing-') as temp:
  copied=pathlib.Path(temp)/'red-horizon';shutil.copy2(exe,copied)
  r=subprocess.run([str(copied),'--listen','--frames','1','--hidden'],cwd=temp,env=env,capture_output=True,text=True,timeout=8)
  assert r.returncode==1 and 'keep red-horizon-coop-server beside the client' in r.stdout;record=rows(r.stdout)[0];assert record['startup_failed']==1 and record['child_exited']==1 and state(record['child_pid']) is None
  evidence.append({'case':'missing sibling exec','host':record})
  companion=pathlib.Path(temp)/'red-horizon-coop-server'
  # Deliberately invalid development startup producers; not gameplay evidence.
  for name,line in [('protocol', '{"port":7777,"protocol":0,"units":8192,"scenario":0}'),('units',json.dumps(dict(port=7777,protocol=VERSION,units=2,scenario=0),separators=(',',':'))),('port',json.dumps(dict(port=0,protocol=VERSION,units=8192,scenario=0),separators=(',',':'))),('scenario',json.dumps(dict(port=7777,protocol=VERSION,units=8192,scenario=1),separators=(',',':'))),('timeout',None)]:
   body='import time\n'+('print('+repr(line)+',flush=True)\n' if line else '')+'time.sleep(20)\n'
   companion.write_text('#!'+sys.executable+'\n'+body);companion.chmod(0o755)
   start=time.monotonic();r=subprocess.run([str(copied),'--listen','--frames','1','--hidden'],cwd=temp,env=env,capture_output=True,text=True,timeout=8);elapsed=time.monotonic()-start
   assert r.returncode==1;record=rows(r.stdout)[0];assert record['startup_failed']==1 and state(record['child_pid']) is None
   if name=='timeout':assert 4.5<=elapsed<7,elapsed
   evidence.append({'case':'invalid development readiness '+name,'reaped':True,'wall_seconds':elapsed})
 print(json.dumps({'suite':'actual-listen-host','passed':True,'cases':evidence,'invalid_combinations':6,'scope':'Linux NASM host and real8192 UDP authority/graphical peer, private llvmpipe; no dense/four-client/frame-quality or Windows acceptance.'}))
finally:
 for p in processes:
  if p.poll() is None:p.terminate();p.communicate(timeout=10)
 if x is not None:x.terminate();x.wait(timeout=10)
 for fd in (read,write):
  if fd>=0:os.close(fd)
