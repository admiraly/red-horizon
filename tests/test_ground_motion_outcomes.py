#!/usr/bin/env python3
"""Observe production ground hull motion; never call an actuator/probe directly."""
import argparse, ctypes as C, hashlib, json, math, struct
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('library');parser.add_argument('--legacy',action='store_true')
parser.add_argument('--report');parser.add_argument('--dense-ticks',type=int,default=120)
a=parser.parse_args();lib=C.CDLL(str(Path(a.library).resolve()))
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Player(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
class Motion(C.Structure):
 _fields_=[(n,C.c_float) for n in ('heading','speed','turn','vx','vz')]+[(n,C.c_uint) for n in ('generation','kind','flags')]
E=(Entity*32768).in_dll(lib,'sim_entities');P=(Player*4).in_dll(lib,'sim_players')
V=(C.c_int*4).in_dll(lib,'sim_player_vehicle');alive=(C.c_uint*2).in_dll(lib,'sim_alive')
try:M=(Motion*32768).in_dll(lib,'sim_ground_motion');enabled=C.c_uint.in_dll(lib,'ground_enabled')
except ValueError:M=enabled=None
try:player_claim_stamp=(C.c_uint*4).in_dll(lib,'vehicle_driver_generation')
except ValueError:player_claim_stamp=None
assert a.legacy or M is not None,'candidate must expose stamped shared hull authority'
lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.sim_order.argtypes=[C.c_uint]*3;lib.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
lib.vehicle_tick_player.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
lib.sim_checksum.restype=C.c_uint64
TOL=.002
def pos(e):return e.x,e.z
def angle(x):return math.atan2(math.sin(x),math.cos(x))
def axis(h):return math.sin(h),math.cos(h)
def snapshot(i):return None if M is None else tuple(getattr(M[i],n) for n,_ in Motion._fields_)
def motion_heading(i):return M[i].heading if M is not None and M[i].generation==E[i].generation and M[i].flags&1 else 0.
def reset(kind=1,xy=(3500.,2000.),driver=True):
 assert lib.sim_init(32,42)==0
 if enabled is not None:enabled.value=int(not a.legacy)
 C.c_uint.in_dll(lib,'hazard_enabled').value=0
 for e in E[:32]:e.hp=0
 alive[0]=alive[1]=0
 for side in (0,1):
  for f in range(3):assert lib.sim_order(side,f,1)==0
 e=E[12];e.x,e.z=xy;e.hp=400;e.kind=kind;e.side=0;e.front=0;e.target=-1;e.generation+=1;alive[0]=1
 assert lib.sim_waypoint(0,0,xy[0],xy[1]+300)==0
 # Public tick establishes generation state; no private motion writes.
 lib.sim_tick()
 if driver:
  assert lib.player_join(0,0)==0;p=P[0];p.x,p.z=e.x+2,e.z;p.y=lib.terrain_height(p.x,p.z)+1.8
  assert lib.vehicle_enter(0)==0 and V[0]==12
 return e
def move(v,buttons=0,world=False):
 if world:
  assert lib.player_input(0,buttons,*v,P[0].yaw,P[0].pitch)==0;lib.sim_tick()
 else:assert lib.vehicle_tick_player(0,buttons,*v)==1
def observe(i,step):
 before=pos(E[i]);old=snapshot(i);step();after=pos(E[i]);new=snapshot(i)
 dx,dz=after[0]-before[0],after[1]-before[1];distance=math.hypot(dx,dz)
 faults=[]
 if new is not None and not a.legacy:
  h,s,t,vx,vz,g,k,flags=new
  if not all(math.isfinite(v) for v in new[:5]):faults.append('nonfinite authority')
  if g!=E[i].generation or k!=E[i].kind or not flags&1:faults.append('invalid stamp')
  ux,uz=axis(h)
  if abs(dx*uz-dz*ux)>TOL:faults.append('sideways hull displacement')
  if math.dist((dx,dz),(vx,vz))>TOL:faults.append('velocity differs from actual displacement')
  if abs(dx*ux+dz*uz-s)>TOL:faults.append('signed speed differs from actual hull-axis displacement')
  if old is not None and old[5]==g and old[6]==k and old[7]&1:
   turn=angle(h-old[0])
   if abs(turn)>.15+TOL:faults.append('unbounded turn')
   if abs(angle(t-turn))>TOL:faults.append('turn differs from observed heading change')
 if distance>.602:faults.append('speed exceeds physical envelope')
 if not a.legacy:assert not faults,(i,before,after,old,new,faults)
 return dict(before=before,after=after,distance=distance,motion=new,faults=faults)
def trace(rows):return hashlib.sha256(b''.join(struct.pack('<ff',*r['after']) for r in rows)).hexdigest()

def driving(world=False,camera=False):
 e=reset();h=motion_heading(12);forward=axis(h);rows=[]
 for t in range(60):
  if camera:P[0].yaw,P[0].pitch=math.sin(t)*2.9,math.cos(t)*.8
  rows.append(observe(12,lambda:move(forward,world=world)))
 speeds=[r['distance'] for r in rows]
 acceleration_faults=int(speeds[0]>.08)+sum(q-p>.081 for p,q in zip(speeds,speeds[1:]))
 assert sum(speeds)>10 and speeds[-1]>.3,('no useful straight acceleration',world,speeds)
 if not a.legacy:assert acceleration_faults==0,('instant acceleration',world,speeds[:5])
 # Ninety-degree steering input should turn the hull, rather than strafe it.
 old_heading=motion_heading(12);right=axis(old_heading+math.pi/2);turns=[]
 for _ in range(90):turns.append(observe(12,lambda:move(right,world=world)))
 first_delta=tuple(q-p for p,q in zip(turns[0]['before'],turns[0]['after']))
 first_strafe=int(math.hypot(*first_delta)>.01 and abs(first_delta[0]*forward[1]-first_delta[1]*forward[0])>.1)
 assert sum(r['distance'] for r in turns)>8,'turning fixture made no useful approach'
 if not a.legacy:
  assert not first_strafe,('instant perpendicular strafe',world,first_delta)
  assert abs(angle(motion_heading(12)-old_heading-math.pi/2))<.15,'hull failed to turn toward request'
 # Release input: real braking displacement and finite stop, then held heading.
 stop=[]
 for _ in range(45):stop.append(observe(12,lambda:move((0.,0.),world=world)))
 braking_fault=int(stop[0]['distance']<.01)
 if not a.legacy:
  assert not braking_fault and sum(r['distance'] for r in stop)>.3,'instant stop instead of bounded braking'
  assert stop[-1]['distance']<TOL,'failed to stop released drive input'
  stopped_h=motion_heading(12)
  assert max(abs(angle(r['motion'][0]-stopped_h)) for r in stop[-10:])<TOL,'stopped hull changed heading'
 return dict(name='drive_world_tick' if world else 'drive_direct_api',camera_varied=camera,acceleration_faults=acceleration_faults,first_strafe_fault=first_strafe,instant_braking_fault=braking_fault,straight_metres=sum(speeds),turn_metres=sum(r['distance'] for r in turns),braking_metres=sum(r['distance'] for r in stop),first_five_steps=speeds[:5],final_straight_speed=speeds[-1],trace_sha256=trace(rows+turns+stop),checksum=f'{lib.sim_checksum():016x}')

def reversal():
 e=reset();h=motion_heading(12);v=axis(h)
 for _ in range(60):observe(12,lambda:move(v))
 rows=[];signed=[]
 for _ in range(70):
  r=observe(12,lambda:move(tuple(-x for x in v)));rows.append(r)
  d=tuple(q-p for p,q in zip(r['before'],r['after']));signed.append(sum(x*y for x,y in zip(d,v)))
 faults=int(signed[0]<-.01)+sum(abs(q-p)>.081 for p,q in zip(signed,signed[1:]))
 if not a.legacy:
  assert not faults,('reversal skipped physical braking',signed[:15])
  assert any(abs(s)<.081 for s in signed) and signed[-1]<-.1,'reverse never became useful after braking'
  assert max(abs(angle(r['motion'][0]-h)) for r in rows)<.05,'reverse spun hull instead of reversing signed drive'
 return dict(name='brake_through_zero_reverse',faults=faults,first_twelve_signed_steps=signed[:12],final_signed_step=signed[-1],trace_sha256=trace(rows))

def army(kind):
 e=reset(kind=kind,driver=False);assert lib.sim_order(0,0,0)==0;start=pos(e);rows=[]
 for _ in range(90):rows.append(observe(12,lib.sim_tick))
 speed=[r['distance'] for r in rows];fault=int(speed[0]>.08)
 assert math.dist(start,pos(e))>8,'AI vehicle made no useful forward progress'
 if not a.legacy:assert not fault,('AI instant acceleration',kind,speed[:5])
 h=motion_heading(12);assert lib.sim_waypoint(0,0,e.x+250,e.z)==0
 turn=[observe(12,lib.sim_tick) for _ in range(90)]
 if not a.legacy:assert abs(angle(motion_heading(12)-h))>.5,'AI heading did not respond to changed waypoint'
 assert sum(r['distance'] for r in turn)>5,'AI turn froze vehicle'
 assert lib.sim_order(0,0,1)==0
 stopped=[observe(12,lib.sim_tick) for _ in range(45)]
 braking=int(stopped[0]['distance']<.01)
 if not a.legacy:assert not braking and stopped[-1]['distance']<TOL,'AI hold did not brake to rest'
 return dict(name='ai_tank' if kind==1 else 'ai_artillery',acceleration_faults=fault,instant_braking_fault=braking,straight_metres=sum(speed),turn_metres=sum(r['distance'] for r in turn),braking_metres=sum(r['distance'] for r in stopped),first_five_steps=speed[:5],trace_sha256=trace(rows+turn+stopped))

def arrival(kind):
 e=reset(kind=kind,driver=False);start=pos(e);goal=(e.x,e.z+20.3)
 assert lib.sim_waypoint(0,0,*goal)==0 and lib.sim_order(0,0,0)==0
 ticks=120 if kind==1 else 240;rows=[]
 for _ in range(ticks):rows.append(observe(12,lib.sim_tick))
 error=math.dist(pos(e),goal);late_motion=max(r['distance'] for r in rows[-10:])
 assert math.dist(start,pos(e))>15,'short goal lost useful approach'
 if not a.legacy:
  assert error<.6,('AI short goal failed arrival deadline',kind,ticks,pos(e),goal,error)
  assert late_motion<.03,('AI passed goal but did not settle',kind,ticks,late_motion)
 return dict(name='ai_tank_settled_arrival' if kind==1 else 'ai_artillery_settled_arrival',ticks=ticks,goal=goal,final=pos(e),final_goal_error=error,maximum_last_ten_steps=late_motion,trace_sha256=trace(rows))

def handoff():
 e=reset(driver=False);assert lib.sim_order(0,0,0)==0
 for _ in range(60):observe(12,lib.sim_tick)
 before=snapshot(12);board_state=before;h=motion_heading(12);assert lib.player_join(0,0)==0
 P[0].x,P[0].z=e.x+2,e.z;P[0].y=lib.terrain_height(P[0].x,P[0].z)+1.8
 assert lib.vehicle_enter(0)==0 and V[0]==12
 if not a.legacy:assert snapshot(12)==before,'boarding reset shared moving hull state'
 r=observe(12,lambda:move(axis(h)))
 if not a.legacy:assert abs(r['distance']-abs(before[1]))<.081,'handoff caused abrupt speed reset/jump'
 before=snapshot(12);assert lib.vehicle_exit(0)==0
 if not a.legacy:assert snapshot(12)==before,'exiting reset shared moving hull state'
 # Move the detached human clear, preserving the actual exit validation above.
 P[0].x,P[0].z=e.x+30,e.z-30;P[0].y=lib.terrain_height(P[0].x,P[0].z)+1.8
 r=observe(12,lib.sim_tick)
 if not a.legacy:assert abs(r['distance']-abs(before[1]))<.081,'AI return reset speed instead of continuing shared state'
 return dict(name='ai_driver_ai_handoff',before_boarding=board_state,before_exit=before,first_ai_return_distance=r['distance'])

def invalid_and_generation():
 e=reset();v=axis(motion_heading(12))
 for _ in range(40):observe(12,lambda:move(v))
 for wx,wz in ((math.nan,0),(math.inf,0),(0,-math.inf),(2,0)):
  before=(bytes(E[12]),bytes(P[0]),snapshot(12),lib.sim_checksum())
  assert lib.vehicle_tick_player(0,0,wx,wz)==1
  assert before==(bytes(E[12]),bytes(P[0]),snapshot(12),lib.sim_checksum()),'malformed drive mutated authority'
 # Recycling invalidates the legitimate claim. New actor must not inherit momentum.
 old=e.generation;e.generation+=1
 assert lib.vehicle_tick_player(0,0,*v)==0 and V[0]==-1
 assert lib.sim_order(0,0,1)==0;lib.sim_tick()
 if not a.legacy:
  assert M[12].generation==old+1 and abs(M[12].speed)<TOL,'recycled stopped actor inherited old momentum/stamp'
 return dict(name='invalid_input_and_recycled_claim',invalid_inputs=4,recycled_generation=e.generation)

def invalid_claims():
 checks=[]
 stale_player_fault=False
 for mutation in ('enemy_side','entity_generation','disconnected','player_generation'):
  reset();v=axis(motion_heading(12))
  for _ in range(30):move(v)
  if mutation=='enemy_side':E[12].side=1
  elif mutation=='entity_generation':E[12].generation+=1
  elif mutation=='player_generation':P[0].generation+=1
  else:P[0].connected=0
  before=(pos(E[12]),snapshot(12))
  rc=lib.vehicle_tick_player(0,0,*v)
  if a.legacy and player_claim_stamp is None and mutation=='player_generation':
   stale_player_fault=rc==1 and pos(E[12])!=before[0] and V[0]==12
   assert stale_player_fault,'old vehicle claim did not expose missing player-generation stamp'
   checks.append(mutation);continue
  assert rc==0,('invalid physical ownership accepted',mutation)
  assert (pos(E[12]),snapshot(12))==before,('invalid claim actuated/reseeded hull',mutation)
  assert V[0]==-1,('invalid claim not cleaned up',mutation)
  checks.append(mutation)
 return dict(name='invalid_claims_cannot_actuate',claims=checks,stale_player_generation_actuated_fault=stale_player_fault)

class Shell(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','vx','vy','vz')]+[('tail',C.c_byte*40)]
def cannon():
 shells=(Shell*512).in_dll(lib,'sim_projectiles');checks=0
 for yaw in (0,math.pi/2,math.pi,-math.pi/2):
  for pitch in (-.5,0,.5):
   reset();P[0].yaw,P[0].pitch=yaw,pitch;h=motion_heading(12);before=pos(E[12])
   move((0.,0.),buttons=1);s=shells[0]
   direction=(math.cos(pitch)*math.sin(yaw),math.sin(pitch),math.cos(pitch)*math.cos(yaw))
   assert abs(math.hypot(s.vx,s.vy,s.vz)-10)<.001 and sum(x*y for x,y in zip(direction,(s.vx,s.vy,s.vz)))>9.999,'cannon failed independent camera aim'
   if not a.legacy:assert pos(E[12])==before and abs(angle(motion_heading(12)-h))<TOL,'stationary cannon aim rotated/moved hull'
   checks+=1
 return dict(name='camera_cannon_independent_of_hull',physical_shell_checks=checks)

def closest(a0,a1,b0,b1):
 d=(a0[0]-b0[0],a0[1]-b0[1]);v=(a1[0]-a0[0]-b1[0]+b0[0],a1[1]-a0[1]-b1[1]+b0[1]);vv=sum(x*x for x in v)
 t=max(0,min(1,-sum(x*y for x,y in zip(d,v))/vv)) if vv else 0
 return math.hypot(d[0]+t*v[0],d[1]+t*v[1])
def rectangle_cross(start,end,b):
 lo,hi=0.,1.
 for p,q,mn,mx in ((start[0],end[0],b[0],b[2]),(start[1],end[1],b[1],b[3])):
  d=q-p
  if not d:
   if not mn<=p<=mx:return False
  else:
   t,u=sorted(((mn-p)/d,(mx-p)/d));lo,hi=max(lo,t),min(hi,u)
   if lo>hi:return False
 return True
def contacts():
 rows=[]
 for obstacle in ('wall','artillery','human'):
  e=reset(xy=(3970.,1300.) if obstacle=='wall' else (3500.,2000.));start=pos(e)
  other=None;br=0
  if obstacle=='artillery':
   other=E[13];other.x,other.z,other.hp,other.side,other.kind,other.front,other.target=3500,2020,400,0,2,1,-1;other.generation+=1;alive[0]+=1;br=4.49
  if obstacle=='human':
   assert lib.player_join(1,1)==0;other=P[1];other.x,other.z=3500,2020;other.y=lib.terrain_height(other.x,other.z)+1.8;br=.55
  request=(1.,.5) if obstacle=='wall' else (0.,1.)
  norm=math.hypot(*request);request=tuple(x/norm for x in request)
  traces=[];faults=0;contacts_=0;near_contact=0
  for t in range(180):
   b0=pos(other) if other is not None else None
   r=observe(12,lambda:move(request,world=True));traces.append(r)
   if obstacle=='wall':
    bad=rectangle_cross(r['before'],r['after'],(3988-3.55+TOL,1100-3.55+TOL,4012+3.55-TOL,1500+3.55-TOL))
    near_contact+=abs(r['after'][0]-(3988-3.55))<.65
   else:
    bad=closest(r['before'],r['after'],b0,pos(other))<3.55+br-TOL
    near_contact+=abs(math.dist(r['after'],pos(other))-(3.55+br))<.65
   faults+=bad;contacts_+=r['distance']<.002
   if not a.legacy:assert not bad,('contact whole segment penetrated physical solid',obstacle,t,r)
  assert math.dist(start,pos(e))>3,'contact fixture froze before useful approach'
  assert near_contact>5,('contact fixture failed to approach obstruction',obstacle,pos(e),near_contact)
  rows.append(dict(name='whole_hull_contact_'+obstacle,swept_overlap_ticks=faults,held_contact_ticks=contacts_,near_contact_ticks=near_contact,approach_metres=math.dist(start,pos(e)),trace_sha256=trace(traces)))
 return rows

def dense(n,driven=False):
 assert lib.sim_init(n,42)==0 and lib.sim_scenario(3)==0
 if enabled is not None:enabled.value=int(not a.legacy)
 claims=[]
 if driven:
  for slot in range(4):
   assert lib.player_join(slot,slot%3)==0
   for x,z,i in sorted((e.x,e.z,i) for i,e in enumerate(E[:n]) if e.hp and e.side==0 and e.kind==1):
    if i in claims:continue
    P[slot].x,P[slot].z=x,z;P[slot].y=lib.terrain_height(x,z)+1.8
    if lib.vehicle_enter(slot)==0:
     assert V[slot]>=0 and V[slot] not in claims;claims.append(V[slot]);break
   else:raise AssertionError('no legitimate four-driver scale fixture')
   assert lib.player_input(slot,0,-1,.3 if slot&1 else 0,0,0)==0
 initial=[(i,pos(e),e.generation) for i,e in enumerate(E[:n]) if e.hp and e.kind in (1,2)]
 hp0=sum(e.hp for e in E[:n]);dead0=sum(not e.hp for e in E[:n]);checks=faults=0;maximum_turn=0.;trace_=hashlib.sha256()
 near_checks=near_faults=driver_moving=driver_frames=0
 for t in range(a.dense_ticks):
  old=[(i,pos(e),e.generation,e.kind,snapshot(i)) for i,e in enumerate(E[:n]) if e.hp and e.kind in (1,2)]
  army=[(i,pos(e),e.kind,e.generation) for i,e in enumerate(E[:n]) if e.hp and e.kind<3] if driven else []
  driver_old={i:pos(E[i]) for i in claims if E[i].hp}
  lib.sim_tick()
  for i,xy,g,k,m0 in old:
   e=E[i]
   if not e.hp or e.generation!=g or e.kind!=k:continue
   new=pos(e);dx,dz=new[0]-xy[0],new[1]-xy[1];distance=math.hypot(dx,dz)
   assert distance<=.602,('dense physical envelope',n,t,i,distance)
   m=snapshot(i)
   if m is not None and not a.legacy:
    checks+=1;h,s,turn,vx,vz,stamp,kind,flags=m;u=axis(h)
    bad=not all(math.isfinite(x) for x in m[:5]) or stamp!=g or kind!=k or not flags&1
    bad|=abs(dx*u[1]-dz*u[0])>TOL or math.dist((dx,dz),(vx,vz))>TOL or abs(dx*u[0]+dz*u[1]-s)>TOL
    if m0 is not None and m0[5]==g and m0[7]&1:
     actual_turn=abs(angle(h-m0[0]));maximum_turn=max(maximum_turn,actual_turn);bad|=actual_turn>.152
    faults+=bad;assert not bad,('dense authority/actual hull coherence',n,t,i,xy,new,m0,m)
   trace_.update(struct.pack('<Iff',i,*new))
  if driven:
   for slot in range(4):
    i=V[slot]
    if i not in driver_old or i<0 or not E[i].hp:continue
    driver_frames+=1;driver_moving+=math.dist(driver_old[i],pos(E[i]))>.002
    for j,xy,k,g in army:
     if i==j or not E[j].hp or E[j].generation!=g:continue
     rr=3.55+(.55,3.55,4.49)[k]
     if abs(xy[0]-driver_old[i][0])>rr+1.3 or abs(xy[1]-driver_old[i][1])>rr+1.3:continue
     near_checks+=1;d0=math.dist(driver_old[i],xy);d1=math.dist(pos(E[i]),pos(E[j]))
     bad=d1<d0-TOL if d0<rr-TOL else closest(driver_old[i],pos(E[i]),xy,pos(E[j]))<rr-TOL
     near_faults+=bad
     if not a.legacy:assert not bad,('dense driven hull relative-circle sweep',n,t,i,j,d0,d1,rr)
 moved=sum(E[i].hp and E[i].generation==g and math.dist(xy,pos(E[i]))>1 for i,xy,g in initial)
 survivors=sum(E[i].hp and E[i].generation==g for i,xy,g in initial)
 assert moved>survivors*.35,('dense vehicles made no useful progress',n,moved,survivors)
 hp1=sum(e.hp for e in E[:n]);assert hp1<hp0,'real scale combat absent'
 if driven:assert driver_frames>a.dense_ticks*2 and driver_moving>a.dense_ticks,('dense drivers lost useful real movement',n,driver_frames,driver_moving)
 return dict(name='actual_scale_hotspot_four_drivers' if driven else 'actual_scale_hotspot',units=n,ticks=a.dense_ticks,initial_boarded_tank_ids=claims,observed_living_driver_frames=driver_frames,observed_driver_moving_ticks=driver_moving,driver_near_relative_sweep_checks=near_checks,driver_relative_sweep_faults=near_faults,initial_ground_vehicles=len(initial),surviving_original_ground_vehicles=survivors,moved_over_one_metre=moved,coherence_checks=checks,coherence_faults=faults,maximum_heading_turn=maximum_turn,army_hp_before=hp0,army_hp_after=hp1,dead_before=dead0,dead_after=sum(not e.hp for e in E[:n]),trace_sha256=trace_.hexdigest(),checksum=f'{lib.sim_checksum():016x}')

def checked(call):
 r=call();assert r==call(),'exact same-build production replay differs';return r
rows=[checked(lambda:driving(world=False)),checked(lambda:driving(world=True)),checked(reversal),checked(lambda:army(1)),checked(lambda:army(2)),checked(handoff),checked(invalid_and_generation),checked(invalid_claims),checked(cannon),checked(lambda:arrival(1)),checked(lambda:arrival(2))]
plain=driving(camera=False);varied=driving(camera=True)
assert plain['trace_sha256']==varied['trace_sha256'],'camera aim changed actual driving trajectory'
rows.append(dict(name='camera_independent_trajectory',trace_sha256=plain['trace_sha256']))
rows+=checked(contacts)
scale=[checked(lambda n=n,driven=driven:dense(n,driven)) for n in (8192,16384) for driven in (False,True)]
if a.legacy:assert rows[0]['acceleration_faults'] and rows[0]['first_strafe_fault'] and rows[0]['instant_braking_fault'] and rows[2]['faults'],'baseline did not expose instant hull movement faults'
report=dict(suite='ground-motion-outcomes',passed=True,legacy=a.legacy,private_player_claim_stamp_present=player_claim_stamp is not None,library_sha256=hashlib.sha256(Path(a.library).read_bytes()).hexdigest(),observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=rows,dense=scale,limits=['Production sim_tick and vehicle/player public APIs only; no ground actuator/probe calls.','Development-only sparse initial placement and generation changes; no motion sidecar writes.','Observed displacement, stamped heading and signed speed jointly checked; circles do not establish oriented hull, suspension, terrain slope or road semantics.','Dense observes every living tank/artillery movement and retains real HP/combat, but does not test every pair of army actors.'])
if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
