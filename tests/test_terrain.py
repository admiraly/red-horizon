#!/usr/bin/env python3
import ctypes as C
import math
import struct
import sys
lib=C.CDLL(sys.argv[1])
lib.terrain_height.argtypes=[C.c_float]*2
lib.terrain_height.restype=C.c_float
lib.terrain_blocked.argtypes=[C.c_float,C.c_float,C.c_uint]
lib.terrain_los.argtypes=[C.c_float]*6
lib.test_terrain_move.argtypes=[C.c_float]*5+[C.c_uint]
lib.test_terrain_move.restype=C.c_uint64
lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
entities=(Entity*32768).in_dll(lib,'sim_entities')
for x,z in [(0,0),(4000,4000),(8000,8000),(3500,1300),(5000,6500)]:
    expected=12+(x-4000)**2*.000001+(z-4000)**2*.0000005+max(0,1-abs(x-4000)/800)*18
    assert math.isclose(lib.terrain_height(x,z),expected,abs_tol=.00001)
assert lib.terrain_blocked(4000,1300,0)==1
assert lib.terrain_blocked(4000,1300,3)==0
assert lib.terrain_blocked(3900,1300,0)==0
assert lib.terrain_los(3950,35,1300,4050,35,1300)==0
assert lib.terrain_los(3950,70,1300,4050,70,1300)==1
assert lib.terrain_los(3950,35,1000,4050,35,1000)==1
x,z=3950.,1300.
went_around=False
for _ in range(500):
    bits=lib.test_terrain_move(x,z,4050,1300,2,0)
    nx,nz=struct.unpack('<ff',struct.pack('<Q',bits))
    assert math.hypot(nx-x,nz-z)<=2.001
    assert lib.terrain_blocked(nx,nz,0)==0
    if nz<1100 or nz>1500: went_around=True
    x,z=nx,nz
assert went_around and math.hypot(x-4050,z-1300)<.001
# A wall-edge start with a goal on the opposite flank exercises bounded
# blocked-step component recovery rather than stepping through the wall.
x,z=4000.,1505.
for _ in range(1000):
    bits=lib.test_terrain_move(x,z,4050,1000,2,0)
    nx,nz=struct.unpack('<ff',struct.pack('<Q',bits))
    assert math.hypot(nx-x,nz-z)<=2.001 and lib.terrain_blocked(nx,nz,0)==0
    x,z=nx,nz
assert math.hypot(x-4050,z-1000)<.001
# Actual world LOS excludes hidden enemies and blocks damage through solids.
assert lib.sim_init(2,1)==0
entities[0].x,entities[0].z=3970,1300
entities[1].x,entities[1].z=4030,1300
for side in (0,1): assert lib.sim_order(side,0,1)==0
for _ in range(80):lib.sim_tick()
assert entities[0].hp==100 and entities[1].hp==100
assert entities[0].target==-1 and entities[1].target==-1
# Actual army movement goes around the wall and arrives physically.
assert lib.sim_init(2,1)==0
entities[0].x,entities[0].z,entities[0].kind=3950,1300,1
entities[1].x,entities[1].z=7000,1300
assert lib.sim_order(1,0,1)==0
assert lib.sim_waypoint(0,0,4050,1300)==0
for _ in range(1200):
    lib.sim_tick()
    assert lib.terrain_blocked(entities[0].x,entities[0].z,1)==0
assert (entities[0].x,entities[0].z)==(4050,1300)
# Default full-capacity spawn validation, including no hidden solid overlap.
assert lib.sim_init(32768,1)==0
assert all(lib.terrain_blocked(e.x,e.z,e.kind)==0 for e in entities[:32768])
print('PASS: analytic height, swept wall LOS, elevated rays, bounded detour, actual army collision/LOS and safe massive spawns')
