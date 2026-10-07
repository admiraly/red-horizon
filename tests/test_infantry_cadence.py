#!/usr/bin/env python3
"""Actual fixed ticks: one finite infantry weapon shared across army/four humans."""
import ctypes as C,hashlib,json,pathlib,sys
source=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(source));l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
class Player(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint)for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
e=(Entity*32768).in_dll(l,'sim_entities');p=(Player*4).in_dll(l,'sim_players');w=(C.c_uint*(32768*8)).in_dll(l,'infantry_weapons');alive=(C.c_uint*2).in_dll(l,'sim_alive')
def run(mixed):
 assert l.sim_init(32,47)==0
 for ident in range(4):assert l.player_join(ident,1)==0
 for ident in range(32):
  if ident not in (0,17):e[ident].hp=0
 assert e[0].hp==e[17].hp==100 and e[17].side==1 and e[17].kind==0
 e[0].x,e[0].z=(2105.,3900.)if mixed else(7000.,7000.)
 e[17].x,e[17].z=2050.,3900.;alive[:]=[1,1]
 w[0:8]=[e[0].generation,0,0,0,120,0,0,0] # declared prior finite exhaustion, no renewal
 for ident in range(4):
  p[ident].x,p[ident].z=2000.+ident*2,3900.;p[ident].y=l.terrain_height(p[ident].x,p[ident].z)+1.8
 for side in range(2):
  for front in range(3):assert l.sim_order(side,front,1)==0
 shots=[];damage=[];before=0;previous_hp=[e[0].hp]+[v.hp for v in p]
 for tick in range(1,81):
  l.sim_tick();stock=tuple(w[17*8:18*8]);hp=[e[0].hp]+[v.hp for v in p]
  delta=[a-b for a,b in zip(previous_hp,hp)]
  assert stock[1]+stock[2]+stock[4]==120
  if stock[4]!=before:
   actual=stock[4]-before
   assert actual==sum(v>0 for v in delta),(tick,stock,delta)
   if '--baseline'not in sys.argv:assert actual==1,(tick,stock,delta)
   shots.extend([tick]*actual);damage.append([tick,*delta])
  else:assert hp==previous_hp,(tick,stock,hp,previous_hp)
  previous_hp=hp;before=stock[4]
 if '--baseline'not in sys.argv:
  assert all(b-a>=8 for a,b in zip(shots,shots[1:])),shots
  assert len(shots)<=10
 return {'mixed_army_target':mixed,'actual_shot_ticks':shots,'actual_damage_per_tick':damage,'final_army_hp':e[0].hp,'final_human_hp':[v.hp for v in p],'final_stock':tuple(w[17*8:18*8]),'checksum':f'{l.sim_checksum():016x}'}
solo=run(False);mixed=run(True)
if '--baseline'in sys.argv:
 assert any(b-a<8 for a,b in zip(solo['actual_shot_ticks'],solo['actual_shot_ticks'][1:])),solo
 print(json.dumps({'suite':'infantry-shared-cadence-baseline','observed_double_target_rate_bug':True,'four_humans':solo,'mixed':mixed,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}))
else:
 # Isolated direct ABI/state gates; separate from live physical encounters.
 cooldowns=(C.c_uint*32768).in_dll(l,'infantry_shot_cooldowns')
 assert l.sim_init(32,47)==0
 assert l.infantry_weapon_shot(0)==0 and cooldowns[0]==8 and w[1]==29 and w[4]==1
 before=l.sim_checksum();assert l.infantry_weapon_shot(0)==1 and l.sim_checksum()==before
 for field,value in ((0,2),(1,31),(2,91),(3,1),(4,121)):
  saved=w[field];w[field]=value;before=l.sim_checksum()
  assert l.infantry_weapon_shot(0)==-1 and l.sim_checksum()==before
  w[field]=saved
 cooldowns[0]=9;before=l.sim_checksum();assert l.infantry_weapon_shot(0)==-1 and l.sim_checksum()==before
 # Death freezes cadence; only a genuine separately declared new body resets.
 assert l.sim_init(32,47)==0
 e[0].hp=0;cooldowns[0]=8;before=tuple(w[:8])
 for _ in range(12):l.sim_tick()
 assert cooldowns[0]==8 and tuple(w[:8])==before
 assert l.sim_init(32,47)==0
 e[0].generation=2;cooldowns[0]=8;l.sim_tick()
 assert w[0]==2 and cooldowns[0]==0
 before=l.sim_checksum();cooldowns[0]=1;assert l.sim_checksum()!=before
 assert run(False)==solo and run(True)==mixed
 assert mixed['actual_shot_ticks']==list(range(7,81,8)) and mixed['final_army_hp']==100 and sum(mixed['final_human_hp'])==300,mixed
 print(json.dumps({'suite':'infantry-shared-actual-shot-cadence','passed':True,'actual_ticks_per_case':80,'four_humans':solo,'mixed':mixed,'same_build_replay':True,'blocked_corrupt_cadence_atomic':True,'dead_cadence_freezes_new_body_resets':True,'cooldown_in_authority_hash':True,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['One sparse startup pose/dead-nonparticipant/prior-allied-exhaustion fixture; real fixed ticks, no later HP/pose/stock/clock writes.','Closest visible human wins over a farther army target at the shared actor8tick phase.','Native causal firing/conservation evidence, not graphics/UDP/full-scale acceptance.']}))
