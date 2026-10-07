#!/usr/bin/env python3
"""Development-only real public-API authored deployment and safety oracle."""
import ctypes as C,json,pathlib,sys,math,hashlib
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()))
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front','target','generation')]
class Player(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
entities=(Entity*32768).in_dll(lib,'sim_entities');players=(Player*4).in_dll(lib,'sim_players');sites=(C.c_uint*96).in_dll(lib,'sim_sites');tick=C.c_uint.in_dll(lib,'sim_tick_count')
lib.sim_checksum.restype=C.c_uint64
lib.terrain_height.argtypes=[C.c_float,C.c_float];lib.terrain_height.restype=C.c_float
reports=[]
def init(mode):
 assert lib.sim_init(8192,42)==0
 assert lib.sim_scenario(mode)==0
for mode in (1,2,3):
 init(mode);army=bytes(entities);states=[]
 for slot in range(4):
  assert lib.player_join(slot,slot%3)==0
  p=players[slot]
  assert p.hp==100 and p.generation==1 and p.connected==1 and p.respawn==0
  assert 2900<p.x<4000 and 1750<p.z<2600,('deployment missed authored combat region',mode,slot,p.x,p.z)
  nearby=[math.hypot(e.x-p.x,e.z-p.z) for e in entities[:8192] if e.hp and e.side==0 and e.kind!=3 and e.front==p.front]
  assert min(nearby)<=250,('no allied formation',mode,slot,min(nearby))
  assert abs(p.y-lib.terrain_height(p.x,p.z)-1.8)<.001
  for other in players[:slot]:assert math.hypot(other.x-p.x,other.z-p.z)>1,('overlapping players',mode,slot)
  states.append({'slot':slot,'front':p.front,'position':[p.x,p.y,p.z],'nearest_allied_formation_m':min(nearby)})
 assert bytes(entities)==army and tick.value==0,'joining mutated armies or clock'
 initial=lib.sim_checksum()
 for _ in range(120):lib.sim_tick()
 assert tick.value==120
 reports.append({'mode':mode,'joins':states,'join_army_unchanged':True,'initial_hash':f'{initial:016x}','tick120_hash':f'{lib.sim_checksum():016x}','tick120_hp':[p.hp for p in players],'tick120_generations':[p.generation for p in players]})
 # Authored anchor does not waive the connected-site gate or retry into danger.
 init(mode)
 for i in range(12):sites[i*8+5]=0
 assert lib.player_join(0,0)==0 and players[0].hp==0
 for _ in range(35):lib.player_tick()
 assert players[0].hp==0
# An airborne formation alone must not qualify as a ground squad location.
init(1)
for e in entities[:8192]:
 if e.side==0 and e.kind!=3:e.hp=0
assert lib.player_join(0,0)==0
p=players[0]
assert p.hp==100 and not (2900<p.x<4000 and 1750<p.z<2600), 'aircraft alone qualified as deployment squad'
# Deployment configuration must participate in replay identity, even before join.
init(0);before=lib.sim_checksum();army=bytes(entities)
lib.player_deployment_set.argtypes=[C.c_float,C.c_float]
lib.player_deployment_set(3450,2250)
assert lib.sim_checksum()!=before and bytes(entities)==army and tick.value==0
assert lib.sim_init(8192,42)==0 and lib.sim_checksum()==before
# Reset must remove previous authored configuration and recover legacy deployment.
init(0);assert lib.player_join(0,0)==0;baseline=bytes(players[0])
for mode in (1,2,3):
 init(mode);assert lib.sim_init(8192,42)==0;assert lib.player_join(0,0)==0
 assert bytes(players[0])==baseline,('authored anchor leaked through world reset',mode)
print(json.dumps({'suite':'actual-authored-squad-deployment','passed':True,'reports':reports,'unavailable_site_negative_controls':3,'world_reset_controls':3,'aircraft_only_formation_rejected':True,'deployment_configuration_hashed':True,'no_live_pose_health_clock_renewal':True,'library_sha256':hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(),'scope':'8192-unit genuine births and public joins/ticks; unavailable sites are explicit development safety controls. Not rendered density, four graphical players, blast-zone safety or whole operation acceptance.'}))
