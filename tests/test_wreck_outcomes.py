#!/usr/bin/env python3
"""Observe real casualty hooks through production combat/player/tick APIs."""
import argparse,ctypes as C,hashlib,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('library');a=p.parse_args();path=Path(a.library).resolve();lib=C.CDLL(str(path))
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class P(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
entities=(E*32768).in_dll(lib,'sim_entities');players=(P*4).in_dll(lib,'sim_players');wrecks=(W*1024).in_dll(lib,'sim_wrecks');alive=(C.c_uint*2).in_dll(lib,'sim_alive');ammo=(C.c_uint*32768).in_dll(lib,'sim_shell_ammo');V=(C.c_int*4).in_dll(lib,'sim_player_vehicle');count=C.c_uint.in_dll(lib,'sim_wreck_count');seq=C.c_uint.in_dll(lib,'sim_wreck_sequence');tick=C.c_uint.in_dll(lib,'sim_tick_count');lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_air_damage.argtypes=[C.c_uint,C.c_uint];lib.sim_order.argtypes=[C.c_uint]*3;lib.projectile_launch.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*3;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.vehicle_tick_player.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];lib.sim_checksum.restype=C.c_uint64
rows=[]
def reset():
 assert lib.sim_init(32,42)==0
 for e in entities[:32]:e.hp=0
 alive[0]=alive[1]=0;C.c_uint.in_dll(lib,'hazard_enabled').value=0
 for side in (0,1):
  for front in range(3):assert lib.sim_order(side,front,1)==0
 assert count.value==seq.value==0

def birth(i,kind=1,side=0,hp=400,x=3500,z=2000):
 e=entities[i];e.x,e.z,e.hp,e.kind,e.side,e.front,e.target=x,z,hp,kind,side,0,-1;alive[side]+=1;return e

def check(e,i,birth_tick):
 w=next(w for w in wrecks if w.flags&1 and w.entity==i and w.generation==e.generation)
 assert w.x==e.x and w.z==e.z and w.kind==e.kind and w.side==e.side
 assert w.birth==birth_tick and w.expiry==(birth_tick+1800)&0xffffffff and w.sequence>0
 assert all(math.isfinite(q) for q in (w.x,w.y,w.z,w.heading,w.pitch,w.bank)) and w.reserved0==w.reserved1==0
 return w

for kind in (1,2):
 for side in (0,1):
  reset();e=birth(12,kind,side,hp=2);lib.ground_init();before=(e.x,e.z,e.generation)
  lib.sim_air_damage(12,1);assert e.hp==1 and count.value==0 and alive[side]==1
  lib.sim_air_damage(12,1);assert e.hp==0 and alive[side]==0 and count.value==seq.value==1
  w=check(e,12,0);saved=bytes(w);checksum=lib.sim_checksum();lib.sim_air_damage(12,1000)
  assert bytes(w)==saved and count.value==seq.value==1 and lib.sim_checksum()==checksum
  assert (e.x,e.z,e.generation)==before
  rows.append(dict(path='shared_projectile_damage',kind=kind,side=side,duplicate_preserved=True,pose_flags=w.flags))
# Infantry and aircraft casualties do not become ground wrecks.
for kind in (0,3):
 reset();e=birth(12,kind=kind,hp=1);lib.sim_air_damage(12,1)
 assert e.hp==0 and alive[0]==0 and count.value==seq.value==0
 rows.append(dict(path='excluded_role',kind=kind))
# Real staggered infantry damage reaches the deferred ground apply loop.
reset();victim=birth(12,hp=1);shooter=birth(16,kind=0,side=1,hp=100,x=3550);ammo[12]=0;lib.ground_init()
for _ in range(16):
 lib.sim_tick()
 if not victim.hp:break
assert victim.hp==0 and shooter.hp==100 and count.value==seq.value==1 and alive[0]==0 and alive[1]==1
w=check(victim,12,tick.value);assert victim.target==-1 or victim.target==16
rows.append(dict(path='deferred_infantry_combat',death_tick=tick.value,shooter_hp=shooter.hp,registered_entity=w.entity))
# Real tank projectile flight/impact/blast reaches the shared casualty hook.
reset();source=birth(12,hp=400);victim=birth(14,kind=2,side=1,hp=80,x=3550);lib.ground_init();ammo[12]=ammo[14]=0;lib.sim_tick();ammo[12]=1
assert lib.projectile_launch(12,1,victim.x,lib.terrain_height(victim.x,victim.z)+3,victim.z)==0 and ammo[12]==0
for _ in range(30):
 lib.sim_tick()
 if not victim.hp:break
assert victim.hp==0 and source.hp==400 and count.value==seq.value==1 and ammo[12]==0
w=check(victim,14,tick.value);rows.append(dict(path='actual_tank_shell_impact_blast',death_tick=tick.value,source_hp=source.hp,registered_entity=w.entity))
# Boarded destruction captures a wreck once and retains genuine crew cleanup.
reset();e=birth(12);lib.ground_init();assert lib.player_join(0,0)==0;players[0].x=e.x+2;players[0].z=e.z;players[0].y=lib.terrain_height(players[0].x,players[0].z)+1.8;assert lib.vehicle_enter(0)==0
lib.sim_air_damage(12,400);saved=bytes(wrecks[0]);before_ammo=ammo[12]
assert lib.vehicle_tick_player(0,1,0,0)==1 and V[0]==-1 and players[0].hp==0 and players[0].respawn==30
assert bytes(wrecks[0])==saved and count.value==seq.value==1 and ammo[12]==before_ammo
assert lib.vehicle_tick_player(0,1,0,0)==0 and count.value==1
rows.append(dict(path='boarded_casualty_cleanup',crew_dead=True,claim_released=True,duplicate_wreck=False))
# Genuine world ticks expire the wreck at its boundary; no private clock writes.
reset();e=birth(12);lib.ground_init();lib.sim_air_damage(12,400);saved=bytes(wrecks[0])
for _ in range(1799):lib.sim_tick()
assert count.value==1 and bytes(wrecks[0])==saved
lib.sim_tick();assert count.value==0 and not wrecks[0].flags&1 and tick.value==1800
assert lib.wreck_register(12)==1
rows.append(dict(path='world_lifetime',expiry_tick=tick.value,active_count=count.value))
# Canonical reset and actual replay include registry state; no covert damage changes.
def replay():
 reset();e=birth(12);lib.ground_init();lib.sim_air_damage(12,400)
 for _ in range(16):lib.sim_tick()
 return bytes(wrecks),lib.sim_checksum()
assert replay()==replay()
# The future-affecting captured state must contribute to full simulation hash.
before=lib.sim_checksum();wrecks[0].birth+=1;assert lib.sim_checksum()!=before
print(json.dumps({'suite':'wreck-casualty-outcomes','passed':True,'cases':rows,'exact_replay':True,'registry_in_sim_checksum':True,'library_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'Real casualty/lifecycle/crew hooks; initial declared births only, no in-flight pose/health renewal. No physical cover/render/replication acceptance.'}))
