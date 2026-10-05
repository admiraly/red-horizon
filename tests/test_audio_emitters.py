#!/usr/bin/env python3
"""Unit routing fixtures use real assembly emitter/mixer and licensed PCM."""
import argparse
import ctypes as C
import json
import pathlib
import struct
import subprocess
import tempfile
root=pathlib.Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--nasm',required=True);args=a.parse_args()
with tempfile.TemporaryDirectory(prefix='rh-audio-routing-') as directory:
    work=pathlib.Path(directory)
    fixture=work/'records.asm';fixture.write_text('section .bss\nglobal sim_players,sim_player_vehicle,sim_events,sim_event_sequence,sim_tick_count\nsim_players: resb 256\nsim_player_vehicle: resb 16\nsim_events: resb 8192\nsim_event_sequence: resd 1\nsim_tick_count: resd 1\nsection .note.GNU-stack noalloc noexec nowrite progbits\n')
    objects=[]
    for i,path in enumerate((root/'src/audio/audio.asm',root/'src/audio/emitters.asm',fixture)):
        obj=work/f'{i}.o';objects.append(str(obj));subprocess.run([args.nasm,'-f','elf64','-I',str(root)+'/',str(path),'-o',str(obj)],check=True)
    shared=work/'routing.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(shared),*objects,'-lasound'],check=True)
    lib=C.CDLL(str(shared));lib.audio_load.argtypes=[C.c_char_p]
    lib.audio_scene_update.argtypes=[C.c_uint]+[C.c_float]*5
    lib.audio_mix_stereo.argtypes=[C.POINTER(C.c_int16),C.c_size_t]
    p=(C.c_ubyte*256).in_dll(lib,'sim_players');v=(C.c_int*4).in_dll(lib,'sim_player_vehicle')
    submitted=C.c_uint64.in_dll(lib,'audio_submitted');culled=C.c_uint64.in_dll(lib,'audio_culled');routed=C.c_uint64.in_dll(lib,'audio_remote_shots')
    for i in range(4):v[i]=-1
    def player(i,shots=0,generation=1,connected=1,x=4025):
        struct.pack_into('<3f',p,i*64,x,20,4000)
        struct.pack_into('<I',p,i*64+44,connected);struct.pack_into('<I',p,i*64+48,shots);struct.pack_into('<I',p,i*64+60,generation)
    def update():lib.audio_scene_update(0,4000,20,4000,1,0)
    assert lib.audio_load(str(root/'content/audio/rifle.pcm').encode())==0
    player(0,9);player(1,9);update()
    assert submitted.value==0,'initial snapshot replayed historical shots'
    player(0,10);update();assert submitted.value==0,'local weapon double played'
    player(1,10);update();assert submitted.value==1 and routed.value==1
    for _ in range(8):update()
    assert submitted.value==1,'frame cadence duplicated one authoritative shot'
    output=(C.c_int16*1600)();assert lib.audio_mix_stereo(output,800)==800
    assert sum(abs(output[i]) for i in range(1,1600,2))>sum(abs(output[i]) for i in range(0,1600,2)),'remote rifle was not panned right'
    player(1,10,generation=2);update();assert submitted.value==1,'redeploy replayed old shot'
    player(1,11,generation=2,connected=0);update();assert submitted.value==1
    player(1,11,generation=2);update();assert submitted.value==1,'join replayed baseline'
    player(1,12,generation=2);v[1]=12;update();assert submitted.value==1,'cannon generated rifle sound'
    v[1]=-1;player(1,13,generation=2,x=7000);update();assert submitted.value==1 and culled.value==1
    player(1,30,generation=2);update();assert submitted.value==2,'skipped snapshots should collapse to one latest rifle event'
    lib.audio_shutdown()
    print(json.dumps({'suite':'audio-emitters','passed':True,'checks':['actual recorded spatial waveform','local exclusion','generation and frame dedup','disconnected baseline','vehicle exclusion','distance cull','snapshot collapse']}))
