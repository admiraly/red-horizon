#!/usr/bin/env python3
"""Independent specific-energy oracle, ABI guards, and real paired public flights."""
import ctypes as C,hashlib,json,math,os,random,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];NASM=os.environ['RED_HORIZON_NASM'];f32=lambda x:C.c_float(x).value
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-air-energy-')as d:
 folder=Path(d);objects=[]
 for src in sorted(p for name in ('sim','nav','ai','game')for p in (R/'src'/name).glob('*.asm'))+[R/'tests/terrain_probe.asm',R/'tests/probe_air_energy.asm']:
  obj=folder/(src.name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(R)+'/',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True,capture_output=True)
 candidate=folder/'candidate.so';link(candidate,objects)
 source=(R/'src/ai/air_energy.asm').read_text();variants={}
 for name,needle,replacement in [('omitted_energy','air_energy_step:\n','air_energy_step:\n jmp air_speed_step wrt ..plt\n'),('wrong_gravity',' subss xmm0,xmm1 ; potential',' addss xmm0,xmm1 ; potential'),('omitted_turn_drag',' mulss xmm1,[rax+rdi*4]\n',' xorps xmm1,xmm1\n')]:
  assert source.count(needle)==1;asm=folder/(name+'.asm');asm.write_text(source.replace(needle,replacement,1));obj=folder/(name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(R)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
  path=folder/(name+'.so');link(path,[obj if o.name=='air_energy.asm.o'else o for o in objects]);variants[name]=path
 preview_source=(R/'src/ai/air_final_clear.asm').read_text().replace('terrain_height,air_energy_step,','terrain_height,air_speed_step,').replace(' call air_energy_step\n',' call air_speed_step\n')
 asm=folder/'no_preview_energy.asm';asm.write_text(preview_source);obj=folder/'no_preview_energy.o';subprocess.run([NASM,'-f','elf64','-I',str(R)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
 no_preview=folder/'no_preview_energy.so';link(no_preview,[obj if o.name=='air_final_clear.asm.o'else o for o in objects])
 def bind(path):
  l=C.CDLL(str(path));l.probe_air_energy.argtypes=[C.c_uint,C.c_uint,*([C.c_float]*4),C.c_void_p,C.c_void_p];l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float;l.sim_checksum.restype=C.c_uint64
  return l
 def sample(l,role,powered,wanted,current,bank,climb):
  out=(C.c_float*4)(123,0,0,456);regs=(C.c_uint64*7)();rc=l.probe_air_energy(role,powered,wanted,current,bank,climb,C.byref(out,4),regs)
  assert out[0]==123 and out[3]==456 and tuple(regs)==tuple(0x123401+i for i in range(6))+(0,)
  return rc,out[1],out[2]
 l=bind(candidate);controls={n:bind(p)for n,p in variants.items()};rng=random.Random(831745)
 cases=[(role,power,6.,6.,bank,climb)for role in (0,1)for power in (0,1)for bank in (0.,.8,1.3)for climb in (-.5,0.,.5)]
 cases += [(rng.randrange(2),rng.randrange(2),rng.uniform(5,7),rng.uniform(5,7),rng.uniform(-1.6,1.6),rng.uniform(-.5,.5))for _ in range(3000)]
 cases += [(role,power,wanted,current,bank,climb)for role in (0,1)for power in (0,1)for wanted in (1,3,7)for current in (1,1.6,2.2,3,4.99)for bank in (0.,.8,1.3)for climb in (-.5,0,.5)]
 mismatch={n:0 for n in controls};max_error=0.;unsaturated=0;max_work_residual=0.
 for role,power,wanted,current,bank,climb in cases:
  wanted,current,bank,climb=map(f32,(wanted,current,bank,climb));acc=(.006,.010)[role];brake=(.009,.012)[role]
  throttle=max(-brake,min(acc,wanted-current))if power else 0
  base=current+throttle;drag=(.00035,.00025)[role]*math.tan(bank)**2+(0 if power else (.0006,.0005)[role])
  energy=base**2-2*current*drag-2*.0109*climb;raw=math.sqrt(max(0,energy));expected=max(1,min(7,current+max(-brake,min(acc,raw-current))))
  rc,speed,delta=sample(l,role,power,wanted,current,bank,climb);assert rc==0
  max_error=max(max_error,abs(speed-expected));assert abs(speed-expected)<1.5e-6,(role,power,wanted,current,bank,climb,speed,expected)
  assert abs(delta-(speed-current))<1e-7 and -brake-1e-6<=delta<=acc+1e-6
  if 1<raw<7 and -brake<raw-current<acc:
   unsaturated+=1;res=abs(speed**2+2*.0109*climb+2*current*drag-base**2);max_work_residual=max(max_work_residual,res);assert res<2e-5
  for n,q in controls.items():
   rr,ss,dd=sample(q,role,power,wanted,current,bank,climb);mismatch[n]+=rr!=0 or abs(ss-expected)>1.5e-6
 assert all(v>500 for v in mismatch.values()),mismatch
 invalid=[(2,1,6,6,0,0),(0,2,6,6,0,0)]
 for index,values in [(2,[0.99,7.01,math.nan,math.inf]),(3,[0.99,7.01,math.nan,math.inf]),(4,[-1.601,1.601,math.nan,math.inf]),(5,[-.501,.501,math.nan,math.inf])]:
  for value in values:
   args=[0,1,6,6,0,0];args[index]=value;invalid.append(tuple(args))
 for args in invalid:assert sample(l,*args)==(-1,0.,0.)
 qualitative=[]
 for role in (0,1):
  level=sample(l,role,1,6,6,0,0)[1];up=sample(l,role,1,6,6,0,.5)[1];down=sample(l,role,1,6,6,0,-.5)[1];turn=sample(l,role,1,6,6,1.3,0)[1];off=sample(l,role,0,7,6,0,0)[1]
  assert up<level==6<down and turn<level and off<level
  qualitative.append(dict(role=role,level=level,climb=up,descent=down,turn=turn,engine_off=off))
 sustained=[]
 for role in (0,1):
  speed=6.8;bank=math.acos(1/(4.5,8)[role]);history=[]
  for tick in range(60):
   rc,speed,delta=sample(l,role,1,7,speed,bank,0);assert rc==0;history.append(speed)
  assert history[-1]<history[0]<6.8
  sustained.append(dict(role=role,ticks=60,initial_speed=6.8,final_speed=speed,maximum_load=(4.5,8)[role],full_commanded_throttle=True))
 # The lower numerical speed floor remains an explicit energy safeguard.
 assert sample(l,0,0,7,1,0,.5)==(0,1.,0.)
 flights=[]
 for side in (0,1):
  for role in (0,1):
   pair=[]
   for path,label in [(candidate,'energy'),(variants['omitted_energy'],'omitted_energy')]:
    repeats=[]
    for repeat in range(2):
     q=bind(path);assert q.sim_init(64,42)==0;e=(Entity*32768).in_dll(q,'sim_entities');a=(Air*32768).in_dll(q,'sim_aircraft')
     for i in range(64):e[i].hp=0
     for team in (0,1):
      for front in range(3):assert q.sim_order(team,front,1)==0
     x=z=(6900.,1100.)[side];h=(math.pi/4,-3*math.pi/4)[side];speed=6.8;bank=(1,-1)[side]*math.acos(1/8)if role else 0.;vy=0. if role else -.5;horizontal=math.sqrt(speed**2-vy**2)
     e[31]=Entity(x,z,200,side,3,1,-1,1);a[31]=Air(q.terrain_height(x,z)+(110,140)[role],h,math.asin(vy/speed),bank,speed,role,0,-1,0,(8,180)[role],1,horizontal*math.sin(h),vy,horizontal*math.cos(h),0,1)
     trace=[];error=0.;first_speed=None
     for tick in range(120):
      old=(e[31].x,a[31].y,e[31].z);q.sim_tick();air=a[31]
      assert e[31].hp==200 and air.gen==1 and air.ammo==(8,180)[role]
      error=max(error,abs(math.dist(old,(e[31].x,air.y,e[31].z))-air.speed),abs(math.sqrt(air.vx**2+air.vy**2+air.vz**2)-air.speed));assert error<.001
      if first_speed is None:first_speed=air.speed
      trace.append((e[31].x,air.y,e[31].z,air.speed,air.bank,air.vy))
     repeats.append(dict(first_speed=first_speed,final_speed=air.speed,motion_error=error,hash=hashlib.sha256(json.dumps(trace).encode()).hexdigest(),checksum=f'{q.sim_checksum():016x}'))
    assert repeats[0]==repeats[1];pair.append(dict(policy=label,**repeats[0]))
   assert pair[0]['hash']!=pair[1]['hash']
   if role==1:assert pair[0]['first_speed']<6.8<pair[1]['first_speed'],pair
   else:assert pair[0]['first_speed']>pair[1]['first_speed'],pair
   flights.append(dict(side=side,role=role,ticks=120,paired=pair))
 # A wall just beyond the no-energy endpoint exposes incorrect final admission.
 # Both queries are read-only; geometry edits are one initial fixture, restored.
 libc=C.CDLL(None);libc.mprotect.argtypes=[C.c_void_p,C.c_size_t,C.c_int];page=os.sysconf('SC_PAGE_SIZE');preview=[]
 for path,label in [(candidate,'energy'),(no_preview,'omitted_preview_energy')]:
  q=bind(path);assert q.sim_init(64,42)==0;e=(Entity*32768).in_dll(q,'sim_entities');a=(Air*32768).in_dll(q,'sim_aircraft')
  for i in range(64):e[i].hp=0
  for team in (0,1):
   for front in range(3):assert q.sim_order(team,front,1)==0
  e[31]=Entity(3500,4000,50,0,3,1,-1,1);a[31]=Air(q.terrain_height(3500,4000)+140,-math.pi/2,0,0,7,1,3,-1,0,180,1,-7,0,0,0,1)
  if label=='energy':
   for tick in range(120):q.sim_tick();assert e[31].hp==50 and a[31].ammo==180 and a[31].gen==1
   physical_endpoint=e[31].x;assert 2743.-4<=physical_endpoint<=2744.5+4,physical_endpoint
   assert q.sim_init(64,42)==0
   for i in range(64):e[i].hp=0
   for team in (0,1):
    for front in range(3):assert q.sim_order(team,front,1)==0
   e[31]=Entity(3500,4000,50,0,3,1,-1,1);a[31]=Air(q.terrain_height(3500,4000)+140,-math.pi/2,0,0,7,1,3,-1,0,180,1,-7,0,0,0,1)
  boxes=(C.c_float*40).in_dll(q,'terrain_obstacles');addr=C.addressof(boxes);start=addr//page*page;span=((addr+C.sizeof(boxes)+page-1)//page)*page-start;saved=bytes(boxes);assert libc.mprotect(start,span,3)==0
  try:
   boxes[0]=2743.;boxes[1]=3950.;boxes[2]=2744.5;boxes[3]=4050.;boxes[4]=0.;boxes[5]=300.
   checksum=q.sim_checksum();before=(bytes(e),bytes(a));rc=q.air_final_clear(31,1)
   assert before==(bytes(e),bytes(a))and checksum==q.sim_checksum()
   assert rc==(0 if label=='energy'else 1),(label,rc)
   preview.append(dict(policy=label,result=rc,wall_x=[2743.,2744.5],source_unchanged=True))
  finally:C.memmove(addr,saved,len(saved));assert libc.mprotect(start,span,1)==0
 print(json.dumps(dict(suite='air-energy',passed=True,cases=len(cases),invalid=len(invalid),maximum_error=max_error,unsaturated_energy_cases=unsaturated,maximum_work_residual=max_work_residual,assembled_negative_mismatches=mismatch,ABI_stack_output_canaries=True,qualitative=qualitative,sustained_high_load=sustained,minimum_speed_saturation_explicit=True,public_flights=flights,final_preview_energy_control=preview,actual_unobstructed_final_endpoint=physical_endpoint,library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),scope='Real kinetic/potential and induced-drag coupling within existing1..7 speed/acceleration safeguards; isolated energy kernel does not establish low-speed lift, landing, total aerodynamic model, timing, graphics or UDP acceptance. Public initial births only, no later pose/health/stores/fuel/time renewal.')))
