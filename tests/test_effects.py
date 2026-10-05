#!/usr/bin/env python3
"""Read-only cosmetic consumer against real authority at independent frame rates."""
import ctypes as C
import json
import sys
lib=C.CDLL(sys.argv[1]);lib.effects_update.argtypes=[C.c_uint,C.c_float]
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Event(C.Structure):
    _fields_=[(n,C.c_float)for n in('x','y','z')]+[(n,C.c_uint)for n in('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
entities=(Entity*32768).in_dll(lib,'sim_entities');events=(Event*256).in_dll(lib,'sim_events')
impacts=C.c_uint.in_dll(lib,'effects_impacts');cursor=C.c_uint.in_dll(lib,'effects_event_cursor')
sequence=C.c_uint.in_dll(lib,'sim_event_sequence');lib.sim_checksum.restype=C.c_uint64
assert lib.sim_init(32,1)==0
for actor in entities[:32]:actor.hp=0
entities[12].x,entities[12].z,entities[12].hp=3500.,2000.,400
entities[16].x,entities[16].z,entities[16].hp=3700.,2000.,100
for side in (0,1):
    for front in range(3):assert lib.sim_order(side,front,1)==0
assert lib.player_join(0,0)==0
player=(C.c_float*16).in_dll(lib,'sim_players');player[0],player[1],player[2]=3500.,22.8,2000.
cooldown=(C.c_uint*32768).in_dll(lib,'sim_shell_cooldown')
# Initial one-tick cooldown reserves this explicit shell while building the grid.
cooldown[12]=1
lib.sim_tick();lib.effects_update(0,.01)
assert cooldown[12]==0
assert lib.projectile_spawn(12,16)==0
for _ in range(25):lib.sim_tick()
assert any(e.kind==3 and e.sequence for e in events)
before=lib.sim_checksum();lib.effects_update(0,.01)
assert impacts.value==1,impacts.value
observed=(impacts.value,cursor.value,sequence.value)
for _ in range(360):lib.effects_update(0,1/120)
assert (impacts.value,cursor.value,sequence.value)==observed,'replayed event without new authority tick'
assert lib.sim_checksum()==before,'cosmetic consumer mutated authority'
records=(C.c_float*(64*8)).in_dll(lib,'effects_records')
assert all(records[i*8+3]<=0 for i in range(64)),'cosmetic lifetimes did not expire'
print(json.dumps({'suite':'effects-frame-independence','passed':True,'actual_impacts':impacts.value,'repeated_render_updates':360,'authority_unchanged':True}))
