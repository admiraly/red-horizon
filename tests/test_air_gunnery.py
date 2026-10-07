#!/usr/bin/env python3
"""Independent physical firing-window oracle, ABI and full-army causal control."""
import ctypes as C,hashlib,json,math,os,pathlib,random,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ.get('RED_HORIZON_NASM','nasm')
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in('cooldown','ammo','generation')]+[(n,C.c_float)for n in('vx','vy','vz')]+[(n,C.c_uint)for n in('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-air-gunnery-')as folder:
 td=pathlib.Path(folder);probe=td/'probe.o';subprocess.run([nasm,'-f','elf64',str(root/'tests/probe_air_gunnery.asm'),'-o',str(probe)],check=True)
 objects=[root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o')for d in('sim','nav','ai','game')for p in sorted((root/'src'/d).glob('*.asm'))]
 good=td/'good.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(good),*map(str,objects),str(root/'build/terrain_probe.o'),str(probe),'-lm'],check=True)
 lib=C.CDLL(str(good));lib.sim_checksum.restype=C.c_uint64;lib.probe_air_gun_solution_ready.argtypes=[C.c_uint,C.c_void_p]
 E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft')
 def setup(relative=(0,0,250),target_velocity=(0,0,0),heading=0,climb=0):
  assert lib.sim_init(64,42)==0
  for e in E[:64]:e.hp=0
  for i,side,generation in((31,0,17),(63,1,19)):
   E[i]=Entity(2000,2000,200,side,3,0,-1,generation)
   A[i]=Air(200,0,0,0,7,1,1,-1,0,180,generation,0,0,0,0,1)
  A[31].target=63;A[31].heading=heading;A[31].pitch=math.atan2(climb,7);A[31].vx=7*math.sin(heading);A[31].vy=climb;A[31].vz=7*math.cos(heading)
  E[63].x=2000+relative[0];A[63].y=200+relative[1];E[63].z=2000+relative[2];A[63].vx,A[63].vy,A[63].vz=target_velocity
 def query(source=31):
  before=lib.sim_checksum();regs=(C.c_uint64*7)();rc=lib.probe_air_gun_solution_ready(source,regs)
  assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,);assert lib.sim_checksum()==before
  return rc
 def oracle():
  r=(E[63].x-E[31].x,A[63].y-A[31].y,E[63].z-E[31].z);v=(A[63].vx,A[63].vy,A[63].vz);u=(A[31].vx,A[31].vy,A[31].vz);length=math.sqrt(sum(x*x for x in u));u=tuple(x/length for x in u)
  rr=sum(x*x for x in r);vv=sum(x*x for x in v);rv=sum(x*y for x,y in zip(r,v));lead_time=(rv+math.sqrt(rv*rv+(784-vv)*rr))/(784-vv)
  lead=tuple(x+y*lead_time for x,y in zip(r,v));cone=sum(x*y for x,y in zip(u,lead))/math.sqrt(sum(x*x for x in lead))
  w=tuple(28*x-y for x,y in zip(u,v));t=sum(x*y for x,y in zip(r,w))/sum(x*x for x in w);miss=math.sqrt(sum((x-y*t)**2 for x,y in zip(r,w)))
  return 0<lead_time<=40 and cone>=.985 and 0<t<=40 and miss<=4,miss
 edges=[]
 for axis in(0,1):
  for offset in(-4.01,-3.99,3.99,4.01):
   r=[0,0,250];r[axis]=offset;setup(r);expected,miss=oracle();assert query()==(0 if expected else -1);edges.append({'axis':axis,'miss_m':miss,'ready':expected})
 rng=random.Random(7983);accepted=rejected=0
 for _ in range(600):
  setup(tuple(rng.uniform(-600,600)for _ in range(3)),tuple(rng.uniform(-4,4)for _ in range(3)),rng.uniform(-math.pi,math.pi),rng.uniform(-.5,.5))
  expected,miss=oracle();assert query()==(0 if expected else -1),(expected,miss);accepted+=expected;rejected+=not expected
 # Construct300 independent crossing solutions about relative-motion rays,
 # split inside/outside the sphere. This also tests successful random queries.
 mixed_accepted=mixed_rejected=0
 for case in range(300):
  heading=rng.uniform(-math.pi,math.pi);climb=rng.uniform(-.5,.5);v=tuple(rng.uniform(-4,4)for _ in range(3))
  flight=(7*math.sin(heading),climb,7*math.cos(heading));length=math.sqrt(sum(x*x for x in flight));u=tuple(x/length for x in flight)
  w=tuple(28*x-y for x,y in zip(u,v));length=math.sqrt(sum(x*x for x in w));direction=tuple(x/length for x in w)
  sideways=(-w[2],0,w[0]);length=math.sqrt(sum(x*x for x in sideways));sideways=tuple(x/length for x in sideways)
  if case%4<2:sideways=(direction[1]*sideways[2],direction[2]*sideways[0]-direction[0]*sideways[2],-direction[1]*sideways[0])
  distance=rng.uniform(100,650);offset=rng.uniform(0,3.9)if case%2==0 else rng.uniform(4.1,8)
  setup(tuple(x*distance+y*offset for x,y in zip(direction,sideways)),v,heading,climb)
  expected,miss=oracle();assert expected==(case%2==0),(case,miss);assert query()==(0 if expected else -1)
  mixed_accepted+=expected;mixed_rejected+=not expected
 # Lead-aligned crossing target: source stays level and emits no sideways aim.
 setup((-62.5,0,250),(7,0,0));assert query()==0
 invalid=0
 for i in(64,32768,0xffffffff):assert query(i)==-1;invalid+=1
 for owner,field,value in[(A[31],'ammo',0),(A[31],'cooldown',1),(A[31],'generation',99),(A[63],'flags',0),(E[63],'hp',0),(E[63],'side',0),(A[63],'vy',math.nan),(A[31],'vz',math.inf)]:
  setup();setattr(owner,field,value);assert query()==-1;invalid+=1
 # Assembled causal control restores only broad-cone firing discipline.
 source=(root/'src/ai/air_gunnery.asm').read_text();control=source.replace('air_gun_solution_ready:\n','air_gun_solution_ready:\n jmp projectile_air_gun_ready\n',1)
 asm=td/'broad.asm';asm.write_text(control);obj=td/'broad.o';subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(asm),'-o',str(obj)],check=True)
 broad=td/'broad.so';control_objects=[obj if p.name=='src_ai_air_gunnery.asm.o'else p for p in objects];subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(broad),*map(str,control_objects),str(root/'build/terrain_probe.o'),'-lm'],check=True)
 def battle(path):
  runtime=C.CDLL(str(path));runtime.sim_checksum.restype=C.c_uint64;e=(Entity*32768).in_dll(runtime,'sim_entities');a=(Air*32768).in_dll(runtime,'sim_aircraft');assert runtime.sim_init(8192,42)==0
  ids=[i for i in range(8192)if e[i].kind==3];original={i:e[i].generation for i in ids};initial_hp={i:e[i].hp for i in ids};previous={i:(180 if (i>>4)&1 else 8)for i in ids}
  for tick in range(900):
   runtime.sim_tick()
   for i in ids:
    assert e[i].generation==original[i] and a[i].ammo<=previous[i];previous[i]=a[i].ammo
  shots=sum(180-a[i].ammo for i in ids if (i>>4)&1);damage=sum(initial_hp[i]-e[i].hp for i in ids)
  return {'units':8192,'ticks':900,'rounds_spent':shots,'total_air_hp_lost':damage,'aircraft_destroyed':sum(not e[i].hp for i in ids),'checksum':f'{runtime.sim_checksum():016x}'}
 baseline=battle(broad);candidate=battle(good);assert battle(good)==candidate
 assert 0<candidate['rounds_spent']<baseline['rounds_spent']*.5 and candidate['aircraft_destroyed']>0
 assert candidate['total_air_hp_lost']/candidate['rounds_spent']>baseline['total_air_hp_lost']/baseline['rounds_spent']
 print(json.dumps({'suite':'air-gunnery','passed':True,'boundary_cases':edges,'independent_random_oracle_cases':600,'random_accepted':accepted,'random_rejected':rejected,'constructed_random_cases':300,'constructed_random_accepted':mixed_accepted,'constructed_random_rejected':mixed_rejected,'crossing_lead':True,'invalid_atomic_ABI_cases':invalid,'query_state_and_nonvolatile_registers_preserved':True,'natural_full_army':{'broad_cone_control':baseline,'physical_window_candidate':candidate,'candidate_replay_equal':True},'control_source_sha256':hashlib.sha256(control.encode()).hexdigest(),'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(good.read_bytes()).hexdigest(),'limits':['Constant observed target velocity and retained4m actor sphere; target manoeuvres can still evade a predicted shot.','No new flight dynamics, perception/FOV, aircraft hitbox, aiming trajectory, stores or live fixture renewal.','Original8192natural battle compares resource efficiency; not universal damage/survival superiority, GL/UDP/performance or spectacle acceptance.']}))
