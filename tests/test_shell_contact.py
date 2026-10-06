#!/usr/bin/env python3
"""Production sampled-actor first-entry ordering, actual NASM and readonly state."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm');LIB=pathlib.Path(sys.argv[1]).resolve()
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
def entry(center,start,end):
 m=[start[i]-center[i] for i in range(3)];d=[end[i]-start[i] for i in range(3)];a=sum(x*x for x in d);b=sum(x*y for x,y in zip(m,d));c=sum(x*x for x in m)-16
 if c<=0:return 0.
 if not a or b>=0:return None
 disc=b*b-a*c
 if disc<0:return None
 t=(-b-math.sqrt(disc))/a
 return t if 0<=t<=1 else None
with tempfile.TemporaryDirectory(prefix='rh-shell-contact-') as name:
 td=pathlib.Path(name);obj=td/'probe.o';subprocess.run([NASM,'-f','elf64',str(ROOT/'tests/probe_shell_contact.asm'),'-o',str(obj)],check=True)
 dll=td/'probe.so';subprocess.run(['cc','-shared',str(obj),str(LIB),'-Wl,-rpath,'+str(LIB.parent),'-o',str(dll)],check=True)
 lib=C.CDLL(str(LIB));probe=C.CDLL(str(dll));probe.probe_shell_contact.argtypes=[C.c_uint,C.c_void_p]+[C.c_float]*6
 lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_checksum.restype=C.c_uint64;lib.sim_entity_height.argtypes=[C.c_uint];lib.sim_entity_height.restype=C.c_float
 entities=(Entity*32768).in_dll(lib,'sim_entities');alive=(C.c_uint*2).in_dll(lib,'sim_alive');calls=0;max_error=0.;cases=[]
 def fixture(rows):
  assert lib.sim_init(64,42)==0
  for e in entities[:64]:e.hp=0
  alive[0]=alive[1]=0
  for side in (0,1):
   for front in range(3):assert lib.sim_order(side,front,1)==0
  for i,x,z,side in rows:entities[i]=Entity(x,z,1000,side,0,0,-1,42);alive[side]+=1
  lib.sim_tick() # production index from declared births; no later state writes
  return {i:(entities[i].x,float(lib.sim_entity_height(i)),entities[i].z) for i,_,_,_ in rows}
 def query(centers,start,end,side=0):
  global calls,max_error
  start,end=tuple(C.c_float(q).value for q in start),tuple(C.c_float(q).value for q in end);regs=C.create_string_buffer(64);before=lib.sim_checksum()
  actual=probe.probe_shell_contact(side,regs,*start,*end);assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert lib.sim_checksum()==before
  expected=[]
  for i,center in centers.items():
   if entities[i].side==side or not entities[i].hp:continue
   t=entry(center,start,end)
   if t is not None:expected.append((C.c_float(t).value,i))
  wanted=min(expected) if expected else None;assert actual==(-1 if wanted is None else wanted[1]),(actual,wanted,start,end)
  xyz=struct.unpack('<3f',regs.raw[48:60]);reported_t=struct.unpack('<f',regs.raw[60:64])[0]
  if wanted:
   assert abs(reported_t-wanted[0])<6e-8
   expected_xyz=[C.c_float(C.c_float(end[j]-start[j]).value*wanted[0]+start[j]).value for j in range(3)];error=max(abs(xyz[j]-expected_xyz[j]) for j in range(3));max_error=max(max_error,error);assert error<=.00025,(xyz,expected_xyz)
  calls+=1;return actual,xyz
 c=fixture([(0,1012,1000,1),(24,1006,1000,1)]);y=c[24][1]
 hit,xyz=query(c,(990,y,1000),(1020,y,1000));assert hit==24;cases.append({'name':'nearer_high_ID_before_far_low_ID','hit':hit,'contact':xyz})
 hit,xyz=query(c,(1020,y,1000),(990,y,1000));assert hit==0;cases.append({'name':'reverse_ray_reverses_nearest','hit':hit,'contact':xyz})
 query(c,(1002.2,y,990),(1002.2,y,1010));query(c,(1006,y,1000),(1006,y,1000));query(c,(980,y,1000),(980,y,1000));query(c,(990,y,1000),(1020,y,1000),side=1)
 c=fixture([(0,1006,1000,1),(24,1006,1000,1)]);hit,_=query(c,(990,c[0][1],1000),(1020,c[0][1],1000));assert hit==0;cases.append({'name':'equal_contact_physical_ID_tie','hit':hit})
 rng=random.Random(33715);births=[(i,1000+rng.random()*120,1000+rng.random()*120,1) for i in range(12)];c=fixture(births)
 for _ in range(200):
  i=rng.randrange(12);center=c[i];start=[center[0]+rng.uniform(-20,20),center[1]+rng.uniform(-5,5),center[2]+rng.uniform(-20,20)];end=[center[0]+rng.uniform(-20,20),center[1]+rng.uniform(-5,5),center[2]+rng.uniform(-20,20)];query(c,start,end)
 print(json.dumps({'suite':'production-shell-first-entry','passed':True,'calls':calls,'random_paths':200,'cases':cases,'max_contact_xyz_error_m':max_error,'radius_m':4,'readonly_checksum_ABI':True,'library_sha256':hashlib.sha256(LIB.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'src/sim/world.asm').read_bytes()).hexdigest(),'scope':'Actual production index/query from declared initial births and one public tick. Nearest among at most216sampled live opposing4m contact envelopes, not all-actor or oriented hitbox/terrain/wreck arbitration acceptance.'}))
