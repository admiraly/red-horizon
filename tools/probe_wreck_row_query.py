#!/usr/bin/env python3
"""Development-only immutable paired runtime experiment; never overwrites input libs."""
import argparse,ctypes as C,hashlib,json,math,os,pathlib,subprocess,tempfile,time
p=argparse.ArgumentParser();p.add_argument('--baseline-root',type=pathlib.Path,required=True);p.add_argument('--ticks',type=int,default=900);p.add_argument('--report',type=pathlib.Path);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];base=a.baseline_root.resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='rh-wreck-row-runtime-') as name:
 td=pathlib.Path(name);objects=[];inputs={}
 for folder in ('sim','nav','ai','game'):
  for src in sorted((base/'src'/folder).glob('*.asm')):
   rel=src.relative_to(base);obj=base/'build'/(str(rel).replace('/','_')+'.o');dest=td/obj.name;dest.write_bytes(obj.read_bytes());inputs[str(rel)]={'source_sha256':sha(src),'object_sha256':sha(dest)};objects.append(dest)
 probe=td/'terrain_probe.o';probe.write_bytes((base/'build/terrain_probe.o').read_bytes())
 def link(path,objs):subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),str(probe),'-lm'],check=True)
 paths=[td/'baseline.so',td/'candidate.so'];link(paths[0],objects)
 new=td/'row-query.o';subprocess.run([os.environ.get('RED_HORIZON_NASM','nasm'),'-f','elf64','-I',str(root)+'/',str(root/'src/nav/wreck_query.asm'),'-o',str(new)],check=True)
 link(paths[1],[new if o.name=='src_nav_wreck_query.asm.o' else o for o in objects])
 libs=[C.CDLL(str(x)) for x in paths]
 for lib in libs:lib.sim_checksum.restype=C.c_uint64
 reports=[]
 for units,scenario in [(8192,0),(8192,3),(16384,0)]:
  for lib in libs:
   assert lib.sim_init(units,42)==0
   if scenario:assert lib.sim_scenario(scenario)==0
  times=[[],[]];samples=[]
  for tick in range(1,a.ticks+1):
   for i in ([0,1] if tick%2 else [1,0]):
    start=time.perf_counter_ns();libs[i].sim_tick();times[i].append((time.perf_counter_ns()-start)/1e6)
   if tick%30==0 or tick==a.ticks:
    hashes=[lib.sim_checksum() for lib in libs];assert hashes[0]==hashes[1],(units,scenario,tick,hashes)
    assert bytes((C.c_ubyte*(32768*32)).in_dll(libs[0],'sim_entities'))==bytes((C.c_ubyte*(32768*32)).in_dll(libs[1],'sim_entities'))
    samples.append(f'{hashes[0]:016x}')
  report={'units':units,'scenario':scenario,'ticks':a.ticks,'equal_checksum_and_all_entity_samples':samples,'timings':[{'mean_ms':sum(t)/len(t),'p95_ms':sorted(t)[math.ceil(.95*len(t))-1]} for t in times]};reports.append(report);print(json.dumps(report),flush=True)
 output={'passed':True,'baseline_root':str(base),'input_objects':inputs,'candidate_query_source_sha256':sha(root/'src/nav/wreck_query.asm'),'library_sha256':[sha(x) for x in paths],'reports':reports,'limits':['Paired production simulation, identical copied objects except wreck_query; immutable libraries.','Authority checksum and all entity bytes every30 ticks, seed42; concurrent frozen verification may affect timings.','Not graphical, UDP, human-quality or full integration acceptance.']}
 target=a.report or root/'docs/evidence/wreck-row-runtime.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(output,indent=2)+'\n')
