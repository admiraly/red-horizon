#!/usr/bin/env python3
"""Actual eight-tick finite shots choose visible human/army targets fairly."""
import ctypes as C,hashlib,json,pathlib,sys
source=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(source));l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
class Player(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint)for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
e=(Entity*32768).in_dll(l,'sim_entities');p=(Player*4).in_dll(l,'sim_players');w=(C.c_uint*(32768*8)).in_dll(l,'infantry_weapons');alive=(C.c_uint*2).in_dll(l,'sim_alive');cool=(C.c_uint*32768).in_dll(l,'infantry_shot_cooldowns')
def setup(army=(7000.,7000.),humans=((2000.,3900.),),enemy=(2050.,3900.)):
 assert l.sim_init(32,47)==0
 for i in range(len(humans)):assert l.player_join(i,1)==0
 for i in range(32):
  if i not in (0,17):e[i].hp=0
 e[0].x,e[0].z=army;e[17].x,e[17].z=enemy;alive[:]=[1,1];w[0:8]=[1,0,0,0,120,0,0,0]
 for i,(x,z)in enumerate(humans):p[i].x,p[i].z=x,z;p[i].y=l.terrain_height(x,z)+1.8
 for side in range(2):
  for front in range(3):assert l.sim_order(side,front,1)==0

def run(name,army,humans,enemy=(2050.,3900.),ticks=80):
 setup(army,humans,enemy);trace=[];prior=0
 for tick in range(1,ticks+1):
  before=[e[0].hp]+[v.hp for v in p];l.sim_tick();after=[e[0].hp]+[v.hp for v in p];spent=w[17*8+4]
  assert w[17*8+1]+w[17*8+2]+spent==120
  if spent!=prior:
   assert spent==prior+1 and sum(a>b for a,b in zip(before,after))==1
   trace.append([tick,*[a-b for a,b in zip(before,after)]])
  else:assert before==after
  prior=spent
 return {'name':name,'shots':trace,'army_hp':e[0].hp,'human_hp':[v.hp for v in p],'actual_spent':prior,'checksum':f'{l.sim_checksum():016x}'}
closer=run('closer-human',(2110.,3900.),((2000.,3900.),),ticks=64)
assert closer['army_hp']==100 and closer['human_hp'][0]==20 and closer['actual_spent']==8,closer
army=run('closer-army',(2070.,3900.),((2000.,3900.),))
assert army['army_hp']==70 and army['human_hp'][0]==100 and army['actual_spent']==10,army
tie=run('army-wins-exact-tie',(2100.,3900.),((2000.,3900.),))
assert tie['army_hp']==70 and tie['human_hp'][0]==100,tie
fair=run('fair-human-distance-ties',(7000.,7000.),((2000.,3900.),(2050.,3850.),(2100.,3900.),(2050.,3950.)),ticks=64)
assert fair['human_hp']==[80]*4 and fair['actual_spent']==8,fair
wall=run('nearer-hidden-human',(4030.,1450.),((3970.,1300.),(4030.,1380.)),enemy=(4030.,1300.),ticks=64)
assert wall['human_hp'][:2]==[100,20] and wall['army_hp']==100,wall
range_edge=run('same240m-rifle-range',(7000.,7000.),((1810.,3900.),),ticks=64)
assert range_edge['human_hp'][0]==20 and range_edge['actual_spent']==8,range_edge
outside=run('beyond-rifle-range',(7000.,7000.),((1809.,3900.),),ticks=64)
assert outside['human_hp'][0]==100 and outside['actual_spent']==0,outside
assert run('fair-human-distance-ties',(7000.,7000.),((2000.,3900.),(2050.,3850.),(2100.,3900.),(2050.,3950.)),ticks=64)==fair
# A genuine driver cannot be shot through its surviving allied hull.
setup(humans=((2002.,3900.),));e[12].hp=400;e[12].x,e[12].z=2000.,3900.;alive[0]+=1
assert l.vehicle_enter(0,12)==0
for _ in range(64):l.sim_tick()
assert p[0].hp==100 and w[17*8+4]==8 and e[12].hp<400
# Invalid shape/IDs/generation guards are read-only before a valid eligible shot.
setup();l.sim_tick() # stable birth/equipment, then declared static gate fixture
for ident,target in ((32,0xffffffff),(0xffffffff,0xffffffff),(17,32),(17,0)):
 # source17 phase occurs at7; static clock fixture belongs only to API gates.
 C.c_uint.in_dll(l,'sim_tick_count').value=7
 if target==0: e[0].generation=0
 before=l.sim_checksum();assert l.infantry_human_fire(ident,target)==-1 and l.sim_checksum()==before
 if target==0:e[0].generation=1
print(json.dumps({'suite':'joint-visible-infantry-human-targets','passed':True,'closer_human':closer,'closer_army':army,'army_exact_tie':tie,'fair_human_ties':fair,'closer_hidden_visible_fallback':wall,'same_rifle_range':range_edge,'outside_range':outside,'genuine_boarded_hull_shields':True,'invalid_gates_atomic':True,'same_build_replay':True,'core_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['Sparse declared initial poses/dead nonparticipants/prior allied exhaustion; real finite shots, LOS and ticks thereafter, no live renewal.','Static API malformed-clock gate separated from physical encounters.','Visible nearest-target arbitration, not strategic knowledge/aim orientation/full capsule/graphics/UDP/scale acceptance.']}))
