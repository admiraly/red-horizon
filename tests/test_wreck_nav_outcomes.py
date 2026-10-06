#!/usr/bin/env python3
"""Genuine public-tick wreck detours, independently observed motion and arrival."""
import argparse,ctypes as C,hashlib,json,math,pathlib,struct
ap=argparse.ArgumentParser();ap.add_argument('library');ap.add_argument('--negative-no-route',action='store_true');a=ap.parse_args()
path=pathlib.Path(a.library).resolve();lib=C.CDLL(str(path))
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
class P(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','gen')]
e=(E*32768).in_dll(lib,'sim_entities');alive=(C.c_uint*2).in_dll(lib,'sim_alive');w=(C.c_byte*65536).in_dll(lib,'sim_wrecks')
b=(C.c_float*(1024*6)).in_dll(lib,'wreck_query_bounds');p=(P*4).in_dll(lib,'sim_players');m=(C.c_uint*8).in_dll(lib,'wreck_nav_metrics')
count=C.c_uint.in_dll(lib,'sim_wreck_count');clock=C.c_uint.in_dll(lib,'sim_tick_count');lib.sim_checksum.restype=C.c_uint64
lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.wreck_body_query.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*5;lib.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
lib.terrain_height.argtypes=[C.c_float,C.c_float];lib.terrain_height.restype=C.c_float
radii=(.551,3.551,4.491);reports=[]
def slab(start,end,box):
 lo,hi=0.,1.
 for q,v,mn,mx in zip(start,(end[0]-start[0],end[1]-start[1]),box[:2],box[2:]):
  if v==0:
   if not mn<=q<=mx:return False
  else:
   a,b=(mn-q)/v,(mx-q)/v;lo=max(lo,min(a,b));hi=min(hi,max(a,b))
   if lo>hi:return False
 return True

def escaping(start,end,box):
 if not (box[0]<=start[0]<=box[2] and box[1]<=start[1]<=box[3]):return False
 dx,dz=end[0]-start[0],end[1]-start[1]
 depths=(start[0]-box[0],box[2]-start[0],start[1]-box[1],box[3]-start[1]);nearest=min(depths)
 return start!=end and any(abs(q-nearest)<1e-5 and v<=0 for q,v in zip(depths,(dx,-dx,dz,-dz)))

def reset(role=1,side=0,wrecks=((3500.,2000.),),later=None,start=(3480.,2000.),goal=(3520.,2000.),crowd=1):
 assert lib.sim_init(32,42)==0
 for x in e[:32]:x.hp=0
 alive[0]=alive[1]=0
 for s in (0,1):
  for front in range(3):assert lib.sim_order(s,front,1)==0
 e[12]=E(*start,400,side,role,0,-1,111);alive[side]=1
 for i,xy in enumerate(wrecks):
  e[13+i]=E(*xy,1,side,1,1,-1,112+i);alive[side]+=1
 if later:
  e[20]=E(*later,1,side,1,1,-1,121);alive[side]+=1
 # Match physical source heading before capture across label swaps.
 for s in (0,1):
  assert lib.sim_waypoint(s,0,*goal)==0
  assert lib.sim_waypoint(s,1,3600,2000)==0
 lib.ground_init()
 for i in range(len(wrecks)):lib.sim_air_damage(13+i,1)
 assert count.value==len(wrecks)
 C.c_uint.in_dll(lib,'crowd_enabled').value=crowd
 assert lib.sim_waypoint(side,0,*goal)==0
 lib.sim_tick() # held while shared ground controller seeds
 assert lib.sim_order(side,0,0)==0
 return goal

def boxes(role):
 out=C.create_string_buffer(24);assert lib.wreck_body_query(out,24,3480,2000,3520,2000,radii[role]) in (0,1)
 result=[]
 for i in range(1024):
  if C.c_uint.from_buffer(w,i*64+52).value&1:
   r=radii[role];result.append((b[i*6]-r,b[i*6+2]-r,b[i*6+3]+r,b[i*6+5]+r))
 return result

def run(role,side=0,crowd=1,wrecks=((3500.,2000.),),later=None,ticks=700,goal=(3520.,2000.),start=(3480.,2000.)):
 reset(role,side,wrecks,later,start=start,goal=goal,crowd=crowd);rects=boxes(role);trace=[];arrival=None;moving=0;max_builds=0
 for t in range(ticks):
  if t==80 and later:lib.sim_air_damage(20,1);rects=boxes(role)
  start=(e[12].x,e[12].z);lib.sim_tick();end=(e[12].x,e[12].z)
  assert all(math.isfinite(q) for q in end);assert math.dist(start,end)<(.502 if role==1 else .202 if role==2 else .122)
  assert not any(slab(start,end,r) and not escaping(start,end,r) for r in rects if start!=end),(role,side,t,start,end,rects)
  assert e[12].hp==400
  if start!=end:moving+=1
  max_builds=max(max_builds,m[6]);assert m[6]<=8 and m[0]<=512
  trace.append(end)
  if math.dist(end,goal)<.01 and arrival is None:arrival=t+1
 if a.negative_no_route:assert arrival is None,'negative route fixture unexpectedly reached'
 else:assert arrival is not None and max(math.dist(q,goal) for q in trace[-10:])<.01,(role,side,crowd,goal,trace[-1],list(m))
 result={'role':role,'side':side,'crowd':crowd,'wrecks':len(wrecks),'later':later,'arrival_tick':arrival,'moving_ticks':moving,'max_builds_per_tick':max_builds,'completed_builds':m[1],'graph_failures':m[4],'local_overflow':m[5],'trace_sha256':hashlib.sha256(b''.join(struct.pack('<ff',*q) for q in trace)).hexdigest(),'checksum':f'{lib.sim_checksum():016x}'}
 reports.append(result);return result
if a.negative_no_route:
 for role in (0,1,2):run(role,crowd=0)
else:
 for role in (0,1,2):
  baseline=run(role)
  swapped=run(role,1);assert swapped['trace_sha256']==baseline['trace_sha256'],'physical label swap changed detour'
  disabled=run(role,crowd=0);assert disabled['arrival_tick']==baseline['arrival_tick']
  replay=run(role);assert replay==baseline,'detour state is not replayable'
if not a.negative_no_route:
 for role in (0,1,2):run(role,start=(3498.5,2000.),goal=(3480.,2000.))
 for role in (0,1,2):run(role,wrecks=((3498.,2000.),(3508.,2003.)),goal=(3530.,2000.))
 run(1,wrecks=((3500.,2000.),(3544.,2000.)),goal=(3600.,2000.))
 baseline=run(1);distant=run(1,later=(7000.,7000.));assert distant['trace_sha256']==baseline['trace_sha256'] and distant['completed_builds']==baseline['completed_builds'],'distant death invalidated local route'
 run(1,later=(3508.,1990.))
 # Real lifetime, unchanged clock: held manual contact recovers after actual expiry.
 reset(0);assert lib.sim_order(0,0,1)==0;assert lib.player_join(0,0)==0
 p[0].x,p[0].z=3480,2000;p[0].y=lib.terrain_height(3480,2000)+1.8
 assert lib.player_input(0,0,1,0,0,0)==0
 held=None;expiry=None
 for t in range(1830):
  lib.sim_tick()
  if t==1700:held=p[0].x;assert count.value==1
  if count.value==0 and expiry is None:expiry=clock.value
 assert expiry==1800 and p[0].x>held+4,'real wreck expiry did not release manual motion'
 reports.append({'case':'actual_expiry_manual_recovery','expiry_tick':expiry,'held_x':held,'final_x':p[0].x,'no_clock_renewal':True})
print(json.dumps({'suite':'wreck-public-detour-arrival','passed':not a.negative_no_route,'negative_no_route':a.negative_no_route,'cases':reports,'library_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'original_radii':list(radii),'no_inflight_pose_health_clock_ordnance_renewal':True,'oracle':'independent closed slabs, genuine public-tick displacement, exact arrival and final hold','limits':['Sparse fixtures; not scale, terrain streaming, art or co-op acceptance.','Queue/budget caps alone do not establish performance.','Finite local graph supports eight relevant wrecks; excess cover fails safely and is reported.']}))
