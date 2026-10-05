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
 for invalid in (-1,2,99):
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
