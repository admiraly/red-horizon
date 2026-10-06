#!/usr/bin/env python3
"""Development causal control: actual movement with the dynamic route hook omitted."""
import hashlib,json,os,pathlib,subprocess,tempfile,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
source=(ROOT/'src/nav/squads.asm').read_text();assert source.count(' call wreck_nav_goal')==1
with tempfile.TemporaryDirectory(prefix='rh-no-wreck-route-') as td:
 td=pathlib.Path(td);asm=td/'squads.asm';asm.write_text(source.replace(' call wreck_nav_goal',' ; causal negative: omit dynamic route proposal'))
 obj=td/'squads.o';subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True)
 objects=[str(ROOT/'build'/(str(p.relative_to(ROOT)).replace('/','_')+'.o')) for folder in ('sim','nav','ai','game') for p in (ROOT/'src'/folder).glob('*.asm') if p!=ROOT/'src/nav/squads.asm']
 library=td/'no-route.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',str(obj),*objects,'-lm','-o',str(library)],check=True)
 subprocess.run([sys.executable,str(ROOT/'tests/test_wreck_nav_outcomes.py'),str(library),'--negative-no-route'],check=True)
 print(json.dumps({'control':'actual_dynamic_route_hook_omitted','detected':True,'only_mutation':'call wreck_nav_goal omitted','assembly_source_sha256':hashlib.sha256(asm.read_bytes()).hexdigest()}))
