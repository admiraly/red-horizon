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
lib.ground_eye.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*3;lib.ground_eye.restype=C.c_int
def supported_eye(actor=12):
    out=(C.c_float*3)();motion=(C.c_float*(32768*8)).in_dll(lib,'sim_ground_motion');e=entities[actor]
    assert lib.ground_eye(out,1,12,e.x,e.z,motion[actor*8])==0
    return tuple(out)


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

# Explicit paved interior retains the original 18m steady road-driving gate.
p,e=reset(3500,1300)
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
# The ownership negative leaves a real unboarded human inside the hull footprint.
# Driving toward that peer must hold, then the free-drive test moves it clear.
blocked=e.x,e.z
assert lib.vehicle_tick_player(0,0,1,0)==1 and (e.x,e.z)==blocked
players[1].x,players[1].z=e.x-6,e.z+10
players[1].y=lib.terrain_height(players[1].x,players[1].z)+1.8
start=e.x,e.z
acceleration_steps=[]
for _ in range(30):
    old=e.x,e.z
    assert lib.vehicle_tick_player(0,0,1,0)==1
    acceleration_steps.append(math.hypot(e.x-old[0],e.z-old[1]))
# Real armor accelerates instead of translating18m from rest in one second.
assert 0<acceleration_steps[0]<.1,acceleration_steps
assert all(a<=b+.001 for a,b in zip(acceleration_steps,acceleration_steps[1:])),acceleration_steps
assert all(0<=b-a<.03 for a,b in zip(acceleration_steps,acceleration_steps[1:])),acceleration_steps
acceleration_distance=math.hypot(e.x-start[0],e.z-start[1])
assert 6<acceleration_distance<12,(start,e.x,e.z,acceleration_steps)
# Retain the original18m steady drive gate after the measured acceleration phase.
start=e.x
for _ in range(30):assert lib.vehicle_tick_player(0,0,1,0)==1
assert abs(e.x-start-18)<.02
assert max(abs(a-b) for a,b in zip((p.x,p.y,p.z),supported_eye()))<.00001
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
# Actual cannon yaw/pitch in all quadrants preserves300m/s and aim direction.
class Shell(C.Structure):
    _fields_=[(n,C.c_float)for n in('x','y','z','vx','vy','vz')]+[('tail',C.c_byte*40)]
shells=(Shell*512).in_dll(lib,'sim_projectiles')
for yaw in (0,math.pi/2,math.pi,-math.pi/2,math.pi/4,-3*math.pi/4):
    for pitch in (-1.3,0,.5,1.3):
        p,e=reset();assert lib.vehicle_enter(0)==0
        p.yaw,p.pitch=yaw,pitch
        assert lib.vehicle_tick_player(0,1,0,0)==1
        shell=shells[0]
        assert abs(math.hypot(shell.vx,shell.vy,shell.vz)-10)<.0001,(yaw,pitch,shell.vx,shell.vy,shell.vz)
        # Forward unit direction dotted with the real shot must stay aligned.
        direction=(math.cos(pitch)*math.sin(yaw),math.sin(pitch),math.cos(pitch)*math.cos(yaw))
        assert sum(a*b for a,b in zip(direction,(shell.vx,shell.vy,shell.vz)))>9.999
        assert p.shots==0 and shots[0]==1 and ammo[12]==63
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
# Invalid direct interactions must preserve the world and NOT consume edges.
# A subsequent valid held ENTER/EXIT proves private history was left untouched.
def vehicle_state():
    return (bytes(players),bytes(vehicles),bytes(mapping),bytes(owners),bytes(shots),
            bytes(ammo),bytes(cooldown),bytes(events),sequence.value,
            C.c_uint.in_dll(lib,'player_deaths').value,lib.sim_checksum())

for buttons,wx,wz in [(8,math.nan,0),(136,0,0),(8,0,math.inf),(8,2,0)]:
    p,e=reset()
    before=vehicle_state()
    assert lib.vehicle_tick_player(0,buttons,wx,wz)==0
    assert vehicle_state()==before, 'invalid detached ENTER modified authoritative state'
    assert lib.vehicle_tick_player(0,8,0,0)==1 and mapping[0]==12
    assert vehicles[0].generation==1, 'invalid ENTER consumed private interaction edge'
    before=vehicle_state()
    assert lib.vehicle_tick_player(0,16,math.nan,0)==1
    assert vehicle_state()==before, 'invalid boarded EXIT modified authoritative state'
    assert lib.vehicle_tick_player(0,144,0,0)==1
    assert vehicle_state()==before, 'unknown EXIT flags modified authoritative state'
    assert lib.vehicle_tick_player(0,16,0,0)==0 and mapping[0]==-1
    assert vehicles[0].generation==1, 'invalid EXIT consumed private interaction edge'
# Restore held-edge lifecycle fixture used by destruction checks below.
p,e=reset();assert lib.vehicle_tick_player(0,8,0,0)==1
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
print(json.dumps({'suite':'vehicles','passed':True,'actual_steady_drive_metres_per_second':18,'first30tick_acceleration_metres':acceleration_distance,
                  'exclusive_ownership':True,'generation_cleanup':True,'safe_exit':True,
                  'persistent_cannon_ammo':True,'swept_shell_damage':True,'single_destruction_event':True,
                  'fixtures':'real assembly; development-only initial state setup'}))
