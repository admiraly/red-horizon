#!/usr/bin/env python3
"""Assembly formation goal movement and physical capture scenarios."""
import ctypes as C
import math
import sys
lib = C.CDLL(sys.argv[1])
lib.sim_init.argtypes = [C.c_uint, C.c_uint]
lib.sim_waypoint.argtypes = [C.c_uint, C.c_uint, C.c_float, C.c_float]
lib.sim_order.argtypes = [C.c_uint, C.c_uint, C.c_uint]
lib.sim_checksum.restype = C.c_uint64
class Entity(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float), ('hp', C.c_uint), ('side', C.c_uint),
                ('kind', C.c_uint), ('front', C.c_uint), ('target', C.c_int), ('generation', C.c_uint)]
class Site(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float), ('owner', C.c_uint), ('capture', C.c_int),
                ('role', C.c_uint), ('connected', C.c_uint), ('health', C.c_uint), ('flags', C.c_uint)]
entities = (Entity * 32768).in_dll(lib, 'sim_entities')
sites = (Site * 12).in_dll(lib, 'sim_sites')
goals = (C.c_float * 12).in_dll(lib, 'sim_waypoints')
alive = (C.c_uint * 2).in_dll(lib, 'sim_alive')
def reset():
    assert lib.sim_init(32, 1) == 0
    # This suite verifies explicit player orders; autonomous tactics are tested separately.
    for side in (0,1):
        for front in range(3):
            assert lib.sim_order(side,front,0) == 0
    for entity in entities[:32]:
        entity.hp = 0
    alive[0] = alive[1] = 0

def unit(index, x, z, side, front, kind=0):
    entity = entities[index]
    entity.x, entity.z, entity.side, entity.front, entity.kind, entity.hp = x,z,side,front,kind,100
    entity.target = -1
    alive[side] += 1
    return entity
reset()
assert list(goals) == [5000,1300,5000,3900,5000,6500,3000,1300,3000,3900,3000,6500]
hash_before = lib.sim_checksum()
for args in ((2,0,1,1),(0,3,1,1),(0,0,-1,1),(0,0,8001,1),(0,0,1,-1),
             (0,0,1,8001),(0,0,4000,1300),(0,0,2800,3570),(0,0,math.nan,1),(0,0,1,math.nan),
             (0,0,math.inf,1),(0,0,1,-math.inf)):
    assert lib.sim_waypoint(*args) == -1
    assert lib.sim_checksum() == hash_before
assert lib.sim_waypoint(0,0,0,8000) == 0
assert lib.sim_checksum() != hash_before
# Short diagonal move arrives exactly without overshoot. Other front/side
# goals remain independent, and dead records never move.
reset()
a = unit(0,10,10,0,0)
b = unit(1,1000,1000,0,1)
c = unit(16,7000,7000,1,0)
dead_pos = (entities[2].x, entities[2].z)
assert lib.sim_waypoint(0,0,10.06,10.08) == 0
untouched = list(goals[2:])
lib.sim_tick()
assert a.x == goals[0] and a.z == goals[1]
assert math.isclose(math.hypot(b.x-1000,b.z-1000),0.12,abs_tol=0.0001)
assert math.isclose(math.hypot(c.x-7000,c.z-7000),0.12,abs_tol=0.001)
assert list(goals[2:]) == untouched and (entities[2].x,entities[2].z) == dead_pos
arrival = (a.x,a.z)
for _ in range(5):
    lib.sim_tick()
assert (a.x,a.z) == arrival
assert lib.sim_order(0,0,1) == 0
old_b = (b.x,b.z)
lib.sim_tick()
assert (a.x,a.z) == arrival and (b.x,b.z) != old_b
# Role speeds use metres per fixed 1/30-second tick.
reset()
for kind in range(4):
    unit(kind,1000,1000,0,0,kind)
lib.sim_tick()
for kind,expected in enumerate((0.12,0.5,0.2,5.0)):
    actor = entities[kind]
    assert math.isclose(math.hypot(actor.x-1000,actor.z-1000),expected,abs_tol=0.0001)
# Real infantry movement reaches a hostile site, then hold completes a
# physical twenty-second capture while another formation keeps moving.
reset()
a = unit(0,4990,1280,0,0)
b = unit(1,1000,7000,0,1)
assert lib.sim_waypoint(0,0,5000,1300) == 0
assert lib.sim_waypoint(0,1,1100,7000) == 0
for _ in range(200):
    lib.sim_tick()
assert (a.x,a.z) == (5000,1300)
assert lib.sim_order(0,0,1) == 0
old_b = (b.x,b.z)
for _ in range(600):
    lib.sim_tick()
assert (a.x,a.z) == (5000,1300) and b.x > old_b[0] and b.x <= 1100
assert sites[2].owner == 0 and sites[2].connected == 1
print('PASS: finite/bounded goals, side/front isolation, correct speed, exact arrival/hold and world-tick physical site capture')
