#!/usr/bin/env python3
"""Independent production cannon direction/cone/atomic rejection observer.
Initial native fixtures only; actual flight/damage encounters use test_aircraft.
"""
import ctypes as C, hashlib, json, math, pathlib, struct, sys
lib=C.CDLL(sys.argv[1]);lib.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in('cooldown','ammo','generation')]+[(n,C.c_float)for n in('vx','vy','vz')]+[(n,C.c_uint)for n in('pass_ticks','flags')]
class Shell(C.Structure):
 _fields_=[(n,C.c_float)for n in('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint)for n in('source','generation','active','source_generation','reserved')]
e=(Entity*32768).in_dll(lib,'sim_entities');a=(Air*32768).in_dll(lib,'sim_aircraft');p=(Shell*512).in_dll(lib,'sim_projectiles');reports=[]
def setup(heading=0,vertical=0):
 assert lib.sim_init(64,7)==0
 for i in range(64):e[i].hp=0
 for i,side in ((31,0),(63,1)):
  e[i].x,e[i].z,e[i].hp,e[i].kind,e[i].side,e[i].generation=2000,2000,200,3,side,100+i
 lib.air_init();lib.air_tick();lib.projectile_init()
 a[31].heading=heading;a[31].pitch=math.atan2(vertical,7);a[31].speed=7
 a[31].vx=7*math.sin(heading);a[31].vy=vertical;a[31].vz=7*math.cos(heading)
 a[31].target=63;a[31].ammo=180;a[31].cooldown=0;a[31].pass_ticks=0;a[31].y=200
 a[63].y=200;a[63].role=1;a[63].vx=a[63].vy=a[63].vz=0
 e[31].x=e[31].z=2000
 v=(a[31].vx,a[31].vy,a[31].vz);length=math.sqrt(sum(x*x for x in v));unit=tuple(x/length for x in v)
 e[63].x=2000+unit[0]*250;e[63].z=2000+unit[2]*250;a[63].y=200+unit[1]*250
 return unit
for heading in (0,.7,-1.2,math.pi-0.01,-math.pi+0.01):
 for vertical in (-.5,0,.5):
  unit=setup(heading,vertical)
  before=lib.sim_checksum()
  if hasattr(lib,'projectile_air_gun_ready'):
   assert lib.projectile_air_gun_ready(31)==0
   assert lib.sim_checksum()==before,'predicate changed authority'
  assert lib.projectile_air_launch(31,4)==0
  shell=next(s for s in p if s.active);velocity=(shell.vx,shell.vy,shell.vz)
  error=max(abs(x-28*y)for x,y in zip(velocity,unit));assert error<5e-6,(heading,vertical,error,velocity,unit)
  assert abs(math.sqrt(sum(x*x for x in velocity))-28)<5e-6
  assert a[31].ammo==180,'producer consumed FSM-owned rounds'
  reports.append({'heading':heading,'vertical_flight_m_per_tick':vertical,'round_xyz':velocity,'maximum_velocity_error':error})
# Within-cone target altitude changes cannot steer an emitted round's vertical axis.
for height in (190,210,220):
 setup();a[63].y=height
 assert lib.projectile_air_launch(31,4)==0
 shell=next(s for s in p if s.active);assert (shell.vx,shell.vy,shell.vz)==(0,0,28),(height,shell.vy)
# Check both vertical and horizontal cone edges independently, including behind.
cone=math.acos(.985);rejected=0;accepted=0
for axis in ('horizontal','vertical'):
 for angle in (cone-.001,cone+.001,-cone+.001,-cone-.001,math.pi):
  setup();e[63].x=2000+250*math.sin(angle) if axis=='horizontal' else 2000
  e[63].z=2000+250*math.cos(angle);a[63].y=200+250*math.sin(angle) if axis=='vertical' else 200
  before=lib.sim_checksum();result=lib.projectile_air_launch(31,4)
  if abs(angle)<cone:assert result==0,(axis,angle,result);accepted+=1
  else:assert result==-1 and lib.sim_checksum()==before,(axis,angle,result);rejected+=1
# A crossing target outside the present-point cone is valid when its independently
# predicted intercept lies on the nose. The emitted round still stays forward.
crossing=[]
for velocity in ((7,0,0),(-7,0,0),(0,.5,7),(0,-.5,-7)):
 setup();t=250/28
 e[63].x=2000-velocity[0]*t;a[63].y=200-velocity[1]*t;e[63].z=2250-velocity[2]*t
 a[63].vx,a[63].vy,a[63].vz=velocity
 before=lib.sim_checksum();assert lib.projectile_air_gun_ready(31)==0 and lib.sim_checksum()==before
 assert lib.projectile_air_launch(31,4)==0
 shell=next(s for s in p if s.active);assert (shell.vx,shell.vy,shell.vz)==(0,0,28)
 crossing.append({'target_velocity_xyz':velocity,'expected_intercept_ticks':t})
# Malformed/lifecycle states must fail without a slot, event, drop or other write.
mutations=[('source_generation',lambda:setattr(a[31],'generation',999)),('target_generation',lambda:setattr(a[63],'generation',999)),('zero_generation',lambda:(setattr(e[63],'generation',0),setattr(a[63],'generation',0))),('target_inactive',lambda:setattr(a[63],'flags',0)),('target_dead',lambda:setattr(e[63],'hp',0)),('target_role',lambda:setattr(a[63],'role',2)),('friendly',lambda:setattr(e[63],'side',0)),('invalid_side',lambda:setattr(e[63],'side',3)),('invalid_target',lambda:setattr(a[31],'target',32768)),('empty',lambda:setattr(a[31],'ammo',0)),('corrupt_ammo',lambda:setattr(a[31],'ammo',0xffffffff)),('cooldown',lambda:setattr(a[31],'cooldown',1)),('zero_velocity',lambda:(setattr(a[31],'vx',0),setattr(a[31],'vy',0),setattr(a[31],'vz',0))),('overspeed',lambda:setattr(a[31],'vz',100)),('zero_speed',lambda:setattr(a[31],'speed',0)),('outside_map',lambda:setattr(e[63],'x',9000)),('overheight',lambda:setattr(a[63],'y',2000))]
for actor,field in ((31,'vx'),(31,'vy'),(31,'vz'),(31,'speed'),(31,'y'),(63,'y'),(63,'vx'),(63,'vy'),(63,'vz')):
 for value in (math.nan,math.inf,-math.inf):mutations.append((f'nonfinite_{actor}_{field}_{value}',lambda actor=actor,field=field,value=value:setattr(a[actor],field,value)))
for label,mutate in mutations:
 setup();mutate();before=lib.sim_checksum();assert lib.projectile_air_launch(31,4)==-1,label;assert lib.sim_checksum()==before,label
# Production public-tick dogfight: initial births only, then observe actual new
# pool generations against the emitting fighter's physical velocity each tick.
setup(math.pi/2);e[63].x=2450;e[63].z=2000;a[63].y=200
for i,heading in ((31,math.pi/2),(63,-math.pi/2)):
 a[i].heading=heading;a[i].speed=7;a[i].vx=7*math.sin(heading);a[i].vy=0;a[i].vz=7*math.cos(heading);a[i].ammo=180;a[i].cooldown=0;a[i].target=-1
for side in (0,1):
 for front in range(3):assert lib.sim_order(side,front,1)==0
seen=set();physical_births=0;physical_error=0.;remaining={i:180 for i in (31,63)}
for tick in range(1,121):
 lib.sim_tick()
 for i in remaining:
  assert a[i].ammo<=remaining[i];remaining[i]=a[i].ammo
 for shell in p:
  if not shell.active or shell.kind!=4 or (shell.source,shell.generation,C.addressof(shell)) in seen:continue
  identity=(shell.source,shell.generation,C.addressof(shell));seen.add(identity)
  # Previously retained rounds need not match a later turning source nose.
  if shell.ttl!=39:continue
  assert shell.source in remaining
  velocity=(a[shell.source].vx,a[shell.source].vy,a[shell.source].vz);length=math.sqrt(sum(x*x for x in velocity))
  error=max(abs(actual-28*flight/length) for actual,flight in zip((shell.vx,shell.vy,shell.vz),velocity))
  assert error<5e-6,(tick,shell.source,error);physical_error=max(physical_error,error);physical_births+=1
assert physical_births>0 and any(e[i].hp<200 for i in remaining)
physical={'ticks':120,'retained_actual_births':physical_births,'maximum_velocity_error':physical_error,'final_hp':{i:e[i].hp for i in remaining},'remaining_rounds':remaining,'no_live_pose_hp_ammo_clock_writes':True}
print(json.dumps({'suite':'air-gun-physical-nose','passed':True,'public_tick_dogfight':physical,'velocity_cases':reports,'target_altitude_invariance_cases':3,'cone_accepted_cases':accepted,'cone_rejected_cases':rejected,'crossing_intercepts':crossing,'atomic_invalid_cases':len(mutations),'library_sha256':hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(),'scope':'Native predicate/launcher fixtures plus sparse public-tick finite dogfight births and real damage; no graphics or whole-game flight realism claim.'}))
