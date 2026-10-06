#!/usr/bin/env python3
"""Initial fixtures drive real public ticks; no in-flight state renewal."""
import ctypes as C,json,math,pathlib,struct,sys
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()));lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.terrain_height.argtypes=[C.c_float,C.c_float];lib.terrain_height.restype=C.c_float;lib.sim_checksum.restype=C.c_uint64
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
e=(E*32768).in_dll(lib,'sim_entities');sites=(C.c_ubyte*384).in_dll(lib,'sim_sites');plans=(C.c_uint*(1536*32)).in_dll(lib,'company_plans');ammo=(C.c_uint*32768).in_dll(lib,'sim_shell_ammo');alive=(C.c_uint*2).in_dll(lib,'sim_alive')
reports=[]
def fixture(enemy_ammo=0):
 assert lib.sim_init(256,42)==0
 for a in e[:256]:a.hp=0
 alive[0]=alive[1]=0
 def unit(i,x,z,kind,side):
  a=e[i];a.x=x;a.z=z;a.hp=(100,400,220)[kind];a.side=side;a.kind=kind;a.front=0;a.target=-1;a.gen=1;alive[side]+=1
  if kind in (1,2):ammo[i]=enemy_ammo if side else 4
 unit(32,3510,2000,0,0)
 for k,i in enumerate(range(33,53)):unit(i,3310+(k%4)*3,1975+(k//4)*12,0,0)
 for i,x,z in [(53,3310,2045),(54,3310,1955)]:unit(i,x,z,1,0)
 for i,x,z in [(55,3290,2040),(56,3290,1960)]:unit(i,x,z,2,0)
 for k,i in enumerate(range(128,136)):unit(i,3720,1890+k*32,1,1)
 C.memmove(C.addressof(sites)+64,struct.pack('<2f',3700,2000),8)
 lib.ai_init();lib.ground_init()
 for front in range(3):assert lib.sim_order(1,front,1)==0
 return [(a.x,a.z,a.hp,a.gen) for a in e[:256]]
for run in range(2):
 initial=fixture();transitions=[];phase_before=-1;trace=[];maxstep=0;hold_steps=0;advance_start=None;minimum_ammo=8
 for tick in range(1,1201):
  old=[(e[i].x,e[i].z) for i in range(32,57)];lib.sim_tick()
  phase=plans[0]
  if phase!=phase_before:transitions.append({'tick':tick,'phase':phase,'reason':plans[19],'support_tick':plans[18],'ready':plans[9],'artillery_ready':plans[23]});phase_before=phase
  for i,(x,z) in zip(range(32,57),old):
   step=math.dist((x,z),(e[i].x,e[i].z));maxstep=max(maxstep,step);assert step<=.501
  if phase==2:
   hold_steps+=math.dist(old[8],(e[40].x,e[40].z))<.001
  if phase==3 and advance_start is None:advance_start=(tick,e[40].x,e[40].z)
  minimum_ammo=min(minimum_ammo,ammo[55]+ammo[56])
  if tick%30==0:trace.append((tick,phase,plans[18],e[40].x,e[40].z,ammo[55],ammo[56],lib.sim_checksum()))
 assert any(x['phase']==1 for x in transitions),transitions
 assert any(x['phase']==2 for x in transitions),transitions
 assert any(x['phase']==3 and x['support_tick']>0 for x in transitions),transitions
 assert hold_steps>0,(hold_steps,transitions)
 assert advance_start and e[40].x>advance_start[1]+30,(advance_start,e[40].x,transitions)
 assert minimum_ammo<8 and e[32].x>initial[32][0]
 reports.append({'transitions':transitions,'physical_preparation_hold_ticks':hold_steps,'physical_post_release_advance_metres':e[40].x-advance_start[1],'max_step':maxstep,'remaining_artillery_stores':ammo[55]+ammo[56],'enemy_survivors':sum(bool(e[i].hp) for i in range(128,136)),'trace':trace})
assert reports[0]==reports[1],'same-build company replay differs'
# Genuine opposing fire causes losses; the plan must withdraw without renewal.
initial=fixture();withdraw_at=None;withdraw_positions=None
for _ in range(100):lib.sim_tick()
assert plans[0]==1
lib.sim_blast.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
bx,bz=e[40].x,e[40].z
lib.sim_blast(1,100,bx,bz,25,lib.terrain_height(bx,bz)+2)
for tick in range(101,1201):
 lib.sim_tick()
 if plans[0]==4 and withdraw_at is None:
  withdraw_at=tick;withdraw_positions={i:(e[i].x,e[i].z) for i in range(32,57) if e[i].hp}
assert withdraw_at is not None and plans[19]==4,(withdraw_at,list(plans[:24]))
retreated=[i for i,(x,z) in withdraw_positions.items() if e[i].hp and e[i].x<x-5]
assert retreated,(withdraw_at,withdraw_positions)
assert sum(bool(e[i].hp) for i in range(32,57))<25,'no genuine own casualties'
loss={'genuine_guarded_blast_after_staging':True,'withdraw_tick':withdraw_at,'reason':plans[19],'surviving_actors_physically_retreating':retreated,'own_survivors':sum(bool(e[i].hp) for i in range(32,57))}
# An explicit front hold takes effect immediately, before the next planner update.
fixture()
for _ in range(100):lib.sim_tick()
assert plans[0]==1
assert lib.sim_order(0,0,1)==0
pose=(e[40].x,e[40].z)
for _ in range(35):lib.sim_tick()
assert pose==(e[40].x,e[40].z) and plans[0]==0
# Malformed public IDs/counts cannot mutate plans or manufacture a goal.
lib.company_goal.argtypes=[C.c_uint,C.c_float,C.c_float];lib.company_goal.restype=C.c_int
before=bytes(plans)
for ident in (256,32768,0xffffffff):lib.company_goal(ident,1000,2000);assert bytes(plans)==before
count=C.c_uint.in_dll(lib,'sim_count');saved=count.value;count.value=32769;lib.company_tick();assert bytes(plans)==before;count.value=saved
print(json.dumps({'loss_case':loss,'manual_override_immediate':True,'invalid_plan_preservation':True}))
print(json.dumps({'suite':'company-public-assault','passed':True,'reports':reports,'limits':['Ground staging/preparation/advance only; aircraft coordination, ownership UI and full-operation quality unproven.','Initial fixtures only; no in-flight pose, HP, store or clock renewal.']}))
