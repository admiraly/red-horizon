#!/usr/bin/env python3
"""Authored air-battle initial layout, real army/flight/weapons and exact replay."""
import ctypes as C,json,collections,sys
lib=C.CDLL(sys.argv[1]);lib.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Event(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z')]+[(n,C.c_uint)for n in ('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
e=(Entity*32768).in_dll(lib,'sim_entities');events=(Event*256).in_dll(lib,'sim_events')
airs=(C.c_uint*2).in_dll(lib,'scenario_air_selected');grounds=(C.c_uint*2).in_dll(lib,'scenario_ground_selected')
lib.terrain_blocked.argtypes=[C.c_float,C.c_float,C.c_uint]
checks=[];counts=[]
for replay in range(2):
 assert lib.sim_init(8192,42)==0
 before=lib.sim_checksum()
 for invalid in (-1,4,99):
  assert lib.sim_scenario(invalid)==-1 and lib.sim_checksum()==before
 assert lib.sim_scenario(0)==0 and lib.sim_checksum()==before
 initial=[(x.hp,x.side,x.kind,x.front,x.target,x.generation)for x in e[:8192]]
 old_positions=[(x.x,x.z)for x in e[:8192]]
 pool=bytes((C.c_ubyte*32768).in_dll(lib,'sim_projectiles'))
 ring=bytes(events)
 assert lib.player_join(0,1)==0
 assert lib.sim_scenario(1)==0
 assert list(airs)==[32,32] and list(grounds)==[128,128]
 assert initial==[(x.hp,x.side,x.kind,x.front,x.target,x.generation)for x in e[:8192]]
 assert sum((x.x,x.z)!=old_positions[i]for i,x in enumerate(e[:8192]))==320
 assert bytes((C.c_ubyte*32768).in_dll(lib,'sim_projectiles'))==pool and bytes(events)==ring
 assert all(not lib.terrain_blocked(x.x,x.z,x.kind)for x in e[:8192])
 shots=collections.Counter()
 for tick in range(1,301):
  lib.sim_tick()
  for v in events:
   if v.tick==tick and v.kind in (6,7,8,9):shots[v.kind]+=1
 assert shots[6]>0 and shots[7]>0 and shots[8]>0,shots
 checks.append(hex(lib.sim_checksum()));counts.append(dict(shots))
 before=lib.sim_checksum();assert lib.sim_scenario(1)==-1 and lib.sim_checksum()==before
assert checks[0]==checks[1] and counts[0]==counts[1]
assert lib.sim_init(128,42)==0
before=lib.sim_checksum();assert lib.sim_scenario(1)==-1 and lib.sim_checksum()==before
print(json.dumps({'suite':'air-battle-scenario','passed':True,'army':8192,'initial_relocated':320,'aircraft_per_side':32,'ground_per_side':128,'kind_side_front_HP_generation_preserved':True,'no_fixture_weapon_or_event_writes':True,'actual_300tick_events':counts[0],'checksum':checks[0],'replay':True}))

# Dense fixtures preserve the complete army; only initial positions/air poses change.
# Count real acquired enemy targets with independent range/LOS checks, rather than
# using the fixture's cohort counters as engagement or visibility evidence.
lib.terrain_height.argtypes=[C.c_float,C.c_float]
lib.terrain_height.restype=C.c_float
lib.terrain_los.argtypes=[C.c_float]*6
engaged=C.c_uint.in_dll(lib,'sim_engaged')
dense_reports=[]
for mode,name,per_side in ((2,'scale-front',1280),(3,'scale-hotspot',1920)):
 results=[]
 for replay in range(2):
  assert lib.sim_init(8192,42)==0 and lib.player_join(0,1)==0
  army_before=[(x.hp,x.side,x.kind,x.front,x.target,x.generation)for x in e[:8192]]
  positions=[(x.x,x.z)for x in e[:8192]]
  pool=bytes((C.c_ubyte*32768).in_dll(lib,'sim_projectiles'));ring=bytes(events)
  assert lib.sim_scenario(mode)==0
  assert list(airs)==[32,32] and list(grounds)==[per_side,per_side]
  assert army_before==[(x.hp,x.side,x.kind,x.front,x.target,x.generation)for x in e[:8192]]
  assert bytes((C.c_ubyte*32768).in_dll(lib,'sim_projectiles'))==pool and bytes(events)==ring
  relocated=[i for i,x in enumerate(e[:8192])if (x.x,x.z)!=positions[i]]
  ground_ids=[i for i in relocated if e[i].kind!=3]
  assert len(ground_ids)==per_side*2 and len(relocated)==per_side*2+64
  assert len({(e[i].x,e[i].z)for i in ground_ids})==len(ground_ids)
  assert all(not lib.terrain_blocked(x.x,x.z,x.kind)for x in e[:8192])
  initial_positions={i:(e[i].x,e[i].z)for i in relocated}
  samples=[];event_counts=collections.Counter()
  for tick in range(1,121):
   lib.sim_tick()
   for v in events:
    if v.tick==tick:event_counts[v.kind]+=1
   if tick not in (1,8,16,30):continue
   valid=0
   for i in ground_ids:
    actor=e[i];target=actor.target
    if not actor.hp or target<0:continue
    assert target<8192
    enemy=e[target]
    # Final damage applies after acquisition; targets may die in this same tick.
    assert enemy.side!=actor.side and enemy.kind!=3
    distance2=(actor.x-enemy.x)**2+(actor.z-enemy.z)**2
    assert distance2<=(240,450,650)[actor.kind]**2+.1
    ya=lib.terrain_height(actor.x,actor.z)+2
    yb=lib.terrain_height(enemy.x,enemy.z)+2
    assert lib.terrain_los(actor.x,ya,actor.z,enemy.x,yb,enemy.z)
    if enemy.hp:valid+=1
   samples.append({'tick':tick,'engaged_total':engaged.value,'living_cohort_enemy_targets':valid})
  assert max(v['living_cohort_enemy_targets']for v in samples)>=2048,samples
  changed=sum((e[i].x,e[i].z)!=initial_positions[i]for i in relocated)
  damage=sum(before[0]-x.hp for before,x in zip(army_before,e[:8192]))
  dead=sum(not x.hp for x in e[:8192])
  assert changed>per_side and damage>0 and dead>0
  assert event_counts[1]>0 and event_counts[2]>0 and event_counts[8]>0,event_counts
  before=lib.sim_checksum()
  for late_mode in (1,2,3):assert lib.sim_scenario(late_mode)==-1 and lib.sim_checksum()==before
  results.append({'samples':samples,'moved_cohort':changed,'actual_hp_damage':damage,
                  'dead':dead,'actual_events':dict(event_counts),'checksum':hex(before)})
 assert results[0]==results[1],results
 dense_reports.append({'scenario':name,'ground_per_side':per_side,'aircraft_per_side':32,
                       'army':8192,'initial_kind_mix':dict(collections.Counter(v[2]for v in army_before)),
                       **results[0]})
for count in (128,2048,4096,8190):
 assert lib.sim_init(count,42)==0
 before=lib.sim_checksum()
 for mode in (2,3):assert lib.sim_scenario(mode)==-1 and lib.sim_checksum()==before
print(json.dumps({'suite':'dense-scenarios','passed':True,'seed':42,'replay':True,
                  'no_fixture_weapon_or_event_writes':True,'terrain_valid':True,
                  'visible_individual_count':'unmeasured','scenarios':dense_reports}))
