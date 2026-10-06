#!/usr/bin/env python3
"""Development-only instrumented build; no runtime source edits or game wrapper."""
import ctypes as C,hashlib,json,math,os,pathlib,re,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[2];B=ROOT/'build';OUT=pathlib.Path(sys.argv[1]).resolve()
def run(args):subprocess.run(args,cwd=ROOT,check=True)
run([sys.executable,'tools/dev.py','build','--target','headless'])
nasm=os.environ['RED_HORIZON_NASM'];objects=[B/(str(p.relative_to(ROOT)).replace('/','_')+'.o') for f in ('sim','nav','ai','game') for p in (ROOT/'src'/f).glob('*.asm')]
probe=B/'terrain_probe.o';run([nasm,'-f','elf64','tests/terrain_probe.asm','-o',str(probe)])
plain=B/'libpass-plain.so';run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(plain),*map(str,objects),str(probe),'-lm'])
src=(ROOT/'src/sim/world.asm').read_text();begin=src.index('sim_tick:');end=src.index('sim_checksum:');part=src[begin:end]
los_src=(ROOT/'src/nav/world_los.asm').read_text(); nested=sorted(set(re.findall(r'^ call (\w+)\s*$',los_src,re.M)))
names=sorted(set(re.findall(r'^ call (\w+)\s*$',part,re.M))|set(nested));source=src[:begin]+re.sub(r'^ call (\w+)\s*$',lambda m:' call profile_'+m[1],part,flags=re.M)+src[end:]
source+='\nextern terrain_ground_query,terrain_solid_query,wreck_query_context\nsection .bss align=64\nglobal profile_cycles,profile_calls\nprofile_cycles: resq '+str(len(names))+'\nprofile_calls: resq '+str(len(names))+'\nsection .text\n'
for i,name in enumerate(names):
 source+=f'''global profile_{name}
profile_{name}:
 sub rsp,40
 mov [rsp],rax
 mov [rsp+8],rdx
 lfence
 rdtsc
 shl rdx,32
 or rax,rdx
 mov [rsp+16],rax
 mov rax,[rsp]
 mov rdx,[rsp+8]
 call {name}
 mov [rsp],rax
 mov [rsp+8],rdx
 lfence
 rdtsc
 shl rdx,32
 or rax,rdx
 sub rax,[rsp+16]
 add [profile_cycles+{i*8}],rax
 inc qword [profile_calls+{i*8}]
 mov rax,[rsp]
 mov rdx,[rsp+8]
 add rsp,40
 ret
'''
p=B/'profile_world.asm';p.write_text(source);obj=B/'profile_world.o';run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)])
los_generated=los_src+'\nextern '+','.join('profile_'+name for name in nested)+'\n'
los_generated=re.sub(r'^ call (\w+)\s*$',lambda m:' call profile_'+m[1],los_generated,flags=re.M)
los_asm=B/'profile_los.asm';los_asm.write_text(los_generated);los_obj=B/'profile_los.o';run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(los_asm),'-o',str(los_obj)])
profile=B/'libpass-profile.so';run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(profile),*[str(obj if x.name=='src_sim_world.asm.o' else los_obj if x.name=='src_nav_world_los.asm.o' else x) for x in objects],str(probe),'-lm'])
libs=[C.CDLL(str(x)) for x in (plain,profile)]
for lib in libs:lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_checksum.restype=C.c_uint64
cycles=(C.c_uint64*len(names)).in_dll(libs[1],'profile_cycles');calls=(C.c_uint64*len(names)).in_dll(libs[1],'profile_calls')
reports=[]
for units,scenario in ((8192,0),(8192,3)):
 results=[]
 for li,lib in enumerate(libs):
  assert lib.sim_init(units,42)==0
  if scenario:assert lib.sim_scenario(scenario)==0
  if li:
   for i in range(len(names)):cycles[i]=calls[i]=0
  hashes=[];times=[]
  for tick in range(1,901):
   started=time.perf_counter_ns();lib.sim_tick();times.append((time.perf_counter_ns()-started)/1e6)
   if tick%30==0:hashes.append(f'{lib.sim_checksum():016x}')
  results.append({'checksum_samples':hashes,'tick_ms_mean':sum(times)/len(times),'tick_ms_p95':sorted(times)[math.ceil(.95*len(times))-1]})
 assert results[0]['checksum_samples']==results[1]['checksum_samples'],'profiling changed authority'
 total=sum(cycles[i] for i,name in enumerate(names)if name not in nested);passes=sorted([{'pass':n,'calls':calls[i],'tsc_cycles':cycles[i],'inclusive_fraction_of_measured_calls':cycles[i]/total if total else 0} for i,n in enumerate(names)if n not in nested],key=lambda x:x['tsc_cycles'],reverse=True)
 nested_total=sum(cycles[i]for i,n in enumerate(names)if n in nested)
 components=[{'pass':n,'calls':calls[i],'tsc_cycles':cycles[i],'fraction_of_LOS_component_calls':cycles[i]/nested_total if nested_total else 0}for i,n in enumerate(names)if n in nested]
 reports.append({'units':units,'scenario':'scale-hotspot' if scenario else 'scale-open','seed':42,'ticks':900,'plain':results[0],'instrumented':results[1],'passes':passes,'world_los_components':components})
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps({'suite':'instrumented-sim-pass-profile','passed':True,'reports':reports,'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'library_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (plain,profile)},'limits':['Development-only LFENCE/RDTSC wrappers; timing instrumentation adds overhead.','Inclusive cycles of direct sim_tick calls; main tick loops excluded. LOS subcomponent fractions separately normalize ground/solid/wreck calls and exclude parent double counting.','Concurrent checkpoint workloads; not isolated hardware or causal performance acceptance.','Every30tick authoritative checksum agrees between production and instrumented builds.']},indent=2)+'\n')
print(OUT.read_text())
