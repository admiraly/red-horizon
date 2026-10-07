#!/usr/bin/env python3
"""Actual assembly recorded loop, moving emitter selection and real flight routing."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-air-audio-') as folder:
 w=pathlib.Path(folder);stub=w/'network.asm';stub.write_text('section .bss\nglobal network_mode,net_connected\nnetwork_mode: resd 1\nnet_connected: resd 1\nsection .note.GNU-stack noalloc noexec nowrite progbits\n')
 sources=[p for f in ('sim','nav','ai','game')for p in (R/'src'/f).glob('*.asm')]+[R/'src/audio/audio.asm',R/'src/audio/aircraft.asm',R/'tests/probe_aircraft_audio.asm',stub]
 objects=[]
 for i,source in enumerate(sources):
  obj=w/f'{i}.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(source),'-o',str(obj)],check=True);objects.append(str(obj))
 so=w/'audio.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(so),*objects,'-lasound','-lm'],check=True)
 l=C.CDLL(str(so));l.sim_checksum.restype=C.c_uint64;l.audio_load_kind.argtypes=[C.c_uint,C.c_char_p];l.audio_listener.argtypes=[C.c_float]*5;l.audio_loop_submit.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;l.audio_aircraft_update.argtypes=[C.c_float]*3
 l.probe_aircraft_audio.argtypes=[C.c_uint]+[C.c_float]*3+[C.c_void_p,C.c_void_p]
 l.audio_mix_stereo.argtypes=[C.POINTER(C.c_int16),C.c_size_t];l.audio_mix.argtypes=[C.POINTER(C.c_int16),C.c_size_t]
 E=(Entity*32768).in_dll(l,'sim_entities');A=(Air*32768).in_dll(l,'sim_aircraft');count=C.c_uint.in_dll(l,'sim_count');mode=C.c_uint.in_dll(l,'network_mode');connected=C.c_uint.in_dll(l,'net_connected')
 counter=lambda n:C.c_uint64.in_dll(l,n).value
 def load(values):
  p=w/'fixture.pcm';p.write_bytes(struct.pack('<'+'h'*len(values),*values));assert l.audio_load_kind(3,str(p).encode())==0
 def stereo(n):
  o=(C.c_int16*(2*n+2))();o[-2]=1234;o[-1]=-2345;assert l.audio_mix_stereo(o,n)==n and list(o)[-2:]==[1234,-2345];return list(o)[:-2]
 def begin():l.audio_loop_begin()
 def submit(i=31,generation=1,x=4000,y=20,z=4000,gain=1):return l.audio_loop_submit(i,generation,x,y,z,gain)
 assert l.audio_listener(4000,20,4000,1,0)==0
 load([2000,-4000,6000]);begin();assert submit()==0;l.audio_loop_end();assert stereo(8)==[v>>1 for v in [2000,-4000,6000,2000,-4000,6000,2000,-4000] for _ in range(2)]
 begin();assert submit()==0;l.audio_loop_end();assert stereo(2)==[3000,3000,1000,1000] and counter('audio_loop_started')==1,'frame update restarted cursor'
 begin();assert submit(x=4025)==0;l.audio_loop_end();right=stereo(1);assert right[0]==0 and right[1]<-3000,'moving loop pan'
 begin();assert submit(generation=2)==0;l.audio_loop_end();assert stereo(1)==[1000,1000] and counter('audio_loop_started')==2 and counter('audio_loop_stopped')==1
 begin();l.audio_loop_end();assert stereo(4)==[0]*8 and l.audio_active()==0
 # Mono compatibility wraps exact short recordings too.
 load([1000,-2000]);begin();assert submit()==0;l.audio_loop_end();o=(C.c_int16*7)();assert l.audio_mix(o,7)==7 and list(o)==[1000,-2000,1000,-2000,1000,-2000,1000]
 load([1000]);begin();assert submit()==0;l.audio_loop_end();assert stereo(1)==[500,500] and l.audio_active()==1,'end cursor remains logically active'
 assert l.audio_listener(7000,20,4000,1,0)==0;assert stereo(3)==[0]*6
 assert l.audio_listener(4000,20,4000,1,0)==0;assert stereo(1)==[500,500],'virtual loop stopped advancing/wrapping'
 load([2000]);bad=[dict(i=32768),dict(generation=0),dict(x=float('nan')),dict(y=float('inf')),dict(z=-1),dict(gain=1.1)]
 for args in bad:begin();assert submit(**args)==-1;l.audio_loop_end();assert l.audio_active()==0
 begin();assert submit(x=5500)==1;l.audio_loop_end()
 # Loop sources cannot steal all128 active weapon voices.
 p=w/'weapon.pcm';p.write_bytes(struct.pack('<800h',*([1000]*800)));assert l.audio_load_kind(0,str(p).encode())==0
 for _ in range(128):l.audio_shot()
 before=counter('audio_replaced');begin();assert submit()==1;l.audio_loop_end();assert l.audio_active()==128 and counter('audio_replaced')==before
 # Actual source bank waveform repeats through the same assembly mixer.
 path=R/'content/audio/aircraft-engine.pcm';assert l.audio_load_kind(3,str(path).encode())==0
 recorded=struct.unpack('<'+str(path.stat().st_size//2)+'h',path.read_bytes());begin();assert submit()==0;l.audio_loop_end();actual=[]
 for _ in range(121):actual.extend(stereo(800)[::2])
 assert actual==[recorded[i%len(recorded)]>>1 for i in range(len(actual))] and counter('audio_loop_started')==1
 def plane(i,x,z=4000,y=160,role=1):
  E[i]=Entity(x,z,200,0,3,1,-1,1);A[i]=Air(y,math.pi/2,0,0,(5,7)[role],role,0,-1,0,180,1,(5,7)[role],0,0,0,1)
 def route():
  before=l.sim_checksum();out=(C.c_float*4)(123,0,0,456);abi=(C.c_uint64*7)();l.probe_aircraft_audio(0,4000.,20.,4000.,C.byref(out,4),abi)
  assert out[0]==123 and out[3]==456 and tuple(abi)==tuple(0x123401+i for i in range(6))+(0,)
  assert l.sim_checksum()==before,'audio changed authority'
 assert l.sim_init(128,42)==0
 for e in E[:128]:e.hp=0
 for i in range(16):plane(i,4000+i*20)
 route();assert C.c_uint.in_dll(l,'audio_aircraft_selected').value==8 and C.c_uint.in_dll(l,'audio_aircraft_candidates').value==16 and l.audio_active()==8
 # Local or replicated powerless glide retires every engine loop, not impacts.
 for i in range(16):A[i].mode=4
 route();assert l.audio_active()==0 and C.c_uint.in_dll(l,'audio_aircraft_selected').value==0 and not any(stereo(256))
 for i in range(16):A[i].mode=0
 route();assert l.audio_active()==8
 # Selection cap and lifecycle: known nearest dies, stale generation is rejected.
 E[0].hp=0;A[1].gen=2;A[2].flags=0;E[3].kind=0;A[4].y=math.nan;route();assert l.audio_active()==8
 mode.value=1;connected.value=0;route();assert l.audio_active()==0
 connected.value=1;route();assert l.audio_active()==8
 count.value=32769;route();assert l.audio_active()==0;count.value=128;mode.value=0
 # Genuine initial birth, no further body/health/ammo/generation/clock writes.
 assert l.sim_init(64,42)==0
 for e in E[:64]:e.hp=0
 plane(31,3500,z=4000,role=1);A[31].ammo=0
 assert l.audio_load_kind(3,str(path).encode())==0
 blocks=[];starts=[]
 for tick in range(1,61):
  l.sim_tick();route();wave=stereo(800);blocks.append([sum(abs(v)for v in wave[::2]),sum(abs(v)for v in wave[1::2])]);starts.append(counter('audio_loop_started'))
 assert starts==[1]*60 and E[31].hp==200 and A[31].ammo==0 and all(sum(x)>0 for x in blocks)
 assert len({tuple(x)for x in blocks})>50 and l.audio_active()==1
 print(json.dumps(dict(suite='aircraft-recorded-audio',passed=True,recorded_frames_verified=121*800,invalid_source_cases=len(bad),pool_limit=128,nearest_source_limit=8,public_flight_ticks=60,public_loop_starts=starts[-1],powerless_glide_engine_silence=True,public_channel_energy=blocks,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),library_sha256=hashlib.sha256(so.read_bytes()).hexdigest(),scope='Actual native looping/moving panning and distance gain; initial live aircraft only, authority readonly. Fixed-rate recorded field excerpt; no Doppler/delay/occlusion or audible hardware quality acceptance.')))
