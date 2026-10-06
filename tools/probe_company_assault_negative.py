#!/usr/bin/env python3
"""Development causal control: omit only production company movement goals."""
import json,os,pathlib,subprocess,tempfile
R=pathlib.Path.cwd();B=R/'build';nasm=os.environ['RED_HORIZON_NASM']
with tempfile.TemporaryDirectory(prefix='rh-company-control-') as folder:
 t=pathlib.Path(folder);s=(R/'src/ai/tactics.asm').read_text();needle='.move: jmp company_goal';assert s.count(needle)==1
 p=t/'no-company-goal.asm';p.write_text(s.replace(needle,'.move: xor eax,eax\n ret'));o=t/'tactics.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(p),'-o',str(o)],check=True)
 objs=[B/(str(p.relative_to(R)).replace('/','_')+'.o') for f in ('sim','nav','ai','game') for p in (R/'src'/f).glob('*.asm') if p.name!='tactics.asm'];lib=t/'control.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(lib),*map(str,objs),str(o),str(B/'terrain_probe.o'),'-lm'],check=True)
 run=subprocess.run(['python3','tests/test_company_assault.py',str(lib)],cwd=R,capture_output=True,text=True,timeout=15)
 assert run.returncode!=0 and 'AssertionError' in run.stderr,(run.returncode,run.stdout,run.stderr)
 print(json.dumps({'suite':'omitted-company-goal-control','detected':True,'exit_code':run.returncode,'stderr':run.stderr,'no_other_runtime_module_changed':True,'same_initial_fixture_and_assertions':True}))
