#!/usr/bin/env python3
"""Actual hostile cannon flight near a human; one declared initial sparse fixture."""
import ctypes as C,hashlib,json,math,pathlib,struct,sys
artillery='--artillery'in sys.argv;attacker=30 if artillery else 28
source=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(source));l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float;l.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
class Player(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint)for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
e=(Entity*32768).in_dll(l,'sim_entities');p=(Player*4).in_dll(l,'sim_players');alive=(C.c_uint*2).in_dll(l,'sim_alive');events=(C.c_ubyte*(256*32)).in_dll(l,'sim_events');seq=C.c_uint.in_dll(l,'sim_event_sequence');shells=(C.c_uint*32768).in_dll(l,'sim_shell_ammo')
assert l.sim_init(32,47)==0 and l.player_join(0,1)==0
for i in range(32):e[i].hp=0
e[0].x,e[0].z,e[0].hp,e[0].side,e[0].front=2000.,3900.,100,0,1
e[attacker].x,e[attacker].z,e[attacker].hp,e[attacker].side,e[attacker].front=2000.,4300.,400,1,0
alive[:]=[1,1];assert e[attacker].kind==(2 if artillery else 1) and shells[attacker]==64
p[0].x,p[0].z=2005.,3900.;p[0].y=l.terrain_height(p[0].x,p[0].z)+1.8
assert l.sim_order(0,1,1)==l.sim_order(1,0,1)==0
assert l.projectile_spawn(attacker,0)==0 and shells[attacker]==63
prior=seq.value;impact=None
for tick in range(1,241):
 l.sim_tick()
 for number in range(prior+1,seq.value+1):
  row=struct.unpack_from('<3f3IfI',bytes(events),(number&255)*32)
  if row[3]==(4 if artillery else 3) and row[4]==1:impact=(tick,row);break
 prior=seq.value
 if impact:break
assert impact,'real hostile shell never impacted'
tick,row=impact;distance=math.sqrt((row[0]-p[0].x)**2+(row[1]-p[0].y)**2+(row[2]-p[0].z)**2)
result={'suite':'player-physical-hostile-artillery'if artillery else'player-physical-hostile-blast','impact_tick':tick,'impact_event':row,'player_eye_distance_m':distance,'actual_blast_radius_m':row[6],'player_hp':p[0].hp,'player_generation':p[0].generation,'target_army_hp':e[0].hp,'finite_shells_remaining':shells[attacker],'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'checksum':f'{l.sim_checksum():016x}','limits':['Sparse startup positions/dead nonparticipants only; actual finite public cannon launch and genuine sim_tick flight/contact/blast afterward.','No live player/army health, pose, clock, stock or projectile renewal.','No original-scale/network/rendered quality acceptance.']}
assert distance<row[6]and p[0].generation==1,result
if '--baseline' in sys.argv:
 assert p[0].hp==100,result;result['observed_missing_player_blast']=True
else:assert p[0].hp==(0 if artillery else 20),result;result['passed']=True
print(json.dumps(result))
