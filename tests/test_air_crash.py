#!/usr/bin/env python3
"""Actual death capture, bounded dead-airframe trajectories and lifecycle."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
class Observation(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in ('owner_gen','target','target_gen','tick','known')]+[('reserved',C.c_uint*5)]

class Crash(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','vx','vy','vz','heading','pitch','bank')]+[(n,C.c_uint)for n in ('role','side','entity','gen','birth','sequence','state')]+[('reserved',C.c_uint*8)]
with tempfile.TemporaryDirectory(prefix='rh-air-crash-')as folder:
 td=pathlib.Path(folder);objects=[]
 for source in [p for f in ('sim','nav','ai','game')for p in (R/'src'/f).glob('*.asm')]+[R/'tests/probe_air_crash.asm']:
  obj=td/(source.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(source),'-o',str(obj)],check=True);objects.append(obj)
 so=td/'crash.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(so),*map(str,objects),'-lm'],check=True)
 l=C.CDLL(str(so));l.sim_checksum.restype=C.c_uint64;l.probe_air_crash.argtypes=[C.c_uint,C.c_void_p];l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float
 e=(Entity*32768).in_dll(l,'sim_entities');a=(Air*32768).in_dll(l,'sim_aircraft');c=(Crash*128).in_dll(l,'sim_air_crashes');count=C.c_uint.in_dll(l,'sim_air_crash_count');now=C.c_uint.in_dll(l,'sim_tick_count')
 def reset(size=256):
  assert l.sim_init(size,42)==0
  for i in range(size):e[i].hp=0
 def born(i=31,dead=True):
  e[i]=Entity(4000,4000,0 if dead else 200,0,3,1,-1,1);a[i]=Air(200,0,0,0,7,1,0,-1,0,180,1,0,0,7,0,1)
 def probe(i=31):
  abi=(C.c_uint64*7)();body=(C.string_at(C.addressof(e),256*32),C.string_at(C.addressof(a),256*64));rc=l.probe_air_crash(i,abi)
  assert tuple(abi)==tuple(0x123401+i for i in range(6))+(0,)
  assert body==(C.string_at(C.addressof(e),256*32),C.string_at(C.addressof(a),256*64))
  return rc
 reset();born();assert probe()==0 and count.value==1
 assert (c[0].x,c[0].y,c[0].z,c[0].vx,c[0].vy,c[0].vz)==(4000,200,4000,0,0,7)
 before=l.sim_checksum();assert probe()==1 and l.sim_checksum()==before
 invalid=[(e[31],'hp',1),(e[31],'kind',2),(e[31],'side',2),(e[31],'gen',0),(a[31],'gen',2),(a[31],'flags',0),(a[31],'role',2),(e[31],'x',math.nan),(e[31],'z',8001),(a[31],'y',math.inf),(a[31],'heading',4),(a[31],'pitch',math.nan),(a[31],'bank',math.inf),(a[31],'vx',math.inf),(a[31],'vz',0)]
 for owner,field,bad in invalid:
  reset();born();setattr(owner,field,bad);before=l.sim_checksum();assert probe()==-1 and l.sim_checksum()==before
 for idx in (256,32768,0xffffffff):
  before=l.sim_checksum();assert probe(idx)==-1 and l.sim_checksum()==before
 # Bounded registry pressure, stable source-generation dedup and ring retirement.
 reset()
 for i in range(200):born(i);assert probe(i)==0
 assert count.value==128 and set(x.entity for x in c)==set(range(72,200))
 before=l.sim_checksum();assert probe(0)==1 and l.sim_checksum()==before
 born(0);e[0].gen=a[0].gen=2;assert probe(0)==0 and count.value==128
 assert all(not any(x.reserved)for x in c)
 # Public projectile casualty with no in-flight body/store/clock writes.
 traces=[]
 for repeat in range(2):
  reset(64);born(31,False);e[31].hp=24;a[31].heading=math.pi/2;a[31].vx=7;a[31].vz=0
  e[63]=Entity(3900,4000,60,1,3,1,-1,1);a[63]=Air(200,math.pi/2,0,0,7,1,0,31,0,180,1,7,0,0,0,1)
  assert l.projectile_air_launch(63,4)==0
  death=landed=None;birth=None;maximum_error=0.;samples=[];stock={31:180,63:180}
  for tick in range(1,1806):
   previous=bytes(c[0]);l.sim_tick()
   for i in stock:assert a[i].ammo<=stock[i];stock[i]=a[i].ammo
   if c[0].state and death is None:
    assert e[31].hp==0 and count.value==1
    death=tick;birth=tuple(getattr(c[0],n)for n in ('x','y','z','vx','vy','vz'));assert birth==tuple((e[31].x,a[31].y,e[31].z,a[31].vx,a[31].vy,a[31].vz))
   if death is not None and c[0].state==1 and tick>death:
    age=tick-death;expected=(birth[0]+age*birth[3],birth[1]+age*birth[4]-.0109*age*(age-1)/2,birth[2]+age*birth[5]);error=max(abs(v-q)for v,q in zip((c[0].x,c[0].y,c[0].z),expected));maximum_error=max(maximum_error,error);assert error<.05,(tick,error)
   if c[0].state==2 and landed is None:
    landed=tick;assert abs(c[0].y-l.terrain_height(c[0].x,c[0].z))<1e-5 and (c[0].vx,c[0].vy,c[0].vz)==(0,0,0)
   if death is not None:
    assert e[31].hp==0 and e[31].gen==1
    before=l.sim_checksum();l.air_crash_tick();assert l.sim_checksum()==before,'same tick moved crash twice'
   if tick%100==0:samples.append((tick,c[0].state,c[0].x,c[0].y,c[0].z,count.value))
  assert death==5 and landed is not None and landed>death and c[0].state==0 and count.value==0
  traces.append({'death_tick':death,'landing_tick':landed,'birth_xyz_velocity':birth,'maximum_ballistic_error_m':maximum_error,'samples':samples,'checksum':hex(l.sim_checksum()),'stores':stock})
 assert traces[0]==traces[1]
 print(json.dumps({'suite':'air-crash-core','passed':True,'invalid_atomic_cases':len(invalid)+3,'registry_pressure_births':201,'retained_capacity':128,'ABI_and_living_records_unchanged_by_registration':True,'public_projectile_casualty':traces[0],'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['One initial direct producer round does not debit FSM stores; no in-flight body/HP/ammo/generation/clock writes.','Ballistic centre-to-terrain contact only, no aerodynamics, footprint/obstacle collision, gameplay cover/blast, render or replication acceptance.','Crash pool separate from living army; oldest record retirement, source-generation dedup and tick expiry.']}))
