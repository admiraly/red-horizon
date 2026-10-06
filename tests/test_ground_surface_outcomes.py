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
roads=json.loads((Path(__file__).resolve().parents[1]/'content/terrain/roads.json').read_text())['roads']
TOL=.002

def road(x,z,radius=0):
 for r in roads:
  ax,az=r['from'];bx,bz=r['to'];dx,dz=bx-ax,bz-az
  t=max(0,min(1,((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz)))
  if math.hypot(x-ax-t*dx,z-az-t*dz)<=r['half_width']-radius:return True
 return False

def pos():return E[12].x,E[12].z
def reset(kind=1,xy=(2000.,1300.),direction=(1.,0.),driver=False):
 assert lib.sim_init(32,42)==0
 # Sparse initial births only. Combat and hazard policy remain untouched.
 for e in E[:32]:e.hp=0
 alive=(C.c_uint*2).in_dll(lib,'sim_alive');alive[0]=1;alive[1]=0
 for side in (0,1):
  for front in range(3):assert lib.sim_order(side,front,1)==0
 e=E[12];e.x,e.z=xy;e.hp=400;e.side=0;e.kind=kind;e.front=0;e.target=-1;e.generation+=1
 assert lib.sim_waypoint(0,0,xy[0]+direction[0]*300,xy[1]+direction[1]*300)==0
 lib.sim_tick()
 assert abs(M[12].speed)<TOL
 if driver:board()
 else:assert lib.sim_order(0,0,0)==0
 return direction

def board():
 assert lib.player_join(0,0)==0
 P[0].x,P[0].z=E[12].x+2,E[12].z;P[0].y=lib.terrain_height(P[0].x,P[0].z)+1.8
 assert lib.vehicle_enter(0)==0 and V[0]==12

def step(direction=None,buttons=0,camera=None):
 before=pos();old=M[12].speed;heading=M[12].heading;kind=E[12].kind
 if direction is not None:
  yaw,pitch=camera if camera is not None else (0.,0.)
  assert lib.player_input(0,buttons,*direction,yaw,pitch)==0
 lib.sim_tick();after=pos();m=M[12];dx,dz=after[0]-before[0],after[1]-before[1]
 assert m.generation==E[12].generation and m.kind==kind and m.flags&1
 assert all(math.isfinite(v) for v in (m.heading,m.speed,m.turn,m.vx,m.vz))
 assert math.dist((dx,dz),(m.vx,m.vz))<TOL
 assert abs(dx*math.cos(m.heading)-dz*math.sin(m.heading))<TOL
 assert abs(dx*math.sin(m.heading)+dz*math.cos(m.heading)-m.speed)<TOL
 assert abs(m.speed-old)<=.041+TOL
 assert abs(math.atan2(math.sin(m.heading-heading),math.cos(m.heading-heading)))<=.061+TOL
 assert abs(m.speed)<=.602 and E[12].hp==400
 return dict(before=before,after=after,old_speed=old,speed=m.speed,heading=m.heading,
             centre_road=road(*before),body_road=road(*before,(0,3.55,4.49)[kind]))

def digest(rows):return hashlib.sha256(b''.join(struct.pack('<ffff',*r['after'],r['speed'],r['heading']) for r in rows)).hexdigest()

def run(kind,driver,xy=(2000.,1300.),direction=(1.,0.),ticks=75,camera=False,fire=False):
 reset(kind,xy,direction,driver);rows=[];shots_before=C.c_uint.in_dll(lib,'vehicle_shots').value
 for t in range(ticks):
  cam=(math.sin(t)*2.8,math.cos(t)*.6) if camera else None
  rows.append(step(direction if driver else None,1 if fire and t==40 else 0,cam))
 if fire:assert C.c_uint.in_dll(lib,'vehicle_shots').value==shots_before+1,'camera/cannon fixture did not launch actual cannon shot'
 return dict(first_step=rows[0]['speed'],last_step=rows[-1]['speed'],distance=math.dist(rows[0]['before'],rows[-1]['after']),trace_sha256=digest(rows),checksum=f'{lib.sim_checksum():016x}',trace=rows)

faults=[];cases=[]
def check(condition,label):
 if not condition:
  faults.append(label)
  if not a.legacy:raise AssertionError(label)

def paired(kind,driver):
 on=run(kind,driver);off=run(kind,driver,(2000.,1400.))
 factor=.8 if kind==1 else .7;acc=.02 if kind==1 else .01;cap=(.6 if driver else .5) if kind==1 else .2
 check(abs(on['first_step']-acc)<TOL,f'{kind}/{driver}: road first acceleration')
 check(abs(off['first_step']-acc*factor)<TOL,f'{kind}/{driver}: offroad first acceleration')
 check(abs(on['last_step']-cap)<TOL,f'{kind}/{driver}: road steady cap')
 check(abs(off['last_step']-cap*factor)<TOL,f'{kind}/{driver}: offroad steady cap')
 check(on['distance']>off['distance']*1.1,f'{kind}/{driver}: useful road advantage')
 for label,result,scale in (('road',on,1),('offroad',off,factor)):
  check(all(abs(r['speed']-min(r['old_speed']+acc*scale,cap*scale))<TOL for r in result['trace']),f'{kind}/{driver}: {label} sustained acceleration envelope')
 return dict(name='paired_'+('driver_tank' if driver else 'ai_tank' if kind==1 else 'ai_artillery'),factor=factor,road=on,offroad=off)

for kind,driver in ((1,False),(2,False),(1,True)):cases.append(paired(kind,driver))
for kind in (1,2):
 centre=run(kind,False,(2000.,1300.));edge=run(kind,False,(2000.,1308.))
 assert all(r['centre_road'] and not r['body_road'] for r in edge['trace'])
 check(edge['last_step']<centre['last_step']*.9,f'{kind}: road centre insufficient for whole hull')
 cases.append(dict(name='whole_hull_edge_tank' if kind==1 else 'whole_hull_edge_artillery',centre=centre,edge=edge))

# Endcap where a tank circle fits, but artillery circle extends beyond the capsule.
for kind in (1,2):
 result=run(kind,False,(996.,1296.),(-1/math.sqrt(2),-1/math.sqrt(2)),ticks=1)
 expected=(.02 if kind==1 else .01)*(1 if kind==1 else .7)
 assert result['trace'][0]['centre_road'] and result['trace'][0]['body_road']==(kind==1)
 check(abs(result['first_step']-expected)<TOL,f'{kind}: finite endcap hull classification')
 cases.append(dict(name='endcap_tank' if kind==1 else 'endcap_artillery',result=result))

# Clear diagonal strategic dogleg: public drive follows its actual centreline.
d=(120/math.hypot(120,250),-250/math.hypot(120,250))
bend=run(1,True,(3860.,1175.),d,ticks=60)
assert all(r['body_road'] for r in bend['trace'])
check(abs(bend['last_step']-.6)<TOL,'diagonal dogleg road drive cap')
cases.append(dict(name='diagonal_dogleg',result=bend))

cross=run(1,True,(2000.,1280.),(0.,1.),ticks=125)
transitions=[]
for i,(p,q) in enumerate(zip(cross['trace'],cross['trace'][1:]),1):
 if p['body_road']!=q['body_road']:transitions.append(dict(tick=i,from_road=p['body_road'],to_road=q['body_road'],before=q['before'],old_speed=q['old_speed'],speed=q['speed']))
assert len(transitions)==2 and transitions[0]['to_road'] and not transitions[1]['to_road'],'fixture missed both real surface boundaries'
exit_=transitions[1]
check(exit_['old_speed']>.5 and .001<exit_['old_speed']-exit_['speed']<=.042,'leaving road brakes without instant offroad clamp')
check(abs(cross['last_step']-.48)<TOL,'crossing settles at offroad speed')
cases.append(dict(name='both_boundaries_bounded_transition',transitions=transitions,result=cross))

for z in (1300.,1400.):
 reset(xy=(2000.,z),driver=True)
 rows=[step((1.,0.)) for _ in range(60)]
 reverse=[step((-1.,0.)) for _ in range(70)]
 expected=-.18*(1 if z==1300 else .8)
 check(abs(reverse[-1]['speed']-expected)<TOL,f'{z}: surface reverse cap')
 assert reverse[0]['speed']>0 and any(abs(r['speed'])<.042 for r in reverse)
 cases.append(dict(name='road_reverse' if z==1300 else 'offroad_reverse',forward=rows[-1],reverse=reverse,trace_sha256=digest(rows+reverse)))

# Compare equal incoming momentum: surface affects traction, not brake or yaw law.
matched=[]
for z,ticks in ((1300.,20),(1400.,25 if not a.legacy else 20)):
 reset(xy=(2000.,z),driver=True)
 for _ in range(ticks):step((1.,0.))
 incoming=M[12].speed
 brake_rows=[step((0.,0.)) for _ in range(20)]
 assert abs(incoming-.4)<TOL and abs(brake_rows[0]['speed']-.36)<TOL
 assert abs(brake_rows[-1]['speed'])<TOL
 matched.append(dict(surface='road' if z==1300 else 'offroad',incoming=incoming,braking=brake_rows))
assert all(abs(p['speed']-q['speed'])<TOL for p,q in zip(matched[0]['braking'],matched[1]['braking']))
cases.append(dict(name='same_momentum_same_braking',surfaces=matched))
matched=[]
for z,ticks in ((1300.,20),(1400.,25 if not a.legacy else 20)):
 reset(xy=(2000.,z),driver=True)
 for _ in range(ticks):step((1.,0.))
 turn_rows=[step((0.,1.)) for _ in range(10)]
 matched.append(dict(surface='road' if z==1300 else 'offroad',turning=turn_rows))
assert all(abs(p['heading']-q['heading'])<TOL and abs(p['speed']-q['speed'])<TOL for p,q in zip(matched[0]['turning'],matched[1]['turning']))
cases.append(dict(name='same_momentum_same_yaw_law',surfaces=matched))

reset(xy=(2000.,1400.));ai=[step() for _ in range(60)];before=bytes(M[12]);board();assert bytes(M[12])==before
first=step((1.,0.));assert abs(first['speed']-ai[-1]['speed'])<.022
assert lib.vehicle_exit(0)==0
P[0].x,P[0].z=E[12].x+30,E[12].z+30;P[0].y=lib.terrain_height(P[0].x,P[0].z)+1.8
returned=step();assert abs(returned['speed']-first['speed'])<.042
check(abs(ai[-1]['speed']-.4)<TOL,'offroad AI before physical handoff')
cases.append(dict(name='offroad_ai_driver_ai_handoff',ai_last=ai[-1],first_driver=first,first_returned_ai=returned))

for z in (1300.,1400.):
 plain=run(1,True,(2000.,z));varied=run(1,True,(2000.,z),camera=True,fire=True)
 assert plain['trace_sha256']==varied['trace_sha256'],'camera/cannon altered physical road trajectory'
 cases.append(dict(name='camera_cannon_road' if z==1300 else 'camera_cannon_offroad',trace_sha256=plain['trace_sha256']))
# Replay checks real world state and observed physical trajectory, with no snapshot writes.
first=run(1,True,(2000.,1280.),(0.,1.),ticks=125)
assert first==run(1,True,(2000.,1280.),(0.,1.),ticks=125),'same-build road crossing replay changed'
cases.append(dict(name='exact_world_replay',trace_sha256=first['trace_sha256'],checksum=first['checksum']))
if a.legacy:assert len(faults)>=8,'previous runtime failed to expose absent road policy'
report=dict(suite='ground-surface-outcomes',passed=True,legacy=a.legacy,library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases,detected_legacy_faults=faults,limits=['Only public sim_tick/player_input/boarding/orders move the authority; no surface/ground actuator calls or motion writes.','Sparse initial development births, same genuine terrain and unchanged HP/combat/hazard policy.','Independent canonical capsule distance determines observed source surface; whole-circle fit in one capsule is the documented approximation.','No slope limits, suspension, oriented hulls, road routing preference, visual quality, target GPU or dense-scale acceptance established here.'])
if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
def concise(value):
 if isinstance(value,dict):return {k:concise(v) for k,v in value.items() if k not in ('trace','reverse','braking','turning')}
 if isinstance(value,list):return [concise(v) for v in value]
 return value
print(json.dumps(concise(report)))
