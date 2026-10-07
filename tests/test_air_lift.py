#!/usr/bin/env python3
"""Independent lift-deficit oracle, real ABI, and causal physical flights."""
import ctypes as C,hashlib,json,math,os,pathlib,random,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[1];N=os.environ['RED_HORIZON_NASM'];f32=lambda x:C.c_float(x).value
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in ('cooldown','ammo','gen')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
with tempfile.TemporaryDirectory(prefix='rh-air-lift-')as d:
 td=pathlib.Path(d);objects=[]
 for src in sorted(p for directory in ('sim','nav','ai','game')for p in (R/'src'/directory).glob('*.asm'))+[R/'tests/probe_air_lift.asm',R/'tests/terrain_probe.asm']:
  obj=td/(src.name+'.o');subprocess.run([N,'-f','elf64','-I',str(R)+'/',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
 source=(R/'src/ai/air_lift.asm').read_text()
 def library(name,text):
  objs=objects
  if text!=source:
   asm=td/(name+'.asm');obj=td/(name+'.o');asm.write_text(text);subprocess.run([N,'-f','elf64','-I',str(R)+'/',str(asm),'-o',str(obj)],check=True,capture_output=True)
   objs=[obj if o.name=='air_lift.asm.o'else o for o in objects]
  so=td/(name+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(so),*map(str,objs),'-lm'],check=True,capture_output=True)
  l=C.CDLL(str(so));l.probe_air_lift.argtypes=[C.c_uint,*([C.c_float]*4),C.c_void_p,C.c_void_p];l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
  return l,so
 production,so=library('production',source)
 variants={name:library(name,text)[0]for name,text in [('omitted_deficit',source.replace('air_lift_step:\n','air_lift_step:\n jmp air_vertical_step wrt ..plt\n',1)),('wrong_gravity',source.replace(' subss xmm1,xmm2\n',' addss xmm1,xmm2\n',1))]}
 def sample(l,role,wanted,speed,old,bank):
  out=(C.c_float*5)(123,0,0,0,456);regs=(C.c_uint64*7)();rc=l.probe_air_lift(role,wanted,speed,old,bank,C.byref(out,4),regs)
  assert out[0]==123 and out[4]==456 and tuple(regs)==tuple(0x123401+i for i in range(6))+(0,)
  return rc,tuple(out)[1:4]
 rng=random.Random(852913)
 cases=[(role,w,s,v,b)for role in (0,1)for w in (-.5,0,.5)for s in (1,1.6,2.2,2.3,3,5,7)for v in (-.5,0,.5)for b in (0,.8,1.45)]
 cases += [(rng.randrange(2),rng.uniform(-.5,.5),rng.uniform(1,7),rng.uniform(-.5,.5),rng.uniform(-1.6,1.6))for _ in range(3000)]
 max_error=0.;mismatch={n:0 for n in variants}
 for role,wanted,speed,old,bank in cases:
  wanted,speed,old,bank=map(f32,(wanted,speed,old,bank));load=(speed/f32((2.2,2.3)[role]))**2*math.cos(bank)
  target=min(wanted,max(-.5,old-.0109*(1-load)))if load<1 else wanted
  accel=(.012,.024)[role];vy=old+max(-accel,min(accel,target-old));horizontal=math.sqrt(speed*speed-vy*vy);pitch=math.atan2(vy,horizontal);expected=(vy,horizontal,pitch)
  rc,out=sample(production,role,wanted,speed,old,bank);error=max(abs(a-b)for a,b in zip(out,expected));max_error=max(max_error,error)
  assert rc==0 and error<2e-6,(role,wanted,speed,old,bank,out,expected)
  assert abs(math.hypot(out[0],out[1])-speed)<1e-6 and abs(out[0]-old)<=accel+1e-7
  for n,l in variants.items():
   status,bad=sample(l,role,wanted,speed,old,bank);mismatch[n]+=status!=0 or max(abs(a-b)for a,b in zip(bad,expected))>=2e-6
 assert all(v>500 for v in mismatch.values()),mismatch
 invalid=[(2,0,3,0,0),(0xffffffff,0,3,0,0),(0,.501,3,0,0),(0,-.501,3,0,0),(0,0,.99,0,0),(0,0,7.01,0,0),(0,0,3,.501,0),(0,0,3,-.501,0),(0,0,3,0,1.601),(0,0,3,0,-1.601)]
 for index in range(1,5):
  for bad in (math.nan,math.inf,-math.inf):
   args=[0,0,3,0,0];args[index]=bad;invalid.append(tuple(args))
 for args in invalid:
  rc,out=sample(production,*args);assert rc==-1 and out==(0.,0.,0.),(args,rc,out)
 flights=[]
 for side in (0,1):
  for role,initial_bank in ((0,0.),(1,0.),(0,1.4),(1,1.4)):
   pair={}
   for label,l in [('production',production),('omitted_deficit',variants['omitted_deficit'])]:
    replays=[]
    for repeat in range(2):
     assert l.sim_init(64,714)==0;e=(Entity*32768).in_dll(l,'sim_entities');a=(Air*32768).in_dll(l,'sim_aircraft')
     for entity in e:entity.hp=0
     e[31]=Entity(4000,4000,200,side,3,1,-1,1);height=l.terrain_height(4000,4000)+(110,140)[role];a[31]=Air(height,-math.pi/2,0,initial_bank,1.6,role,0,-1,0,(8,180)[role],1,-1.6,0,0,0,1)
     rows=[];error=0.;minimum_vy=0.;minimum_y=height
     for tick in range(600):
      old=(e[31].x,a[31].y,e[31].z);speed=a[31].speed;old_vy=a[31].vy;old_bank=a[31].bank;l.sim_tick();air=a[31]
      assert e[31].hp==200 and air.gen==1 and air.ammo==(8,180)[role]
      error=max(error,abs(math.dist(old,(e[31].x,air.y,e[31].z))-air.speed),abs(math.sqrt(air.vx**2+air.vy**2+air.vz**2)-air.speed));assert error<.001,(side,role,label,tick,old,air.speed,air.vx,air.vy,air.vz,error)
      assert 1<=air.speed<=7 and -(.009002,.012002)[role]<=air.speed-speed<=(.006002,.010002)[role]
      assert abs(air.vy-old_vy)<=(.012002,.024002)[role] and abs(air.bank-old_bank)<=(.060002,.100002)[role]
      minimum_vy=min(minimum_vy,air.vy);minimum_y=min(minimum_y,air.y);rows.append((e[31].x,air.y,e[31].z,air.speed,air.vy,air.bank))
     replays.append(dict(first_vy=rows[0][4],first100_minimum_y=min(v[1]for v in rows[:100]),minimum_vy=minimum_vy,minimum_y=minimum_y,final_speed=a[31].speed,final_y=a[31].y,maximum_motion_error=error,hash=hex(l.sim_checksum()),trace_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest()))
    assert replays[0]==replays[1];pair[label]=replays[0]
   assert pair['production']['first_vy']<0 and pair['production']['final_speed']>3
   assert pair['production']['first100_minimum_y']<pair['omitted_deficit']['first100_minimum_y']-1,pair
   flights.append(dict(side=side,role=role,initial_bank=initial_bank,initial_speed=1.6,ticks=600,paired=pair))
 ground_contacts=[]
 for side in (0,1):
  for role in (0,1):
   pair={}
   for label,l in [('production',production),('omitted_deficit',variants['omitted_deficit'])]:
    assert l.sim_init(64,714)==0;e=(Entity*32768).in_dll(l,'sim_entities');a=(Air*32768).in_dll(l,'sim_aircraft')
    for entity in e:entity.hp=0
    height=l.terrain_height(3500,4000)+5.5
    e[31]=Entity(3500,4000,200,side,3,1,-1,1);a[31]=Air(height,-math.pi/2,0,0,1.6,role,0,-1,0,(8,180)[role],1,-1.6,0,0,0,1)
    death=None
    for tick in range(1,81):
     l.sim_tick()
     if not e[31].hp:death=tick;break
    pair[label]=dict(death_tick=death,hp=e[31].hp,ammo=a[31].ammo,generation=a[31].gen,flags=a[31].flags,y=a[31].y,hash=hex(l.sim_checksum()))
   assert pair['production']['death_tick'] is not None and pair['omitted_deficit']['hp']==200,pair
   ground_contacts.append(dict(side=side,role=role,initial_ground_clearance=5.5,initial_speed=1.6,paired=pair))
 print(json.dumps(dict(suite='air-lift',passed=True,independent_cases=len(cases),invalid_cases=len(invalid),maximum_error=max_error,negative_mismatches=mismatch,ABI_stack_output_canaries=True,public_vertical_and_roll_continuity=True,public_flights=flights,actual_stall_ground_contact=ground_contacts,library_sha256=hashlib.sha256(so.read_bytes()).hexdigest(),limits=['Practical speed/bank lift-deficit sink with existing response and terminal vertical-speed caps; no angle-of-attack, spin, touchdown or complete aerodynamic model.','One declared initial birth per replay; no later pose, health, stores, fuel or clock renewal. No graphics, UDP or performance acceptance.'])))
