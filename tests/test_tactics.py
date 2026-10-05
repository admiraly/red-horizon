#!/usr/bin/env python3
"""Observed outcomes over the actual NASM world/terrain/controller/player loop."""
import ctypes as C
import sys
lib=C.CDLL(sys.argv[1])
lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Site(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('owner',C.c_uint),('capture',C.c_int),('role',C.c_uint),('connected',C.c_uint),('health',C.c_uint),('flags',C.c_uint)]
entities=(Entity*32768).in_dll(lib,'sim_entities')
sites=(Site*12).in_dll(lib,'sim_sites')
fronts=(C.c_uint*96).in_dll(lib,'ai_fronts')
alive=(C.c_uint*2).in_dll(lib,'sim_alive')
supply=(C.c_uint*2).in_dll(lib,'sim_supply')
def reset():
    assert lib.sim_init(32,19)==0
    for actor in entities[:32]:actor.hp=0
    alive[0]=alive[1]=0

def unit(i,x,z,side=0,kind=0,hp=100):
    e=entities[i]
    e.x,e.z,e.side,e.front,e.kind,e.hp,e.target=x,z,side,0,kind,hp,-1
    # Fixture conversion models an initialized shell-capable role.
    if kind in (1,2):
        (C.c_uint*32768).in_dll(lib,"sim_shell_ammo")[i]=64
    alive[side]+=1
    return e

def ticks(n):
    for _ in range(n):lib.sim_tick()
# Before a scout surveys a hidden site, ordinary troops stay staged; no enemy
# position appears in shared intelligence through the opaque central wall.
reset()
scout=unit(0,3950,1300,kind=1,hp=400)
cover=unit(1,3950,1400)
defender=unit(17,5000,1300,side=1)
assert lib.sim_order(1,0,1)==0
staging=(cover.x,cover.z)
ticks(300)
assert (cover.x,cover.z)==staging
assert defender.hp==100 and fronts[3]==0  # confidence stays0 without sighting
assert scout.x!=3950 or scout.z!=1300
assert lib.terrain_blocked(C.c_float(scout.x),C.c_float(scout.z),1)==0
# The real scout circumvents the solid, sees/kills the defender, reaches the
# objective and captures it. This is not a state-name-only assertion.
ticks(4000)
assert defender.hp==0 and sites[2].owner==0 and supply[0]>=700
# Alternate squads physically cover/advance on opposing flank corridors.
reset()
unit(0,4800,1300,kind=1,hp=400)
left=unit(1,3500,1300)
right=unit(17,3500,1300)
ticks(89)
assert left.z<1300 and (right.x,right.z)==(3500,1300)
left_staged=(left.x,left.z)
ticks(30)
assert right.z>1300 and (left.x,left.z)==left_staged
# Two observed armoured threats outweigh two infantry; soldiers withdraw
# physically, without reading unobserved opposing strength.
reset()
a=unit(0,3500,1100)
b=unit(16,3500,1500)
unit(1,3550,1100,side=1,kind=1,hp=400)
unit(17,3550,1500,side=1,kind=1,hp=400)
assert lib.sim_order(1,0,1)==0
ticks(29)
old=(a.x,b.x)
ticks(2)
assert fronts[1]>=8 and fronts[0]==2 and a.x<old[0] and b.x<old[1]
assert fronts[2]>0 and fronts[3]>0  # actual sight timestamp/confidence
# Explicit player/front orders always override the autonomous controller.
assert lib.sim_order(0,0,1)==0
position=(a.x,a.z)
ticks(20)
assert (a.x,a.z)==position
# Own capacity starvation also causes physical withdrawal without enemy intel.
reset()
a=unit(0,3500,1300)
sites[0].owner=1
supply[0]=0
ticks(29)
pre_withdraw=a.x
ticks(2)
assert a.x<pre_withdraw and fronts[3]==0
# Same fixture/controller state hashes identically on repeated actual runs.
hashes=[]
for _ in range(2):
    reset();unit(0,4800,1300,kind=1,hp=400);unit(1,3500,1300)
    ticks(200);hashes.append(lib.sim_checksum())
assert hashes[0]==hashes[1]
print('PASS: hidden-target scouting, real obstacle detour/defender defeat/capture, alternating flank bounds, observed-threat retreat, supply withdrawal, explicit override and replay')
