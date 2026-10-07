#!/usr/bin/env python3
"""Actual local/8192-authority UDP client ALSA output with engine-only toggle."""
from xvfb_display import read_display_number
import array,hashlib,json,os,pathlib,select,signal,struct,subprocess,sys,tempfile,time
EXE=pathlib.Path(sys.argv[1]).resolve();SERVER=pathlib.Path(sys.argv[2]).resolve()
symbols={p[2]:int(p[0],16) for line in subprocess.check_output(['nm','-n',str(EXE)],text=True).splitlines() if len(p:=line.split())==3}
reports=[]
for network in (False,True):
 with tempfile.TemporaryDirectory(prefix='rh-air-audio-client-') as directory:
  w=pathlib.Path(directory);raw=w/'device.raw';config=w/'asound.conf';config.write_text('</usr/share/alsa/alsa.conf>\npcm.rh_capture { type file slave.pcm "null" file "'+str(raw)+'" format "raw" }\n')
  read,write=os.pipe();xserver=process=authority=None;memory=None
  try:
   with (w/'client.log').open('w+') as log:
    xserver=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','640x360x24','-nolisten','tcp'],pass_fds=(write,),stdout=log,stderr=log);os.close(write);write=-1
    number=read_display_number(read,10);assert number.isdigit();os.close(read);read=-1
    extra=[]
    if network:
     authority=subprocess.Popen([str(SERVER),'--port','0','--ticks','600','--units','8192'],cwd=SERVER.parent,stdout=subprocess.PIPE,stderr=log,text=True)
     assert select.select([authority.stdout],[],[],10)[0];ready=json.loads(authority.stdout.readline());assert ready['units']==8192
     extra=['--connect','127.0.0.1','--port',str(ready['port'])]
    env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',RH_AUDIO_DEVICE='rh_capture',ALSA_CONFIG_PATH=str(config));env.pop('WAYLAND_DISPLAY',None)
    process=subprocess.Popen([str(EXE),'--width','640','--height','360',*extra],cwd=EXE.parent,env=env,stdout=log,stderr=log)
    memory=os.open(f'/proc/{process.pid}/mem',os.O_RDWR)
    def u32(name):
     try:return struct.unpack('<I',os.pread(memory,4,symbols[name]))[0]
     except (OSError,struct.error):return 0
    def put(name,data):os.pwrite(memory,data,symbols[name])
    def until(predicate):
     deadline=time.monotonic()+15
     while not predicate():
      if process.poll()is not None or time.monotonic()>deadline:
       log.seek(0);raise AssertionError(dict(exit=process.poll(),frames=u32('frame_count'),selected=u32('audio_aircraft_selected'),connected=u32('net_connected'),log=log.read()))
      time.sleep(.01)
    until(lambda:u32('frame_count')>=4 and (not network or u32('net_connected')==1))
    # Audio-only isolation: disable rifle/explosion/footstep banks, no army writes.
    put('sample_count',bytes(24))
    def phase(enabled):
     put('audio_aircraft_enabled',struct.pack('<I',enabled))
     until(lambda:u32('audio_aircraft_selected')==(0 if not enabled else min(8,u32('audio_aircraft_candidates'))))
     frame=u32('frame_count');written=struct.unpack('<Q',os.pread(memory,8,symbols['audio_written_frames']))[0]
     # File-backend flushing can lag accepted device frames. Index the actual
     # stream by accepted writes, with one bounded already-mixed pending block.
     start=(written+800)*4
     until(lambda:u32('frame_count')>=frame+20 and raw.exists() and raw.stat().st_size>start+6400)
     data=raw.read_bytes()[start:];data=data[:len(data)//4*4];assert len(data)>6400
     samples=array.array('h');samples.frombytes(data)
     return {'frames':len(samples)//2,'left_energy':sum(abs(v)for v in samples[::2]),'right_energy':sum(abs(v)for v in samples[1::2]),'selected':u32('audio_aircraft_selected'),'army_count':u32('sim_count'),'source_tick':u32('sim_tick_count'),'accepted_start_frame':start//4,'capture_end_frame':raw.stat().st_size//4},samples
    on,wave=phase(1);off,_=phase(0);again,_=phase(1)
    assert 1<=on['selected']<=8 and 1<=again['selected']<=8 and on['left_energy']+on['right_energy']>0 and again['left_energy']+again['right_energy']>0
    assert off['left_energy']==off['right_energy']==0,off
    if not network:assert on['army_count']==again['army_count']==8192
    # Graceful production exit flushes the ALSA file backend.
    put('frame_limit',struct.pack('<I',u32('frame_count')+3));process.wait(timeout=10);assert process.returncode==0
    capture=pathlib.Path(tempfile.gettempdir())/('red-horizon-aircraft-engine-'+('udp'if network else'local')+'.wav')
    import wave as wav
    with wav.open(str(capture),'wb')as out:out.setnchannels(2);out.setsampwidth(2);out.setframerate(48000);out.writeframes(wave.tobytes())
    reports.append({'network':network,'on':on,'off':off,'again':again,'capture':str(capture),'client_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest()})
  finally:
   if memory is not None:os.close(memory)
   for p in (process,authority,xserver):
    if p is not None:
     if p.poll()is None:p.terminate()
     p.wait(timeout=5)
   if read>=0:os.close(read)
   if write>=0:os.close(write)
print(json.dumps({'suite':'aircraft-engine-actual-client','passed':True,'cases':reports,'scope':'Actual client ALSA file backend captures, engine-only paired toggle. Local8192army and actual8192UDP server; no army/pose/HP/ammo/gen/clock writes. Playback audio-only bank isolation and enable toggle are declared cosmetic controls. Software GL/null file backend, not physical speaker quality/latency/spectacle acceptance.'}))
