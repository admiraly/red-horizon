#!/usr/bin/env python3
"""Actual public world ticks plus separate atomic resupply edge fixtures."""
import ctypes as C,hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(p));l.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
class Weapon(C.Structure):
 _fields_=[(n,C.c_uint)for n in ('generation','magazine','reserve','reload','shots','empty_tick','received','last_supply')]
entities=(Entity*32768).in_dll(l,'sim_entities');weapons=(Weapon*32768).in_dll(l,'infantry_weapons');sites=(C.c_uint*96).in_dll(l,'sim_sites');depots=(C.c_uint*48).in_dll(l,'depot_ammunition');shells=(C.c_uint*32768).in_dll(l,'sim_shell_ammo');alive=(C.c_uint*2).in_dll(l,'sim_alive');count=C.c_uint.in_dll(l,'sim_count');tick=C.c_uint.in_dll(l,'sim_tick_count')
l.infantry_weapon_resupply.argtypes=[C.c_uint];l.infantry_weapon_resupply.restype=C.c_int

def setup(n=32):
 assert l.sim_init(n,73)==0
 for e in entities[:n]:e.hp=0
 for side in (0,1):
  for front in range(3):assert l.sim_order(side,front,1)==0
 alive[0]=alive[1]=0

def actor(i,x=1020.,z=3900.,side=0,front=1):
 entities[i]=Entity(x,z,100,side,0,front,0xffffffff,11)
 alive[side]+=1

def equip():assert l.infantry_weapon_init()==0

def low(i):
 w=weapons[i];w.magazine=30;w.reserve=0;w.shots=90

def conservation(i):
 w=weapons[i];assert w.magazine+w.reserve+w.shots==120+w.received
 assert w.magazine<=30 and w.reserve<=90 and w.reload<=60
 assert not w.reload or not w.magazine

def physical():
 setup();actor(0);entities[16]=Entity(1240.,3900.,400,1,1,1,0xffffffff,11);alive[1]=1;shells[16]=0;equip()
 credits=[];previous=0;shots=[]
 for t in range(1,1401):
  oldshots=weapons[0].shots;oldhp=entities[16].hp;l.sim_tick();w=weapons[0];conservation(0)
  assert (entities[0].x,entities[0].z,entities[0].hp,entities[0].generation)==(1020.,3900.,100,11)
  assert depots[16]+depots[17]==12000 and depots[17]==w.received
  if w.received!=previous:
   assert w.last_supply==t and (t+0)%30==0
   credits.append([t,w.received-previous,w.magazine,w.reserve,w.reload]);previous=w.received
  if w.shots!=oldshots:assert oldhp-entities[16].hp==min(3,oldhp),(t,oldhp,entities[16].hp,oldshots,w.shots);shots.append(t)
  else:assert oldhp==entities[16].hp
 assert credits[0]==[300,30,30,90,0],credits
 assert weapons[0].shots==134 and entities[16].hp==0 and weapons[0].received>0
 return {'credits':credits,'actual_shots':len(shots),'last_shot':shots[-1],'target_hp':entities[16].hp,'depot_remaining':depots[16],'checksum':f'{l.sim_checksum():016x}'}
combat=physical();assert physical()==combat
# Actual occupancy restores the command root after20 capture evaluations. No
# live position/health/stock/clock changes after independent initial fixture.
setup();actor(0);actor(16,1000.,1300.,front=0);equip();low(0)
sites[2]=1;sites[3]=10;sites[4*8+5]=0
restore=[]
for t in range(1,631):
 l.sim_tick();conservation(0)
 if t<600:assert weapons[0].received==0 and depots[16]==12000 and sites[4*8+5]==0
 elif not restore:restore=[t,sites[2],sites[4*8+5],weapons[0].received,depots[16]]
assert restore==[600,0,1,90,11910],restore
# Genuine contested occupation blocks current operation-record supply at the
# same evaluation tick; both exhausted actors remain physically alive.
setup();actor(0);actor(16,1040.,3900.,side=1);equip()
for i in (0,16):weapons[i].magazine=0;weapons[i].reserve=0;weapons[i].shots=120
for _ in range(120):l.sim_tick()
assert sites[4*8+7]&4 and depots[16]==12000 and weapons[0].received==weapons[16].received==0
assert entities[0].hp==entities[16].hp==100
# Independent initial store contention fixture; each request is an actual
# depot debit+actor credit, not a live replenishment/renewal of combat fixtures.
setup(256)
for i in range(135):actor(i,1000.+(i%15)*2,3880.+(i//15)*2)
equip()
for i in range(135):low(i)
l.sim_tick() # birth/state valid and clock naturally positive; records are ready
initial_issued=depots[17];initial_received=sum(weapons[i].received for i in range(135));assert initial_issued==initial_received
for i in range(135):l.infantry_weapon_resupply(i);conservation(i)
assert depots[16]==0 and depots[17]==12000 and sum(weapons[i].received for i in range(135))==12000
assert sorted(weapons[i].received for i in range(135))==[0,30]+[90]*133
before=l.sim_checksum();assert l.infantry_weapon_resupply(134)==0 and l.sim_checksum()==before
# Capture retains exhausted physical-site stock. Causal occupancy capture in a
# fresh exhausted-site fixture, with no further observer mutation.
setup();actor(0,1020.,3900.,side=1);equip();low(0);depots[16]=0;depots[17]=12000
for _ in range(600):l.sim_tick();conservation(0)
assert sites[4*8+2]==1 and depots[16]==0 and depots[17]==12000 and weapons[0].received==0
# Direct transaction boundary checks, separately declared before observation.
def api_fixture(x=1020.,z=3900.):
 setup();actor(0,x,z);equip();low(0);l.sim_tick()

def unchanged(expected):
 before=l.sim_checksum();r=l.infantry_weapon_resupply(0);assert r==expected and l.sim_checksum()==before,(r,expected)
blocked=[]
for name,offset,value in [('cut',5,0),('malformed_connectivity',5,2),('destroyed',6,0),('contested',7,4),('foreign',2,1),('wrong_role',4,2)]:
 api_fixture();sites[4*8+offset]=value;unchanged(0);blocked.append(name)
api_fixture(x=1060.01);unchanged(0);blocked.append('outside60m')
api_fixture(x=1060.);assert l.infantry_weapon_resupply(0)==90;conservation(0)
# Same geometry and stores accept the other own-side label without a refill.
api_fixture();entities[0].side=1;sites[4*8+2]=1;assert l.infantry_weapon_resupply(0)==90;conservation(0)
assert l.infantry_weapon_resupply(0)==0
api_fixture(x=3970.,z=1300.)
# Reposition a declared source site before the first queried resupply, never an
# actor/combat renewal. Actual authored wall lies between3970 and4030.
C.c_float.from_buffer(sites,4*32).value=4030.;C.c_float.from_buffer(sites,4*32+4).value=1300.;unchanged(0);blocked.append('opaque_wall')
for x in (float('nan'),float('inf'),-1.,8001.):api_fixture(x=x);unchanged(-1)
for field,value in [('reserve',91),('received',144001),('received',1),('reload',1),('generation',12)]:
 api_fixture();setattr(weapons[0],field,value);unchanged(-1)
api_fixture();entities[0].hp=0;unchanged(-1)
for ident in (32,32768,0xffffffff):
 api_fixture();h=l.sim_checksum();assert l.infantry_weapon_resupply(ident)==-1 and l.sim_checksum()==h
api_fixture();before=bytes(weapons)+bytes(depots);count.value=32769
assert l.infantry_weapon_resupply_tick()==-1 and bytes(weapons)+bytes(depots)==before;count.value=32
print(json.dumps({'suite':'infantry-finite-depot-resupply','passed':True,'physical_world_combat':combat,'actual_route_restoration':restore,'actual_contested_occupation_blocks':True,'actual_capture_exhausted_store_no_refill':True,'contention_total_rounds':12000,'partial_last_transfer':30,'blocked_sources':blocked,'malformed_calls_atomic':True,'same_build_replay':True,'library_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'limits':['Declared independent initial fixtures; physical combat/route/capture traces have no live pose/HP/stock/clock renewal. Direct API/corruption fixtures are separate.','Army rifle only; no shortage UI, supply-aware return routes, player/vehicle/air rearm, stock replication, convoy/production or full operation/hardware acceptance.']}))
