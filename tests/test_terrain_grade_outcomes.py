#!/usr/bin/env python3
"""Independent road handling observations through authoritative public gameplay APIs."""
import argparse, ctypes as C, hashlib, json, math, struct
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument('library');ap.add_argument('--legacy',action='store_true');ap.add_argument('--report')
a=ap.parse_args();library=Path(a.library).resolve();lib=C.CDLL(str(library))
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Player(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
class Motion(C.Structure):
 _fields_=[(n,C.c_float) for n in ('heading','speed','turn','vx','vz')]+[(n,C.c_uint) for n in ('generation','kind','flags')]
E=(Entity*32768).in_dll(lib,'sim_entities');P=(Player*4).in_dll(lib,'sim_players')
M=(Motion*32768).in_dll(lib,'sim_ground_motion');V=(C.c_int*4).in_dll(lib,'sim_player_vehicle')
lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.sim_order.argtypes=[C.c_uint]*3;lib.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_checksum.restype=C.c_uint64
field=json.loads((Path(__file__).resolve().parents[1]/'content/terrain/relief.json').read_text())['fields'][0]
X=field['x'];Z=field['z'];H=field['height'];TOL=.002
faults=[];cases=[]
def factor(v,b):
 if v<=b[0] or v>=b[3]:return 0.,0.
 if v<b[1]:return (v-b[0])/(b[1]-b[0]),1/(b[1]-b[0])
 if v<=b[2]:return 1.,0.
 return (b[3]-v)/(b[3]-b[2]),-1/(b[3]-b[2])
def height(x,z):
 fx,_=factor(x,X);fz,_=factor(z,Z)
 return 12+(x-4000)**2*.000001+(z-4000)**2*.0000005+max(0,1-abs(x-4000)*.00125)*18+H*fx*fz
def gradient(x,z):
 fx,dx=factor(x,X);fz,dz=factor(z,Z)
 ridge=0 if abs(x-4000)>=800 else (-.0225 if x>4000 else .0225)
 return .000002*(x-4000)+ridge+H*dx*fz,.000001*(z-4000)+H*fx*dz
def capsule_distance(p,a,b):
 dx,dz=b[0]-a[0],b[1]-a[1];vv=dx*dx+dz*dz
 t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/vv)) if vv else 0
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dz)
def sampled_grade(a,b,r):
 points=[]
 for t in (0,.5,1):
  x,z=a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]);points.append((x,z))
  points.extend((x+r*math.cos(j*math.tau/24),z+r*math.sin(j*math.tau/24)) for j in range(24))
 xs=[a[0],b[0],min(a[0],b[0])-r,max(a[0],b[0])+r]+[v for v in X if min(a[0],b[0])-r<=v<=max(a[0],b[0])+r]
 zs=[a[1],b[1],min(a[1],b[1])-r,max(a[1],b[1])+r]+[v for v in Z if min(a[1],b[1])-r<=v<=max(a[1],b[1])+r]
 points.extend((x,z) for x in xs for z in zs if capsule_distance((x,z),a,b)<=r+1e-8)
 # Closed cusp sides are sampled explicitly; zero derivative at a cusp is not clearance.
 return max(math.hypot(*gradient(x+dx,z+dz)) for x,z in points for dx,dz in ((0,0),(-1e-6,0),(1e-6,0),(0,-1e-6),(0,1e-6)))
def check(ok,label):
 if not ok:
  faults.append(label)
  if not a.legacy:raise AssertionError(label)
def pos():return E[12].x,E[12].z
def reset(kind=1,xy=(5375.,5200.),goal=(5500.,5200.),driver=False):
 assert lib.sim_init(32,42)==0
 for e in E[:32]:e.hp=0
 alive=(C.c_uint*2).in_dll(lib,'sim_alive');alive[0]=1;alive[1]=0
 for side in (0,1):
  for front in range(3):assert lib.sim_order(side,front,1)==0
 e=E[12];e.x,e.z=xy;e.hp=400;e.side=0;e.kind=kind;e.front=0;e.target=-1;e.generation+=1
 assert lib.sim_waypoint(0,0,*goal)==0;lib.sim_tick()
 assert abs(M[12].speed)<TOL
 if driver:board()
 else:assert lib.sim_order(0,0,0)==0
 return e
def board():
 assert lib.player_join(0,0)==0
 P[0].x,P[0].z=E[12].x+1,E[12].z;P[0].y=lib.terrain_height(P[0].x,P[0].z)+1.8
 assert lib.vehicle_enter(0)==0 and V[0]==12

def step(direction=None,camera=(0.,0.)):
 before=pos();old=M[12].speed;oldh=M[12].heading
 if direction is not None:assert lib.player_input(0,0,*direction,*camera)==0
 lib.sim_tick();after=pos();m=M[12];delta=(after[0]-before[0],after[1]-before[1]);kind=E[12].kind
 assert E[12].hp==400 and m.generation==E[12].generation and m.kind==kind and m.flags&1
 assert math.dist(delta,(m.vx,m.vz))<TOL and abs(delta[0]*math.cos(m.heading)-delta[1]*math.sin(m.heading))<TOL
 assert abs(delta[0]*math.sin(m.heading)+delta[1]*math.cos(m.heading)-m.speed)<TOL
 assert (abs(m.speed)<TOL or abs(m.speed-old)<.043) and abs(m.speed)<=.602
 assert abs(math.atan2(math.sin(m.heading-oldh),math.cos(m.heading-oldh)))<=.063
 grade=sampled_grade(before,after,3.55 if kind==1 else 4.49)
 limit=math.tan(math.radians(35 if kind==1 else 25))
 moving=math.dist(before,after)>.001
 if moving:check(grade<=limit+.00003,f'accepted role{kind} sweep exceeds slope limit')
 actual_h=lib.terrain_height(*after);expected=height(*after)
 check(abs(actual_h-expected)<.0015,'public world height missing canonical raised relief')
 if V[0]==12:check(abs(P[0].y-expected-3)<.002,'boarded player eye missing raised world height')
 return dict(before=before,after=after,speed=m.speed,heading=m.heading,maximum_sampled_grade=grade,
             world_height=actual_h,expected_height=expected,driver_eye=P[0].y if V[0]==12 else None)
def digest(rows):return hashlib.sha256(b''.join(struct.pack('<ffff',*r['after'],r['speed'],r['world_height']) for r in rows)).hexdigest()
def run(kind,xy,goal,ticks,driver=False,direction=None,camera=False):
 reset(kind,xy,goal,driver);rows=[]
 for t in range(ticks):rows.append(step(direction if driver else None,(math.sin(t)*2.7,math.cos(t)*.7) if camera else (0.,0.)))
 return dict(start=xy,goal=goal,ticks=ticks,final=pos(),goal_error=math.dist(pos(),goal),distance=math.dist(xy,pos()),maximum_accepted_grade=max((r['maximum_sampled_grade'] for r in rows if math.dist(r['before'],r['after'])>.001),default=0),trace_sha256=digest(rows),checksum=f'{lib.sim_checksum():016x}',trace=rows)

# Genuine central steep ramp: player input cannot invoke autonomous bypass movement.
steep=run(1,(5375.,5200.),(5500.,5200.),200,True,(1.,0.))
check(steep['final'][0]<=5400-3.55+.002,'driver crossed steep ramp before whole hull rejection')
assert steep['distance']>10,'steep fixture did not approach the real obstruction'
cases.append(dict(name='whole_hull_central_steep_stop',result=steep))
# Approach a combined X/Z fringe from genuinely clear terrain. Neither scalar
# gradient alone exceeds the tank cap, but their combined norm eventually does.
corner=run(1,(5380.,4965.),(5510.,4965.),300,True,(1.,0.))
check(5410<corner['final'][0]<5470 and abs(corner['trace'][-1]['speed'])<TOL,'combined corner failed useful approach and slope stop')
cases.append(dict(name='combined_gradient_corner_stop',result=corner))
# Parallel motion outside the face remains useful when the entire circle clears.
parallel=run(1,(5395.,5150.),(5395.,5300.),150,True,(0.,1.))
assert parallel['distance']>50 and parallel['maximum_accepted_grade']<.01
cases.append(dict(name='whole_body_clear_parallel_edge',result=parallel))


# The public AI must find useful safe routes around the steep western face.
for kind in (1,2):
 start=(5375.,5200.);goal=(5550.,5200.)
 # Conservative actual detour: outer southwest/northwest, east entrance, plateau.
 route=[start,(5394.,4794.),(5826.,4794.),(5826.,5200.),goal]
 length=sum(math.dist(p,q) for p,q in zip(route,route[1:]));cap=.4 if kind==1 else .14
 ticks=math.ceil(length/cap)+400
 result=run(kind,start,goal,ticks)
 check(result['goal_error']<.6,f'role{kind} safe raised plateau route failed derived deadline')
 cases.append(dict(name='tank_reachable_plateau' if kind==1 else 'artillery_reachable_plateau',route_length_budget=length,result=result))

for kind in (1,2):
 for uphill in (True,False):
  start,goal=((5750.,5200.),(5590.,5200.)) if uphill else ((5590.,5200.),(5750.,5200.))
  cap=.4 if kind==1 else .14;ticks=math.ceil(math.dist(start,goal)/cap)+160
  result=run(kind,start,goal,ticks)
  check(result['goal_error']<.6,f'role{kind} gentle ascent/descent failed useful arrival')
  assert result['distance']>150
  cases.append(dict(name=('tank' if kind==1 else 'artillery')+('_gentle_ascent' if uphill else '_gentle_descent'),result=result))

# Fringe admits 35-degree tanks but not 25-degree artillery.
role_results=[]
for kind in (1,2):
 result=run(kind,(5380.,4940.),(5460.,4940.),850)
 if kind==1:check(result['goal_error']<.6,'tank failed reachable moderate grade fringe')
 else:check(result['goal_error']>4,'artillery accepted tank-only fringe goal')
 role_results.append(dict(kind=kind,result=result))
cases.append(dict(name='authentic_role_slope_difference',roles=role_results))

for upward in (True,False):
 start=(5750.,5200.) if upward else (5590.,5200.);direction=(-1.,0.) if upward else (1.,0.)
 goal=(start[0]+direction[0]*300,start[1]);result=run(1,start,goal,100,True,direction)
 check(abs(result['trace'][-1]['speed']-.48)<TOL,'gentle driver forward offroad cap changed')
 assert result['distance']>30
 plain=result;varied=run(1,start,goal,100,True,direction,True)
 assert plain['trace_sha256']==varied['trace_sha256'],'camera changed raised ground drive trajectory'
 cases.append(dict(name='driver_uphill_camera_independence' if upward else 'driver_downhill_camera_independence',result=result))

reset(1,(5750.,5200.),(5500.,5200.),True)
forward=[step((-1.,0.)) for _ in range(60)];reverse=[step((1.,0.)) for _ in range(70)]
check(abs(reverse[-1]['speed']+.144)<TOL,'gentle slope reverse offroad cap changed')
assert reverse[0]['speed']>0 and any(abs(r['speed'])<.042 for r in reverse)
cases.append(dict(name='gentle_slope_bounded_reverse',trace_sha256=digest(forward+reverse),reverse=reverse))

reset(1,(5750.,5200.),(5590.,5200.),True)
rows=[step((-1.,0.)) for _ in range(60)];before=bytes(M[12]);assert lib.vehicle_exit(0)==0;assert bytes(M[12])==before
P[0].x,P[0].z=E[12].x+30,E[12].z+30;P[0].y=lib.terrain_height(P[0].x,P[0].z)+1.8
assert lib.sim_order(0,0,0)==0
returned=step();assert abs(returned['speed']-rows[-1]['speed'])<.043
cases.append(dict(name='real_driver_to_ai_grade_handoff',last_driver=rows[-1],first_ai=returned))

reset(1,(5750.,5200.),(5500.,5200.),True)
for malformed in ((math.nan,0.),(math.inf,0.),(0.,-math.inf),(2.,0.)):
 before=bytes(E[12]),bytes(P[0]),bytes(M[12]),lib.sim_checksum()
 assert lib.player_input(0,0,*malformed,0.,0.)!=0
 assert before==(bytes(E[12]),bytes(P[0]),bytes(M[12]),lib.sim_checksum())
cases.append(dict(name='malformed_public_input_preserves_authority',inputs=4))

first=run(1,(5750.,5200.),(5500.,5200.),100,True,(-1.,0.))
assert first==run(1,(5750.,5200.),(5500.,5200.),100,True,(-1.,0.)),'raised terrain same-build replay changed'
cases.append(dict(name='exact_raised_world_replay',trace_sha256=first['trace_sha256'],checksum=first['checksum']))
if a.legacy:assert any('slope limit' in f for f in faults) and any('height missing' in f for f in faults),'causal baseline did not expose absent height and grade'
report=dict(suite='terrain-grade-outcomes',passed=True,legacy=a.legacy,library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases,detected_legacy_faults=sorted(set(faults)),limits=['Public gameplay APIs only; sparse initial births, no motion/grade helper calls, private sidecar writes or HP renewal.','Independent sampled actual swept circles include cusp sides and combined analytic hill+bowl gradients; samples support outcomes but do not prove continuous safety everywhere.','Conservative route budget based on actual outer bypass and gentle entrance distances; existing acceptance deadlines unchanged.','No suspension, oriented hull, shortest routes, per-role nav cache, visual art or dense scale acceptance established.'])
if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
def concise(v):
 if isinstance(v,dict):return {k:concise(x) for k,x in v.items() if k not in ('trace','reverse')}
 if isinstance(v,list):return [concise(x) for x in v]
 return v
print(json.dumps(concise(report)))
