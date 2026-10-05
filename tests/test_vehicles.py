#!/usr/bin/env python3
"""Real assembly vehicle, terrain and moving cannon projectile outcomes."""
import ctypes as C
import json
import math
import pathlib
import sys
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()))
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Player(C.Structure):
    _fields_=[(n,C.c_float)for n in('x','y','z','yaw','pitch')]+[(n,C.c_uint)for n in('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
class Vehicle(C.Structure):
    _fields_=[('entity',C.c_uint),('entity_generation',C.c_uint),('driver',C.c_uint),('active',C.c_uint),('ammo',C.c_uint),('cooldown',C.c_uint),('generation',C.c_uint),('flags',C.c_uint)]
class Event(C.Structure):
    _fields_=[(n,C.c_float)for n in('x','y','z')]+[(n,C.c_uint)for n in('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
entities=(Entity*32768).in_dll(lib,'sim_entities')
players=(Player*4).in_dll(lib,'sim_players')
vehicles=(Vehicle*4).in_dll(lib,'sim_vehicles')
mapping=(C.c_int*4).in_dll(lib,'sim_player_vehicle')
owners=(C.c_int*32768).in_dll(lib,'vehicle_entity_driver')
shots=(C.c_uint*4).in_dll(lib,'vehicle_shots')
ammo=(C.c_uint*32768).in_dll(lib,'sim_shell_ammo')
cooldown=(C.c_uint*32768).in_dll(lib,'sim_shell_cooldown')
events=(Event*256).in_dll(lib,'sim_events')
sequence=C.c_uint.in_dll(lib,'sim_event_sequence')
lib.terrain_height.argtypes=[C.c_float,C.c_float];lib.terrain_height.restype=C.c_float
lib.terrain_blocked.argtypes=[C.c_float,C.c_float,C.c_uint];lib.terrain_blocked.restype=C.c_int
lib.vehicle_tick_player.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.sim_checksum.restype=C.c_uint64


def reset(x=3500,z=2000):
    assert lib.sim_init(32,42)==0
    lib.vehicle_init()
    for i,e in enumerate(entities[:32]):
        e.x,e.z,e.hp=1000 if i<16 else 7000,7000,0
    e=entities[12];e.x,e.z,e.hp,e.kind,e.side=x,z,400,1,0
    for side in(0,1):
        for front in range(3):assert lib.sim_order(side,front,1)==0
    lib.sim_tick() # Real spatial grid for projectile/blast query.
    assert lib.player_join(0,0)==0
    p=players[0];p.x,p.z=x+2,z;p.y=lib.terrain_height(p.x,p.z)+1.8
    return p,e

p,e=reset()
assert list(mapping)==[-1]*4 and all(o==-1 for o in owners)
assert [v.driver for v in vehicles]==list(range(4))
assert lib.vehicle_enter(4)==-1 and lib.vehicle_exit(4)==-1
lib.vehicle_detach(4)
assert lib.vehicle_enter(0)==0 and mapping[0]==12 and owners[12]==0
assert vehicles[0].active==1 and vehicles[0].entity_generation==e.generation
assert lib.vehicle_enter(0)==-1
assert lib.player_join(1,0)==0
players[1].x,players[1].z=e.x+2,e.z;players[1].y=p.y
assert lib.vehicle_enter(1)==-1 and mapping[1]==-1 and owners[12]==0
start=e.x
for _ in range(30):assert lib.vehicle_tick_player(0,0,1,0)==1
assert abs(e.x-start-18)<.02 and p.x==e.x and p.z==e.z
assert abs(p.y-lib.terrain_height(e.x,e.z)-3)<.001
for x,z in[(math.nan,0),(math.inf,0),(2,0),(0,-2)]:
    before=bytes(p),bytes(e)
    assert lib.vehicle_tick_player(0,0,x,z)==1 and (bytes(p),bytes(e))==before
# Camera yaw/pitch aim fires physical shared shells; rifle counters untouched.
rifle=p.shots,p.hits,p.ammo
p.yaw,p.pitch=0,0
before_ammo=ammo[12]
assert lib.vehicle_tick_player(0,1,0,0)==1
assert shots[0]==1 and ammo[12]==before_ammo-1 and cooldown[12]==30
assert vehicles[0].ammo==ammo[12] and vehicles[0].cooldown==30
assert (p.shots,p.hits,p.ammo)==rifle and any(ev.kind==1 for ev in events)
assert lib.vehicle_tick_player(0,1,0,0)==1 and shots[0]==1
assert lib.vehicle_exit(0)==0 and mapping[0]==-1 and owners[12]==-1
assert abs(p.x-e.x)>=5.9 and lib.terrain_blocked(p.x,p.z,0)==0
p.x,p.z=e.x+2,e.z;p.y=lib.terrain_height(p.x,p.z)+1.8
assert lib.vehicle_enter(0)==0 and ammo[12]==before_ammo-1 and cooldown[12]==30
assert lib.vehicle_tick_player(0,1,0,0)==1 and shots[0]==1,'reboarding reset persistent cannon cadence'
# Nearby enemy armor and nonarmor cannot be boarded; disconnected/dead reject.
p,e=reset();e.side=1
assert lib.vehicle_enter(0)==-1
e.side,e.kind=0,0
assert lib.vehicle_enter(0)==-1
e.kind=1;p.x=e.x+8.01
assert lib.vehicle_enter(0)==-1
p.x=e.x+2;p.hp=0
assert lib.vehicle_enter(0)==-1
p.hp=100;p.connected=0
assert lib.vehicle_enter(0)==-1
# Interaction holds are consumed once. Holding ENTER after EXIT cannot reboard.
p,e=reset()
assert lib.vehicle_tick_player(0,8,0,0)==1
assert lib.vehicle_tick_player(0,8,0,0)==1 and vehicles[0].generation==1
assert lib.vehicle_tick_player(0,24,0,0)==0
assert lib.vehicle_tick_player(0,8,0,0)==0
assert lib.vehicle_tick_player(0,0,0,0)==0
assert lib.vehicle_tick_player(0,8,0,0)==1 and vehicles[0].generation==2
# Owned hull destruction kills driver once and emits one actual cosmetic event.
before_deaths=C.c_uint.in_dll(lib,'player_deaths').value
before_events=sequence.value
e.hp=0
assert lib.vehicle_tick_player(0,1,0,0)==1
assert p.hp==0 and p.respawn==30 and mapping[0]==-1 and owners[12]==-1
assert C.c_uint.in_dll(lib,'player_deaths').value==before_deaths+1
assert sequence.value==before_events+1 and events[sequence.value&255].kind==5
assert lib.vehicle_tick_player(0,1,0,0)==0 and sequence.value==before_events+1
# Recycling entity IDs releases old ownership without killing the new actor.
p,e=reset();assert lib.vehicle_enter(0)==0
e.generation+=1
assert lib.vehicle_tick_player(0,0,0,0)==0 and p.hp==100 and owners[12]==-1
p,e=reset();assert lib.vehicle_enter(0)==0
p.connected=0
assert lib.vehicle_tick_player(0,0,0,0)==0 and owners[12]==-1 and mapping[0]==-1
p,e=reset();assert lib.vehicle_enter(0)==0
lib.vehicle_detach(0)
assert mapping[0]==-1 and owners[12]==-1 and vehicles[0].driver==0
# Wall clearance prevents crossing the authored wall with a driven tank.
p,e=reset(x=3980,z=1300)
assert lib.vehicle_enter(0)==0
for _ in range(30):lib.vehicle_tick_player(0,0,1,0)
assert not (3988<=e.x<=4012 and 1100<=e.z<=1500)
# All eight exit candidates occupied: rejected exit preserves every claim.
p,e=reset();assert lib.vehicle_enter(0)==0
for i,(dx,dz) in enumerate([(-6,0),(6,0),(0,-6),(0,6),(-6,-6),(6,6),(-6,6),(6,-6)]):
    entities[i].x,entities[i].z,entities[i].hp=e.x+dx,e.z+dz,100
before=bytes(p),bytes(vehicles[0])
assert lib.vehicle_exit(0)==-1 and (bytes(p),bytes(vehicles[0]))==before and owners[12]==0
for i in range(8):entities[i].hp=0
assert lib.vehicle_exit(0)==0 and owners[12]==-1
# Cannon launches are stopped by physical terrain and the real swept actor query.
p,e=reset(x=3970,z=1300);assert lib.vehicle_enter(0)==0
p.yaw,p.pitch=math.pi/2,0
lib.vehicle_tick_player(0,1,0,0)
for _ in range(20):lib.projectile_tick()
assert any(ev.kind==3 and 3970<ev.x<3988.01 for ev in events)
p,e=reset();entities[16].x,entities[16].z,entities[16].hp=e.x,e.z+60,100
lib.sim_tick();p.x,p.z=e.x+2,e.z;p.y=lib.terrain_height(p.x,p.z)+1.8
assert lib.vehicle_enter(0)==0
p.yaw,p.pitch=0,0
lib.vehicle_tick_player(0,1,0,0)
for _ in range(15):lib.projectile_tick()
assert entities[16].hp<100 and any(ev.kind==3 for ev in events)
print(json.dumps({'suite':'vehicles','passed':True,'actual_drive_metres_per_second':18,
                  'exclusive_ownership':True,'generation_cleanup':True,'safe_exit':True,
                  'persistent_cannon_ammo':True,'swept_shell_damage':True,'single_destruction_event':True,
                  'fixtures':'real assembly; development-only initial state setup'}))
