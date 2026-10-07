#!/usr/bin/env python3
"""Native fuel lifecycle/ABI plus causal public recovery and ground-contact glide.
One-time initial fuel/plane fixtures declared; real assembly sim_tick thereafter.
"""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in('cooldown','ammo','gen')]+[(n,C.c_float)for n in('vx','vy','vz')]+[(n,C.c_uint)for n in('pass_ticks','flags')]
class Fuel(C.Structure):
 _fields_=[(n,C.c_uint)for n in('gen','units','tick','role')]
with tempfile.TemporaryDirectory(prefix='rh-air-fuel-')as folder:
 td=pathlib.Path(folder);objects=[]
 for source in [p for f in('sim','nav','ai','game')for p in(R/'src'/f).glob('*.asm')]+[R/'tests/terrain_probe.asm',R/'tests/probe_air_fuel.asm']:
  obj=td/(source.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(source),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True,capture_output=True)
 so=td/'candidate.so';link(so,objects)
 # Omitted-fuel policy is the causal control, no production hook or fixture renewal.
 src=(R/'src/ai/air_fuel.asm').read_text().replace('air_fuel_status:\n','air_fuel_status:\n xor eax,eax\n ret\n',1);(td/'control.asm').write_text(src);obj=td/'control.o';subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(td/'control.asm'),'-o',str(obj)],check=True,capture_output=True);control=td/'control.so';link(control,[obj if p.name=='air_fuel.asm.o'else p for p in objects])
 def bind(p):
  l=C.CDLL(str(p));l.sim_checksum.restype=C.c_uint64;l.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float
  for n in('probe_air_fuel_step','probe_air_fuel_status'):getattr(l,n).argtypes=[C.c_uint,C.c_void_p]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft'),(Fuel*32768).in_dll(l,'sim_air_fuel'),C.c_uint.in_dll(l,'sim_tick_count')
 l,e,a,f,t=bind(so)
 def reset(l,e,a,f):
  assert l.sim_init(64,42)==0
  for i in range(64):e[i].hp=0
  for side in(0,1):
   for front in range(3):assert l.sim_order(side,front,1)==0
  assert l.sim_waypoint(0,1,7000.,3900.)==0
  e[31]=Entity(2000.,3900.,200,0,3,1,-1,1);a[31]=Air(l.terrain_height(2000,3900)+90,math.pi/2,0,0,7,1,0,-1,0,180,1,7,0,0,0,1)
 def probe(name='step',ident=31):
  abi=(C.c_uint64*7)();rc=getattr(l,'probe_air_fuel_'+name)(ident,abi);assert tuple(abi)==tuple(0x123401+i for i in range(6))+(0,);return rc
 reset(l,e,a,f);physical=(bytes(e),bytes(a));assert probe('status')==0 and f[31].gen==0
 assert probe()==0 and f[31].units==21600 and physical==(bytes(e),bytes(a));cases=1
 for role,capacity in((0,36000),(1,21600)):
  reset(l,e,a,f);a[31].role=role;a[31].speed=(5,7)[role];assert probe()==0 and f[31].units==capacity
  before=bytes(f);assert probe()==0 and bytes(f)==before;cases+=2
  for bank,vy,cost in((0,0,1),(1,0,2),(-1,0,2),(0,.11,2),(1,.11,3),(1,-.11,2),(.99,.1,1)):
   t.value+=1;a[31].bank=bank;a[31].vy=vy;n=f[31].units;assert probe()==0 and f[31].units==n-cost;cases+=1
  a[31].bank=0;a[31].vy=0
  for units,status in((3601,0),(3600,1),(1,1),(0,2)):
   f[31].units=units;before=bytes(f);h=l.sim_checksum();assert probe('status')==status and bytes(f)==before and l.sim_checksum()==h;cases+=1
  f[31].units=1;t.value+=1;a[31].bank=1;a[31].vy=.2;assert probe()==2 and f[31].units==0;t.value+=1;assert probe()==2 and f[31].units==0;cases+=2
  e[31].gen+=1;a[31].gen+=1;assert probe()==0 and f[31].units==capacity;cases+=1
 reset(l,e,a,f);probe()
 for obj,field,value in((e[31],'hp',0),(e[31],'kind',0),(e[31],'side',2),(e[31],'front',3),(e[31],'gen',0),(a[31],'gen',99),(a[31],'flags',0),(a[31],'role',2),(a[31],'speed',math.nan),(a[31],'speed',0.99),(a[31],'speed',7.01),(a[31],'bank',math.inf),(a[31],'vy',math.nan),(f[31],'units',21601),(f[31],'role',1)):
  old=getattr(obj,field);setattr(obj,field,value);before=bytes(f);assert probe()==-1 and bytes(f)==before,(field,value);setattr(obj,field,old);cases+=1
 for i in(64,32768,0xffffffff):
  before=bytes(f);assert probe(ident=i)==-1 and bytes(f)==before;cases+=1
 # Extreme valid owner, corrupt count, wrapping fixed-tick stamp and a full tank.
 reset(l,e,a,f);probe();count=C.c_uint.in_dll(l,'sim_count');count.value=32769
 before=bytes(f);assert probe()==-1 and bytes(f)==before;cases+=1
 count.value=32768;e[32767]=e[31];a[32767]=a[31];assert probe(ident=32767)==0 and f[32767].units==21600;cases+=1
 count.value=64;t.value=0xffffffff;probe();n=f[31].units;t.value=0;assert probe()==0 and f[31].units==n-1;cases+=1
 reset(l,e,a,f);probe();f[30]=Fuel(11,22,33,44);f[32]=Fuel(55,66,77,88);adjacent=(bytes(f[30]),bytes(f[32]))
 for tick in range(1,21601):
  t.value=tick;status=l.air_fuel_step(31)
 assert status==2 and f[31].units==0 and (bytes(f[30]),bytes(f[32]))==adjacent;cases+=1
 # Same state, private fuel affects replay checksum; status itself remains pure.
 h=l.sim_checksum();f[31].units-=1;assert l.sim_checksum()!=h;cases+=1
 outcomes=[]
 for role,initial,condition in((0,3600,'bomber-reserve'),(1,3600,'fighter-reserve'),(0,0,'bomber-empty'),(1,0,'fighter-empty')):
  pair=[]
  for path,label in((so,'candidate'),(control,'omitted-policy')):
   ll,ee,aa,ff,tt=bind(path);reset(ll,ee,aa,ff);aa[31].role=role;aa[31].speed=(5,7)[role];aa[31].vx=(5,7)[role];aa[31].ammo=(8,180)[role];ll.sim_tick()
   ee[31].x=2000;ee[31].z=3900;aa[31].y=ll.terrain_height(2000,3900)+20;aa[31].heading=math.pi/2;aa[31].bank=0;aa[31].vx=(5,7)[role];aa[31].vy=0;aa[31].vz=0;ff[31].units=initial
   ammo=aa[31].ammo;trace=[];death=None
   for n in range(1,181):
    ll.sim_tick()
    if n%20==0:trace.append([n,ee[31].hp,aa[31].mode,aa[31].y,aa[31].vy,ff[31].units])
    if ee[31].hp==0:death=n;break
   pair.append(dict(label=label,hp=ee[31].hp,mode=aa[31].mode,death_tick=death,fuel=ff[31].units,ammo=aa[31].ammo,trace=trace))
   assert aa[31].ammo==ammo,'fuel must not fabricate refill or fire'
  candidate,omitted=pair
  if initial==0:assert candidate['death_tick'] and omitted['hp']==200,(condition,pair);assert any(x[2]==4 and x[4]<0 for x in candidate['trace'])
  else:assert candidate['hp']==200 and candidate['mode']==3 and omitted['mode']!=3,(condition,pair)
  outcomes.append(dict(condition=condition,paired=pair))
 print(json.dumps(dict(suite='air-fuel-native',passed=True,cases=cases,ABI=True,birth_only_refill=True,duplicate_tick_no_burn=True,saturating_consumption=True,query_readonly_hash=True,causal_public_outcomes=outcomes,library_sha256=hashlib.sha256(so.read_bytes()).hexdigest(),scope='Production NASM and real sim_tick; one-time plane/fuel staging declared, no live HP/fuel/clock renewal. Reserve withdrawal and powerless bounded glide/static contact vs omitted-policy control, not landing/rearm/full aerodynamics/audio/GPU/operation acceptance.')))
