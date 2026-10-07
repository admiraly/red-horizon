#!/usr/bin/env python3
"""Independent wheel braking and actual airborne rejection of blocked ground roll."""
import ctypes as C,hashlib,json,math,os,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NASM=os.environ['RED_HORIZON_NASM']
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-final-clear-')as d:
 folder=Path(d);objects=[]
 for src in sorted(p for name in ('sim','nav','ai','game')for p in (ROOT/'src'/name).glob('*.asm'))+[ROOT/'tests/terrain_probe.asm',ROOT/'tests/probe_air_approach.asm',ROOT/'tests/probe_air_final_clear.asm',ROOT/'tests/probe_air_rollout.asm',ROOT/'tests/probe_air_ground_speed.asm']:
  obj=folder/(src.name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True,capture_output=True)
 candidate=folder/'candidate.so';link(candidate,objects)
 text=(ROOT/'src/ai/air_rollout.asm').read_text().replace('air_rollout_clear:\n','air_rollout_clear:\n mov eax,1\n ret\n',1)
 asm=folder/'control.asm';asm.write_text(text);obj=folder/'control.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
 control=folder/'control.so';link(control,[obj if o.name=='air_rollout.asm.o'else o for o in objects])
 def bind(path):
  l=C.CDLL(str(path));l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
  l.probe_air_final_clear.argtypes=[C.c_uint,C.c_uint,C.c_void_p];l.probe_air_rollout_clear.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_void_p];l.probe_air_ground_speed.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_void_p,C.c_void_p];l.probe_air_approach_goal.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft'),((C.c_uint*4)*32768).in_dll(l,'sim_air_approaches'),((C.c_uint*4)*6).in_dll(l,'sim_air_traffic'),((C.c_uint*8)*12).in_dll(l,'sim_sites'),(C.c_float*40).in_dll(l,'terrain_obstacles')
 def reset(b,side=0,role=1,front=1):
  l,e,a,route,traffic,sites,boxes=b;assert l.sim_init(64,42)==0
  for i in range(64):e[i].hp=0
  for team in (0,1):
   for region in range(3):assert l.sim_order(team,region,1)==0
  x=(3350.,4650.)[side];z=2000.*(front+1);speed=(5.,7.)[role];direction=(-1.,1.)[side]
  e[31]=Entity(x,z,50,side,3,front,-1,1);a[31]=Air(l.terrain_height(x,z)+(110.,140.)[role],direction*math.pi/2,0,0,speed,role,0,-1,0,(8,180)[role],1,direction*speed,0,0,0,1)
 def query(b,ident=31,base=1,planned=3.):
  l,e,a,route,traffic,sites,boxes=b;regs=(C.c_uint64*7)();before=(l.sim_checksum(),bytes(e),bytes(a),bytes(route),bytes(traffic),bytes(sites),bytes(boxes))
  result=l.probe_air_rollout_clear(ident,base,planned,regs)
  assert tuple(regs)==tuple(0x123401+i for i in range(6))+(0,)
  assert before==(l.sim_checksum(),bytes(e),bytes(a),bytes(route),bytes(traffic),bytes(sites),bytes(boxes))
  return result
 def goal(b):
  out=(C.c_float*3)();regs=(C.c_uint64*9)();assert b[0].probe_air_approach_goal(31,81.,17.,91.,out,regs)==1
  assert tuple(regs)[:7]==tuple(0x123401+i for i in range(6))+(0,)
  return tuple(out)
 ground_source=(ROOT/'src/ai/air_ground_speed.asm').read_text()
 ground_controls={}
 for name,edited in [('omitted_brake',ground_source.replace(' subss xmm0,[rax+rdi*4]',' ; omitted wheel braking')),('wrong_gravity',ground_source.replace(' subss xmm0,xmm1',' addss xmm0,xmm1'))]:
  asm=folder/(name+'.asm');obj=folder/(name+'.o');asm.write_text(edited);subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
  so=folder/(name+'.so');link(so,[obj if o.name=='air_ground_speed.asm.o'else o for o in objects]);ground_controls[name]=bind(so)[0]
 def speed(l,role,v,grade):
  out=(C.c_float*4)(123,0,0,456);regs=(C.c_uint64*7)();rc=l.probe_air_ground_speed(role,v,grade,C.byref(out,4),regs)
  assert out[0]==123 and out[3]==456 and tuple(regs)==tuple(0x123401+i for i in range(6))+(0,)
  return rc,out[1],out[2]
 primitive=bind(candidate)[0];mismatches={k:0 for k in ground_controls};oracle_count=0;stops=[];maximum_error=0
 for role in (0,1):
  for grade in (-.02,-.01,0.,.01,.02):
   grade=C.c_float(grade).value
   for index in range(321):
    v=C.c_float(index*.01).value;expected=max(0,v-(.012,.018)[role]-.0109*grade/math.sqrt(1+grade*grade));rc,new,delta=speed(primitive,role,v,grade)
    error=max(abs(new-expected),abs(delta-(expected-v)));maximum_error=max(maximum_error,error);assert rc==0 and error<3e-7 and 0<=new<=v
    for name,q in ground_controls.items():
     rc,bad,d=speed(q,role,v,grade);mismatches[name]+=abs(bad-expected)>3e-7
    oracle_count+=1
   actual=expected=3.2;distance=independent=0.;ticks=0
   while actual>0:
    rc,actual,_=speed(primitive,role,actual,grade);expected=max(0,expected-(.012,.018)[role]-.0109*grade/math.sqrt(1+grade*grade));distance+=actual/math.sqrt(1+grade*grade);independent+=expected/math.sqrt(1+grade*grade);ticks+=1;assert ticks<=300
   assert abs(distance-independent)<.01 and expected==0;stops.append(dict(role=role,grade=grade,ticks=ticks,distance=distance,independent_distance=independent))
 assert all(n>1000 for n in mismatches.values()),mismatches
 invalid_speed=[(2,3,0),(0xffffffff,3,0),(0,-.01,0),(0,3.21,0),(0,3,.021),(0,3,-.021)]
 for column in (1,2):
  for bad in (math.nan,math.inf,-math.inf):
   args=[0,3,0];args[column]=bad;invalid_speed.append(args)
 for args in invalid_speed:assert speed(primitive,*args)==(-1,0,0)
 bound=bind(candidate);l,e,a,route,traffic,sites,boxes=bound;cases=0
 for side in (0,1):
  for front in range(3):
   for role in (0,1):reset(bound,side,role,front);assert query(bound,base=side*3+front)==1;cases+=1
 for planned in (0.,-.1,3.201,math.nan,math.inf,-math.inf):
  reset(bound);assert query(bound,planned=planned)==-1;cases+=1
 for planned in (.001,1.,3.2):
  reset(bound);assert query(bound,planned=planned)==1;cases+=1
 for ident,base in [(64,1),(32768,1),(0xffffffff,1),(31,6),(31,0xffffffff),(31,0)]:
  reset(bound);assert query(bound,ident,base)==-1;cases+=1
 for field,value in [('gen',2),('role',2),('flags',0)]:
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
   # A wall only on the prospective ground roll, below all airborne final
   # heights: existing descending-final forecast alone must remain clear.
   bx=(2400.,5600.)[side];bz=4000.;top=50.
   pair=[]
   for path,label in ((candidate,'candidate'),(control,'omitted-rollout')):
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
       assert 1<=air[31].speed<=7 and -(.009,.012)[role]-.000002<=air[31].speed-old_speed<=(.006,.010)[role]+.000002
       assert abs(air[31].vy-oldvy)<=(.012,.024)[role]+.000002
       assert abs(air[31].bank-oldbank)<=(.06,.1)[role]+.000002
       rows.append((en[31].x,air[31].y,en[31].z,air[31].bank,air[31].vy,st[31][2]))
      repeated.append(dict(minimum_y=min(r[1]for r in rows),first20_minimum_y=min(r[1]for r in rows[:20]),first20_final_frames=sum(r[5]==2 for r in rows[:20]),first20_lateral_travel=max(abs(r[2]-4000)for r in rows[:20]),first20_max_bank=max(abs(r[3])for r in rows[:20]),final_xyz=rows[-1][:3],final_frames=sum(r[5]==2 for r in rows),trace_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest()))
     finally:restore(b,info)
    assert repeated[0]==repeated[1];pair.append(dict(policy=label,**repeated[0]))
   assert pair[0]['first20_final_frames']==0 and pair[1]['first20_final_frames']==20,pair
   assert pair[0]['first20_lateral_travel']>pair[1]['first20_lateral_travel']+.5,pair
   assert pair[0]['first20_max_bank']>pair[1]['first20_max_bank']+.1,pair
   traces.append(dict(side=side,role=role,wall_top_y=top,ground_roll_wall_xyz=(bx,top,bz),paired=pair))
 reset(bound);start=time.perf_counter()
 for _ in range(100):assert l.air_final_clear(31,1)==1
 elapsed=time.perf_counter()-start
 print(json.dumps(dict(suite='air-rollout-clearance',independent_braking_cases=oracle_count,invalid_braking_cases=len(invalid_speed),maximum_braking_error=maximum_error,negative_mismatches=mismatches,independent_stops=stops,passed=True,guard_cases=cases,public_paired_flights=traces,abi_stack_readonly_canaries=True,preview_100_calls_seconds=elapsed,library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),control_sha256=hashlib.sha256(control.read_bytes()).hexdigest(),scope='Prospective wheel-braked ground roll admission, real terrain/solid hull. Both-role/side initial-only wall fixtures below airborne final; control omits only rollout admission, retains descending-final forecast and live collision. Public120-tick go-around flights with finite original stores. No actual touchdown/ground mode, wreck/actor contact, UDP, GPU or performance acceptance.')))
