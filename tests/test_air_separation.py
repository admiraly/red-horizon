#!/usr/bin/env python3
"""Independent 3D closest-approach oracle and public no-renewal flight controls."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-separation-')as d:
 td=pathlib.Path(d);objects=[]
 for src in [p for f in ('sim','nav','ai','game')for p in(R/'src'/f).glob('*.asm')]+[R/'tests/probe_air_separation.asm']:
  obj=td/(src.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(src),'-o',str(obj)],check=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True)
 so=td/'candidate.so';link(so,objects);source=(R/'src/ai/aircraft.asm').read_text();control_source=source.replace(' call air_separation_step',' xor eax,eax',1)
 # Disable commits only; derived snapshot/predictor remains compiled and identical.
 asm=td/'control.asm';asm.write_text(control_source);obj=td/'control.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(asm),'-o',str(obj)],check=True);control_so=td/'control.so';link(control_so,[obj if p.name=='aircraft.asm.o'else p for p in objects])
 def bindings(path):
  l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.probe_air_separation.argtypes=[C.c_uint,C.c_void_p];l.air_separation_step.argtypes=[C.c_uint,C.c_uint]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft'),(C.c_uint*(32768*4)).in_dll(l,'sim_air_separation'),(C.c_float*12).in_dll(l,'sim_waypoints'),C.c_uint.in_dll(l,'sim_tick_count')
 l,e,a,state,w,now=bindings(so)
 def reset():
  assert l.sim_init(128,42)==0
  for i in range(128):e[i].hp=0
 def born(i,x,z,y,yaw,side=0,role=1,front=1):
  v=7 if role else 5
  e[i]=Entity(x,z,200,side,3,front,-1,1);a[i]=Air(y,yaw,0,0,v,role,0,-1,0,180 if role else 6,1,math.sin(yaw)*v,0,math.cos(yaw)*v,0,1)
 def probe(owner=31):
  regs=(C.c_uint64*7)();before=(C.string_at(C.addressof(e),128*32),C.string_at(C.addressof(a),128*64));rc=l.probe_air_separation(owner,regs);assert tuple(regs)==tuple(0x123401+i for i in range(6))+(0,);assert before==(C.string_at(C.addressof(e),128*32),C.string_at(C.addressof(a),128*64));return rc
 def oracle():
  p=(e[63].x-e[31].x,a[63].y-a[31].y,e[63].z-e[31].z);v=(a[63].vx-a[31].vx,a[63].vy-a[31].vy,a[63].vz-a[31].vz);dot=sum(x*y for x,y in zip(p,v));speed=sum(x*x for x in v)
  if sum(x*x for x in p)>250000 or dot>=0:return -1
  t=-dot/speed
  if t>60 or sum((x+t*y)**2 for x,y in zip(p,v))>900:return -1
  return 63
 rng=random.Random(57217);views=0;warnings=0
 for i in range(1000):
  reset();born(31,4000,4000,200,rng.uniform(-math.pi,math.pi));born(63,4000+rng.uniform(-500,500),4000+rng.uniform(-500,500),200+rng.uniform(-100,100),rng.uniform(-math.pi,math.pi));l.air_separation_build();wanted=oracle();actual=probe();assert actual==wanted,(i,actual,wanted);warnings+=actual>=0;views+=1
 # Deliberate true/false convergence geometries across yaw, altitude and time.
 for i in range(500):
  reset();yaw=rng.uniform(-math.pi,math.pi);other=(yaw+math.pi+math.pi)%(2*math.pi)-math.pi;distance=rng.uniform(14,400);offset=rng.uniform(-20,20) if i<250 else rng.choice((-1,1))*rng.uniform(35,70)
  born(31,4000,4000,200,yaw);born(63,4000+math.sin(yaw)*distance+math.cos(yaw)*offset,4000+math.cos(yaw)*distance-math.sin(yaw)*offset,200+rng.uniform(-10,10),other)
  l.air_separation_build();actual=probe();wanted=oracle();assert actual==wanted and (actual==63)==(i<250),(i,actual,wanted);warnings+=actual>=0;views+=1
 reset();born(31,3800,4000,200,math.pi/2);born(63,4200,4000,200,-math.pi/2);l.air_separation_build();assert probe()==63
 bad=[(e[63],'hp',0),(e[63],'kind',0),(e[63],'side',1),(a[63],'gen',2),(a[63],'flags',0),(a[63],'role',2),(a[63],'vx',math.nan),(e[63],'x',math.inf)]
 for owner,field,value in bad:
  reset();born(31,3800,4000,200,math.pi/2);born(63,4200,4000,200,-math.pi/2);setattr(owner,field,value);l.air_separation_build();assert probe()==-1
 reset();born(31,3800,4000,200,math.pi/2);born(63,4200,4000,200,-math.pi/2);a[63].ammo=0;e[63].hp=60;l.air_separation_build();assert probe()==63,'disabled friendly still poses convergence risk'
 before=l.sim_checksum();assert probe()==63 and l.sim_checksum()==before
 # Exact role lifetime/refractory and blocked urgent-defence guards, standalone clocks.
 reset();born(31,3800,4000,200,math.pi/2);born(63,4200,4000,200,-math.pi/2);l.air_separation_build();assert l.air_separation_step(31,1)==0
 now.value=1;l.air_separation_build();assert l.air_separation_step(31,0)==24;before=l.sim_checksum();assert l.air_separation_step(31,0)==24 and l.sim_checksum()==before
 for tick in range(2,26):now.value=tick;l.air_separation_build();assert l.air_separation_step(31,0)==max(0,25-tick)
 assert state[31*4+4-4]==1 and state[31*4+2]>0
 # Real physical pressure caps do not depend on hidden opposing fleet placement.
 reset();born(31,3800,4000,200,math.pi/2);born(63,4200,4000,200,-math.pi/2)
 for i in range(100):
  if i not in (31,63):born(i,4000,4000,200,0,side=1)
 l.air_separation_build();assert probe()==63
 # Cap reached under same-side physical pressure; no opposite-side budget use.
 reset();born(31,3800,4000,200,math.pi/2)
 for i in range(128):
  if i!=31:born(i,4000,4000,200,0)
 born(127,4200,4000,200,-math.pi/2)
 l.air_separation_build();metrics=(C.c_uint64*5).in_dll(l,'air_separation_metrics');before=tuple(metrics);probe();after=tuple(metrics);assert after[2]-before[2]<=25 and after[3]-before[3]==64
 # Unbuilt/stale derived caches never supply a warning.
 now.value+=1;assert probe()==-1
 # Public head-on flight. Only initial births/waypoints are written, no later resets.
 traces={}
 for name,path in [('candidate',so),('control',control_so)]:
  traces[name]=[]
  for repeat in range(2):
   x,ee,aa,ss,ww,nn=bindings(path);assert x.sim_init(64,42)==0
   for i in range(64):ee[i].hp=0
   for i,px,heading,front in ((31,3800,math.pi/2,0),(63,4200,-math.pi/2,2)):
    ee[i]=Entity(px,4000,200,0,3,front,-1,1);aa[i]=Air(200,heading,0,0,7,1,0,-1,0,180,1,math.sin(heading)*7,0,math.cos(heading)*7,0,1)
   ww[0],ww[1],ww[4],ww[5]=6500,4000,1500,4000
   minimum=1e10;samples=[]
   for tick in range(1,121):
    x.sim_tick();distance=math.sqrt((ee[31].x-ee[63].x)**2+(ee[31].z-ee[63].z)**2+(aa[31].y-aa[63].y)**2);minimum=min(minimum,distance)
    assert ee[31].hp==ee[63].hp==200 and aa[31].ammo==aa[63].ammo==180
    if tick<=35 or tick%30==0:samples.append((tick,distance,aa[31].heading,aa[63].heading,ss[31*4+1],ss[63*4+1]))
   traces[name].append(dict(minimum_separation_m=minimum,samples=samples,checksum=hex(x.sim_checksum())))
  assert traces[name][0]==traces[name][1]
 assert traces['candidate'][0]['minimum_separation_m']>traces['control'][0]['minimum_separation_m']+10,traces
 role_flights=[]
 for roles in ((0,0),(0,1),(1,0)):
  results={}
  for name,path in [('candidate',so),('control',control_so)]:
   replays=[]
   for repeat in range(2):
    x,ee,aa,ss,ww,nn=bindings(path);assert x.sim_init(64,42)==0
    for i in range(64):ee[i].hp=0
    for i,px,heading,front,role in ((31,3800,math.pi/2,0,roles[0]),(63,4200,-math.pi/2,2,roles[1])):
     speed=(5,7)[role];ammo=(6,180)[role]
     ee[i]=Entity(px,4000,200,0,3,front,-1,1);aa[i]=Air(200,heading,0,0,speed,role,0,-1,0,ammo,1,math.sin(heading)*speed,0,math.cos(heading)*speed,0,1)
    ww[0],ww[1],ww[4],ww[5]=6500,4000,1500,4000;minimum=1e10;commit=[]
    for tick in range(1,121):
     x.sim_tick();minimum=min(minimum,math.sqrt((ee[31].x-ee[63].x)**2+(ee[31].z-ee[63].z)**2+(aa[31].y-aa[63].y)**2));assert ee[31].hp==ee[63].hp==200 and (aa[31].ammo,aa[63].ammo)==tuple((6,180)[role]for role in roles)
     if not commit and ss[31*4+1]:commit=[tick,ss[31*4+1],ss[63*4+1]]
    replays.append(dict(minimum_separation_m=minimum,first_commit=commit,checksum=hex(x.sim_checksum())))
   assert replays[0]==replays[1];results[name]=replays[0]
  assert results['candidate']['minimum_separation_m']>results['control']['minimum_separation_m']+10,(roles,results)
  role_flights.append(dict(roles=roles,results=results))
 print(json.dumps(dict(suite='air-friendly-separation',passed=True,independent_views=views,warnings=warnings,additional_role_flights=role_flights,invalid_peer_cases=len(bad),ABI_and_readonly=True,source_side_budget_isolated=True,finite_nonrenewing_commit=True,causal_public_flight={k:v[0]for k,v in traces.items()},library_sha256=hashlib.sha256(so.read_bytes()).hexdigest(),limits=['Friendly radio snapshots within500m,25cells/64candidates; no enemy observation/ground truth decisions.','Approaching-path avoidance only: no exact mesh collision, parallel/overlapping-born separation, obstacle avoidance or general traffic guarantee.','Native lifecycle uses declared standalone clocks; public encounters use initial births only, never live body/HP/ammo/generation/clock renewal.'])) )
