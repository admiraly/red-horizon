#!/usr/bin/env python3
"""Read-only tactical stock API, private actual assembly core and ABI probe."""
import ctypes as C,hashlib,json,os,pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
nasm=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
with tempfile.TemporaryDirectory(prefix='rh-round-query-')as directory:
 td=pathlib.Path(directory);objects=[];hashes={}
 for folder in ('sim','nav','ai','game'):
  for p in(root/'src'/folder).glob('*.asm'):
   name=str(p.relative_to(root)).replace('/','_')+'.o';data=(root/'build'/name).read_bytes();dest=td/name;dest.write_bytes(data);objects.append(str(dest));hashes[name]=hashlib.sha256(data).hexdigest()
 probe=td/'probe.o';subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(root/'tests/probe_infantry_rounds.asm'),'-o',str(probe)],check=True)
 library=td/'rounds.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(library),*objects,str(probe),'-lm'],check=True)
 l=C.CDLL(str(library));l.sim_checksum.restype=C.c_uint64;l.probe_infantry_rounds.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_void_p];l.probe_infantry_rounds.restype=C.c_int
 entities=(C.c_uint*262144).in_dll(l,'sim_entities');stocks=(C.c_uint*262144).in_dll(l,'infantry_weapons');count=C.c_uint.in_dll(l,'sim_count');calls=0
 def query(actor):
  global calls
  registers=(C.c_uint64*7)();r=l.probe_infantry_rounds(actor,None,0,registers);calls+=1
  assert tuple(registers)==tuple(0x123401+i for i in range(6))+(0,);return r
 scenes=[]
 for ticks in (0,120):
  assert l.sim_init(128,73)==0
  for _ in range(ticks):l.sim_tick()
  before=l.sim_checksum();known=[]
  for i in range(128):
   e=entities[i*8:i*8+8];w=stocks[i*8:i*8+8]
   expected=w[1]+w[2]if e[2]and e[4]==0 and e[7]==w[0]else -1
   assert query(i)==expected
   if expected>=0:known.append(expected)
  assert l.sim_checksum()==before
  scenes.append({'ticks':ticks,'living_known_infantry':len(known),'minimum_rounds':min(known),'maximum_rounds':max(known)})
 assert l.sim_init(32,73)==0
 before=l.sim_checksum()
 for ident in (32,32768,0xffffffff):assert query(ident)==-1
 assert l.sim_checksum()==before
 malformed=[]
 for field,value in ((0,2),(1,31),(2,91),(3,61),(3,1),(4,121),(6,144001),(6,1)):
  old=stocks[field];stocks[field]=value;before=l.sim_checksum();assert query(0)==-1 and l.sim_checksum()==before;stocks[field]=old;malformed.append([field,value])
 old=count.value;count.value=32769;assert query(0)==-1;count.value=old
 print(json.dumps({'suite':'infantry-rounds-query-prerequisite','passed':True,'actual_initial_and120tick_scenes':scenes,'malformed_stock_unknown':malformed,'read_only_checksum':True,'abi_calls':calls,'core_object_sha256':hashes,'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'limits':['Read-only stock API foundation; no resupply detour, navigation namespace or world hook implemented; not integrated.']}))
