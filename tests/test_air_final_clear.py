#!/usr/bin/env python3
"""Native descending-final swept preview and paired public abort flights."""
import ctypes as C,hashlib,json,math,os,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NASM=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-final-clear-')as d:
 folder=Path(d);objects=[]
 for src in sorted(p for name in ('sim','nav','ai','game')for p in (ROOT/'src'/name).glob('*.asm'))+[ROOT/'tests/terrain_probe.asm',ROOT/'tests/probe_air_approach.asm',ROOT/'tests/probe_air_final_clear.asm']:
  obj=folder/(src.name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True,capture_output=True)
 candidate=folder/'candidate.so';link(candidate,objects)
 text=(ROOT/'src/ai/air_final_clear.asm').read_text().replace('air_final_clear:\n','air_final_clear:\n mov eax,1\n ret\n',1)
 asm=folder/'control.asm';asm.write_text(text);obj=folder/'control.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
 control=folder/'control.so';link(control,[obj if o.name=='air_final_clear.asm.o'else o for o in objects])
 def bind(path):
  l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
  l.probe_air_final_clear.argtypes=[C.c_uint,C.c_uint,C.c_void_p];l.probe_air_approach_goal.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft'),((C.c_uint*4)*32768).in_dll(l,'sim_air_approaches'),((C.c_uint*4)*6).in_dll(l,'sim_air_traffic'),((C.c_uint*8)*12).in_dll(l,'sim_sites'),(C.c_float*40).in_dll(l,'terrain_obstacles')
 def reset(b,side=0,role=1,front=1):
  l,e,a,route,traffic,sites,boxes=b;assert l.sim_init(64,42)==0
  for i in range(64):e[i].hp=0
  for team in (0,1):
   for region in range(3):assert l.sim_order(team,region,1)==0
  x=(3350.,4650.)[side];z=2000.*(front+1);speed=(5.,7.)[role];direction=(-1.,1.)[side]
  e[31]=Entity(x,z,50,side,3,front,-1,1);a[31]=Air(l.terrain_height(x,z)+(110.,140.)[role],direction*math.pi/2,0,0,speed,role,0,-1,0,(8,180)[role],1,direction*speed,0,0,0,1)
 def query(b,ident=31,base=1):
  l,e,a,route,traffic,sites,boxes=b;regs=(C.c_uint64*7)();before=(l.sim_checksum(),bytes(e),bytes(a),bytes(route),bytes(traffic),bytes(sites),bytes(boxes))
  result=l.probe_air_final_clear(ident,base,regs)
  assert tuple(regs)==tuple(0x123401+i for i in range(6))+(0,)
  assert before==(l.sim_checksum(),bytes(e),bytes(a),bytes(route),bytes(traffic),bytes(sites),bytes(boxes))
  return result
 def goal(b):
  out=(C.c_float*3)();regs=(C.c_uint64*9)();assert b[0].probe_air_approach_goal(31,81.,17.,91.,out,regs)==1
  assert tuple(regs)[:7]==tuple(0x123401+i for i in range(6))+(0,)
  return tuple(out)
 bound=bind(candidate);l,e,a,route,traffic,sites,boxes=bound;cases=0
 for side in (0,1):
  for front in range(3):
   for role in (0,1):reset(bound,side,role,front);assert query(bound,base=side*3+front)==1;cases+=1
 for ident,base in [(64,1),(32768,1),(0xffffffff,1),(31,6),(31,0xffffffff),(31,0)]:
  reset(bound);assert query(bound,ident,base)==-1;cases+=1
 for field,value in [('y',math.nan),('y',math.inf),('heading',math.nan),('heading',6.4),('bank',1.61),('vy',.51),('speed',4.99),('speed',7.01),('speed',math.nan),('gen',2),('role',2),('flags',0)]:
  reset(bound);setattr(a[31],field,value);assert query(bound)==-1;cases+=1
 for field,value in [('x',-1),('z',8001),('x',math.nan),('hp',0),('kind',1),('side',2),('gen',0)]:
  reset(bound);setattr(e[31],field,value);assert query(bound)==-1;cases+=1
 reset(bound);count=C.c_uint.in_dll(l,'sim_count');count.value=32769;assert query(bound)==-1;count.value=64;cases+=1
 reset(bound);sites[4][6]=0;assert query(bound)==-1;cases+=1
 libc=C.CDLL(None);libc.mprotect.argtypes=[C.c_void_p,C.c_size_t,C.c_int];page=os.sysconf('SC_PAGE_SIZE')
 def writable(b):
  bs=b[-1];addr=C.addressof(bs);start=addr//page*page;span=((addr+C.sizeof(bs)+page-1)//page)*page-start;assert libc.mprotect(start,span,3)==0
  return addr,start,span,bytes(bs)
 def restore(b,info):
  addr,start,span,saved=info;C.memmove(addr,saved,len(saved));assert libc.mprotect(start,span,1)==0
 reset(bound);info=writable(bound)
 try:
  for field,value in [(4,math.nan),(2,boxes[0]-1),(5,-1)]:
   boxes[field]=value;assert query(bound)==-1;goal(bound);assert route[31][2]==0 and not any(bytes(traffic));C.memmove(info[0],info[3],len(info[3]));cases+=1
 finally:restore(bound,info)
 traces=[]
 for side in (0,1):
  for role in (0,1):
   # Independent actual clear-flight samples place a wall only in the future
   # descent, below the initial horizontal trajectory. Fixture is initial-only.
   baseline=bind(candidate);reset(baseline,side,role);initial_y=baseline[2][31].y
   for tick in range(80):baseline[0].sim_tick()
   bx,bz,by=baseline[1][31].x,baseline[1][31].z,baseline[2][31].y
   assert initial_y-by>12,(side,role,initial_y,by)
   top=(initial_y+by)/2-4
   pair=[]
   for path,label in ((candidate,'candidate'),(control,'omitted-final-preview')):
    repeated=[]
    for repeat in range(2):
     b=bind(path);reset(b,side,role);q,en,air,st,tr,ss,bs=b;info=writable(b)
     try:
      # Replace one authored solid record; all other terrain remains genuine.
      bs[0]=bx-20;bs[1]=bz-50;bs[2]=bx+20;bs[3]=bz+50;bs[4]=0;bs[5]=top
      assert q.air_world_warning(31)==0,'present velocity already sees fixture'
      if label=='candidate':assert query(b,base=side*3+1)==0
      goal(b)
      assert st[31][2]==(0 if label=='candidate'else 2)
      assert bool(any(bytes(tr)))==(label!='candidate')
      rows=[]
      for tick in range(120):
       old=(en[31].x,air[31].y,en[31].z);oldvy=air[31].vy;oldbank=air[31].bank;old_speed=air[31].speed;q.sim_tick()
       assert en[31].hp==50 and air[31].ammo==(8,180)[role],(side,role,label,tick,en[31].hp)
       assert abs(math.dist(old,(en[31].x,air[31].y,en[31].z))-air[31].speed)<.001
       assert 5<=air[31].speed<=7 and -(.009,.012)[role]-.000002<=air[31].speed-old_speed<=(.006,.010)[role]+.000002
       assert abs(air[31].vy-oldvy)<=(.012,.024)[role]+.000002
       assert abs(air[31].bank-oldbank)<=(.06,.1)[role]+.000002
       rows.append((en[31].x,air[31].y,en[31].z,air[31].bank,air[31].vy,st[31][2]))
      repeated.append(dict(minimum_y=min(r[1]for r in rows),first20_minimum_y=min(r[1]for r in rows[:20]),first20_final_frames=sum(r[5]==2 for r in rows[:20]),first20_lateral_travel=max(abs(r[2]-4000)for r in rows[:20]),first20_max_bank=max(abs(r[3])for r in rows[:20]),final_xyz=rows[-1][:3],final_frames=sum(r[5]==2 for r in rows),trace_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest()))
     finally:restore(b,info)
    assert repeated[0]==repeated[1];pair.append(dict(policy=label,**repeated[0]))
   assert pair[0]['first20_final_frames']==0 and pair[1]['first20_final_frames']==20,pair
   assert pair[0]['first20_lateral_travel']>pair[1]['first20_lateral_travel']+.5,pair
   assert pair[0]['first20_max_bank']>pair[1]['first20_max_bank']+.1,pair
   traces.append(dict(side=side,role=role,wall_top_y=top,baseline_tick80_xyz=(bx,by,bz),paired=pair))
 reset(bound);start=time.perf_counter()
 for _ in range(100):assert l.air_final_clear(31,1)==1
 elapsed=time.perf_counter()-start
 print(json.dumps(dict(suite='air-final-clearance',passed=True,guard_cases=cases,public_paired_flights=traces,abi_stack_readonly_canaries=True,preview_100_calls_seconds=elapsed,library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),control_sha256=hashlib.sha256(control.read_bytes()).hexdigest(),scope='120 uninterrupted final ticks, production bank/vertical actuators, real terrain/solid hull sweeps. Both-role/side initial-only hazardous-wall fixtures; existing current-velocity warning and contact remain enabled in control. Not full landing, future external evasive orders, wreck/actor collision or whole-operation acceptance.')))
