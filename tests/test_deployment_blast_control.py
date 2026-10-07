#!/usr/bin/env python3
"""Development-only omitted-hook causal control; no production bypass flag."""
import json,pathlib,subprocess,sys,tempfile,os
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-deployment-causal-') as temp:
 folder=pathlib.Path(temp);source=root/'src/game/player.asm'
 text=source.read_text();assert text.count(' call deployment_blast_clear')==1
 altered=folder/'player.asm';altered.write_text(text.replace(' call deployment_blast_clear',' xor eax,eax ; development-only omitted deployment guard'))
 obj=folder/'player.o'
 subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','-I',str(root)+'/',str(altered),'-o',str(obj)],check=True)
 objects=[str(root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o')) for d in ('sim','nav','ai','game') for p in (root/'src'/d).glob('*.asm') if p!=source]
 library=folder/'libcontrol.so'
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(library),*objects,str(obj),'-lm'],check=True)
 report=json.loads(subprocess.check_output([sys.executable,str(root/'tests/test_deployment_blast.py'),str(library),'--baseline'],text=True))
 assert report['baseline_hook_omitted'] and report['initial_avoided_distance_m']==0 and report['minimum_hp_over60ticks']==20
 print(json.dumps({'suite':'deployment-blast-omitted-hook-control','passed':True,'same_runtime_objects_except_guard_call':True,'original_source_preserved':source.read_text()==text,'control':report}))
