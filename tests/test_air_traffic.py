#!/usr/bin/env python3
"""Exclusive runway final guidance, actual paired public flights and lease faults."""
import ctypes as C,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NASM=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-air-traffic-')as d:
 folder=Path(d);objects=[]
 for src in sorted(p for name in ('sim','nav','ai','game')for p in (ROOT/'src'/name).glob('*.asm'))+[ROOT/'tests/terrain_probe.asm',ROOT/'tests/probe_air_traffic.asm']:
  obj=folder/(src.name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True,capture_output=True)
 candidate=folder/'candidate.so';link(candidate,objects)
 text=(ROOT/'src/ai/air_traffic.asm').read_text().replace('air_traffic_request:\n','air_traffic_request:\n mov eax,1\n ret\n',1)
 asm=folder/'control.asm';asm.write_text(text);obj=folder/'control.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
 control=folder/'control.so';link(control,[obj if o.name=='air_traffic.asm.o'else o for o in objects])
 def bind(path):
  l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
  l.probe_air_traffic_request.argtypes=[C.c_uint,C.c_uint,C.c_void_p,C.c_void_p]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft'),((C.c_uint*4)*6).in_dll(l,'sim_air_traffic'),((C.c_uint*8)*12).in_dll(l,'sim_sites'),((C.c_uint*4)*32768).in_dll(l,'sim_air_approaches')
 def reset(bound,side=0,front=1,role=1):
  l,e,a,t,sites,approaches=bound;assert l.sim_init(64,42)==0
  for i in range(64):e[i].hp=0
  for team in (0,1):
   for region in range(3):assert l.sim_order(team,region,1)==0
  direction=(-1.,1.)[side];speed=(5.,7.)[role];x=(3400.,4600.)[side];z=2000.*(front+1)
  for ident,offset in [(31,0),(63,-direction*150)]:
   px=x+offset;e[ident]=Entity(px,z,50,side,3,front,-1,1);a[ident]=Air(l.terrain_height(px,z)+(110.,140.)[role],direction*math.pi/2,0,0,speed,role,3,-1,0,(8,180)[role],1,direction*speed,0,0,0,1)
 b=bind(candidate);l,e,a,t,sites,approaches=b
 def request(ident=31,base=1):
  vectors=(C.c_uint*34)(*[0xabc]*34);regs=(C.c_uint64*7)();before=(bytes(e),bytes(a),bytes(sites));rc=l.probe_air_traffic_request(ident,base,C.byref(vectors,4),regs)
  assert vectors[0]==vectors[33]==0xabc and tuple(vectors)[1:33]==tuple(0x3f000001+i for i in range(32))
  assert tuple(regs)==tuple(0x123401+i for i in range(6))+(0,)
  assert before==(bytes(e),bytes(a),bytes(sites));return rc
 cases=[]
 for side in (0,1):
  for front in range(3):
   reset(b,side,front);base=side*3+front
   assert request(31,base)==1 and tuple(t[base])==(32,1,0,side)
   before=l.sim_checksum();assert request(63,base)==0 and l.sim_checksum()==before
   assert request(31,base)==1 and l.sim_checksum()==before
   assert l.air_traffic_release(63)==0 and l.sim_checksum()==before
   assert l.air_traffic_release(31)==1 and tuple(t[base])==(0,0,0,0)
   assert request(63,base)==1;cases.append((side,front))
 tick=C.c_uint.in_dll(l,'sim_tick_count')
 reset(b);tick.value=100;assert request()==1;tick.value=159;assert request(63)==0;tick.value=160;assert request(63)==1
 reset(b);tick.value=100;assert request()==1;tick.value=159;assert request()==1;tick.value=218;assert request(63)==0;tick.value=219;assert request(63)==1
 reset(b);tick.value=0xffffffe2;assert request()==1;tick.value=29;assert request(63)==0;tick.value=30;assert request(63)==1
 lifecycle=[]
 for group,field,bad in [(e[31],'hp',0),(e[31],'kind',0),(e[31],'gen',2),(a[31],'gen',2),(a[31],'flags',0),(e[31],'side',1)]:
  reset(b);assert request()==1;setattr(group,field,bad);assert request(63)==1;lifecycle.append(field)
 reset(b);assert request()==1;e[31].gen=2;a[31].gen=2;assert request()==1 and t[1][1]==2
 for ident in (64,32768,0xffffffff):
  before=l.sim_checksum();assert request(ident)==-1 and l.air_traffic_release(ident)==-1 and before==l.sim_checksum()
 for base in (6,0xffffffff):
  before=l.sim_checksum();assert request(63,base)==-1 and before==l.sim_checksum()
 reset(b);assert request(31,0)==-1
 for field,bad in [(0,32769),(1,0),(2,1),(3,2)]:
  reset(b);assert request()==1;t[1][field]=bad;before=bytes(t);assert request(63)==-1 and bytes(t)==before
 reset(b);t[1][1]=1;before=bytes(t);assert request()==-1 and bytes(t)==before
 reset(b);assert request()==1;e[31].hp=200
 assert l.air_approach_goal(31)==0 and tuple(t[1])==(0,0,0,0)
 reset(b)
 for slot in t:slot[0]=32;slot[1]=1
 assert l.air_traffic_release(31)==6 and not any(bytes(t))
 reset(b);assert request()==1;count=C.c_uint.in_dll(l,'sim_count');count.value=32769;before=bytes(t)
 assert request(63)==-1 and l.air_traffic_release(31)==-1 and bytes(t)==before;count.value=64
 # Capture invalidates the old recorded side before examining its enemy body.
 reset(b);assert request()==1
 for r in sites:r[5]=0
 sites[4][2]=1;sites[4][5]=1;sites[4][6]=1000
 e[63].side=1;e[31].x=math.nan;a[31].y=math.inf
 assert request(63)==1 and t[1][3]==1
 # Genuine stop/init clears all leases; serialized private metadata enters hash.
 assert any(bytes(t));before=l.sim_checksum();l.air_traffic_init();assert not any(bytes(t)) and l.sim_checksum()!=before
 flights=[]
 for side in (0,1):
  for role in (0,1):
   pair=[]
   for path,label in [(candidate,'candidate'),(control,'omitted-admission')]:
    repeats=[]
    for repeat in range(2):
     bound=bind(path);reset(bound,side,role=role);q,en,ar,leases,ss,ap=bound;active_peak=0;both_descending=0;admitted=set();trace=[]
     for frame in range(2400):
      q.sim_tick();active=[]
      for ident in (31,63):
       assert en[ident].hp==50 and ar[ident].ammo==(8,180)[role]
       speed=math.sqrt(ar[ident].vx**2+ar[ident].vy**2+ar[ident].vz**2);assert abs(speed-(5.,7.)[role])<2e-5
       if ap[ident][2]==2 and ar[ident].mode==3:active.append(ident);admitted.add(ident)
      active_peak=max(active_peak,len(active));both_descending+=len(active)==2 and all(ar[i].vy<-.05 for i in active)
      if label=='candidate':
       assert len(active)<=1,(side,role,frame,active,tuple(leases[side*3+1]))
       if active:assert leases[side*3+1][0]==active[0]+1
      if frame%60==0:trace.append((frame,tuple(leases[side*3+1]),[(i,en[i].x,en[i].z,ar[i].y,ap[i][2])for i in (31,63)],q.sim_checksum()))
     if label=='candidate':assert admitted=={31,63},(side,role,admitted)
     else:assert active_peak==2 and both_descending>0,(side,role,active_peak,both_descending)
     repeats.append(dict(active_peak=active_peak,both_descending_frames=both_descending,admitted=sorted(admitted),trace_sha256=hashlib.sha256(json.dumps(trace).encode()).hexdigest()))
    assert repeats[0]==repeats[1],(side,role,label,repeats)
    pair.append(dict(policy=label,**repeats[0]))
   flights.append(dict(side=side,role=role,paired=pair))
 print(json.dumps(dict(suite='air-traffic-native',passed=True,bases=len(cases),lifecycle_guards=lifecycle,ABI_stack_all8XMM_public_sources_preserved=True,public_paired_flights=flights,library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),control_sha256=hashlib.sha256(control.read_bytes()).hexdigest(),scope='Exclusive generation-aware final approach leases, expiry/wrap/death/capture and both-side/both-role paired actual2400-tick flights twice. No live pose/HP/ammo/fuel/clock renewal. Not physical aircraft collision, queue fairness, ground occupancy, touchdown or service acceptance.')))
