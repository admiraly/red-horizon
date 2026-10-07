#!/usr/bin/env python3
"""Independent bounded acceleration oracle and real final/go-around airspeed."""
import ctypes as C,hashlib,json,math,os,random,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NASM=os.environ['RED_HORIZON_NASM'];f32=lambda x:C.c_float(x).value
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-air-speed-')as d:
 folder=Path(d);objects=[]
 for src in sorted(p for name in ('sim','nav','ai','game')for p in (ROOT/'src'/name).glob('*.asm'))+[ROOT/'tests/terrain_probe.asm',ROOT/'tests/probe_air_speed.asm']:
  obj=folder/(src.name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 def link(path,objs):subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(path),*map(str,objs),'-lm'],check=True,capture_output=True)
 candidate=folder/'candidate.so';link(candidate,objects)
 variants={}
 for name,label,needle,body in [('no_actuator','air_speed.asm','air_speed_step:\n','movaps xmm0,xmm1\n xorps xmm1,xmm1\n xor eax,eax\n ret\n'),('instant_speed','air_speed.asm','air_speed_step:\n','subss xmm1,xmm0\n xor eax,eax\n ret\n'),('stale_preview','air_final_clear.asm',' call air_energy_step\n',' xor eax,eax\n movss xmm0,[rsp+12]\n')]:
  source=(ROOT/'src/ai'/label).read_text();assert source.count(needle)==1
  changed=source.replace(needle,needle+body,1)if label=='air_speed.asm'else source.replace(needle,body,1)
  asm=folder/(name+'.asm');asm.write_text(changed);obj=folder/(name+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
  path=folder/(name+'.so');replaced=[obj if o.name==label+'.o'else o for o in objects]
  if name=='no_actuator':
   energy=(ROOT/'src/ai/air_energy.asm').read_text().replace('air_energy_step:\n','air_energy_step:\n movaps xmm0,xmm1\n xorps xmm1,xmm1\n xor eax,eax\n ret\n',1)
   ep=folder/'no_energy.asm';ep.write_text(energy);eo=folder/'no_energy.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(ep),'-o',str(eo)],check=True,capture_output=True)
   replaced=[eo if o.name=='air_energy.asm.o'else o for o in replaced]
  link(path,replaced);variants[name]=path
 def bind(path):
  l=C.CDLL(str(path));l.probe_air_speed.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_void_p,C.c_void_p]
  l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
  return l,(Entity*32768).in_dll(l,'sim_entities'),(Air*32768).in_dll(l,'sim_aircraft'),((C.c_uint*4)*32768).in_dll(l,'sim_air_approaches')
 bound=bind(candidate);l,e,a,route=bound
 def sample(lib,role,wanted,current):
  out=(C.c_float*4)(123,0,0,456);regs=(C.c_uint64*7)();rc=lib.probe_air_speed(role,wanted,current,C.byref(out,4),regs)
  assert out[0]==123 and out[3]==456 and tuple(regs)==tuple(0x123401+i for i in range(6))+(0,)
  return rc,tuple(out)[1:3]
 rng=random.Random(487231);cases=[(role,wanted,current)for role in (0,1)for wanted in (5,5.001,6,6.999,7)for current in (5,5.001,6,6.999,7)]
 cases += [(rng.randrange(2),rng.uniform(5,7),rng.uniform(5,7))for _ in range(2000)]
 negatives={name:0 for name in ('no_actuator','instant_speed')};control_libs={name:bind(variants[name])[0]for name in negatives};error=0.
 for role,wanted,current in cases:
  wanted,current=f32(wanted),f32(current);rc,(speed,delta)=sample(l,role,wanted,current);assert rc==0
  change=max(-(.009,.012)[role],min((.006,.010)[role],wanted-current));expected=current+change
  error=max(error,abs(speed-expected));assert abs(speed-expected)<5e-7
  assert abs(delta-(speed-current))<1e-7 and 5<=speed<=7
  assert min(wanted,current)-1e-7<=speed<=max(wanted,current)+1e-7
  for name,lib in control_libs.items():
   rr,(ss,dd)=sample(lib,role,wanted,current);negatives[name]+=rr!=0 or abs(ss-expected)>=5e-7
 assert all(v>100 for v in negatives.values()),negatives
 invalid=[(2,5,5),(0xffffffff,5,5)]+[(0,x,6)for x in (4.99,7.01,math.nan,math.inf,-math.inf)]+[(1,6,x)for x in (4.99,7.01,math.nan,math.inf,-math.inf)]
 for args in invalid:assert sample(l,*args)==(-1,(0.,0.))
 reversals=[]
 for role in (0,1):
  speed=7.;trace=[]
  for i in range(500):
   wanted=5. if i<260 else 7.;old=speed;rc,(speed,delta)=sample(l,role,wanted,speed);assert rc==0
   assert -(.009,.012)[role]-1e-6<=delta<=(.006,.010)[role]+1e-6;trace.append(speed)
  assert trace[259]==5 and trace[260]>5 and trace[260]-5<.011
  reversals.append(dict(role=role,settle_tick=next(i for i,v in enumerate(trace)if v==5),first_acceleration=trace[260]-5,last_speed=trace[-1]))
 def reset(b,side=0,role=1,initial_speed=7.):
  q,en,ar,st=b;assert q.sim_init(64,42)==0
  for i in range(64):en[i].hp=0
  for team in (0,1):
   for front in range(3):assert q.sim_order(team,front,1)==0
  x=(3500.,4500.)[side];direction=(-1.,1.)[side];en[31]=Entity(x,4000,50,side,3,1,-1,1)
  ar[31]=Air(q.terrain_height(x,4000)+(110,140)[role],direction*math.pi/2,0,0,initial_speed,role,3,-1,0,(8,180)[role],1,direction*initial_speed,0,0,0,1)
 flights=[]
 for side in (0,1):
  for role in (0,1):
   pair=[]
   for path,label in [(candidate,'candidate'),(variants['no_actuator'],'omitted-speed-actuator')]:
    repeats=[]
    for repeat in range(2):
     b=bind(path);reset(b,side,role);q,en,ar,st=b;rows=[];max_error=0.;reaccelerated=False;seenfinal=False;final_min=7.
     for tick in range(900):
      old=(en[31].x,ar[31].y,en[31].z);old_speed=ar[31].speed;q.sim_tick();air=ar[31]
      assert en[31].hp==50 and air.ammo==(8,180)[role]and air.gen==1
      displacement=math.dist(old,(en[31].x,air.y,en[31].z));norm=math.sqrt(air.vx**2+air.vy**2+air.vz**2)
      max_error=max(max_error,abs(displacement-air.speed),abs(norm-air.speed));assert max_error<.001
      assert 5<=air.speed<=7 and -(.009,.012)[role]-.000002<=air.speed-old_speed<=(.006,.010)[role]+.000002
      if st[31][2]==2:seenfinal=True;final_min=min(final_min,air.speed)
      if seenfinal and st[31][2]==0 and air.speed>old_speed:reaccelerated=True
      rows.append((tick,en[31].x,air.y,en[31].z,air.speed,air.bank,air.vy,st[31][2]))
     assert seenfinal
     if label=='candidate':assert final_min==5 and (role==0 or reaccelerated)
     else:assert final_min==7 and not reaccelerated
     repeats.append(dict(final_minimum_speed=final_min,goaround_reaccelerated=reaccelerated,maximum_motion_speed_error=max_error,trace_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest()))
    assert repeats[0]==repeats[1];pair.append(dict(policy=label,**repeats[0]))
   flights.append(dict(side=side,role=role,initial_speed=7,paired=pair))
 # Invalid actual endpoint rolls back total airspeed with every saved pose.
 reset(bound,initial_speed=5.)
 e[31].x=7999.;e[31].hp=200;a[31].heading=math.pi/2;a[31].vx=5.;a[31].vy=0.;a[31].vz=0.;a[31].y=200.
 saved=(e[31].x,e[31].z,a[31].y,a[31].speed,a[31].heading,a[31].pitch,a[31].bank,a[31].vx,a[31].vy,a[31].vz)
 l.sim_tick()
 assert saved==(e[31].x,e[31].z,a[31].y,a[31].speed,a[31].heading,a[31].pitch,a[31].bank,a[31].vx,a[31].vy,a[31].vz)
 # Actual uninterrupted clear final determines reachable120-tick extent.
 # A tall initial-only wall lies outside the braked trajectory but inside a
 # stale constant-speed preview. Existing warning may separately interrupt it.
 reset(bound)
 for _ in range(120):l.sim_tick()
 endpoint=e[31].x;assert endpoint>2700+4,endpoint
 libc=C.CDLL(None);libc.mprotect.argtypes=[C.c_void_p,C.c_size_t,C.c_int];page=os.sysconf('SC_PAGE_SIZE');preview=[]
 for path,label in [(candidate,'candidate'),(variants['stale_preview'],'omitted-preview-speed-update')]:
  b=bind(path);reset(b);q,en,ar,st=b;boxes=(C.c_float*40).in_dll(q,'terrain_obstacles');addr=C.addressof(boxes);start=addr//page*page;span=((addr+C.sizeof(boxes)+page-1)//page)*page-start;saved=bytes(boxes);assert libc.mprotect(start,span,3)==0
  try:
   boxes[0]=2695;boxes[1]=3950;boxes[2]=2700;boxes[3]=4050;boxes[4]=0;boxes[5]=300
   physical=(bytes(en),bytes(ar));rc=q.air_final_clear(31,1);assert physical==(bytes(en),bytes(ar));assert rc==(1 if label=='candidate'else 0),(label,rc)
   preview.append(dict(policy=label,result=rc,wall_x=(2695,2700),actual_clear_tick120_x=endpoint))
  finally:C.memmove(addr,saved,len(saved));assert libc.mprotect(start,span,1)==0
 print(json.dumps(dict(suite='air-speed',passed=True,independent_cases=len(cases),invalid_cases=len(invalid),maximum_math_error=error,assembled_negative_mismatches=negatives,ABI_stack_guarded_outputs=True,reversal_traces=reversals,public_paired_flights=flights,predictor_speed_control=preview,library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),scope='Bounded longitudinal airborne5..7 actuator and physical final braking/go-around acceleration. Both-role/side initial7m/tick staged flights, no live body/HP/ammo/fuel/clock renewal; bomber default cruise remains5. Not low-speed landing, lift/drag/stall/ground contact or finite service acceptance.')))
