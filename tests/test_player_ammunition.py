#!/usr/bin/env python3
"""Actual finite player weapon/stock outcomes; explicit static fault fixtures.
Every moving/shooting scene writes only its startup declaration, then real APIs.
"""
import ctypes as C,hashlib,json,math,pathlib,sys
libpath=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(libpath));l.sim_checksum.restype=C.c_uint64
l.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
class Player(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint)for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
class Stock(C.Structure):
 _fields_=[(n,C.c_uint)for n in ('generation','reserve','spent','received','last_tick','initial','reserved0','reserved1')]
pool=(Player*4).in_dll(l,'sim_players');actors=(Entity*32768).in_dll(l,'sim_entities');stock=(Stock*4).in_dll(l,'player_ammunition');receipts=C.c_uint64.in_dll(l,'player_ammunition_receipts');depots=(C.c_uint*48).in_dll(l,'depot_ammunition');sites=(C.c_uint*96).in_dll(l,'sim_sites');vehicle=(C.c_int*4).in_dll(l,'sim_player_vehicle');worldtick=C.c_uint.in_dll(l,'sim_tick_count')
def scene(x=3900,z=2000):
 assert l.sim_init(2,73)==0 and l.player_join(0,1)==0
 for side in (0,1):
  for front in range(3):assert l.sim_order(side,front,1)==0
 actors[0].x,actors[0].z=7000,7000;actors[1].x,actors[1].z=7000,6500
 p=pool[0];p.x,p.z=x,z;p.y=l.terrain_height(x,z)+1.8
 assert p.ammo==30 and stock[0].reserve==90 and stock[0].generation==p.generation==1 and stock[0].initial==120
 return p
def input(flags=0,dx=0,dz=0):assert l.player_input(0,flags,dx,dz,0.,0.)==0
def invariant(check_query=False):
 p=pool[0];s=stock[0];assert p.ammo+s.reserve+s.spent==120+s.received
 assert p.ammo<=30 and s.reserve<=90 and s.received<=144000 and s.reserved0==s.reserved1==0
 assert sum(depots[i*4+1]for i in range(12))==receipts.value
 if check_query:
  before=l.sim_checksum();q=l.player_ammunition_reserve(0);assert q==s.reserve and l.sim_checksum()==before
p=scene();samples=[]
for magazine in range(4):
 input(1)
 for _ in range(140):
  l.sim_tick();invariant()
  if p.ammo==0:break
 else:raise AssertionError('actual rifle did not consume magazine')
 assert p.shots==(magazine+1)*30 and stock[0].spent==p.shots
 if magazine<3:
  input(2);l.sim_tick();assert p.reload==60
  input()
  for _ in range(60):l.sim_tick();invariant()
  assert p.ammo==30 and p.reload==0 and stock[0].reserve==60-30*magazine
 samples.append([worldtick.value,p.ammo,stock[0].reserve,p.shots])
assert p.shots==120 and p.ammo==stock[0].reserve==0 and receipts.value==0
input(3)
for _ in range(180):l.sim_tick();invariant();assert p.shots==120 and p.ammo==p.reload==0
empty={'actual_shots':p.shots,'spent':stock[0].spent,'empty_request_ticks':180,'magazine_samples':samples}
p=scene();input(1)
for _ in range(5):l.sim_tick()
assert p.shots==2 and p.ammo==28;input(2);l.sim_tick();assert p.reload==60;input()
for _ in range(59):l.sim_tick();invariant()
assert p.reload==1 and p.ammo==28 and stock[0].reserve==90
l.sim_tick();invariant();assert p.ammo==30 and stock[0].reserve==88 and stock[0].spent==2
partial={'unchanged_magazine_during_animation':28,'final_magazine':30,'final_reserve':88,'actual_spent':2}
p=scene(1080,3900);stock[0].reserve=0;stock[0].spent=90;input(0,-1,0);previous=(p.x,p.z);first=None
for tick in range(1,181):
 l.sim_tick();invariant();current=(p.x,p.z);assert math.dist(previous,current)<=.1668;previous=current
 if stock[0].received and first is None:first=tick;assert math.dist(current,(1000,3900))<=60 and stock[0].received==90
assert first==150 and depots[16:19]==[11910,90,12000] and p.ammo==30 and p.hp==100,(first,depots[16:19],p.ammo,p.hp,p.x)
walk={'initial_distance_m':80,'actual_credit_tick':first,'final_position':[p.x,p.z],'received':90,'depot_remaining':11910,'magazine_unchanged':30}
# Actual new join/body resets its own declaration, retaining previous depot debits.
old_generation=p.generation;assert l.player_leave(0)==0;frozen=bytes(stock);l.sim_tick();assert bytes(stock)==frozen
assert l.player_join(0,2)==0 and p.generation==old_generation+1
assert p.ammo==30 and stock[0].reserve==90 and stock[0].spent==stock[0].received==0 and receipts.value==90 and depots[17]==90
body={'fresh_join_generation':p.generation,'fresh_body_equipment':120,'retained_lifetime_receipts':90,'retained_depot_issued':90}
# Genuine death and safe deployment equip only the actual new body. Credits
# from the previous body remain in the lifetime depot ledger.
p=scene(1020,3900);stock[0].reserve=0;stock[0].spent=90
actors[1].x,actors[1].z=1100,3900
l.sim_tick();assert l.player_ammunition_resupply(0)==90
dead=None;frozen=None
for _ in range(400):
 l.sim_tick()
 if p.hp==0 and dead is None:dead=worldtick.value;frozen=bytes(stock)
 if dead and p.generation==1:assert bytes(stock)==frozen and receipts.value==90
 if p.generation==2:break
else:raise AssertionError('actual death/deployment did not publish a new body')
assert dead and p.hp==100 and p.ammo==30 and stock[0].generation==2 and stock[0].reserve==90
assert stock[0].spent==stock[0].received==0 and receipts.value==depots[17]==90
body['actual_death_tick']=dead;body['actual_safe_deploy_tick']=worldtick.value;body['dead_stock_frozen']=True
# Destroyed command root and genuinely cut graph prevent equipment on repeated
# failed deployment attempts; no clock/connectivity repair writes after setup.
assert l.sim_init(2,73)==0
sites[6]=0
for i in range(12):sites[i*8+5]=0
assert l.player_join(0,1)==0 and pool[0].hp==0
for _ in range(120):l.sim_tick();assert pool[0].hp==0 and bytes(stock)==bytes(128) and receipts.value==0
body['failed_spawn_actual_ticks_without_equipment']=120
# Exhaust the actual finite store through genuine public input/ticks. No stock,
# pose, health or clock writes after this fully equipped startup declaration.
p=scene(1020,3900)
for _ in range(100000):
 s=stock[0]
 flags=0 if p.reload else (1 if p.ammo else (2 if s.reserve else 0))
 input(flags);l.sim_tick();invariant(worldtick.value%120==0);assert p.hp==100 and p.generation==1
 if depots[16]==0 and p.ammo==s.reserve==p.reload==0:break
else:raise AssertionError('finite store depletion did not complete')
assert p.shots==stock[0].spent==12120 and stock[0].received==receipts.value==depots[17]==12000
input(3)
for _ in range(180):l.sim_tick();invariant();assert p.shots==12120 and p.ammo==p.reload==0 and depots[16]==0
exhaustion={'actual_rifle_shots':p.shots,'depot_received':stock[0].received,'remaining':depots[16],'spent':stock[0].spent,'ticks':worldtick.value,'empty_requests':180,'original_count':2}
# Separate static API/corruption fixtures. Every failure preserves all hashed
# authority, including invalid/dead/boarding/visibility/stock cases.
def fixture():
 p=scene(1020,3900);l.sim_tick();stock[0].reserve=60;stock[0].spent=30;return p
p=fixture();assert l.player_ammunition_resupply(0)==30;invariant();assert l.player_ammunition_resupply(0)==0
assert stock[0].reserve==90 and stock[0].received==30 and p.ammo==30
fields=[('generation',2),('reserve',91),('spent',31),('received',1),('initial',0),('reserved0',1),('reserved1',1)]
rejected=[]
for field,value in fields:
 p=fixture();setattr(stock[0],field,value)
 for fn in (l.player_ammunition_reserve,l.player_ammunition_fire,l.player_ammunition_reload_finish,l.player_ammunition_resupply):
  before=l.sim_checksum();assert fn(0)==-1 and l.sim_checksum()==before
 rejected.append(field)
for field,value in [('ammo',31),('reload',61),('hp',0),('hp',101),('connected',0),('front',3),('generation',0)]:
 p=fixture();setattr(p,field,value);before=l.sim_checksum();assert l.player_ammunition_resupply(0)==-1 and l.sim_checksum()==before;rejected.append('player_'+field)
for field,value in [('x',math.nan),('z',math.inf),('x',-1),('z',8001),('y',math.nan),('y',1001)]:
 p=fixture();setattr(p,field,value);before=l.sim_checksum();assert l.player_ammunition_resupply(0)==-1 and l.sim_checksum()==before;rejected.append('pose_'+field)
for index,value,label in [(34,1,'enemy'),(36,2,'role'),(37,0,'cut'),(38,0,'destroyed'),(39,4,'contested')]:
 p=fixture();sites[index]=value;before=l.sim_checksum();assert l.player_ammunition_resupply(0)==0 and l.sim_checksum()==before;rejected.append(label)
p=fixture();vehicle[0]=0;before=l.sim_checksum();assert l.player_ammunition_resupply(0)==0 and l.sim_checksum()==before
p=fixture();p.x,p.z=3970,1300;p.y=l.terrain_height(p.x,p.z)+1.8
C.c_float.from_buffer(sites,4*32).value=4030.;C.c_float.from_buffer(sites,4*32+4).value=1300.
before=l.sim_checksum();assert l.player_ammunition_resupply(0)==0 and l.sim_checksum()==before
for ident in (4,0xffffffff):
 before=l.sim_checksum();assert l.player_ammunition_resupply(ident)==-1 and l.sim_checksum()==before
p=fixture();stock[0].reserve=0;stock[0].spent=120;p.ammo=0;before=l.sim_checksum();assert l.player_ammunition_equip(0)==0 and l.sim_checksum()==before
before=l.sim_checksum();stock[3].reserved1=1;assert l.sim_checksum()!=before;stock[3].reserved1=0
before=l.sim_checksum();receipts.value+=1;assert l.sim_checksum()!=before
print(json.dumps({'suite':'finite-player-ammunition','passed':True,'actual_depletion':empty,'partial_reload':partial,'physical_depot_walk':walk,'fresh_body_and_retired_receipts':body,'actual_finite_store_exhaustion':exhaustion,'rejected_static_cases':rejected,'same_body_never_reequips':True,'inactive_and_lifetime_state_hashed':True,'library_sha256':hashlib.sha256(libpath.read_bytes()).hexdigest(),'limits':['Sparse actual public rifle input/ticks; startup stock declarations are distinct from no-renewal depletion/exhaustion. Static API faults are separate.','Own authority only: no network/HUD/broader weapon or vehicle/air rearm acceptance.']}))
