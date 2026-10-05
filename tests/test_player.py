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
players=(Player*4).in_dll(lib,'sim_players')
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
for args in [(0,8,0,0,0,0),(4,0,0,0,0,0),(0,0,float('nan'),0,0,0),(0,0,0,0,float('inf'),0),(0,0,0,0,0,2),(0,0,2,0,0,0)]:
    before=bytes(players)
    assert lib.player_input(*args)==-1 and bytes(players)==before
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
# A real solid wall prevents rifle damage and enemy threats in both directions.
p=reset();p.x,p.z=3970,1300;p.y=lib.terrain_height(p.x,p.z)+1.8
place_enemy(4030,1300)
yaw,pitch=aim(p,4030,1300)
lib.player_input(0,1,0,0,yaw,pitch)
tick.value=16
for _ in range(10):lib.player_tick()
assert p.hp==100 and p.hits==0 and entities[1].hp==100
# Living enemies suppress and kill; dead players cannot move or fire.
p=reset();place_enemy(3900,2080);tick.value=16
for _ in range(10):lib.player_tick()
assert p.hp==0 and p.respawn==30 and p.suppression>0
x,z,shots=p.x,p.z,p.shots
lib.player_input(0,5,1,1,0,0);lib.player_tick()
assert (p.x,p.z,p.shots)==(x,z,shots)
for _ in range(29):lib.player_tick()
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
print('PASS: player validation, fixed-tick movement, rifle LOS/cadence/reload, suppression/death, safe redeployment and replay state')
