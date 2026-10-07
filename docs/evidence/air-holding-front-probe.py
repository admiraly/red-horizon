#!/usr/bin/env python3
"""Owned recovery policy/ABI and genuine-projectile-triggered public withdrawal."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
R=pathlib.Path('/mnt/titan_nv3/projects/red-horizon-workers/air-holding/runs/jobs/e092137fb4cc/source');nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
class Observation(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in ('owner_gen','target','target_gen','tick','known')]+[('reserved',C.c_uint*5)]

with tempfile.TemporaryDirectory(prefix='rh-air-recovery-') as folder:
 td=pathlib.Path(folder);objects=[]
 for source in [p for f in ('sim','nav','ai','game')for p in (R/'src'/f).glob('*.asm')]+[R/'tests/terrain_probe.asm',R/'tests/probe_air_recovery.asm',R/'tests/probe_air_holding.asm']:
  obj=td/(source.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(source),'-o',str(obj)],check=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True)
 so=td/'candidate.so';link(so,objects)
 source=(R/'src/ai/air_recovery.asm').read_text();control_source=source.replace('air_recovery_goal:\n','air_recovery_goal:\n cmp edi,31\n jne .normal\n xor eax,eax\n ret\n.normal:\n',1);(td/'control.asm').write_text(control_source)
 obj=td/'control.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(td/'control.asm'),'-o',str(obj)],check=True)
 control=td/'control.so';link(control,[obj if p.name=='air_recovery.asm.o'else p for p in objects])
 def bind(path):
  l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];l.probe_air_recovery.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft')
 l,e,a=bind(so)
 def reset(l,e,a):
  assert l.sim_init(64,42)==0
  for i in range(64):e[i].hp=0
  for side in (0,1):
   for front in range(3):assert l.sim_order(side,front,1)==0
  assert l.sim_waypoint(0,0,7000.,4000.)==0 and l.sim_waypoint(1,0,1000.,4000.)==0
 def plane(e,a,i,x,side,hp,ammo,role=1):
  speed=(5,7)[role];e[i]=Entity(x,4000,hp,side,3,1,-1,1);a[i]=Air(200,math.pi/2,0,0,speed,role,0,-1,0,ammo,1,speed,0,0,0,1)
 def query(i=31,hash_sample=True):
  out=(C.c_float*4)(123,0,0,456);abi=(C.c_uint64*7)();before=l.sim_checksum()if hash_sample else None;physical=(C.string_at(C.addressof(e),64*C.sizeof(Entity)),C.string_at(C.addressof(a),64*C.sizeof(Air)));rc=l.probe_air_recovery(i,81.,-17.,0.,C.byref(out,4),abi)
  assert out[0]==123 and out[3]==456 and tuple(abi)==tuple(0x123401+i for i in range(6))+(0,) and (not hash_sample or l.sim_checksum()==before)
  assert physical==(C.string_at(C.addressof(e),64*C.sizeof(Entity)),C.string_at(C.addressof(a),64*C.sizeof(Air)))
  return rc,tuple(out)[1:3]
 reset(l,e,a);plane(e,a,31,4000,0,200,180)
 cases=0
 for role in (0,1):
  a[31].role=role
  for side in (0,1):
   e[31].side=side
   for front in range(3):
    e[31].front=front
    for hp in range(1,201):
     e[31].hp=hp
     for ammo in (0,1,8,180):
      a[31].ammo=ammo;expected=(1,((2000.,6000.)[side],2000.*(front+1)))if hp<=60 or ammo==0 else(0,(81.,-17.));assert query(hash_sample=cases%128==0)==expected;cases+=1
 guards=[]
 for owner,field,bad in [(e[31],'hp',0),(e[31],'kind',0),(e[31],'side',2),(e[31],'front',3),(e[31],'gen',0),(a[31],'gen',2),(a[31],'flags',0),(a[31],'role',2)]:
  reset(l,e,a);plane(e,a,31,4000,0,60,180);old=getattr(owner,field);setattr(owner,field,bad);assert query()==(0,(81.,-17.));setattr(owner,field,old);guards.append(field)
 for idx in (64,32768,0xffffffff):assert query(idx)==(0,(81.,-17.))
 reset(l,e,a);plane(e,a,31,4000,0,60,180);before=query();e[63]=Entity(math.nan,8001,0,1,3,2,-1,999);a[63].y=math.inf;assert query()==before
 empty=[]
 for role in (0,1):
  for side in (0,1):
   reset(l,e,a);plane(e,a,31,4000,side,200,0,role);closest=2000.;travel=0.
   for tick in range(1200):
    old=(e[31].x,a[31].y,e[31].z);l.sim_tick();step=math.dist(old,(e[31].x,a[31].y,e[31].z));assert abs(step-(5,7)[role])<.001;travel+=step
    assert a[31].ammo==0 and e[31].hp==200 and a[31].target==-1 and a[31].mode==3
    assert 0<=e[31].x<=8000 and 0<=e[31].z<=8000
    closest=min(closest,math.dist((e[31].x,e[31].z),((2000,6000)[side],4000)))
   assert closest<150,(role,side,closest)
   empty.append({'role':role,'side':side,'ticks':1200,'closest_recovery_gap_m':closest,'travel_m':travel,'remaining_rounds':a[31].ammo,'hp':e[31].hp,'checksum':hex(l.sim_checksum())})
 l.probe_air_holding.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
 h=(C.c_uint*(32768*2)).in_dll(l,'sim_air_holding')
 def holdquery(i=31):
  out=(C.c_float*4)(123,0,0,456);abi=(C.c_uint64*7)()
  before=(C.string_at(C.addressof(e),64*32),C.string_at(C.addressof(a),64*64))
  rc=l.probe_air_holding(i,81.,-17.,0.,C.byref(out,4),abi)
  assert out[0]==123 and out[3]==456 and tuple(abi)==tuple(0x123401+i for i in range(6))+(0,)
  assert before==(C.string_at(C.addressof(e),64*32),C.string_at(C.addressof(a),64*64))
  return rc,tuple(out)[1:3]
 holding_views=0
 for role in (0,1):
  for side in (0,1):
   for front in range(3):
    for j in range(100):
     reset(l,e,a);plane(e,a,31,4000,side,60,180,role);e[31].front=front
     cx=(2000,6000)[side];cz=2000*(front+1);r=100+j*13;theta=j*2.399963229728653
     e[31].x=cx+r*math.sin(theta);e[31].z=cz+r*math.cos(theta);h[62]=1;h[63]=1
     dx=e[31].x-cx;dz=e[31].z-cz;actual_r=math.hypot(dx,dz);nx=dx/actual_r;nz=dz/actual_r;radius=(600,650)[role];correction=max(-1,min(1,2*(radius-actual_r)/radius))
     expected=(e[31].x+250*(nz+nx*correction),e[31].z+250*(-nx+nz*correction))
     rc,value=holdquery();assert rc==1 and math.dist(value,expected)<.002,(value,expected)
     assert tuple(h[62:64])==(1,1);holding_views+=1
 reset(l,e,a);plane(e,a,31,4000,0,60,180);h[62]=9;h[63]=1
 assert holdquery()==(1,(2000.,4000.)) and tuple(h[62:64])==(1,0)
 e[31].x=2000.;assert holdquery()[0]==1 and h[63]==1
 e[31].hp=200;assert holdquery()==(0,(81.,-17.)) and tuple(h[62:64])==(0,0)
 invalid_holding=0
 for idx in (64,32768,0xffffffff):assert holdquery(idx)==(0,(81.,-17.));invalid_holding+=1
 for owner,field,bad in [(e[31],'x',math.nan),(e[31],'z',math.inf),(e[31],'x',-1),(a[31],'vx',math.inf),(a[31],'vx',0),(a[31],'vy',math.nan)]:
  reset(l,e,a);plane(e,a,31,2000,0,60,180);setattr(owner,field,bad);before=tuple(h[62:64]);assert holdquery()==(0,(81.,-17.)) and before==tuple(h[62:64]);invalid_holding+=1
 reports=[];holding_front=int(os.environ['RH_HOLDING_FRONT'])
 for role in (0,1):
  for side in (0,1):
   repeats=[]
   for repeat in range(2):
    reset(l,e,a);plane(e,a,31,4000,side,200,0,role);e[31].front=holding_front
    holding=(C.c_uint*(32768*2)).in_dll(l,'sim_air_holding');arrival=None;closest=math.inf;radial=[];turn_total=0.;last_theta=None;max_speed_error=0.;max_roll=0.;last_bank=a[31].bank;trace=[]
    for tick in range(1,3001):
     old=(e[31].x,a[31].y,e[31].z);l.sim_tick();gap=math.dist((e[31].x,e[31].z),((2000,6000)[side],2000*(holding_front+1)));closest=min(closest,gap)
     max_speed_error=max(max_speed_error,abs(math.dist(old,(e[31].x,a[31].y,e[31].z))-(5,7)[role]))
     max_roll=max(max_roll,abs(a[31].bank-last_bank));last_bank=a[31].bank
     assert e[31].hp==200 and a[31].ammo==0 and a[31].mode==3 and a[31].target==-1
     assert 600<=e[31].x<=7400 and 600<=e[31].z<=7400,(role,side,tick,e[31].x,e[31].z,gap,holding[62],holding[63])
     if holding[31*2+1] and arrival is None:arrival=tick
     if tick>2000:
      assert 1200<=e[31].x<=6800 and 1200<=e[31].z<=6800
      radial.append(gap);theta=math.atan2(e[31].x-(2000,6000)[side],e[31].z-2000*(holding_front+1))
      if last_theta is not None:turn_total+=(theta-last_theta+math.pi)%(2*math.pi)-math.pi
      last_theta=theta
     if tick%120==0:trace.append([tick,gap,a[31].heading,a[31].bank,l.sim_checksum()])
    repeats.append(dict(role=role,side=side,front=holding_front,arrival_tick=arrival,closest_gap_m=closest,late_radial_range_m=[min(radial),max(radial)],late_turn_radians=turn_total,max_speed_error_m=max_speed_error,max_roll_step=max_roll,trace=trace))
   assert repeats[0]==repeats[1]
   report=repeats[0];print(json.dumps(report),flush=True)
   assert report['arrival_tick'] is not None and report['closest_gap_m']<150
   radius=(600,650)[role]
   assert radius-75<report['late_radial_range_m'][0]<=report['late_radial_range_m'][1]<radius+75,report
   assert report['late_turn_radians']>2*math.pi and report['max_speed_error_m']<.001
   assert report['max_roll_step']<(.06001,.10001)[role]
   reports.append(report)
 print(json.dumps(dict(suite='air-holding',passed=True,independent_holding_views=holding_views,invalid_holding_cases=invalid_holding,flights=reports,library_sha256=hashlib.sha256(so.read_bytes()).hexdigest(),scope='Initial births only; real public tick3000 twice per role/faction, arrival plus sustained physical orbit, no live HP/ammo/pose/gen/clock renewal. No landing/repair/refill or traffic guarantee.')))
