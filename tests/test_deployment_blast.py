#!/usr/bin/env python3
"""Read-only native corridor controls and actual production finite shell flight."""
import ctypes as C,json,pathlib,sys,math,hashlib,subprocess,tempfile,os
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()))
class Projectile(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint) for n in ('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint) for n in ('source','generation','active','source_generation','reserved')]
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front','target','generation')]
class Player(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
pool=(Projectile*512).in_dll(lib,'sim_projectiles');entities=(Entity*32768).in_dll(lib,'sim_entities');players=(Player*4).in_dll(lib,'sim_players');events=(C.c_ubyte*(256*32)).in_dll(lib,'sim_events');tick=C.c_uint.in_dll(lib,'sim_tick_count')
# Real native wrapper verifies all six callee-owned registers and stack return.
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='rh-deployment-abi-') as tmp:
 obj=pathlib.Path(tmp)/'probe.o';wrapped=pathlib.Path(tmp)/'probe.so'
 subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(root/'tests/probe_deployment_blast.asm'),'-o',str(obj)],check=True)
 subprocess.run(['gcc','-shared','-o',str(wrapped),str(obj),str(pathlib.Path(sys.argv[1]).resolve()),'-Wl,-rpath,'+str(pathlib.Path(sys.argv[1]).resolve().parent)],check=True)
 abi=C.CDLL(str(wrapped))
lib.deployment_blast_clear.argtypes=[C.c_float]*3;abi.deployment_blast_abi.argtypes=[C.c_float]*3;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_checksum.restype=C.c_uint64;lib.projectile_launch.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*3
cases=[]
def reset():
 assert lib.sim_init(32,47)==0
 C.memset(C.addressof(pool),0,C.sizeof(pool));C.memset(C.addressof(events),0,C.sizeof(events))
def check(label,xyz,wanted):
 before=lib.sim_checksum();raw=bytes(pool)+bytes(events)
 got=lib.deployment_blast_clear(*xyz)
 assert got==wanted,(label,got,wanted,xyz)
 assert abi.deployment_blast_abi(*xyz)==wanted,(label,'ABI register/stack corruption')
 assert lib.sim_checksum()==before and bytes(pool)+bytes(events)==raw,(label,'query changed authority')
 cases.append(label)
def shot(slot=0,**kw):
 p=pool[slot];p.x,p.y,p.z=1000,200,1000;p.vx,p.vy,p.vz=10,0,0;p.ttl,p.side,p.kind,p.damage,p.radius,p.generation,p.active=100,1,1,80,18,1,1
 for name,value in kw.items():setattr(p,name,value)
reset();check('empty',(1200,200,1000),0)
shot();check('straight_hostile_shell',(1200,200,1000),1);check('off_corridor',(1200,200,1100),0);check('behind_shell',(900,200,1000),0);check('high_overflight',(1200,280,1000),0)
shot(ttl=1);check('expiry_before_contact',(1000,200,1000),0)
shot(ttl=2);check('last_live_segment',(1005,200,1000),1);check('beyond_ttl',(1100,200,1000),0)
shot(side=0);check('friendly_shell',(1200,200,1000),0)
shot(kind=4,radius=0);check('nonexplosive_air_gun',(1200,200,1000),0)
shot(kind=99);check('malformed_active_kind',(1200,200,1000),1)
shot(active=0);check('inactive',(1200,200,1000),0)
shot(vx=0,vy=0,vz=0);check('stationary_hostile',(1000,200,1000),1)
shot(x=7990,vx=100);check('map_expiry_before_contact',(7995,200,1000),0)
shot(x=1000,y=300,vx=0,vy=-1,vz=0,kind=3,radius=36);check('gravity_bomb',(1000,200,1000),1)
shot(x=1000,y=300,vx=0,vy=-1,vz=0,kind=2,radius=35);check('gravity_artillery',(1000,200,1000),1)
shot(x=1000,y=lib.terrain_height(1000,1000)-1,vx=10);check('terrain_stops_corridor_before_candidate',(1200,lib.terrain_height(1000,1000)-1,1000),0)
shot(x=float('nan'));check('malformed_active_projectile',(1200,200,1000),1)
shot(radius=float('nan'));check('malformed_radius',(1200,200,1000),1)
reset();shot(511);check('last_pool_slot',(1200,200,1000),1)
reset();check('malformed_candidate',(float('nan'),200,1000),1)
import struct
for kind in (3,4,7):
 reset();tick.value=100
 struct.pack_into('<3f3IfI',events,0,1200,200,1000,kind,1,100,18,1)
 check('recent_impact_'+str(kind),(1200,200,1000),1)
 tick.value=130;check('recent_impact_boundary_'+str(kind),(1200,200,1000),1)
 tick.value=131;check('expired_impact_'+str(kind),(1200,200,1000),0)
reset();tick.value=2;struct.pack_into('<3f3IfI',events,0,1200,200,1000,3,1,0xfffffffe,18,0)
check('impact_tick_and_sequence_wrap',(1200,200,1000),1)
# Public finite tank launch aimed at the actual legacy deployment position.
reset();assert lib.player_join(0,0)==0
baseline=(players[0].x,players[0].y,players[0].z);assert lib.player_leave(0)==0
for e in entities[:32]:e.hp=0
entities[0].x,entities[0].z,entities[0].hp,entities[0].side,entities[0].front=baseline[0]+100,baseline[2],100,0,0
(C.c_uint*2).in_dll(lib,'sim_alive')[:]=[1,1]
attacker=28;e=entities[attacker];assert e.kind==1
e.x,e.z,e.hp,e.side=baseline[0],baseline[2]+300,400,1
assert lib.player_join(0,0)==0 and (players[0].x,players[0].y,players[0].z)==baseline
assert lib.player_leave(0)==0
assert lib.projectile_launch(attacker,1,baseline[0],lib.terrain_height(baseline[0],baseline[2]),baseline[2])==0
check('actual_finite_launch_rejects_target',baseline,1)
assert lib.player_join(0,0)==0
p=players[0];distance=math.dist(baseline,(p.x,p.y,p.z))
control='--baseline' in sys.argv
initial_join=(p.x,p.y,p.z)
assert p.hp==100 and (distance<.001 if control else distance>38),('join exclusion causal control',control,baseline,initial_join)
# Real authority continues; no projectile/pose/HP/ammo/clock refresh thereafter.
minimum_hp=p.hp
for _ in range(60):
 lib.sim_tick();minimum_hp=min(minimum_hp,p.hp)
assert tick.value==60
assert minimum_hp==(20 if control else 100), (control,minimum_hp)
print(json.dumps({'suite':'actual-deployment-blast-exclusion','passed':True,'read_only_controls':cases,'six_register_native_ABI_preserved':True,'real_launch_avoided_position':baseline,'actual_join_position':initial_join,'minimum_hp_over60ticks':minimum_hp,'baseline_hook_omitted':control,'initial_avoided_distance_m':distance,'tick60_hp':p.hp,'tick60_generation':p.generation,'finite_shells_remaining':(C.c_uint*32768).in_dll(lib,'sim_shell_ammo')[attacker],'library_sha256':hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(),'scope':'Controlled initial projectile/event negatives plus actual public finite tank launch and60 genuine ticks. No incoming-data writes after setup; conservative90-tick corridor/30-tick impact window, static production-contact forecast only, not all future fire/dynamic interception/full-scale performance acceptance.'}))
