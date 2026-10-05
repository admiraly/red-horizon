#!/usr/bin/env python3
import ctypes as C
import math
import random
import json
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
# Independent 2D slab oracle checks entire movement segments, not only endpoints.
# Copy physical records from the real module; query expectations use Python doubles.
obstacles=(C.c_float*(5*8)).in_dll(lib,'terrain_obstacles')
boxes=[tuple(obstacles[i*8:i*8+4]) for i in range(5)]
def crosses(start,end,box):
    low,high=0.,1.
    for p,q,mn,mx in ((start[0],end[0],box[0],box[2]),
                       (start[1],end[1],box[1],box[3])):
        delta=q-p
        if delta==0:
            if not mn<=p<=mx:return False
        else:
            a,b=sorted(((mn-p)/delta,(mx-p)/delta))
            low,high=max(low,a),min(high,b)
            if low>high:return False
    return True
def move(start,goal,step,kind=0):
    return struct.unpack('<ff',struct.pack('<Q',lib.test_terrain_move(*start,*goal,step,kind)))
def safe_step(start,goal,step):
    end=move(start,goal,step)
    assert math.dist(start,end)<=step+.001
    assert lib.terrain_blocked(*end,0)==0
    assert not any(crosses(start,end,box) for box in boxes),(start,goal,end)
    return end
# Before correction this selects the distant central wall (record0), passes
# through the nearer bunker (record3), and finishes at4808.64,2464.43.
start=(5243.89013671875,1564.114990234375)
goal=(3125.11279296875,5204.44287109375)
end=safe_step(start,goal,1000)
assert math.dist(end,(5234,1604))<.001,('nearest obstruction not selected',end)
# Arrival rather than safe permanent holding, at actual ground-role speeds.
route_steps=0
for step in (.12,.2,.5,1000):
    point=start
    for tick in range(math.ceil(6000/step)):
        point=safe_step(point,goal,step)
        route_steps+=1
        if math.dist(point,goal)<.001:break
    assert math.dist(point,goal)<.001,('bunker/wall route did not arrive',step,point)
# Seeded large steps cover every authored obstacle and slide-fallback geometry.
rng=random.Random(731)
swept_cases=0
for _ in range(2000):
    start=tuple(C.c_float(v).value for v in (rng.uniform(2500,5500),rng.uniform(500,7000)))
    goal=tuple(C.c_float(v).value for v in (rng.uniform(2500,5500),rng.uniform(500,7000)))
    if lib.terrain_blocked(*start,0) or lib.terrain_blocked(*goal,0):continue
    safe_step(start,goal,rng.choice((.12,.5,1000,8000)))
    swept_cases+=1
# Aircraft preserve their existing solid bypass and direct capped movement.
start=(3950.,1300.);goal=(4050.,1300.)
assert move(start,goal,1000,3)==goal
print(json.dumps({'suite':'terrain-swept-movement','passed':True,
                  'seed':731,'random_clear_start_cases':swept_cases,
                  'arrival_route_steps':route_steps,'nearest_obstacle_endpoint':end,
                  'role_steps_metres':[.12,.2,.5,1000],
                  'oracle':'independent double-precision segment/rectangle intersection'}))
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
