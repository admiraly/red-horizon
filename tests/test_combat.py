#!/usr/bin/env python3
"""Actual authoritative projectile pools, physical collision and bounded blasts."""
import ctypes as C
import math
import sys
lib=C.CDLL(sys.argv[1])
lib.projectile_launch.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*3
lib.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Shell(C.Structure):
    _fields_=[(n,C.c_float)for n in('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint)for n in('source','generation','active','source_generation','reserved')]
class Event(C.Structure):
    _fields_=[(n,C.c_float)for n in('x','y','z')]+[(n,C.c_uint)for n in('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
entities=(Entity*32768).in_dll(lib,'sim_entities')
shells=(Shell*512).in_dll(lib,'sim_projectiles')
events=(Event*256).in_dll(lib,'sim_events')
count=C.c_uint.in_dll(lib,'sim_projectile_count')
dropped=C.c_uint.in_dll(lib,'sim_projectile_dropped')
event_count=C.c_uint.in_dll(lib,'sim_event_count')
sequence=C.c_uint.in_dll(lib,'sim_event_sequence')
ammo=(C.c_uint*32768).in_dll(lib,'sim_shell_ammo')
cooldown=(C.c_uint*32768).in_dll(lib,'sim_shell_cooldown')
alive=(C.c_uint*2).in_dll(lib,'sim_alive')
assert C.sizeof(Shell)==64 and C.sizeof(Event)==32

def reset(kind=1,x=3500,z=2000,target_x=3700,target_z=2000):
    assert lib.sim_init(32,1)==0
    for e in entities[:32]:e.hp=0
    source=12 if kind==1 else 14
    entities[source].x,entities[source].z,entities[source].front,entities[source].hp=x,z,0,400
    entities[16].x,entities[16].z,entities[16].front,entities[16].hp=target_x,target_z,0,100
    entities[1].x,entities[1].z,entities[1].front,entities[1].hp=target_x,target_z+3,0,100
    alive[0],alive[1]=2,1
    for side in(0,1):
        for front in range(3):lib.sim_order(side,front,1)
    lib.sim_tick()  # Builds the real authoritative spatial grid.
    return source

source=reset()
before=lib.sim_checksum()
for args in ((32,1,3700,20,2000),(0,1,3700,20,2000),(source,3,3700,20,2000),
             (source,1,math.nan,20,2000),(source,1,3700,math.inf,2000),(source,1,3700,20,8001)):
    assert lib.projectile_launch(*args)==-1 and lib.sim_checksum()==before
assert lib.projectile_spawn(source,16)==0
assert count.value==1 and entities[16].hp==100 and list(alive)==[2,1]
shell=next(p for p in shells if p.active)
start=(shell.x,shell.y,shell.z)
lib.projectile_tick()
assert shell.active and shell.x>start[0] and entities[16].hp==100
for _ in range(30):lib.projectile_tick()
assert count.value==0 and entities[16].hp==20 and entities[1].hp==100
assert any(e.kind==3 and e.sequence for e in events)
# Full world ticks also advance and apply physical shell contact.
source=reset();assert lib.projectile_spawn(source,16)==0
for _ in range(25):lib.sim_tick()
assert entities[16].hp<100 and count.value==0
# A swept wall impact remains on its near side, with no distant through-wall hit.
source=reset(x=3970,z=1300,target_x=4030,target_z=1300)
assert lib.projectile_spawn(source,16)==0
for _ in range(15):lib.projectile_tick()
impacts=[e for e in events if e.sequence and e.kind==3]
assert count.value==0 and entities[16].hp==100 and impacts
assert 3970<impacts[-1].x<3988.01
# Even an artillery blast whose radius reaches the far side respects solid LOS.
source=reset(kind=2,x=3970,z=1300,target_x=4014,target_z=1300)
assert lib.projectile_spawn(source,16)==0
for _ in range(20):lib.projectile_tick()
assert count.value==0 and entities[16].hp==100
# A lethal impact decrements army living counts exactly once.
source=reset();entities[16].hp=50
assert lib.projectile_spawn(source,16)==0
for _ in range(30):lib.projectile_tick()
assert entities[16].hp==0 and list(alive)==[2,0]
for _ in range(10):lib.projectile_tick()
assert list(alive)==[2,0]
# Artillery has real vertical travel and gravity, not instantaneous damage.
source=reset(kind=2)
assert lib.projectile_spawn(source,16)==0
shell=next(p for p in shells if p.active)
vy=shell.vy;y=shell.y
lib.projectile_tick()
assert shell.y>y and shell.vy<vy and entities[16].hp==100
for _ in range(80):lib.projectile_tick()
assert count.value==0 and entities[16].hp<100 and any(e.kind==4 and e.sequence for e in events)
# Steep/near-vertical actor contact explodes at the projected contact point,
# rather than at a distant segment endpoint that would miss the actual actor.
source=reset(target_x=3500,target_z=2000)
entities[16].kind=3
assert lib.projectile_launch(source,1,3500,1000,2000)==0
lib.projectile_tick()
assert count.value==0 and entities[16].hp==20
impact=events[sequence.value&255]
assert impact.kind==3 and 50<impact.y<200 and math.isfinite(impact.y)
# Saturated pools reject launches without corrupting records; counts never
# inflate army membership, and cosmetics are an independently resettable ring.
source=reset();ammo[source]=600
for _ in range(480):
    cooldown[source]=0
    assert lib.projectile_spawn(source,16)==0
cooldown[source]=0
assert lib.projectile_spawn(source,16)==-1 and dropped.value==1
assert lib.projectile_spawn(1,16)==-1 and dropped.value==1  # invalid infantry source
cooldown[source]=1
assert lib.projectile_spawn(source,16)==-1 and dropped.value==1  # cadence rejection
cooldown[source]=0
# Human/API launches can use the reserved32 slots.
lib.terrain_height.argtypes=[C.c_float,C.c_float]
lib.terrain_height.restype=C.c_float
goal_y=lib.terrain_height(3700,2000)+1
for _ in range(32):
    cooldown[source]=0
    assert lib.projectile_launch(source,1,3700,goal_y,2000)==0
cooldown[source]=0
assert count.value==512 and lib.projectile_spawn(source,16)==-1
assert dropped.value==2 and count.value==512 and C.c_uint.in_dll(lib,'sim_count').value==32
assert event_count.value==256 and sequence.value==512
assert {e.sequence for e in events}==set(range(257,513))
assert events[512&255].sequence==512
h=lib.sim_checksum();lib.reset_event_ring()
assert event_count.value==0 and sequence.value==0 and lib.sim_checksum()==h
# Repeat a real travel/impact fixture, including ammo/pool state in checksum.
hashes=[]
for _ in range(2):
    source=reset();lib.projectile_spawn(source,16)
    for _ in range(31):lib.projectile_tick()
    hashes.append(lib.sim_checksum())
assert hashes[0]==hashes[1]
print('PASS: moving tank/artillery shells, swept ground/wall/actor contact, enemy-only bounded blast, pool saturation, cosmetic ring/reset and authoritative replay')
