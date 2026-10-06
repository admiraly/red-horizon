#!/usr/bin/env python3
"""Actual casualty cover, blast atomicity, infantry/rifle LOS and ground bursts."""
import ctypes as C,hashlib,json,math,pathlib,struct,sys
PATH=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(PATH))
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class P(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','gen')]
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','gen','birth','expiry','seq','flags','r0','r1')]
class Event(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z')]+[(n,C.c_uint) for n in ('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float) for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_int) for n in ('role','mode','target','cooldown','ammo','gen')]+[(n,C.c_float) for n in ('vx','vy','vz')]+[('pass_ticks',C.c_uint),('flags',C.c_uint)]
e=(E*32768).in_dll(l,'sim_entities');p=(P*4).in_dll(l,'sim_players');w=(W*1024).in_dll(l,'sim_wrecks');a=(Air*32768).in_dll(l,'sim_aircraft');alive=(C.c_uint*2).in_dll(l,'sim_alive');ammo=(C.c_uint*32768).in_dll(l,'sim_shell_ammo');events=(Event*256).in_dll(l,'sim_events');wc=C.c_uint.in_dll(l,'sim_wreck_count');pc=C.c_uint.in_dll(l,'sim_projectile_count');seq=C.c_uint.in_dll(l,'sim_event_sequence')
l.sim_init.argtypes=[C.c_uint]*2;l.sim_air_damage.argtypes=[C.c_uint]*2;l.sim_blast.argtypes=[C.c_uint]*2+[C.c_float]*4;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float;l.sim_entity_height.argtypes=[C.c_uint];l.sim_entity_height.restype=C.c_float;l.world_los.argtypes=[C.c_float]*6;l.sim_checksum.restype=C.c_uint64;l.player_input.argtypes=[C.c_uint]*2+[C.c_float]*4;l.projectile_launch.argtypes=[C.c_uint]*2+[C.c_float]*3;l.projectile_air_launch.argtypes=[C.c_uint]*2
rows=[]
def reset(births,player=False,prime=True):
 assert l.sim_init(64,42)==0
 for entity in e[:64]:entity.hp=0
 alive[0]=alive[1]=0;C.c_uint.in_dll(l,'hazard_enabled').value=0
 for side in (0,1):
  for front in range(3):assert l.sim_order(side,front,1)==0
 for i,x,z,side,kind,hp in births:e[i]=E(x,z,hp,side,kind,0,-1,42);alive[side]+=1;ammo[i]=0
 l.ground_init()
 if player:
  assert l.player_join(0,0)==0;p[0].x=3490;p[0].z=2000;p[0].y=l.terrain_height(3490,2000)+1.8
 if prime:l.sim_tick()
def death(i):
 before=wc.value;l.sim_air_damage(i,e[i].hp);assert e[i].hp==0 and wc.value==before+1;return bytes(w[before])
# Actual shared casualty captures useful cover, independent of faction/ID order.
for kind in (1,2):
 for side in (0,1):
  for near,far in ((24,26),(26,24)):
   reset([(12,3500,2000,1-side,kind,1),(near,3492,2000,1-side,0,100),(far,3508,2000,1-side,0,100)])
   saved=death(12);before=e[far].hp;y=l.terrain_height(3490,2000)+1.6
   assert l.sim_blast(side,200,3490,2000,36,y)==1;assert e[near].hp==0 and e[far].hp==before and bytes(w[0])==saved
   rows.append({'case':'genuine_wreck_blast_shields_far_side','kind':kind,'side':side,'near_id':near,'far_id':far,'far_hp':before})
# Visibility must be decided before casualties from this same explosion register.
for side in (0,1):
 for first,second in ((24,26),(26,24)):
  reset([(first,3500,2000,1-side,1,1),(second,3508,2000,1-side,2,1)])
  assert l.sim_blast(side,200,3490,2000,36,l.terrain_height(3490,2000)+1.6)==2
  assert e[first].hp==e[second].hp==0 and wc.value==2
  rows.append({'case':'same_explosion_does_not_self_shield','side':side,'ids':[first,second],'sequences':[w[0].seq,w[1].seq]})
# Actual human rifle and opposing infantry threat loops both respect cover.
for cover_kind in (0,1,2):
 reset([(12,3500,2000,1,cover_kind,1),(24,3510,2000,1,0,100)],player=True)
 if cover_kind:death(12)
 else:l.sim_air_damage(12,e[12].hp);assert wc.value==0
 before=e[24].hp;player_hp=p[0].hp;delta=l.sim_entity_height(24)-p[0].y
 assert l.player_input(0,1,0,0,math.pi/2,math.atan2(delta,e[24].x-p[0].x))==0;l.player_tick()
 assert p[0].shots==1 and p[0].ammo==29
 if cover_kind:assert e[24].hp==before and p[0].hits==0 and p[0].hp==player_hp
 else:assert e[24].hp==before-34 and p[0].hits==1
 assert l.player_input(0,0,0,0,math.pi/2,math.atan2(delta,e[24].x-p[0].x))==0
 for _ in range(15):l.sim_tick()
 if cover_kind:assert p[0].hp==player_hp
 else:assert p[0].hp<player_hp,(cover_kind,player_hp,p[0].hp)
 rows.append({'case':'public_rifle_and_enemy_threat','cover_kind':cover_kind,'hits':p[0].hits,'victim_hp':e[24].hp,'player_hp':p[0].hp})
# Actual world acquisition/infantry fire lose the target behind a new casualty.
reset([(0,3490,2000,0,0,100),(12,3500,2000,1,1,1000),(24,3510,2000,1,0,100)])
death(12);before=e[0].hp,e[24].hp
for _ in range(16):l.sim_tick();assert e[0].target==-1 and e[24].target==-1
assert (e[0].hp,e[24].hp)==before;rows.append({'case':'new_cover_blocks_actual_acquisition_and_infantry_damage','ticks':16,'HP':list(before)})
# Gravity artillery on base/ridge/relief uses a clear-side ground blast origin.
for x,z in ((1000,2000),(3300,2000),(4000,2000),(5470,5150),(5600,5200)):
 reset([(12,x,z-80,0,2,400),(24,x+10,z,1,0,100)])
 ammo[12]=1;assert l.projectile_launch(12,2,x,l.terrain_height(x,z),z)==0
 for tick in range(1,241):
  l.projectile_tick()
  if not pc.value:break
 impacts=[v for v in events if v.kind==4];assert len(impacts)==1 and e[24].hp==0,(x,z,tick,e[24].hp)
 impact=impacts[0];assert abs(impact.x-x)<.002 and abs(impact.z-z)<.2,(x,z,impact.x,impact.y,impact.z,tick)
 assert abs(impact.y-l.terrain_height(impact.x,impact.z)-.002)<.005
 rows.append({'case':'real_artillery_ground_burst','anchor':[x,z],'impact':[impact.x,impact.y,impact.z],'ticks':tick,'victim_hp':e[24].hp})
# Public bomb launch from a declared initial sidecar; predict only fixture birth.
def f(v):return C.c_float(v).value
def predict(x,y,z,vx,vy,vz):
 for step in range(1,241):
  end=(f(x+vx),f(y+vy),f(z+vz));next_vy=f(vy-f(.0109))
  if end[1]<=l.terrain_height(end[0],end[2])+.002:
   lo,hi=0.,1.
   for _ in range(50):
    t=(lo+hi)/2;qx=x+(end[0]-x)*t;qy=y+(end[1]-y)*t;qz=z+(end[2]-z)*t
    if qy>l.terrain_height(qx,qz)+.002:lo=t
    else:hi=t
   return x+(end[0]-x)*hi,z+(end[2]-z)*hi
  x,y,z=end;vy=next_vy
 raise AssertionError('no predicted ground')
for x,z in ((1000,2000),(4000,2000),(5600,4300)):
 y=l.terrain_height(x,z)+120;hit=predict(x,y,z,0,0,6)
 reset([(12,x,z,0,3,1000),(24,hit[0]+10,hit[1],1,0,100)])
 a[12]=Air(y,0,0,0,6,0,0,-1,0,1,42,0,0,6,0,1)
 assert l.projectile_air_launch(12,3)==0 and pc.value==1
 for tick in range(1,241):
  l.projectile_tick()
  if not pc.value:break
 impacts=[v for v in events if v.kind==7];assert len(impacts)==1 and e[24].hp==0,(x,z,tick,e[24].hp,hit,[(v.x,v.y,v.z) for v in impacts],(e[24].x,e[24].z))
 impact=impacts[0];assert math.hypot(impact.x-hit[0],impact.z-hit[1])<36
 rows.append({'case':'public_bomb_ground_burst','source':[x,y,z],'impact':[impact.x,impact.y,impact.z],'ticks':tick,'victim_hp':e[24].hp})
print(json.dumps({'suite':'production-wreck-cover-outcomes','passed':True,'cases':rows,'no_inflight_health_pose_clock_ordnance_renewal':True,'library_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'scope':'Actual corpse capture/blast atomicity/world acquisition/infantry/human rifle and gravity artillery/bomb damage. Controlled initial births; no body/nav/remote prediction or artistic/whole-operation acceptance.'}))
