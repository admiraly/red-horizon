#!/usr/bin/env python3
"""Real assembly dual-bank mixing and authoritative combat_event ring routing."""
import argparse,ctypes as C,hashlib,json,pathlib,struct,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--nasm',required=True);args=a.parse_args()
with tempfile.TemporaryDirectory(prefix='rh-audio-battle-') as directory:
 w=pathlib.Path(directory)
 fixture=w/'authority.asm';fixture.write_text('''section .bss
global sim_players,sim_player_vehicle,sim_entities,sim_count,sim_tick_count
sim_players: resb 256
sim_player_vehicle: resb 16
sim_entities: resb 1048576
sim_count: resd 1
sim_tick_count: resd 1
section .text
global sim_blast,sim_shell_contact,terrain_height,terrain_los
sim_blast:
sim_shell_contact:
terrain_height:
terrain_los:
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
''')
 objects=[]
 for i,path in enumerate((root/'src/audio/audio.asm',root/'src/audio/emitters.asm',root/'src/sim/projectiles.asm',fixture)):
  obj=w/f'{i}.o';objects.append(str(obj));subprocess.run([args.nasm,'-f','elf64','-I',str(root)+'/',str(path),'-o',str(obj)],check=True)
 shared=w/'battle.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(shared),*objects,'-lasound'],check=True)
 lib=C.CDLL(str(shared))
 lib.audio_load.argtypes=[C.c_char_p];lib.audio_load_kind.argtypes=[C.c_uint,C.c_char_p]
 lib.audio_emit_kind.argtypes=[C.c_uint]+[C.c_float]*4
 lib.audio_listener.argtypes=[C.c_float]*5
 lib.audio_scene_update.argtypes=[C.c_uint]+[C.c_float]*5
 lib.combat_event.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
 for name in ('audio_mix','audio_mix_stereo'):getattr(lib,name).argtypes=[C.POINTER(C.c_int16),C.c_size_t]
 def counter(name):return C.c_uint64.in_dll(lib,name).value
 def emit(bank):assert lib.audio_emit_kind(bank,4000,20,4000,1)==0
 def load(bank,values):
  path=w/f'{bank}.pcm';path.write_bytes(struct.pack('<'+'h'*len(values),*values));assert lib.audio_load_kind(bank,str(path).encode())==0
 def mix(n,stereo=False):
  k=2 if stereo else 1;o=(C.c_int16*(n*k+2))();o[n*k]=1234;o[n*k+1]=-2345
  assert getattr(lib,'audio_mix_stereo' if stereo else 'audio_mix')(o,n)==n
  assert list(o)[n*k:]==[1234,-2345]
  return list(o)[:n*k]
 assert lib.audio_listener(4000,20,4000,1,0)==0
 load(0,[2000,-4000]);load(1,[6000,8000,10000])
 emit(0);emit(1)
 assert mix(4)==[8000,4000,10000,0] and lib.audio_active()==0,'bank overlap/retirement'
 load(0,[2000,-4000]);load(1,[6000,8000,10000]);emit(0);emit(1)
 assert mix(4,True)==[4000,4000,2000,2000,5000,5000,0,0]
 load(0,[2000]);load(1,[-6000]*3)
 for i in range(128):emit(i%2)
 assert lib.audio_active()==128
 assert mix(1)==[-32768]
 # Rifle voices have expired but explosion voices persist. Replacing rifle0
 # should count free; replacing explosion1 must count actual replacement.
 emit(1);assert counter('audio_replaced')==0
 emit(0);assert counter('audio_replaced')==1
 assert lib.audio_active()==65,'one bounded shared pool and bank-length retirement'
 assert mix(3,True)==[-32768,-32768,-32768,-32768,-3000,-3000]
 for bad in (b'',b'\0',b'\0'*384002):
  p=w/'bad.pcm';p.write_bytes(bad);assert lib.audio_load_kind(1,str(p).encode())==1
  assert lib.audio_emit_kind(1,4000,20,4000,1)==-1
 assert lib.audio_load_kind(2,b'nope')==1
 assert lib.audio_load_kind(1,b'nope')==1
 assert lib.audio_emit_kind(2,4000,20,4000,1)==-1
 # Existing bank remains valid when the other bank fails.
 assert lib.audio_load(str(root/'content/audio/rifle.pcm').encode())==0
 assert lib.audio_load_kind(1,str(root/'content/audio/explosion.pcm').encode())==0
 for bank,file in ((0,'rifle.pcm'),(1,'explosion.pcm')):
  assert lib.audio_load_kind(bank,str(root/'content/audio'/file).encode())==0
  recorded=(root/'content/audio'/file).read_bytes();emit(bank)
  expected=struct.unpack('<800h',recorded[:1600]);assert any(expected)
  assert mix(800,True)==[v>>1 for v in expected for _ in range(2)],'exact recorded bank waveform'
 # Recordings overlap independently; no accidental cross-bank reads.
 assert lib.audio_load(str(root/'content/audio/rifle.pcm').encode())==0
 assert lib.audio_load_kind(1,str(root/'content/audio/explosion.pcm').encode())==0
 emit(0);emit(1)
 r=struct.unpack('<800h',(root/'content/audio/rifle.pcm').read_bytes()[:1600])
 e=struct.unpack('<800h',(root/'content/audio/explosion.pcm').read_bytes()[:1600])
 clamp=lambda v:max(-32768,min(32767,v))
 assert mix(800,True)==[clamp((x>>1)+(y>>1)) for x,y in zip(r,e) for _ in range(2)]
 # Fresh mixer state for authoritative routing: records written by combat_event.
 assert lib.audio_load_kind(1,str(root/'content/audio/explosion.pcm').encode())==0
 ticks=C.c_uint.in_dll(lib,'sim_tick_count');ticks.value=100
 seq=C.c_uint.in_dll(lib,'sim_event_sequence');ring=(C.c_ubyte*8192).in_dll(lib,'sim_events')
 players=(C.c_ubyte*256).in_dll(lib,'sim_players')
 def event(kind,x=4000):lib.combat_event(kind,1,x,20,4000,25)
 def update():
  before=bytes(ring),bytes(players),seq.value,ticks.value
  lib.audio_scene_update(0,4000,20,4000,1,0)
  assert (bytes(ring),bytes(players),seq.value,ticks.value)==before,'audio wrote authority'
 for kind in range(1,11):event(kind)
 update();assert counter('audio_battle_events')==5 and counter('audio_airgun_events')==1
 assert counter('audio_submitted')==6,'launch/unknown kinds must not make impact sounds'
 for _ in range(360):update()
 assert counter('audio_submitted')==6,'render frame repetition duplicated authority audio'
 # Stale/future events and mismatched overwritten slot are never played.
 event(7);ticks.value=116;update();assert counter('audio_submitted')==6
 ticks.value=200;event(7);ticks.value=199;update();assert counter('audio_submitted')==6
 ticks.value=200;event(7);struct.pack_into('<I',ring,(seq.value&255)*32+28,0);update();assert counter('audio_submitted')==6
 event(7,7000);update();assert counter('audio_submitted')==6 and counter('audio_culled')==1
 ticks.value=201
 for _ in range(300):event(7)
 update();assert counter('audio_submitted')==262 and lib.audio_active()==128,'bounded latest 256 events/128 voices'
 assert C.c_uint.in_dll(lib,'audio_event_cursor').value==seq.value
 lib.reset_event_ring();update();assert counter('audio_submitted')==262,'scenario reset replayed events'
 event(9);update();assert counter('audio_submitted')==263,'new events after reset lost'
 manifest=json.loads((root/'content/asset-manifest.json').read_text())
 asset=next(a for a in manifest['assets'] if a['id']=='explosion-surrogate')
 assert asset['recorded'] and hashlib.sha256((root/asset['source_file']).read_bytes()).hexdigest()==asset['original_sha256']
 assert hashlib.sha256((root/asset['destination']).read_bytes()).hexdigest()==asset['derived_sha256']
 print(json.dumps({'suite':'audio-battle','passed':True,'checks':['mono/stereo bank overlap and retirement','shared128 pool/replacement by bank length','malformed/missing bank','exact rifle/explosion recorded waveforms','actual combat_event routing kinds3/4/5/7/8/9','360 frame dedup and authority immutability','stale/future/overwritten rejection','distance cull','300-event backlog bounded256','scenario reset'],'recording_limitation':asset['limitation']}))
