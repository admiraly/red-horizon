#!/usr/bin/env python3
"""Native route guards and actual powered runway passes, with omitted-guide control."""
import ctypes as C,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NASM=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-approach-')as d:
 folder=Path(d);objects=[]
 for src in sorted(p for name in ('sim','nav','ai','game')for p in (ROOT/'src'/name).glob('*.asm'))+[ROOT/'tests/terrain_probe.asm',ROOT/'tests/probe_air_approach.asm']:
  obj=folder/(src.name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True,capture_output=True)
 candidate=folder/'candidate.so';link(candidate,objects)
 source=(ROOT/'src/ai/air_approach.asm').read_text();source=source.replace('air_approach_goal:\n','air_approach_goal:\n xor eax,eax\n ret\n',1)
 asm=folder/'control.asm';asm.write_text(source);obj=folder/'control.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
 control=folder/'control.so';link(control,[obj if o.name=='air_approach.asm.o'else o for o in objects])
 def bind(path):
  lib=C.CDLL(str(path));lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_checksum.restype=C.c_uint64
  lib.probe_air_approach_goal.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
  return lib,(Entity*32768).in_dll(lib,'sim_entities'),(Air*32768).in_dll(lib,'sim_aircraft'),((C.c_uint*4)*32768).in_dll(lib,'sim_air_approaches'),((C.c_uint*8)*12).in_dll(lib,'sim_sites')
 def reset(bound,side=0,role=1,front=1):
  lib,e,a,state,sites=bound;assert lib.sim_init(64,42)==0
  for i in range(64):e[i].hp=0
  for team in (0,1):
   for region in range(3):assert lib.sim_order(team,region,1)==0
  x=(3500.,4500.)[side];z=2000.*(front+1);speed=(5.,7.)[role];direction=(-1.,1.)[side]
  e[31]=Entity(x,z,50,side,3,front,-1,1);a[31]=Air(lib.terrain_height(x,z)+(110.,140.)[role],direction*math.pi/2,0,0,speed,role,0,-1,0,(8,180)[role],1,direction*speed,0,0,0,1)
 bound=bind(candidate);lib,e,a,state,sites=bound
 def query(ident=31):
  out=(C.c_float*5)(123,0,0,0,456);regs=(C.c_uint64*9)();before=(bytes(e),bytes(a),bytes(sites))
  result=lib.probe_air_approach_goal(ident,81.,17.,91.,C.byref(out,4),regs)
  assert tuple(regs)[:7]==tuple(0x123401+i for i in range(6))+(0,)
  assert out[0]==123 and out[4]==456 and before==(bytes(e),bytes(a),bytes(sites))
  if result==0:assert tuple(out)[1:4]==(81.,17.,91.)
  return result,tuple(out)[1:4]
 cases=[]
 for side in (0,1):
  for front in range(3):
   for role in (0,1):
    reset(bound,side,role,front);result,point=query();assert result==1 and state[31][2]==2
    expected=(e[31].x+(-600,600)[side],e[31].z,lib.terrain_height(e[31].x,e[31].z)+115.)
    expected=expected[:2]+(min(expected[2],lib.terrain_height(e[31].x,e[31].z)+(110.,140.)[role]),)
    assert max(abs(x-y)for x,y in zip(point,expected))<.001,(point,expected)
    private=bytes(state);assert query()==(result,point) and bytes(state)==private
    cases.append((side,front,role))
 reset(bound);query();sites[4][6]=0;query();assert state[31][1]!=1,'destroyed home retained'
 for row in sites:row[5]=0
 assert query()[0]==0 and bytes(state[31])==bytes(16)
 for ident in (64,32768,0xffffffff):assert query(ident)[0]==0
 for field,bad in [('y',math.nan),('vx',math.inf),('speed',4.9)]:
  reset(bound);setattr(a[31],field,bad);private=bytes(state);assert query()[0]==0 and bytes(state)==private
 reset(bound);query();a[31].gen=2;assert query()[0]==0
 reset(bound);query();e[31].hp=200;a[31].ammo=180;assert query()[0]==0 and bytes(state[31])==bytes(16)
 reset(bound);query();e[31].gen=2;a[31].gen=2;query();assert state[31][0]==2
 circuits=[]
 for side in (0,1):
  for front in range(3):
   for role in (0,1):
    reset(bound,side,role,front)
    e[31].x=4000.;a[31].heading=(1.,-1.)[side]*math.pi/2;a[31].vx=(1.,-1.)[side]*(5.,7.)[role]
    a[31].y=lib.terrain_height(e[31].x,e[31].z)+(110.,140.)[role]
    captured=None;gap=math.inf
    for tick in range(2400):
     lib.sim_tick();assert e[31].hp==50 and a[31].ammo==(8,180)[role]
     if state[31][2]==2 and captured is None:captured=tick
     gap=min(gap,math.dist((e[31].x,e[31].z),((2000.,6000.)[side],2000.*(front+1))))
     assert 600<=e[31].x<=7400 and 600<=e[31].z<=7400,(side,front,role,tick,e[31].x,e[31].z)
    assert captured is not None and gap<150,(side,front,role,captured,gap)
    circuits.append(dict(side=side,front=front,role=role,capture_tick=captured,closest_gap=gap))
 traces=[]
 for side in (0,1):
  for role in (0,1):
   paired=[]
   for path,label in ((candidate,'candidate'),(control,'omitted-guidance')):
    b=bind(path);reset(b,side,role);l,es,ars,st,ss=b;records=[];goaround=False
    for tick in range(900):
     previous_speed=ars[31].speed; l.sim_tick();own=es[31];air=ars[31];ground=l.terrain_height(own.x,own.z)
     assert own.hp==50 and air.ammo==(8,180)[role]
     speed=math.sqrt(air.vx**2+air.vy**2+air.vz**2);assert abs(speed-air.speed)<2e-5 and 5<=air.speed<=7
     assert -(.009,.012)[role]-.000002<=air.speed-previous_speed<=(.006,.010)[role]+.000002
     if label=='candidate' and st[31][2]==0 and tick>100:goaround=True
     if abs(own.x-(2000.,6000.)[side])<500 and abs(own.z-4000.)<40:
      records.append(dict(tick=tick,x=own.x,z=own.z,clearance=air.y-ground,bank=air.bank,vy=air.vy))
    assert records,(side,role,label)
    low=min(r['clearance']for r in records)
    if label=='candidate':
     assert 68<low<78,(side,role,low)
     assert max(r['x']for r in records)-min(r['x']for r in records)>850,(side,role,records)
     assert goaround,(side,role)
    else:assert low>100,(side,role,low)
    paired.append(dict(policy=label,samples=len(records),minimum_clearance=low,goaround=goaround,trace_sha256=hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()))
   traces.append(dict(side=side,role=role,paired=paired))
 print(json.dumps(dict(suite='air-approach-native',passed=True,route_cases=len(cases),misaligned_circuit_flights=circuits,public_paired_traces=traces,nonvolatile_stack_canaries_and_public_sources_preserved=True,library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),control_sha256=hashlib.sha256(control.read_bytes()).hexdigest(),scope='Powered final approach/controlled descent/go-around, actual public900-tick both-role both-side flights and omitted-only-guidance control; no live pose/HP/ammo/fuel/clock renewal. Not touchdown, ground rollout, traffic, service or whole-operation acceptance.')))
