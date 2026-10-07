#!/usr/bin/env python3
"""Independent fighter view/memory ABI and hidden-body causal steering fixtures."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
class Observation(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in ('owner_gen','target','target_gen','tick','known')]+[('reserved',C.c_uint*5)]
with tempfile.TemporaryDirectory(prefix='rh-air-observation-')as folder:
 td=pathlib.Path(folder);objects=[]
 for source in [p for f in ('sim','nav','ai','game')for p in (R/'src'/f).glob('*.asm')]+[R/'tests/terrain_probe.asm',R/'tests/probe_air_observation.asm']:
  obj=td/(source.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(source),'-o',str(obj)],check=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True)
 so=td/'candidate.so';link(so,objects)
 # Causal control changes only guidance into live enemy body reads. Keep it
 # self-contained for source archives and shallow CI checkouts (no git history).
 original=(R/'src/ai/aircraft.asm').read_text()
 gate=' mov edi,r12d\n call air_observation_goal\n'
 replacement=''' mov edi,[rbp+AIR_TARGET]
 cmp edi,[sim_count]
 jae .no_observation
 mov eax,edi
 shl eax,5
 lea rcx,[sim_entities]
 movss xmm0,[rcx+rax+ENTITY_X]
 movss xmm2,[rcx+rax+ENTITY_Z]
 shl edi,6
 lea rcx,[sim_aircraft]
 movss xmm1,[rcx+rdi+AIR_Y]
 movss xmm3,[rcx+rdi+AIR_VX]
 movss xmm4,[rcx+rdi+AIR_VY]
 movss xmm5,[rcx+rdi+AIR_VZ]
 mov eax,1
'''
 assert original.count(gate)==1
 original=original.replace(gate,replacement,1)
 (td/'original.asm').write_text(original);original_obj=td/'original.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(td/'original.asm'),'-o',str(original_obj)],check=True)
 control=td/'live-body-control.so';link(control,[original_obj if p.name=='aircraft.asm.o'else p for p in objects])
 def bind(path):
  l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.probe_air_observation.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft'),(Observation*32768).in_dll(l,'sim_air_observations'),C.c_uint.in_dll(l,'sim_tick_count')
 l,e,a,o,tick=bind(so)
 def setup(l,e,a,o):
  assert l.sim_init(64,7)==0
  for i in range(64):e[i].hp=0
  for i,side,z in ((31,0,4000),(63,1,4400)):
   e[i].x,e[i].z,e[i].hp,e[i].kind,e[i].side=4000,z,200,3,side
  l.air_init();l.air_observation_init();l.air_tick();l.projectile_init()
  for i,z,h in ((31,4000,0),(63,4400,math.pi)):
   e[i].x,e[i].z=4000,z;a[i].y=200;a[i].heading=h;a[i].speed=7;a[i].vx=a[i].vy=0;a[i].vz=7 if i==31 else -7;a[i].target=63 if i==31 else 31;a[i].ammo=180;a[i].cooldown=0
 def probe(mode=1,owner=31,target=63):
  out=(C.c_float*9)(123,*([0]*7),456);abi=(C.c_uint64*7)();rc=l.probe_air_observation(owner,target,mode,C.byref(out,4),abi)
  assert tuple(abi)==tuple(0x123401+i for i in range(6))+(0,) and out[0]==123 and out[8]==456
  return rc,tuple(out)[1:8]
 setup(l,e,a,o);assert probe()==(0,(0.,)*7)
 # Random independent3D range and view oracle, all points safely above terrain.
 rng=random.Random(671231);cases=[(distance,angle,0)for distance in (50,749,751)for angle in (0,1.5,2.08,2.11,math.pi,-2.08,-2.11)]
 cases += [(rng.uniform(20,900),rng.uniform(-math.pi,math.pi),rng.uniform(-30,30))for _ in range(1500)]
 accepted=0
 for distance,angle,y in cases:
  e[63].x=4000+distance*math.sin(angle);e[63].z=4000+distance*math.cos(angle);a[63].y=200+y
  r=(e[63].x-e[31].x,a[63].y-a[31].y,e[63].z-e[31].z);rr=sum(v*v for v in r);dot=r[2]*7;expected=rr<=750**2 and(dot>=0 or dot*dot<=rr*49*.25)
  before=l.sim_checksum();body=(bytes(e),bytes(a));rc,_=probe(0)
  assert bool(rc)==expected,(distance,angle,y,r,rc,expected)
  assert body==(bytes(e),bytes(a)),'capture changed physical bodies'
  if not expected:assert l.sim_checksum()==before,'rejected capture mutated knowledge'
  else:accepted+=1;assert o[31].known==1 and(o[31].x,o[31].y,o[31].z)==(e[63].x,a[63].y,e[63].z)
 # Rotated/climbing own flight tests all three view-vector components.
 rotated_accepted=0
 for _ in range(500):
  heading=rng.uniform(-math.pi,math.pi);vy=rng.uniform(-.5,.5);horizontal=math.sqrt(49-vy*vy)
  a[31].y=300;a[31].heading=heading;a[31].vx=horizontal*math.sin(heading);a[31].vy=vy;a[31].vz=horizontal*math.cos(heading)
  distance=rng.uniform(20,900);angle=rng.uniform(-math.pi,math.pi)
  e[63].x=4000+distance*math.sin(angle);e[63].z=4000+distance*math.cos(angle);a[63].y=300+rng.uniform(-40,40)
  r=(e[63].x-e[31].x,a[63].y-a[31].y,e[63].z-e[31].z);v=(a[31].vx,a[31].vy,a[31].vz);rr=sum(x*x for x in r);vv=sum(x*x for x in v);dot=sum(x*y for x,y in zip(r,v));expected=rr<=750**2 and(dot>=0 or dot*dot<=rr*vv*.25)
  before=l.sim_checksum();rc,_=probe(0);assert bool(rc)==expected,(r,v,rc,expected)
  if rc:rotated_accepted+=1
  else:assert l.sim_checksum()==before
 # Every age, bounded extrapolation/confidence, no hidden target lookup or writes.
 setup(l,e,a,o);a[63].vx,a[63].vy,a[63].vz=math.sqrt(49-.25),.5,0;assert probe(0)[0]==1
 stored=bytes(o[31]);actual=(o[31].x,o[31].y,o[31].z);velocity=(o[31].vx,o[31].vy,o[31].vz)
 e[63].x,e[63].z,e[63].hp,e[63].gen=7000,1000,0,999;a[63].y=a[63].vx=math.nan;a[63].gen=999
 maximum=0
 for age in range(101):
  tick.value=age;before=l.sim_checksum();rc,out=probe();assert bytes(o[31])==stored and l.sim_checksum()==before,'recall wrote state'
  if age>=90:assert rc==0 and out==(0.,)*7
  else:
   expected=tuple(max(0,min(1000 if i==1 else 8000,actual[i]+velocity[i]*min(age,30)))for i in range(3))+velocity+(1-age/90,)
   error=max(abs(x-y)for x,y in zip(out,expected));maximum=max(maximum,error);assert rc==1 and error<.0003,(age,out,expected,error)
 # Lifecycle, malformed body and cache controls, each isolated before query.
 invalid=[('dead',lambda:setattr(e[63],'hp',0)),('ally',lambda:setattr(e[63],'side',0)),('generation',lambda:setattr(a[63],'gen',999)),('inactive',lambda:setattr(a[63],'flags',0)),('role',lambda:setattr(a[63],'role',2)),('outside',lambda:setattr(e[63],'x',9000)),('zero_velocity',lambda:setattr(a[63],'vz',0)),('nonfinite_velocity',lambda:setattr(a[63],'vy',math.nan)),('nonfinite_y',lambda:setattr(a[63],'y',math.inf)),('owner_empty',lambda:setattr(a[31],'ammo',0)),('owner_role',lambda:setattr(a[31],'role',0))]
 for name,mutate in invalid:
  setup(l,e,a,o);mutate();before=l.sim_checksum();assert probe(0)[0]==0 and l.sim_checksum()==before,name
 setup(l,e,a,o);a[31].y=a[63].y=1;assert probe(0)[0]==0,'buried trace ignored terrain LOS'
 setup(l,e,a,o);e[31].side,e[63].side=1,0;assert probe(0)[0]==1,'side label changed sight'
 setup(l,e,a,o);assert probe(0)[0]==1;e[31].gen+=1;a[31].gen+=1;assert probe()==(0,(0.,)*7)
 setup(l,e,a,o);assert probe(0)[0]==1;o[31].tick=1;assert probe()==(0,(0.,)*7),'future observation accepted'
 cached_invalid=[('known',2),('target',32768),('target_gen',0),('owner_gen',999),('x',math.nan),('z',-1),('y',math.inf),('vx',math.nan),('vy',math.inf),('vz',100)]
 for field,value in cached_invalid:
  setup(l,e,a,o);assert probe(0)[0]==1;setattr(o[31],field,value);before=l.sim_checksum();record=bytes(o[31]);assert probe()==(0,(0.,)*7),field;assert bytes(o[31])==record and l.sim_checksum()==before
 # Causal declared hidden-body fixtures: same previously seen point, two rear
 # ground-truth poses. These are isolated getter fixtures, not live encounters.
 metamorphic=[]
 for path in (so,control):
  ll,ee,aa,oo,tt=bind(path);poses=[]
  for x,y in ((3990,198),(4010,202)):
   setup(ll,ee,aa,oo);ee[63].z=4200;assert ll.air_observation_capture(31,63)==1
   # Twenty-tick last sight; owner has flown140m, unseen target has passed
   # behind with two bounded lateral/climb alternatives. Getter fixtures only.
   tt.value=20;ee[31].z=4140;ee[63].x,ee[63].z=x,4060;aa[63].y=y
   ll.air_tick();poses.append([ee[31].x,aa[31].y,ee[31].z,aa[31].heading,aa[31].pitch,aa[31].bank,aa[31].vx,aa[31].vy,aa[31].vz])
  metamorphic.append({'control':path==control,'own_poses':poses,'equal':poses[0]==poses[1]})
 assert metamorphic[0]['equal'] and not metamorphic[1]['equal'],metamorphic
 # Actual public tick encounter, initial births only; genuine finite weapons.
 replays=[]
 for _ in range(2):
  setup(l,e,a,o);a[31].target=a[63].target=-1
  remaining={31:180,63:180};births=set();seen=0;memory_only=0
  events=(C.c_uint*(256*8)).in_dll(l,'sim_events')
  for step in range(360):
   l.sim_tick()
   for i in remaining:
    assert a[i].ammo<=remaining[i];remaining[i]=a[i].ammo
    if o[i].known:seen+=1
    if o[i].known and a[i].target==-1 and tick.value-o[i].tick<90:memory_only+=1
   for j in range(256):
    if events[j*8+3]==8 and events[j*8+7]:births.add(events[j*8+7])
  assert births and any(e[i].hp<200 for i in remaining) and seen>0
  replays.append({'checksum':hex(l.sim_checksum()),'births':len(births),'hp':{i:e[i].hp for i in remaining},'rounds':remaining,'observed_samples':seen,'memory_only_samples':memory_only})
 assert replays[0]==replays[1],replays
 print(json.dumps({'suite':'air-observed-enemy-memory','passed':True,'view_geometry_cases':len(cases),'accepted':accepted,'rotated_climbing_view_cases':500,'rotated_accepted':rotated_accepted,'memory_ages':101,'maximum_memory_error':maximum,'invalid_metadata_cases':len(invalid),'malformed_cache_cases':len(cached_invalid),'ABI_atomic_rejection_and_readonly_recall':True,'occlusion_generation_future_expiry_label_controls':True,'hidden_body_metamorphic':metamorphic,'live_body_control_source_sha256':hashlib.sha256(original.encode()).hexdigest(),'public_encounter':replays[0],'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Isolated geometry/lifecycle/hidden-body kernel fixtures plus360public ticks without in-flight body/HP/ammo/clock renewal.','Pilot240degree field,90tick memory and30tick constant-velocity estimate are approximations, not full sensor/fusion or coordinated tactical acceptance.']}))
