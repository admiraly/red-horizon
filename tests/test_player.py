#!/usr/bin/env python3
"""Exercise authoritative player outcomes against the actual assembly core."""
import ctypes as C
import math
import sys
lib=C.CDLL(sys.argv[1])
class Player(C.Structure):
    _fields_=[('x',C.c_float),('y',C.c_float),('z',C.c_float),('yaw',C.c_float),('pitch',C.c_float)]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Motion(C.Structure):
    _fields_=[('feet',C.c_float),('step',C.c_float)]+[(n,C.c_uint) for n in ('generation','latch','grounded','initialized')]+[('eye',C.c_float),('reserved',C.c_uint)]
players=(Player*4).in_dll(lib,'sim_players')
motion=(Motion*4).in_dll(lib,'player_motion')
entities=(Entity*32768).in_dll(lib,'sim_entities')
sites=(C.c_uint*96).in_dll(lib,'sim_sites')
tick=C.c_uint.in_dll(lib,'sim_tick_count')
lib.terrain_height.argtypes=[C.c_float,C.c_float];lib.terrain_height.restype=C.c_float
lib.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
lib.sim_checksum.restype=C.c_uint64

def reset(count=2):
    assert lib.sim_init(count,1)==0
    lib.player_init()
    assert lib.player_join(0,1)==0
    p=players[0]
    p.x,p.z=3900,2000
    p.y=lib.terrain_height(p.x,p.z)+1.8
    for i,e in enumerate(entities[:count]):
        e.x,e.z,e.hp,e.side,e.kind=7000,7000,100,i&1,0
    tick.value=1
    return p

def place_enemy(x,z):
    entities[1].x,entities[1].z=x,z
    entities[1].hp=100

def aim(p,x,z):
    dy=lib.terrain_height(x,z)+1-p.y
    return math.atan2(x-p.x,z-p.z),math.atan2(dy,math.hypot(x-p.x,z-p.z))

p=reset(8192)
assert lib.player_join(0,1)==-1
assert lib.player_join(4,0)==-1 and lib.player_join(1,3)==-1
assert lib.player_join(1,2)==0 and players[1].hp==100
assert lib.player_leave(1)==0 and lib.player_leave(1)==-1
for args in [(0,128,0,0,0,0),(4,0,0,0,0,0),(0,0,float('nan'),0,0,0),(0,0,0,0,float('inf'),0),(0,0,0,0,0,2),(0,0,2,0,0,0)]:
    before=bytes(players)
    assert lib.player_input(*args)==-1 and bytes(players)==before
for field in range(4):
    for value in (float('nan'),float('inf'),float('-inf')):
        floats=[0.,0.,0.,0.];floats[field]=value
        before=bytes(players)
        assert lib.player_input(0,0,*floats)==-1 and bytes(players)==before
x=p.x
assert lib.player_input(0,0,1,0,0,0)==0
for _ in range(30):lib.player_tick()
assert abs(p.x-x-5)<.01
x=p.x
lib.player_input(0,4,1,0,0,0)
for _ in range(30):lib.player_tick()
assert abs(p.x-x-9)<.02
p=reset()
place_enemy(3900,2080)
yaw,pitch=aim(p,3900,2080)
assert lib.player_input(0,1,0,0,yaw,pitch)==0
lib.player_tick()
assert p.ammo==29 and p.shots==1 and p.hits==1 and entities[1].hp==66
for _ in range(3):lib.player_tick()
assert p.shots==1
lib.player_tick()
assert p.shots==2 and entities[1].hp==32
lib.player_input(0,2,0,0,yaw,pitch)
lib.player_tick()
assert p.reload==60
lib.player_input(0,0,0,0,yaw,pitch)
for _ in range(59):lib.player_tick()
assert p.reload==1 and p.ammo==28
lib.player_tick()
assert p.reload==0 and p.ammo==30
# Suppression changes an actual grazing shot outcome, rather than just a HUD value.
p=reset();place_enemy(3903,2080)
_,pitch=aim(p,3903,2080)
lib.player_input(0,1,0,0,0,pitch);lib.player_tick()
assert p.hits==1
p=reset();place_enemy(3903,2080);p.suppression=80
lib.player_input(0,1,0,0,0,pitch);lib.player_tick()
assert p.shots==1 and p.hits==0 and entities[1].hp==100
# Humans/allies never receive rifle damage.
p=reset();place_enemy(3900,2080);entities[1].side=0
lib.player_input(0,1,0,0,0,0);lib.player_tick()
assert p.shots==1 and p.hits==0 and entities[1].hp==100
# An intent step must never put the authoritative player inside a solid wall.
p=reset();p.x,p.z=3987.9,1300;p.y=lib.terrain_height(p.x,p.z)+1.8
lib.player_input(0,4,1,0,0,0)
for _ in range(30):
    lib.player_tick()
    assert lib.terrain_blocked(C.c_float(p.x),C.c_float(p.z),0)==0
# A real solid wall prevents rifle damage and enemy threats in both directions.
p=reset();p.x,p.z=3970,1300;p.y=lib.terrain_height(p.x,p.z)+1.8
place_enemy(4030,1300)
yaw,pitch=aim(p,4030,1300)
lib.player_input(0,1,0,0,yaw,pitch)
tick.value=16
for _ in range(10):lib.player_tick()
assert p.hp==100 and p.hits==0 and entities[1].hp==100
# Living enemies suppress and kill; dead players cannot move or fire.
p=reset();place_enemy(3900,2080)
# The former fixture called player_tick ten times at the same world tick,
# bypassing a real weapon cadence. Advance genuine fixed world ticks instead.
for _ in range(240):
    lib.sim_tick()
    if p.hp==0:break
assert p.hp==0 and 0<p.respawn<=30 and p.suppression>0
x,z,shots=p.x,p.z,p.shots
lib.player_input(0,5,1,1,0,0);lib.player_tick()
assert (p.x,p.z,p.shots)==(x,z,shots)
for _ in range(p.respawn):lib.sim_tick()
assert p.hp==100 and p.respawn==0 and p.generation==2
assert math.hypot(p.x-3900,p.z-2080)>160
# When all connected deployment sites are unavailable, do not spawn into danger.
p=reset();lib.player_leave(0)
for i in range(12):sites[i*8+5]=0
assert lib.player_join(0,1)==0 and players[0].hp==0
for _ in range(35):lib.player_tick()
assert players[0].hp==0
# Simulation initialization clears all player state, and intent participates in replay hash.
lib.sim_init(2,1)
assert all(p.connected==0 for p in players), 'sim_init must own player reset'
assert lib.player_join(0,1)==0
h=lib.sim_checksum()
lib.player_input(0,0,1,0,0,0)
assert lib.sim_checksum()!=h, 'replay must include authoritative player intent'
x=players[0].x
lib.sim_tick()
assert players[0].x>x, 'sim_tick must advance real player input'
print('PASS: player validation, fixed-tick movement, rifle LOS/cadence/reload, suppression/death, safe redeployment and replay state')

# Actual production movement: crouch eye/speed, normalized diagonals and sprint override.
p=reset();base=lib.terrain_height(p.x,p.z);x,z=p.x,p.z
assert lib.player_input(0,32|4,1,0,0,0)==0
for _ in range(30):lib.player_tick()
assert abs(p.x-x-2.5)<.02 and abs(p.y-lib.terrain_height(p.x,p.z)-1.1)<.0001
assert motion[0].grounded==1 and motion[0].eye==C.c_float(1.1).value
p=reset();x,z=p.x,p.z
lib.player_input(0,0,1,1,0,0)
for _ in range(30):lib.player_tick()
assert abs(math.hypot(p.x-x,p.z-z)-5)<.02, 'diagonal must retain walk speed'
# Jump parabola is world-space at30Hz:6m/s takeoff,9.8m/s² gravity, exact landing.
p=reset();base=lib.terrain_height(p.x,p.z);lib.player_input(0,64,0,0,0,0)
heights=[]
for _ in range(90):
    lib.player_tick();heights.append(p.y-base-1.8)
    assert math.isfinite(p.y) and p.y>=base+1.8-1e-5
assert .19<heights[0]<.21 and 1.9<max(heights)<2.0
assert heights[19]<heights[18] and abs(heights[37])<.0001
assert all(abs(y)<.0001 for y in heights[38:]), 'held jump must not bunny-hop'
assert motion[0].grounded==1 and motion[0].step==0
lib.player_input(0,0,0,0,0,0);lib.player_tick()
lib.player_input(0,64,0,0,0,0);lib.player_tick()
assert motion[0].grounded==0 and p.y>base+1.99
# Crouch in flight adjusts eye only, never foot trajectory. A crouched jump is
# consumed rather than deferred until the player stands while holding the key.
feet=motion[0].feet
lib.player_input(0,32|64,0,0,0,0);lib.player_tick()
assert motion[0].feet>feet and abs(p.y-motion[0].feet-1.1)<.0001
p=reset();lib.player_input(0,32|64,0,0,0,0);lib.player_tick()
lib.player_input(0,64,0,0,0,0);lib.player_tick()
assert motion[0].grounded==1
# Uphill/downhill travel follows the actual terrain while grounded; airborne
# feet follow gravity independently of its gradient, then clamp at touchdown.
p=reset();p.x,p.z=3200,4000;p.y=lib.terrain_height(p.x,p.z)+1.8
lib.player_input(0,4,1,0,0,0)
for _ in range(60):
    lib.player_tick();assert abs(p.y-lib.terrain_height(p.x,p.z)-1.8)<.0001
lib.player_input(0,64|4,1,0,0,0)
lib.player_tick();feet=motion[0].feet;step=motion[0].step
lib.player_tick();assert abs(motion[0].feet-feet-step)<.0001
for _ in range(60):lib.player_tick()
assert motion[0].grounded==1 and abs(p.y-lib.terrain_height(p.x,p.z)-1.8)<.0001
# Jump/crouch cannot bypass swept solids and do not increase planar speed.
p=reset();p.x,p.z=3987.9,1300;p.y=lib.terrain_height(p.x,p.z)+1.8
lib.player_input(0,64|4,1,0,0,0)
for _ in range(60):
    x,z=p.x,p.z;lib.player_tick()
    assert lib.terrain_blocked(C.c_float(p.x),C.c_float(p.z),0)==0
    assert math.hypot(p.x-x,p.z-z)<.301
# Invalid private velocity/feet are repaired to grounded, and malformed actual
# positions enter safe redeployment without reaching terrain withNaN/Inf.
for field in ('step','feet'):
    for invalid in (float('nan'),float('inf'),float('-inf'),1e30):
        p=reset();lib.player_tick();setattr(motion[0],field,invalid)
        lib.player_tick();assert motion[0].grounded==1 and math.isfinite(p.y)
for field in ('x','y','z'):
    p=reset();setattr(p,field,float('nan'));lib.player_tick()
    assert p.hp==0 and p.respawn==30 and motion[0].initialized==0
    assert all(math.isfinite(getattr(p,k)) for k in ('x','y','z'))
    for _ in range(30):lib.player_tick()
    assert p.hp==100 and all(math.isfinite(getattr(p,k)) for k in ('x','y','z'))
# Slot reuse, initialization, generation changes and death reset flight state.
p=reset();lib.player_input(0,64,0,0,0,0);lib.player_tick()
assert motion[0].grounded==0
assert lib.player_leave(0)==0 and bytes(motion[0])==bytes(32)
assert lib.player_join(0,1)==0 and bytes(motion[0])==bytes(32)
lib.player_tick();assert motion[0].grounded==1
lib.player_input(0,64,0,0,0,0);lib.player_tick();p.hp=0;p.respawn=1
lib.player_tick();assert p.hp==100 and motion[0].initialized==0
lib.player_tick();assert motion[0].grounded==1, 'held jump through death must require release'
# Boarded jump/crouch never applies infantry altitude. Existing vehicle mask in
# this isolated patch rejects newmovement bits for drive; root must widen to127.
p=reset();entities[0].x,entities[0].z=p.x,p.z;entities[0].kind=1
lib.ground_init() # Complete the initial role-changing birth before boarding.
assert lib.vehicle_enter(0)==0
lib.player_input(0,64|32,0,0,0,0);lib.player_tick()
assert motion[0].initialized==0 and motion[0].latch==64
assert lib.vehicle_exit(0)==0
lib.player_tick();assert motion[0].grounded==1
# Hash covers private momentum, latch and generation; deterministic input replay.
p=reset();lib.player_tick();h=lib.sim_checksum();motion[0].step=.01
assert lib.sim_checksum()!=h

def movement_replay():
    reset(8192)
    for n in range(90):
        bits=64 if n<45 else (32|4 if n<70 else 0)
        assert lib.player_input(0,bits,.6,.8,.1,.2)==0
        lib.sim_tick()
    return lib.sim_checksum(),bytes(players),bytes(motion)
assert movement_replay()==movement_replay()
print('PASS: crouch eye/speed/sprint override, normalized movement,30Hz jump parabola/edge/gravity/landing, terrain slopes/solids, malformed motion/positions, death/reuse/boarding, authoritative replay')
