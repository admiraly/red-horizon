#!/usr/bin/env python3
"""Finite production bomber FSM releases/falls/impacts beside a human."""
import ctypes as C,hashlib,json,math,pathlib,struct,sys
source=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(source));l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
class Player(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint)for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in ('role','mode','target','cooldown','ammo','generation')]+[(n,C.c_float)for n in ('vx','vy','vz')]+[(n,C.c_uint)for n in ('pass_ticks','flags')]
e=(Entity*32768).in_dll(l,'sim_entities');p=(Player*4).in_dll(l,'sim_players');a=(Air*32768).in_dll(l,'sim_aircraft');alive=(C.c_uint*2).in_dll(l,'sim_alive');events=(C.c_ubyte*(256*32)).in_dll(l,'sim_events');seq=C.c_uint.in_dll(l,'sim_event_sequence')
assert l.sim_init(32,47)==0 and l.player_join(0,1)==0
for i in range(32):e[i].hp=0
e[0].x,e[0].z,e[0].hp,e[0].side,e[0].front=2000.,3900.,100,0,1
e[15].x,e[15].z,e[15].hp,e[15].side,e[15].front=2000.,3000.,200,1,0
alive[:]=[1,1]
p[0].x,p[0].z=2005.,3900.;p[0].y=l.terrain_height(p[0].x,p[0].z)+1.8
assert l.sim_order(0,1,1)==l.sim_order(1,0,1)==0
# Genuine first world tick equips the real aircraft body. Declare its coherent
# startup pose/velocity once at tick1; no HP/stock/clock writes or later renewal.
l.sim_tick();assert e[15].kind==3 and a[15].role==0 and a[15].ammo==8
e[15].x,e[15].z=2000.,3000.
a[15].y=l.terrain_height(2000.,3900.)+120.;a[15].heading=a[15].pitch=a[15].bank=0.;a[15].speed=6.;a[15].vx=a[15].vy=0.;a[15].vz=6.;a[15].mode=0;a[15].target=0xffffffff
prior=0;launch=None;impact=None;trace=[]
for tick in range(1,1201):
 l.sim_tick()
 for number in range(prior+1,seq.value+1):
  row=struct.unpack_from('<3f3IfI',bytes(events),(number&255)*32)
  if row[3]==6 and row[4]==1 and launch is None:launch=(tick,row,a[15].ammo)
  if row[3]==7 and row[4]==1:impact=(tick,row);break
 prior=seq.value
 if tick%30==0:trace.append([tick,e[15].x,e[15].z,a[15].y,a[15].bank,a[15].mode,a[15].ammo,p[0].hp,p[0].generation])
 if impact:break
assert launch and impact,(launch,impact,trace)
tick,row=impact;distance=math.sqrt((row[0]-p[0].x)**2+(row[1]-p[0].y)**2+(row[2]-p[0].z)**2)
result={'suite':'player-physical-production-bomb','startup_pose_fixture_tick':1,'launch':launch,'impact':impact,'finite_bombs_remaining':a[15].ammo,'player_hp':p[0].hp,'player_generation':p[0].generation,'player_eye_distance_m':distance,'actual_blast_radius_m':row[6],'trace':trace,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['Sparse coherent initial bomber/target/human positions only; actual production aircraft FSM/store debit/release, gravity flight/world contact afterward.','No live pose/HP/stock/clock/projectile renewal; no manual launch.','Full-scale/network/graphics/hardware and human-target AI designation are separate.']}
assert launch[2]==7 and distance<36 and p[0].generation==1,result
if '--baseline' in sys.argv:assert p[0].hp>0,result;result['observed_missing_player_bomb_blast']=True
else:assert p[0].hp==0 and 0<p[0].respawn<=30,result;result['passed']=True
print(json.dumps(result))
