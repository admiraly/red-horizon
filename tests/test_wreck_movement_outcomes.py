#!/usr/bin/env python3
"""Public gameplay motion against a genuine casualty; independent closed slabs."""
import argparse,ctypes as C,hashlib,json,math,pathlib
ap=argparse.ArgumentParser();ap.add_argument('library');ap.add_argument('--legacy',action='store_true');a=ap.parse_args()
path=pathlib.Path(a.library).resolve();lib=C.CDLL(str(path))
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class P(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
e=(E*32768).in_dll(lib,'sim_entities');p=(P*4).in_dll(lib,'sim_players');alive=(C.c_uint*2).in_dll(lib,'sim_alive')
w=(C.c_byte*65536).in_dll(lib,'sim_wrecks');b=(C.c_float*(1024*6)).in_dll(lib,'wreck_query_bounds')
lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
lib.terrain_height.argtypes=[C.c_float,C.c_float];lib.terrain_height.restype=C.c_float
lib.wreck_body_query.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*5
radii=(.551,3.551,4.491);reports=[];violations=[]
def intersects(start,end,rect):
 # Closed slab intersection, calculated independently in Python double.
 lo,hi=0.,1.
 for q,v,mn,mx in zip(start,(end[0]-start[0],end[1]-start[1]),rect[:2],rect[2:]):
  if v==0:
   if q<mn or q>mx:return False
  else:
   t0,t1=(mn-q)/v,(mx-q)/v;lo=max(lo,min(t0,t1));hi=min(hi,max(t0,t1))
   if lo>hi:return False
 return True

def run(mode,role,crowd=1,z=2000.):
 assert lib.sim_init(32,42)==0
 for x in e[:32]:x.hp=0
 alive[0]=2;alive[1]=0
 for side in (0,1):
  for front in range(3):assert lib.sim_order(side,front,1)==0
 e[12]=E(3480,z,400,0,role,0,-1,111);e[13]=E(3500,2000,1,0,1,0,-1,112)
 lib.ground_init();lib.sim_air_damage(13,1)
 assert C.c_uint.in_dll(lib,'sim_wreck_count').value==1
 saved=bytes(w);result=C.create_string_buffer(24);assert lib.wreck_body_query(result,24,3480,z,3520,z,radii[role]) in (0,1)
 radius=radii[role];rect=(b[0]-radius,b[2]-radius,b[3]+radius,b[5]+radius)
 C.c_uint.in_dll(lib,'crowd_enabled').value=crowd
 lib.sim_tick() # Stationary controller seeding while every front holds.
 if mode in ('foot','driver'):
  assert lib.player_join(0,0)==0
  p[0].x,p[0].z=(3482,z) if mode=='driver' else (3480,z)
  p[0].y=lib.terrain_height(p[0].x,p[0].z)+1.8
  if mode=='driver':assert lib.vehicle_enter(0)==0
  assert lib.player_input(0,0,1,0,0,0)==0
 else:
  assert lib.sim_waypoint(0,0,3520,z)==0;assert lib.sim_order(0,0,0)==0
 positions=[];bad=[]
 for tick in range(240):
  actor=p[0] if mode=='foot' else e[12];start=(actor.x,actor.z)
  lib.sim_tick();end=(actor.x,actor.z)
  assert all(math.isfinite(v) for v in end)
  assert math.dist(start,end)<(.602 if mode=='driver' else .502 if role==1 else .202 if role==2 else .302)
  if start!=end and intersects(start,end,rect):bad.append(tick)
  assert bytes(w)==saved,'movement changed casualty pose or lifetime record'
  assert e[12].hp==400,'unexpected damage invalidates sparse motion fixture'
  positions.append(end)
 if bad:violations.append({'mode':mode,'role':role,'crowd':crowd,'z':z,'ticks':bad[:8]})
 if not a.legacy:assert not bad,(mode,role,crowd,z,bad[:8],rect)
 reports.append({'mode':mode,'role':role,'crowd':crowd,'z':z,'moving_ticks':sum(x!=y for x,y in zip([(3480,z)]+positions,positions)),'end':positions[-1],'goal_error_m':math.dist(positions[-1],(3520,z)),'penetrations':len(bad)})
for crowd in (0,1):
 for role in (0,1,2):run('ai',role,crowd)
 run('foot',0,crowd);run('driver',1,crowd)
# A clear route controls against holding every proposal indiscriminately.
for role in (0,1,2):run('ai',role,1,2010.)
if a.legacy:assert violations,'causal control did not expose original missing collision hook'
print(json.dumps({'suite':'wreck-public-movement','passed':not violations,'legacy_control':a.legacy,'cases':reports,'causal_violations':violations,'library_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'genuine_casualty':True,'no_inflight_pose_health_clock_ordnance_renewal':True,'oracle':'independent closed XZ slabs from captured production bounds plus original role radius','limits':['Sparse initial fixtures only; no scale or graphics acceptance.','Reported goal error does not establish autonomous wreck detour acceptance.','No expiry, arbitrary orientation or remote prediction acceptance.']}))
