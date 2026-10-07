#!/usr/bin/env python3
"""Black-box multi-frame reductions and authority immutability of diagnostics."""
import json,pathlib,subprocess,sys,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import dev
stub='''default rel
extern battle_metrics_reset,battle_metrics_capture,battle_metrics_report
section .data
global sim_alive,sim_engaged,sim_projectile_count,mesh_high_instances,mesh_low_instances,mesh_marker_instances,effects_active,air_trails_active
sim_alive: dd 4096,4096
sim_engaged: dd 2100
sim_projectile_count: dd 12
mesh_high_instances: dd 252
mesh_low_instances: dd 1300
mesh_marker_instances: dd 6640
effects_active: dd 9
air_trails_active: dd 24
voices: dd 7
section .text
global main,audio_active
audio_active:
 mov eax,[voices]
 ret
main:
 sub rsp,8
 call battle_metrics_reset
 call battle_metrics_capture
 mov dword [sim_alive],4000
 mov dword [sim_engaged],3100
 mov dword [mesh_low_instances],1100
 mov dword [voices],0
 call battle_metrics_capture
 mov dword [sim_projectile_count],0
 mov dword [voices],16
 call battle_metrics_capture
 call battle_metrics_report
 cmp dword [sim_alive],4000
 jne .fail
 cmp dword [sim_alive+4],4096
 jne .fail
 cmp dword [sim_engaged],3100
 jne .fail
 cmp dword [mesh_low_instances],1100
 jne .fail
 call battle_metrics_reset
 call battle_metrics_report
 xor eax,eax
 jmp .done
.fail:
 mov eax,1
.done:
 add rsp,8
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
with tempfile.TemporaryDirectory() as directory:
 p=pathlib.Path(directory);(p/'stub.asm').write_text(stub)
 for source,name in ((dev.ROOT/'src/render/battle_metrics.asm','metrics'),(p/'stub.asm','stub')):
  subprocess.run([dev.nasm(),'-f','elf64',str(source),'-o',str(p/(name+'.o'))],check=True)
 subprocess.run(['gcc','-no-pie','-Wl,-z,noexecstack',str(p/'stub.o'),str(p/'metrics.o'),'-o',str(p/'probe')],check=True)
 rows=[json.loads(line) for line in subprocess.check_output([str(p/'probe')],text=True).splitlines()]
 a,b=rows
 assert a['initial_living']==8192 and b['initial_living']==8096,(a,b)
 assert a['samples']==3 and a['simultaneous_projectiles_effects_audio_frames']==1,a
 expected={'peak_living':8192,'peak_engaged':3100,'peak_projectiles':12,'peak_submitted_high':252,'peak_submitted_low':1300,'peak_submitted_markers':6640,'peak_effect_records':9,'peak_trail_records':24,'peak_audio_voices':16}
 assert all(a[k]==v for k,v in expected.items()),a
 assert b['samples']==0 and all(b[k]==0 for k in expected),b
 assert a['visible_individual_count']=='unmeasured'
print(json.dumps({'suite':'battle-metrics','passed':True,'multi_frame_reduction':True,'independent_peaks_distinguished':True,'simultaneous_positive_negative_frames':True,'reset':True,'authority_unchanged':True}))
