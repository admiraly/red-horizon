#!/usr/bin/env python3
"""Development-only same-world/query differential and paired actual tick timing."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,sys,time
R=pathlib.Path(__file__).resolve().parents[1];B=R/'build';baseline=B/'libpass-plain.so';output=pathlib.Path(sys.argv[1]);nasm=os.environ['RED_HORIZON_NASM']
obj=B/'wreck-envelope.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(R/'src/nav/wreck_query.asm'),'-o',str(obj)],check=True)
objects=[B/(str(p.relative_to(R)).replace('/','_')+'.o') for f in ('sim','nav','ai','game') for p in (R/'src'/f).glob('*.asm') if p.name!='wreck_query.asm'];candidate=B/'libwreck-envelope.so'
subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(candidate),*map(str,objects),str(obj),str(B/'terrain_probe.o'),'-lm'],check=True)
libs=[C.CDLL(str(p)) for p in (baseline,candidate)]
for lib in libs:
 lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_checksum.restype=C.c_uint64
 lib.wreck_query.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*6;lib.wreck_body_query.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*5
for lib in libs:assert lib.sim_init(8192,42)==0 and lib.sim_scenario(3)==0
samples=[[],[]];hashes=[]
for tick in range(1,901):
 for i in (tick%2,1-tick%2):
  started=time.perf_counter_ns();libs[i].sim_tick();samples[i].append((time.perf_counter_ns()-started)/1e6)
 if tick%30==0:
  values=[lib.sim_checksum() for lib in libs];assert values[0]==values[1],(tick,values);hashes.append(f'{values[0]:016x}')
records=[(C.c_ubyte*65536).in_dll(lib,'sim_wrecks') for lib in libs];assert bytes(records[0])==bytes(records[1]);before=[lib.sim_checksum() for lib in libs]
boxes=(C.c_float*(1024*6)).in_dll(libs[0],'wreck_query_bounds');out=[C.create_string_buffer(24) for _ in libs];count=hits=0
# Warm the derived source bounds using a valid query.
for i,lib in enumerate(libs):lib.wreck_query(out[i],24,0,100,0,8000,100,8000)
def check(args,body=False):
 global count,hits
 results=[]
 for i,lib in enumerate(libs):
  C.memset(out[i],90,24);rc=(lib.wreck_body_query if body else lib.wreck_query)(out[i],24,*args);results.append((rc,out[i].raw))
 assert results[0]==results[1],(args,body,results)
 count+=1;hits+=results[0][0]==1
rng=random.Random(198618)
for _ in range(12000):
 x,z=rng.uniform(0,8000),rng.uniform(0,8000);check((x,rng.uniform(0,200),z,x+rng.uniform(-100,100),rng.uniform(0,200),z+rng.uniform(-100,100)))
for slot in range(1024):
 record=bytes(records[0][slot*64:(slot+1)*64])
 if not struct.unpack_from('<I',record,52)[0]&1:continue
 xmin,ymin,zmin,xmax,ymax,zmax=boxes[slot*6:(slot+1)*6]
 for radius in (0,.551,3.551,4.491):
  for direction in (-1,1):
   for off in (-.005,-.002,0,.002,.005):
    x=(xmin-radius if direction<0 else xmax+radius)+off;z=(zmin+zmax)/2
    check((x-direction*10,z,x,z,radius),True)
 for y in (ymin-.005,ymin,ymax,ymax+.005):check((xmin-10,y,(zmin+zmax)/2,xmax+10,y,(zmin+zmax)/2))
assert [lib.sim_checksum() for lib in libs]==before
rows=[{'variant':name,'tick_ms_mean':sum(s)/len(s),'tick_ms_p95':sorted(s)[math.ceil(.95*len(s))-1],'tick_ms_p99':sorted(s)[math.ceil(.99*len(s))-1]} for name,s in zip(('baseline','envelope'),samples)]
d={'suite':'wreck-envelope-controlled-differential','passed':True,'ticks':900,'units':8192,'seed':42,'scenario':'scale-hotspot','paired_order_alternates_each_tick':True,'authoritative_checksums_equal_every30ticks':hashes,'wreck_bytes_equal':True,'query_results_byte_equal':count,'query_hits':hits,'queries_readonly':True,'timings':rows,'library_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (baseline,candidate)},'source_sha256':hashlib.sha256((R/'src/nav/wreck_query.asm').read_bytes()).hexdigest(),'limits':['Concurrent full checkpoint; paired same-world timings, not isolated target GPU acceptance.','Conservative4mm rejection allowance, exact original slab/escape decisions for surviving candidates.','No new geometry or combat rules; malformed sources remain validated before rejection.']}
output.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
