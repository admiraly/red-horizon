#!/usr/bin/env python3
"""Observed outcomes over the actual NASM world/terrain/controller/player loop."""
import ctypes as C
import sys
import math
import json
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
# Before a scout surveys a hidden site, support already approaches; no enemy
# position appears in shared intelligence through the opaque central wall.
reset()
scout=unit(0,3950,1300,kind=1,hp=400)
cover=unit(1,3950,1400)
defender=unit(17,5000,1300,side=1)
assert lib.sim_order(1,0,1)==0
staging=(cover.x,cover.z)
ticks(300)
assert cover.x>staging[0] and (cover.x,cover.z)!=staging
assert defender.hp==100 and fronts[3]==0  # confidence stays0 without sighting
assert scout.x!=3950 or scout.z!=1300
assert lib.terrain_blocked(C.c_float(scout.x),C.c_float(scout.z),1)==0
# The real scout circumvents the solid, sees/kills the defender, reaches the
# objective and captures it. This is not a state-name-only assertion.
ticks(4000)
assert defender.hp==0 and sites[2].owner==0 and supply[0]>=700
# Squads approach on opposing flank corridors without a stationary gate.
reset()
unit(0,4800,1300,kind=1,hp=400)
left=unit(1,3500,1300)
right=unit(17,3500,1300)
ticks(89)
assert left.z<1300 and right.z>1300 and left.x>3500 and right.x>3500
left_staged=(left.x,left.z)
ticks(30)
assert right.z>1300 and left.x>left_staged[0]
# Acquired visible targets permit short alternating firing dwells, not
# indefinite combat stalls. The peer squad continues its physical bound.
reset()
left=unit(1,3500,1000)
right=unit(17,3500,1700)
unit(20,3550,1000,side=1)
unit(21,3550,1700,side=1)
assert lib.sim_order(1,0,1)==0
ticks(1)
left_first=(left.x,left.z)
right_first=(right.x,right.z)
ticks(9)
assert left.target!=-1 and right.target!=-1
assert (left.x,left.z)==left_first and (right.x,right.z)!=right_first
ticks(10)
assert (left.x,left.z)!=left_first
ticks(40)
right_dwell=(right.x,right.z)
left_dwell=(left.x,left.z)
ticks(5)
assert (right.x,right.z)==right_dwell and (left.x,left.z)!=left_dwell
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
# Actual default battles, not selected fixture actors: both sides/all fronts
# must broadly advance, including the player's initial visible ground bubble.
class Player(C.Structure):
    _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
players=(Player*4).in_dll(lib,'sim_players')
lib.terrain_blocked.argtypes=[C.c_float,C.c_float,C.c_uint]
evidence=[]
def default_run(count, record=False):
    assert lib.sim_init(count,42)==0 and lib.player_join(0,1)==0
    initial=[(e.x,e.z) for e in entities[:count]]
    for tick in range(1,301):
        lib.sim_tick()
        if tick not in (30,120,300):continue
        rows=[]
        for side in (0,1):
            for front in range(3):
                actors=[(i,e) for i,e in enumerate(entities[:count]) if e.hp and e.kind!=3 and e.side==side and e.front==front]
                distance=[math.hypot(e.x-initial[i][0],e.z-initial[i][1]) for i,e in actors]
                progress=[(e.x-initial[i][0])*(1 if side==0 else -1) for i,e in actors]
                threshold=1 if tick==30 else 5
                assert len(actors)>count//12
                assert sum(d>threshold for d in distance)>=len(actors)*.95, (count,tick,side,front,min(distance),max(distance))
                if tick==300:
                    assert sum(p>10 for p in progress)>=len(actors)*.90
                assert all(lib.terrain_blocked(e.x,e.z,e.kind)==0 for _,e in actors)
                rows.append(round(sum(distance)/len(distance),3))
        near=[(i,e) for i,e in enumerate(entities[:count]) if e.hp and e.kind!=3 and e.front==1 and math.hypot(e.x-players[0].x,e.z-players[0].z)<256]
        moved=sum(math.hypot(e.x-initial[i][0],e.z-initial[i][1])>1 for i,e in near)
        assert len(near)>100 and moved>=len(near)*.95
        if record:evidence.append(dict(units=count,tick=tick,mean_ground_metres_by_front=rows,player_bubble_ground=len(near),player_bubble_moving=moved))
    return lib.sim_checksum()
first=default_run(8192,True)
assert default_run(8192)==first
# The same broad movement and collision expectations apply at the stretch cap.
default_run(16384,True)
# Real controller + terrain recovery from a wall face: both direct scout and
# flank support armour cross around a solid without teleporting or getting stuck.
reset()
scout=unit(0,3985,1300,kind=1,hp=400)
support=unit(1,3985,1330,kind=1,hp=400)
for _ in range(1200):
    before=[(e.x,e.z) for e in (scout,support)]
    lib.sim_tick()
    for e,(x,z) in zip((scout,support),before):
        assert math.hypot(e.x-x,e.z-z)<=.501
        assert lib.terrain_blocked(e.x,e.z,e.kind)==0
assert scout.x>4050 and support.x>4050
print('PASS: physical scouting/support, real obstacle/defender defeat/capture, flank approach, observed-threat retreat, supply withdrawal, explicit override, wall recovery and default 8k/16k motion/replay')
print(json.dumps(dict(suite='tactics-default-motion',passed=True,evidence=evidence)))
