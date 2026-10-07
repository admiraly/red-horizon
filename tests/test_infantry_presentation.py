#!/usr/bin/env python3
"""Actual native shot -> recorded PCM/brief source flash; authority stays identical."""
import ctypes as C,hashlib,json,os,pathlib,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-infantry-presentation-') as directory:
 shared=pathlib.Path(directory)/'presentation.so'
 objects=[str(root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o'))for folder in ('sim','nav','ai','game')for p in (root/'src'/folder).glob('*.asm')]
 objects += [str(root/'build'/name)for name in ('terrain_probe.o','src_render_effects.asm.o','src_audio_audio.asm.o','src_audio_emitters.asm.o')]
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(shared),*objects,'-lm','-lasound'],check=True)
 sys.argv=[sys.argv[0],str(shared)]
 prefix=(root/'tests/test_infantry_human_targets.py').read_text().split('closer=run(')[0];exec(compile(prefix,'<actual native fixture>','exec'))
 l.effects_update.argtypes=[C.c_uint,C.c_float];l.audio_scene_update.argtypes=[C.c_uint]+[C.c_float]*5;l.audio_load.argtypes=[C.c_char_p];l.audio_mix_stereo.argtypes=[C.POINTER(C.c_int16),C.c_size_t]
 assert l.audio_load(str(root/'content/audio/rifle.pcm').encode())==0
 setup();flash=C.c_uint.in_dll(l,'effects_rifle_flashes');sounds=C.c_uint64.in_dll(l,'audio_infantry_events');effects=(C.c_ubyte*2048).in_dll(l,'effects_records');samples=(C.c_int16*1600)();reports=[];oldshots=0;pcm_nonzero=0
 for t in range(1,81):
  l.sim_tick();authority=l.sim_checksum();priorflash=flash.value;priorsound=sounds.value
  l.effects_update(0,1/30);l.audio_scene_update(0,p[0].x,p[0].y,p[0].z,1.,0.)
  actual=w[140]-oldshots
  assert flash.value-priorflash==sounds.value-priorsound==actual,(t,actual,flash.value,sounds.value)
  for _ in range(3):l.effects_update(0,0.);l.audio_scene_update(0,p[0].x,p[0].y,p[0].z,1.,0.)
  assert flash.value==priorflash+actual and sounds.value==priorsound+actual,'frame duplicate'
  assert l.sim_checksum()==authority,'cosmetic consumption altered authority'
  active=[]
  for i in range(64):
   row=__import__('struct').unpack_from('<7fI',effects,i*32)
   if row[3]>0:
    assert row[7]==2 and row[4]==.25 and row[3]<=.065001,row
    active.append(row)
  assert len(active)<=1,'rifle event produced explosive layers'
  assert l.audio_mix_stereo(samples,800)==800
  if actual:
   assert active and sum(abs(v)for v in samples)>0,'missing actual flash/recorded waveform'
   pcm_nonzero+=1;reports.append({'tick':t,'flash_xyz':active[0][:3],'life_s':active[0][3],'radius_m':active[0][4]})
  oldshots=w[140]
 assert flash.value==sounds.value==10 and pcm_nonzero==10
 print(json.dumps({'suite':'actual-infantry-presentation','passed':True,'actual_shots':10,'recorded_pcm_nonzero_shots':pcm_nonzero,'brief_flashes':reports,'authority_unchanged_by_consumers':True,'same_frame_no_duplicates':True,'no_explosive_layers':True,'library_sha256':hashlib.sha256(shared.read_bytes()).hexdigest(),'limits':['Native production effects/audio routing with actual sim_tick, not GPU pixels or physical sound quality.','Source body eye approximates muzzle; aiming and bullet trajectories remain separate.']}))
