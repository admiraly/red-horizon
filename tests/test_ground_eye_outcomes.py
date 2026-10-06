#!/usr/bin/env python3
"""Independent driver anchor/aim outcomes through actual gameplay APIs."""
import argparse,ctypes as C,hashlib,json,math,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('library');p.add_argument('--legacy',action='store_true');p.add_argument('--report');p.add_argument('--source-revision',default='unspecified; library hash is authoritative');a=p.parse_args()
path=Path(a.library).resolve();lib=C.CDLL(str(path))
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Player(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
class Motion(C.Structure):
 _fields_=[(n,C.c_float) for n in ('heading','speed','turn','vx','vz')]+[(n,C.c_uint) for n in ('generation','kind','flags')]
class Shell(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','vx','vy','vz')]+[('rest',C.c_byte*40)]
E=(Entity*32768).in_dll(lib,'sim_entities');P=(Player*4).in_dll(lib,'sim_players');M=(Motion*32768).in_dll(lib,'sim_ground_motion');V=(C.c_int*4).in_dll(lib,'sim_player_vehicle')
owners=(C.c_int*32768).in_dll(lib,'vehicle_entity_driver');shells=(Shell*512).in_dll(lib,'sim_projectiles');shots=(C.c_uint*4).in_dll(lib,'vehicle_shots')
lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];lib.sim_order.argtypes=[C.c_uint]*3
lib.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;lib.vehicle_tick_player.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_checksum.restype=C.c_uint64
TOL=.004
def terrain(x,z):return float(lib.terrain_height(x,z))
def position(e):return (e.x,e.z)
def player_xyz():return (P[0].x,P[0].y,P[0].z)
def matrix_product(A,B):return [[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def rotate(A,v):return tuple(sum(row[k]*v[k] for k in range(3)) for row in A)
def solve(A,b):
 # Generic least-squares normal-equation solve, independent of the actuator's
 # closed-form symmetric sums and SSE evaluation order.
 q=[list(row)+[value] for row,value in zip(A,b)]
 for k in range(3):
  j=max(range(k,3),key=lambda j:abs(q[j][k]));q[k],q[j]=q[j],q[k];d=q[k][k];assert abs(d)>1e-9
  q[k]=[v/d for v in q[k]]
  for j in range(3):
   if j!=k:
    f=q[j][k];q[j]=[v-f*w for v,w in zip(q[j],q[k])]
 return tuple(row[3] for row in q)
def expected_eye():
 e=E[12];h=M[12].heading;s,c=math.sin(h),math.cos(h)
 local=[(x,0.,z-.45) for x in (-1.75,1.75) for z in (-2.55,2.55)]
 heights=[terrain(e.x+c*x+s*z,e.z-s*x+c*z) for x,y,z in local]
 rows=[(1.,x,z) for x,y,z in local]
 normal=[[sum(r[i]*r[j] for r in rows) for j in range(3)] for i in range(3)]
 rhs=[sum(r[i]*y for r,y in zip(rows,heights)) for i in range(3)]
 intercept,rs,fs=solve(normal,rhs)
 support=max([terrain(e.x,e.z)]+[height-rs*x-fs*z for (x,y,z),height in zip(local,heights)])
 pitch=math.atan2(fs,1.);bank=math.atan2(rs,math.sqrt(1+fs*fs))
 cp,sp,cb,sb=math.cos(pitch),math.sin(pitch),math.cos(bank),math.sin(bank)
 yaw=[[c,0,s],[0,1,0],[-s,0,c]];pitch_matrix=[[1,0,0],[0,cp,sp],[0,-sp,cp]];bank_matrix=[[cb,-sb,0],[sb,cb,0],[0,0,1]]
 frame=matrix_product(matrix_product(yaw,pitch_matrix),bank_matrix)
 offsets=[rotate(frame,v) for v in local]
 contact=max([terrain(e.x,e.z)]+[terrain(e.x+v[0],e.z+v[2])-v[1] for v in offsets])
 base=max(support,contact);up=rotate(frame,(0,1,0));eye=tuple(x+3*u for x,u in zip((e.x,base,e.z),up))
 return eye,base,up
def check_eye():
 before=lib.sim_checksum();expected,base,up=expected_eye();assert lib.sim_checksum()==before,'read-only independent terrain sampling changed authority'
 actual=player_xyz();error=math.dist(actual,expected)
 if not a.legacy:assert error<TOL,('gameplay eye differs from independent terrain/frame anchor',position(E[12]),M[12].heading,actual,expected,error)
 assert all(math.isfinite(v) for v in actual) and P[0].hp==100 and E[12].hp==400,'eye fixture lost valid gameplay health/pose'
 assert V[0]==12 and owners[12]==0,'eye attachment lost actual claim'
 if not a.legacy:
  delta=tuple(x-y for x,y in zip(actual,(E[12].x,base,E[12].z)))
  assert abs(sum(x*y for x,y in zip(delta,up))-3)<TOL and math.dist(delta,tuple(3*u for u in up))<TOL,'anchor is not up-three from supported origin'
 return error,math.hypot(actual[0]-E[12].x,actual[2]-E[12].z)
def birth(x,z,h):
 assert lib.sim_init(32,42)==0;C.c_uint.in_dll(lib,'hazard_enabled').value=0
 for e in E[:32]:e.hp=0
 alive=(C.c_uint*2).in_dll(lib,'sim_alive');alive[0],alive[1]=1,0
 for side in (0,1):
  for front in range(3):assert lib.sim_order(side,front,1)==0
 e=E[12];e.x,e.z,e.hp,e.side,e.kind,e.front,e.target=x,z,400,0,1,0,-1;e.generation+=1
 assert lib.sim_waypoint(0,0,x+100*math.sin(h),z+100*math.cos(h))==0
 lib.sim_tick();assert position(e)==(x,z),'held birth fixture moved'
 assert lib.player_join(0,0)==0;P[0].x,P[0].z=x+6,z;P[0].y=terrain(x+6,z)+1.8
 return e
def board():assert lib.vehicle_enter(0)==0;return check_eye()
def step(v,world=False,fire=False,yaw=.4,pitch=.2):
 if world:assert lib.player_input(0,int(fire),*v,yaw,pitch)==0;lib.sim_tick()
 else:
  P[0].yaw,P[0].pitch=yaw,pitch;assert lib.vehicle_tick_player(0,int(fire),*v)==1
 return check_eye()
def trajectory(name,x,z,h,world=False,ticks=180):
 birth(x,z,h);entry=board();errors=[entry[0]];offsets=[entry[1]];trace=hashlib.sha256();hull_trace=hashlib.sha256();travel=0.;maximum_turn=0.
 forward=(math.sin(h),math.cos(h));old_heading=M[12].heading
 for t in range(ticks):
  v=forward if t<ticks//2 else tuple(-v for v in forward) if t<3*ticks//4 else (math.cos(h),-math.sin(h))
  before=position(E[12]);err,off=step(v,world);after=position(E[12]);delta=tuple(q-p for p,q in zip(before,after));distance=math.hypot(*delta)
  assert distance<.603,'support changed physical speed envelope'
  angle=math.atan2(math.sin(M[12].heading-old_heading),math.cos(M[12].heading-old_heading));maximum_turn=max(maximum_turn,abs(angle));assert abs(angle)<.065,'support changed hull turn bound';old_heading=M[12].heading
  assert abs(delta[0]*math.cos(old_heading)-delta[1]*math.sin(old_heading))<TOL,'supported eye changed hull-axis movement'
  travel+=distance;errors.append(err);offsets.append(off);trace.update(struct.pack('<fffff',*player_xyz(),*after))
  hull_trace.update(struct.pack('<fff',*after,M[12].heading))
 assert travel>3,(name,'natural fixture has no useful movement',travel)
 return dict(name=name,world_tick=world,ticks=ticks,natural_hull_travel_m=travel,maximum_eye_error_m=max(errors),maximum_eye_hull_xz_offset_m=max(offsets),maximum_actual_heading_change=maximum_turn,trace_sha256=trace.hexdigest(),physical_hull_trace_sha256=hull_trace.hexdigest(),checksum=f'{lib.sim_checksum():016x}')
def cannon(yaw,pitch):
 birth(5700,5100,.7);board();expected,base,up=expected_eye();eye_before=player_xyz();h=M[12].heading
 source=(E[12].x,terrain(E[12].x,E[12].z)+3,E[12].z)
 look=(math.cos(pitch)*math.sin(yaw),math.sin(pitch),math.cos(pitch)*math.cos(yaw))
 target=tuple(x+600*d for x,d in zip(expected,look));direction=tuple(t-s for t,s in zip(target,source));norm=math.sqrt(sum(v*v for v in direction));velocity=tuple(10*v/norm for v in direction)
 step((0,0),fire=True,yaw=yaw,pitch=pitch);s=shells[0];actual=(s.vx,s.vy,s.vz);error=math.dist(actual,velocity)
 assert shots[0]==1 and M[12].heading==h and player_xyz()==eye_before,'camera fire changed hull heading/eye or failed physical cannon'
 assert math.dist((s.x,s.y,s.z),source)<TOL,'shell source changed beyond the retained upright-centre contract'
 if not a.legacy:assert error<.0002,('real shell not aimed from supported eye target',yaw,pitch,actual,velocity,error)
 return dict(name='supported_eye_cannon_target',yaw=yaw,pitch=pitch,velocity_error=error,actual_source=source)
def lifecycle(kind):
 birth(5700,5100,.4);board()
 for _ in range(45):step((math.sin(.4),math.cos(.4)))
 state=bytes(M[12]);before_hull=position(E[12]);before_eye=player_xyz()
 if kind=='exit':
  assert lib.vehicle_exit(0)==0 and V[0]==-1 and owners[12]==-1
  assert bytes(M[12])==state and position(E[12])==before_hull,'exit reinitializes/moves actual hull'
  offsets=((-6,0),(6,0),(0,-6),(0,6),(-6,-6),(6,6),(-6,6),(6,-6))
  assert any(math.dist((P[0].x-E[12].x,P[0].z-E[12].z),o)<TOL for o in offsets),'exit centred on shifted eye rather than physical hull'
  assert abs(P[0].y-terrain(P[0].x,P[0].z)-1.8)<TOL,'infantry exit height changed'
 elif kind=='disconnect':assert lib.player_leave(0)==0 and V[0]==-1 and owners[12]==-1
 elif kind=='player_generation':
  P[0].generation+=1;assert lib.vehicle_tick_player(0,1,0,0)==0 and V[0]==-1 and owners[12]==-1
 elif kind=='entity_generation':
  E[12].generation+=1;assert lib.vehicle_tick_player(0,1,0,0)==0 and V[0]==-1 and owners[12]==-1
 elif kind=='player_death':
  P[0].hp=0;assert lib.vehicle_tick_player(0,1,0,0)==0 and V[0]==-1 and owners[12]==-1
 if kind!='exit':assert position(E[12])==before_hull and player_xyz()==before_eye and bytes(M[12])==state,'adversarial lifecycle invalidation actuated or adopted a new attachment'
 assert shots[0]==0,'invalid lifecycle fired a shell'
 return dict(name=kind,claims_released=True,scope='Actual movement before expressly labelled lifecycle state injection' if kind!='exit' else 'Actual validated hull-centred exit')
def handoff():
 birth(5700,5100,0);assert lib.sim_order(0,0,0)==0
 for _ in range(12):lib.sim_tick()
 before=bytes(M[12]);speed=M[12].speed;initial_speed=speed;assert speed>.1,'natural AI handoff lacked momentum'
 board();assert bytes(M[12])==before,'eye boarding reseeded shared AI motion'
 for _ in range(45):step((0,1),True)
 before=bytes(M[12]);speed=M[12].speed;hull=position(E[12]);assert lib.vehicle_exit(0)==0 and bytes(M[12])==before
 lib.sim_tick();delta=math.dist(hull,position(E[12]));assert delta>.1 and abs(delta-abs(speed))<.081,'supported eye changed driver/AI continuity'
 assert V[0]==-1 and owners[12]==-1 and P[0].hp==100 and E[12].hp==400
 return dict(name='natural_ai_driver_ai_handoff',initial_ai_speed=initial_speed,first_ai_return_step=delta,checksum=f'{lib.sim_checksum():016x}')
def invalid_inputs():
 birth(5700,5100,.5);board();checked_inputs=[]
 for buttons,x,z in ((1,math.nan,0),(1,math.inf,0),(1,0,-math.inf),(128,0,0),(1,2,0)):
  before=lib.sim_checksum();state=bytes(E),bytes(P),bytes(M),bytes(shells)
  assert lib.vehicle_tick_player(0,buttons,x,z)==1
  assert lib.sim_checksum()==before and state==(bytes(E),bytes(P),bytes(M),bytes(shells)),'numeric/button invalid call consumed history or mutated complete authority'
  assert shots[0]==0
  checked_inputs.append((buttons,'NaN' if math.isnan(x) else x if math.isfinite(x) else 'infinite','infinite' if not math.isfinite(z) else z))
 return dict(name='numeric_and_unknown_input_rejected_before_history',cases=checked_inputs,complete_authority_unchanged=True)
def adversarial(field,held=False):
 birth(5700,5100,.5)
 if held:board()
 if field=='generation':M[12].generation+=1
 elif field=='kind':M[12].kind=2
 elif field=='flags':M[12].flags=0
 else:M[12].heading=math.nan
 def unchanged_state():
  return (bytes(E),bytes(P),bytes(M),bytes(V),bytes(owners),bytes(shells),bytes(shots),bytes((C.c_byte*128).in_dll(lib,'sim_vehicles')),bytes((C.c_uint*4).in_dll(lib,'vehicle_driver_generation')),bytes((C.c_uint*32768).in_dll(lib,'sim_shell_ammo')),bytes((C.c_uint*32768).in_dll(lib,'sim_shell_cooldown')),bytes((C.c_byte*8192).in_dll(lib,'sim_events')),C.c_uint.in_dll(lib,'sim_projectile_count').value,C.c_uint.in_dll(lib,'sim_event_sequence').value)
 before=unchanged_state();hash_before=lib.sim_checksum()
 rc=lib.vehicle_tick_player(0,1,0,0) if held else lib.vehicle_enter(0)
 after=unchanged_state();hash_after=lib.sim_checksum()
 if not a.legacy:
  assert rc==(1 if held else -1),(field,held,'invalid stamped support accepted',rc)
  assert before==after,(field,held,'invalid stamped support mutated authority/attachment')
  if not held:assert hash_before==hash_after,'rejected entry changed complete authority'
  if held:
   assert lib.vehicle_tick_player(0,1,0,0)==1 and lib.sim_checksum()==hash_after and unchanged_state()==after,'repeated held FIRE on invalid support changed authority after history edge'
  assert shots[0]==0,'invalid stamped support fired'
 return dict(name='invalid_motion_'+field,held_claim=held,return_code=rc,physical_resources_events_claim_changed=before!=after,complete_checksum_changed=hash_before!=hash_after,repeated_held_input_checksum_stable=held and not a.legacy,input_edge_scope='Valid FIRE edge is consumed by an existing claim before the eye guard; held state must preserve pose, motion, ownership, ammunition and projectiles.')
def checked(call):
 r=call();assert r==call(),'same-build public gameplay replay differs';return r
rows=[checked(lambda:trajectory('descending_slope_direct',5700,5100,math.pi/2)),checked(lambda:trajectory('banked_slope_world',5700,4900,.7,True)),checked(lambda:trajectory('plateau_crest_descent_world',5580,5100,math.pi/2,True,600)),checked(lambda:trajectory('ridge_cusp_world',4000,2000,math.pi/2,True))]
rows += [checked(lambda y=y,p=p:cannon(y,p)) for y,p in ((0,0),(.7,.4),(-1.7,-.3),(2.4,.7))]
rows += [checked(lambda k=k:lifecycle(k)) for k in ('exit','disconnect','player_generation','entity_generation','player_death')]
rows.append(checked(handoff))
rows.append(checked(invalid_inputs))
rows += [checked(lambda f=f,h=h:adversarial(f,h)) for f in ('generation','kind','flags','heading') for h in (False,True)]
if a.legacy:assert max(r['maximum_eye_error_m'] for r in rows[:4])>.05,'old accepted library did not expose actual upright-eye faults'
report=dict(suite='ground-eye-outcomes',passed=True,legacy=a.legacy,runtime_source_revision=a.source_revision,library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=rows,limits=['Actual public gameplay paths; independent least-squares support, matrix composition and contact floor use only real terrain_height samples.','Sparse initial friendly birth fixtures; no post-start pose/health manipulation outside labelled lifecycle/security injections.','Legacy local anchor height3 retained; no measured cockpit/turret socket or transformed physical shell origin claim.','No renderer, network, scale throughput or complete vehicle realism acceptance.'])
if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
