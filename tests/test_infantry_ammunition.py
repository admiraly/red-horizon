#!/usr/bin/env python3
"""Finite army magazines over real authoritative ticks; initial births only."""
import ctypes as C,hashlib,json,pathlib,struct,sys
p=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(p));l.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
class Weapon(C.Structure):
 _fields_=[(n,C.c_uint)for n in ('generation','magazine','reserve','reload','shots','empty_tick','reserved0','reserved1')]
entities=(Entity*32768).in_dll(l,'sim_entities');weapons=(Weapon*32768).in_dll(l,'infantry_weapons');ammo=(C.c_uint*32768).in_dll(l,'sim_shell_ammo')
alive=(C.c_uint*2).in_dll(l,'sim_alive');tick=C.c_uint.in_dll(l,'sim_tick_count');count=C.c_uint.in_dll(l,'sim_count')
assert C.sizeof(Weapon)==32

def setup(side=0,target_x=2200.,source_x=2000.,kind=1):
 assert l.sim_init(32,73)==0
 for e in entities[:32]:e.hp=0
 entities[0]=Entity(source_x,1300.,100,side,0,0,0xffffffff,11)
 entities[16]=Entity(target_x,1300.,400,1-side,kind,0,0xffffffff,11)
 alive[0]=alive[1]=1
 l.projectile_init();ammo[16]=0
 for faction in (0,1):
  for front in range(3):assert l.sim_order(faction,front,1)==0
 return (entities[0].x,entities[0].z,entities[0].generation)

def run(side=0):
 initial=setup(side);shot_ticks=[];reloads=[];trace=[];previous_shots=0;previous_magazine=30
 for t in range(1,1401):
  hp=entities[16].hp;l.sim_tick();w=weapons[0]
  assert (entities[0].x,entities[0].z,entities[0].generation)==initial
  assert w.magazine+w.reserve+w.shots==120,(t,tuple(getattr(w,n)for n,_ in w._fields_))
  assert w.magazine<=30 and w.reserve<=90 and w.reload<=60
  if w.shots!=previous_shots:
   assert w.shots==previous_shots+1 and hp-entities[16].hp==3
   shot_ticks.append(t)
  else:assert hp==entities[16].hp,'damage without one spent round'
  if previous_magazine==0 and w.magazine:reloads.append(t)
  if w.reload:assert w.magazine==0
  if t%60==0:trace.append((t,w.magazine,w.reserve,w.reload,w.shots,entities[16].hp,f'{l.sim_checksum():016x}'))
  previous_shots=w.shots;previous_magazine=w.magazine
 assert len(shot_ticks)==120 and entities[16].hp==40 and weapons[0].magazine==weapons[0].reserve==weapons[0].reload==0
 assert shot_ticks[:30]==list(range(8,241,8)),shot_ticks[:30]
 assert reloads==[300,596,892],reloads
 assert all(shot_ticks[i]-shot_ticks[i-1]==8 for i in range(1,120)if i%30)
 assert [shot_ticks[i]-shot_ticks[i-1]for i in (30,60,90)]==[64,64,64]
 assert weapons[0].empty_tick==shot_ticks[-1] and weapons[0].generation==11
 l.sim_tick();assert weapons[0].shots==120 and entities[16].hp==40
 return {'shot_ticks':shot_ticks,'reload_completion_ticks':reloads,'empty_tick':weapons[0].empty_tick,'target_hp':entities[16].hp,'trace':trace}
report=run();assert run()==report
swapped=run(1);assert swapped['shot_ticks']==report['shot_ticks'] and swapped['target_hp']==report['target_hp']
# Range, opacity, same side and no target all preserve rounds. Fixtures are
# declared before the first public tick, never renewed during observation.
exclusions=[]
for name,x,sx,friendly,dead in [('outside_range',2300.,2000.,False,False),('opaque_wall',4030.,3970.,False,False),('friendly',2200.,2000.,True,False),('dead_target',2200.,2000.,False,True)]:
 setup(target_x=x,source_x=sx)
 if friendly:entities[16].side=entities[0].side
 if dead:entities[16].hp=0
 for _ in range(400):l.sim_tick()
 assert weapons[0].magazine==30 and weapons[0].reserve==90 and weapons[0].shots==0 and weapons[0].reload==0,name
 exclusions.append(name)
# Legitimate equipment lifecycle: death freezes a pending reload; a separately
# declared birth resets exactly once for its new body generation.
setup();l.sim_tick();weapons[0].magazine=0;weapons[0].shots=30;weapons[0].reserve=90;weapons[0].reload=60;entities[0].hp=0
corpse=bytes(weapons[0])
for _ in range(90):l.sim_tick()
assert bytes(weapons[0])==corpse
 # Avoid changing a live encounter to prove birth: reset world then declare
 # reused ID/generation and only afterward begin its independent trace.
setup();entities[0].generation=22
for _ in range(4):l.sim_tick()
assert weapons[0].generation==22 and weapons[0].magazine==30 and weapons[0].reserve==90 and weapons[0].shots==0
# Same-generation side/front or company changes must not replenish stocks.
setup();l.sim_tick();weapons[0].magazine=29;weapons[0].shots=1;entities[0].front=2;entities[0].side=1
l.infantry_weapon_tick();assert weapons[0].magazine==29 and weapons[0].shots==1
# Invalid caller/count and corrupt stock records are atomic, not self-repairing.
l.infantry_weapon_fire.argtypes=[C.c_uint]
setup();l.sim_tick()
for ident in (16,32,32768,0xffffffff):
 before=l.sim_checksum();assert l.infantry_weapon_fire(ident)==-1 and l.sim_checksum()==before
for field,value in [('magazine',31),('reserve',91),('reload',61),('reload',1),('shots',121),('reserve',89)]:
 setup();l.sim_tick();setattr(weapons[0],field,value);before=bytes(weapons[0]);h=l.sim_checksum()
 assert l.infantry_weapon_fire(0)==-1 and bytes(weapons[0])==before and l.sim_checksum()==h
 l.infantry_weapon_tick();assert bytes(weapons[0])==before
setup();l.sim_tick();before=bytes(weapons);saved=count.value;count.value=32769
assert l.infantry_weapon_tick()==-1 and l.infantry_weapon_init()==-1 and bytes(weapons)==before;count.value=saved
print(json.dumps({'suite':'infantry-finite-ammunition','passed':True,'physical_combat':report,'labels_only_same_shots_and_damage':True,
                  'no_shot_no_spending':exclusions,'dead_reload_frozen':True,'declared_generation_birth_once':True,'side_front_change_no_refill':True,
                  'corrupt_stock_and_invalid_calls_atomic':True,'conserved_initial_rounds':120,'library_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                  'limits':['Declared independent initial fixtures; no live pose/HP/ammo/clock renewal in the combat/exhaustion traces. Separate lifecycle/corruption fixtures manipulate stocks explicitly.',
                            'This trace has no nearby depot. Resupply is verified separately; weapon variety, NPC reload animation, ammunition replication and hardware/full-game acceptance remain open.']}))
