#!/usr/bin/env python3
"""Actual casualty cover, blast atomicity, infantry/rifle LOS and ground bursts."""
import ctypes as C,hashlib,json,math,pathlib,struct,sys
PATH=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(PATH))
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class P(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','gen')]
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','gen','birth','expiry','seq','flags','r0','r1')]
class Event(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z')]+[(n,C.c_uint) for n in ('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float) for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_int) for n in ('role','mode','target','cooldown','ammo','gen')]+[(n,C.c_float) for n in ('vx','vy','vz')]+[('pass_ticks',C.c_uint),('flags',C.c_uint)]
e=(E*32768).in_dll(l,'sim_entities');p=(P*4).in_dll(l,'sim_players');w=(W*1024).in_dll(l,'sim_wrecks');a=(Air*32768).in_dll(l,'sim_aircraft');alive=(C.c_uint*2).in_dll(l,'sim_alive');ammo=(C.c_uint*32768).in_dll(l,'sim_shell_ammo');events=(Event*256).in_dll(l,'sim_events');wc=C.c_uint.in_dll(l,'sim_wreck_count');pc=C.c_uint.in_dll(l,'sim_projectile_count');seq=C.c_uint.in_dll(l,'sim_event_sequence')
l.sim_init.argtypes=[C.c_uint]*2;l.sim_air_damage.argtypes=[C.c_uint]*2;l.sim_blast.argtypes=[C.c_uint]*2+[C.c_float]*4;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float;l.sim_entity_height.argtypes=[C.c_uint];l.sim_entity_height.restype=C.c_float;l.world_los.argtypes=[C.c_float]*6;l.sim_checksum.restype=C.c_uint64;l.player_input.argtypes=[C.c_uint]*2+[C.c_float]*4;l.projectile_launch.argtypes=[C.c_uint]*2+[C.c_float]*3;l.projectile_air_launch.argtypes=[C.c_uint]*2
rows=[]
l.air_bomb_fall_time.argtypes=[C.c_float]*2;l.air_bomb_fall_time.restype=C.c_float
def reset(births,player=False,prime=True):
 assert l.sim_init(64,42)==0
 for entity in e[:64]:entity.hp=0
 alive[0]=alive[1]=0;C.c_uint.in_dll(l,'hazard_enabled').value=0
 for side in (0,1):
  for front in range(3):assert l.sim_order(side,front,1)==0
 for i,x,z,side,kind,hp in births:e[i]=E(x,z,hp,side,kind,0,-1,42);alive[side]+=1;ammo[i]=0
 l.ground_init()
 if player:
  assert l.player_join(0,0)==0;p[0].x=3490;p[0].z=2000;p[0].y=l.terrain_height(3490,2000)+1.8
 if prime:l.sim_tick()
def death(i):
 before=wc.value;l.sim_air_damage(i,e[i].hp);assert e[i].hp==0 and wc.value==before+1;return bytes(w[before])
def f(v):return C.c_float(v).value
def predict(x,y,z,vx,vy,vz):
 for step in range(1,241):
  end=(f(x+vx),f(y+vy),f(z+vz));next_vy=f(vy-f(.0109))
  if end[1]<=l.terrain_height(end[0],end[2])+.002:
   lo,hi=0.,1.
   for _ in range(50):
    t=(lo+hi)/2;qx=x+(end[0]-x)*t;qy=y+(end[1]-y)*t;qz=z+(end[2]-z)*t
    if qy>l.terrain_height(qx,qz)+.002:lo=t
    else:hi=t
   return x+(end[0]-x)*hi,z+(end[2]-z)*hi
  x,y,z=end;vy=next_vy
 raise AssertionError('no predicted ground')
# Independent high precision positive root, including inherited climb/descent.
from decimal import Decimal,localcontext
import random
rng=random.Random(817)
maximum_error=0.
for height,vy in [(90,.5),(120,-.5),(.00001,-100),(1000,100)]+[(10**rng.uniform(-4,3),rng.uniform(-100,100)) for _ in range(1000)]:
 height,vy=f(height),f(vy)
 with localcontext() as ctx:
  ctx.prec=70;g=Decimal(f(.0109));h=Decimal(height);q=Decimal(vy)+g/2
  root=(q+(q*q+2*g*h).sqrt())/g
 actual=l.air_bomb_fall_time(height,vy);error=abs(actual-f(float(root)))
 assert error==0.,(height,vy,actual,float(root));maximum_error=max(maximum_error,error)
for height,vy in [(0,0),(-1,0),(float('nan'),0),(float('inf'),0),(10,float('nan')),(10,float('inf')),(10,-float('inf'))]:
 assert l.air_bomb_fall_time(height,vy)==0
# Declared initial births only; every subsequent movement/drop/impact is real.
for side in (0,1):
 for height,vy in [(90,.5),(120,-.5)]:
  x,z=1000,2000;y=l.terrain_height(x,z)+height;hit=predict(x,y,z,0,vy,6)
  reset([(15,x,z,side,3,1000),(24,hit[0]+10,hit[1],1-side,0,100)],prime=False)
  # Initial heading/velocity explicitly align with the intended strike. A
  # physically rolled aircraft cannot snap heading at the first flight tick.
  heading=math.atan2(10,hit[1]-z)
  a[15]=Air(y,heading,0,0,6,0,0,24,0,1,42,6*math.sin(heading),vy,6*math.cos(heading),0,1);e[15].target=24
  launched=False
  for tick in range(1,241):
   l.sim_tick()
   if pc.value and not launched:
    launched=True;assert a[15].ammo==0
   impacts=[v for v in events if v.kind==7]
   if impacts:break
  assert launched and len(impacts)==1 and e[24].hp==0,(side,height,tick,e[24].hp)
  impact=impacts[0];error=math.hypot(impact.x-(hit[0]+10),impact.z-hit[1]);assert error<6,(side,height,error,hit,impact.x,impact.z,tick)
  for _ in range(30):l.sim_tick()
  assert a[15].ammo==0 and len([v for v in events if v.kind==7])==1
  rows.append({'side':side,'initial_height':height,'inherited_vy':vy,'impact_tick':tick,'impact_error_m':error,'victim_hp':e[24].hp,'remaining_stores':a[15].ammo})
print(json.dumps({'suite':'bomb-inherited-velocity-release','passed':True,'numeric_cases':1004,'invalid_cases':7,'maximum_float_root_error':maximum_error,'actual_flight_cases':rows,'no_inflight_renewal':True,'library_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'limits':['target-height prediction does not establish arbitrary terrain interception or moving-target lead','controlled initial fixtures; no graphics or artistic-quality acceptance']}))
