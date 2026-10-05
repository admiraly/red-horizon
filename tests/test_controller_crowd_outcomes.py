#!/usr/bin/env python3
"""Independent relative-circle sweeps on production sim_tick/controller paths."""
import argparse,ctypes as C,hashlib,json,math,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('library');p.add_argument('--legacy',action='store_true');p.add_argument('--report');p.add_argument('--dense-ticks',type=int,default=60);a=p.parse_args()
lib=C.CDLL(str(Path(a.library).resolve()))
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Player(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
E=(Entity*32768).in_dll(lib,'sim_entities');P=(Player*4).in_dll(lib,'sim_players');V=(C.c_int*4).in_dll(lib,'sim_player_vehicle');alive=(C.c_uint*2).in_dll(lib,'sim_alive');enabled=C.c_uint.in_dll(lib,'crowd_enabled')
lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];lib.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_checksum.restype=C.c_uint64
R=(.55,3.55,4.49);TOL=.002

def pos(b):return b.x,b.z

def closest(a0,a1,b0,b1):
 d=(a0[0]-b0[0],a0[1]-b0[1]);v=(a1[0]-a0[0]-b1[0]+b0[0],a1[1]-a0[1]-b1[1]+b0[1]);vv=v[0]**2+v[1]**2;t=max(0,min(1,-(d[0]*v[0]+d[1]*v[1])/vv)) if vv else 0
 return math.hypot(d[0]+t*v[0],d[1]+t*v[1])

def reset(n=32):
 assert lib.sim_init(n,42)==0;enabled.value=int(not a.legacy);C.c_uint.in_dll(lib,'hazard_enabled').value=0
 for e in E[:n]:e.hp=0
 alive[0]=alive[1]=0
 for side in (0,1):
  for f in range(3):assert lib.sim_order(side,f,1)==0

def actor(i,kind,xy,side=0):
 e=E[i];e.x,e.z=xy;e.hp=400;e.kind=kind;e.side=side;e.front=0;e.target=-1;alive[side]+=1;return e

def human(slot,xy):
 assert lib.player_join(slot,0)==0;b=P[slot];b.x,b.z=xy;b.y=lib.terrain_height(*xy)+1.8;return b

def drive(slot,i,xy):
 e=actor(i,1,xy);b=human(slot,(xy[0]+2,xy[1]));assert lib.vehicle_enter(slot)==0 and V[slot]==i;return e

def input_(slot,v):assert lib.player_input(slot,4,*v,0,0)==0

def intent(before,after,v,speed,name,tick):
 norm=max(1,math.hypot(*v));ds=[q-p for p,q in zip(before,after)]
 assert math.hypot(*ds)<=speed+.0015,(name,'norm',tick,ds)
 assert all(abs(d)<=.0015 if x==0 else d*x>=-TOL and abs(d)<=speed*abs(x)/norm+.0015 for d,x in zip(ds,v)),(name,'input component/sign',tick,ds,v)

def fixture(mode,obstacle,diagonal=False,overlap=False,outward=False,moving=False,mirror=False,transition=None):
 reset();name=f'{mode}_vs_{obstacle}'+('_diagonal' if diagonal else '')+('_overlap_out' if overlap and outward else '_overlap_in' if overlap else '')+('_moving' if moving else '')+('_'+transition if transition else '')
 k={'infantry':0,'tank':1,'artillery':2}.get(obstacle);br=3.55 if obstacle=='driver' else .55 if k is None else R[k];sr=3.55 if mode=='driver' else .55
 start=(3500-sr-br+.1,2000) if overlap else (3500-sr-br-.3,2000) if diagonal else (3488,2000) if mode=='ai' else (3480,2000)
 if mode=='human':source=human(0,start)
 elif mode=='driver':source=drive(0,12,start)
 else:source=actor(12,0,start,int(mirror))
 if obstacle=='driver':other=drive(1,13,(3500,2000))
 elif obstacle=='human':other=human(1,(3500,2000))
 else:other=actor(13,k,(3500,2000),int(mirror))
 v=(-1,0) if outward else (1,1) if diagonal else (1,0)
 if mode=='ai':assert lib.sim_waypoint(int(mirror),0,3540,2000)==0;assert lib.sim_order(int(mirror),0,0)==0
 else:input_(0,v)
 if moving:input_(1,(-1,0))
 speed=.6 if mode=='driver' else .12 if mode=='ai' else .3
 faults=initial=0;minimum=math.dist(pos(source),pos(other));trace=hashlib.sha256();progress=0;released=False
 for t in range(120):
  if transition and t==75:
   if transition=='death':other.hp=0
   elif transition=='disconnect':assert lib.player_leave(1)==0
   elif transition=='generation':other.generation+=1;other.x,other.z=3550,2000
   released=True
  s0,b0=pos(source),pos(other);live=bool(other.hp and (obstacle!='human' or other.connected));lib.sim_tick();s1,b1=pos(source),pos(other)
  if mode!='ai':intent(s0,s1,v,speed,name,t)
  assert source.hp>0,(name,'fixture polluted by damage',t)
  d0=math.dist(s0,b0);d1=math.dist(s1,b1);d=closest(s0,s1,b0,b1);minimum=min(minimum,d)
  if live and other.hp:
   if d0<sr+br-TOL:
    initial+=1
    if not a.legacy:assert d1>=d0-TOL,(name,'deepened overlap',t,d0,d1)
   elif d<sr+br-TOL:
    faults+=1
    if not a.legacy:raise AssertionError((name,'introduced relative swept overlap',t,s0,s1,b0,b1,d,sr+br))
  progress+=math.dist(s0,s1);trace.update(struct.pack('<ffff',*s1,*b1))
 if not (overlap and not outward):assert progress>1,(name,'no useful approach/free travel')
 if diagonal:assert pos(source)[1]-start[1]>15,(name,'lost requested free-axis progress')
 if overlap and outward:assert math.dist(pos(source),pos(other))>sr+br+1,(name,'no outward recovery')
 if transition and not a.legacy:assert pos(source)[0]>3505,(name,'stale body blocked after transition')
 if mode=='driver':assert pos(P[0])==pos(source),(name,'boarded duplicate/driver detached')
 return dict(name=name,mode=mode,obstacle=obstacle,ticks=120,start=start,final=pos(source),swept_overlap_ticks=faults,initial_overlap_ticks=initial,minimum_relative_distance=minimum,progress_m=progress,trace_sha256=trace.hexdigest(),checksum=f'{lib.sim_checksum():016x}')

def checked(*args,**kwargs):
 r=fixture(*args,**kwargs);assert r==fixture(*args,**kwargs),'deterministic production replay differs';return r

rows=[]
for mode in ('human','driver'):
 for obstacle in ('infantry','tank','artillery','human'):
  for diagonal in (False,True):
   kw=dict(mode=mode,obstacle=obstacle,diagonal=diagonal);r=fixture(**kw);assert r==fixture(**kw),'replay';rows.append(r)
for mode in ('human','driver'):
 for out in (False,True):rows.append(checked(mode,'human',overlap=True,outward=out))
for mode in ('human','driver','ai'):rows.append(checked(mode,'human',moving=True))
rows.append(checked('driver','driver',moving=True))
for transition in ('death','disconnect','generation'):rows.append(checked('human','human',transition=transition))
for moving in (False,True):
 r=checked('ai','human',moving=moving);m=fixture('ai','human',moving=moving,mirror=True);assert r['trace_sha256']==m['trace_sha256'],'faction label dependent movement';rows.append(r)
if a.legacy:assert all(r['swept_overlap_ticks']>0 for r in rows if r['name'] in [f'{m}_vs_{o}' for m in ('human','driver') for o in ('infantry','tank','artillery','human')]),'baseline controls did not expose real collisions'



def four_controllers(driven=False,reverse=False):
 reset();starts=((3485,2000),(3515,2000),(3500,1985),(3500,2015));vectors=((1,0),(-1,0),(0,1),(0,-1));bodies=[]
 for physical,(xy,v) in enumerate(zip(starts,vectors)):
  slot=3-physical if reverse else physical
  body=drive(slot,8+physical,xy) if driven else human(slot,xy);input_(slot,v);bodies.append(body)
 radius=3.55 if driven else .55;speed=.6 if driven else .3;faults=0;traces=[hashlib.sha256() for b in bodies];progress=[0.]*4
 for t in range(120):
  old=[pos(b) for b in bodies];lib.sim_tick();new=[pos(b) for b in bodies]
  for i in range(4):
   assert bodies[i].hp>0;intent(old[i],new[i],vectors[i],speed,'four_drivers' if driven else 'four_humans',t);progress[i]+=math.dist(old[i],new[i]);traces[i].update(struct.pack('<ff',*new[i]))
   for j in range(i):
    d=closest(old[i],new[i],old[j],new[j])
    if d<2*radius-TOL:
     faults+=1
     if not a.legacy:raise AssertionError(('four controllers relative sweep',driven,reverse,t,i,j,d,2*radius))
 assert min(progress)>2,('four controllers no useful approach',driven,reverse,progress)
 return dict(driven=driven,reversed_slots=reverse,ticks=120,swept_overlap_ticks=faults,progress_m=progress,physical_trace_sha256=[h.hexdigest() for h in traces],checksum=f'{lib.sim_checksum():016x}')
four=[]
for driven in (False,True):
 for reverse in (False,True):
  r=four_controllers(driven,reverse);assert r==four_controllers(driven,reverse),'four controller exact replay';four.append(r)
slot_trace_invariance=[four[i]['physical_trace_sha256']==four[i+1]['physical_trace_sha256'] for i in (0,2)]

# Occupied publication locations must not create a fresh body overlap.
def placements():
 reset();sites=(C.c_float*96).in_dll(lib,'sim_sites')
 points=[(sites[i*8],sites[i*8+1]) for i in range(12)]
 z=sites[1];points += [(3780+dx,z+dz) for dx,dz in ((0,0),(-80,0),(0,80),(0,-80),(-150,0),(-150,80),(-150,-80),(-250,0))]
 for i,xy in enumerate(points):actor(i,2,xy)
 assert lib.player_join(0,0)==0
 overlaps=sum(math.dist(pos(P[0]),xy)<R[2]+.55-TOL for xy in points) if P[0].hp else 0
 if not a.legacy:assert not overlaps,('deployment published into occupied ground body',pos(P[0]))
 deploy=dict(name='fully_occupied_deployment',living_player=bool(P[0].hp),published_body_overlaps=overlaps)
 reset();hull=drive(0,12,(3500,2000));points=[]
 offsets=((-6,0),(6,0),(0,-6),(0,6),(-6,-6),(6,6),(-6,6),(6,-6))
 for i,(dx,dz) in enumerate(offsets):
  norm=math.hypot(dx,dz);xy=(3500+dx+4.5*dx/norm,2000+dz+4.5*dz/norm);points.append(xy);actor(i,2,xy)
 rc=lib.vehicle_exit(0)
 overlaps=sum(math.dist(pos(P[0]),xy)<R[2]+.55-TOL for xy in points) if rc==0 else 0
 if not a.legacy:assert not overlaps,('exit published into artillery footprint',pos(P[0]))
 assert rc in (-1,0)
 if rc==-1:assert V[0]==12 and pos(P[0])==pos(hull),'failed exit altered legitimate claim'
 exit_=dict(name='artillery_ring_exit',return_code=rc,published_body_overlaps=overlaps,boarded=V[0]==12)
 if a.legacy:assert deploy['published_body_overlaps'] and exit_['published_body_overlaps'],'placement causal controls absent'
 return [deploy,exit_]
placement_rows=placements()

# Actual combat scale: O(4N) controller-to-army sweeps; army mutual pairs are
# deliberately outside this observer (separate crowd suite). Persistent initial
# overlap is not newly introduced overlap, and is counted explicitly.
def census(n):
 assert lib.sim_init(n,42)==0 and lib.sim_scenario(3)==0;enabled.value=int(not a.legacy)
 controllers=[]
 for slot in range(4):
  assert lib.player_join(slot,slot%3)==0
  # Initially open finite routes across real allied fronts; no relocated armies.
  p=P[slot]
  # Approach existing allied bodies, without moving or freezing army actors.
  e=next(e for i,e in enumerate(E[:n]) if e.hp and e.side==0 and e.kind==0 and e.x<3800 and i>slot*100)
  p.x,p.z=e.x-4,e.z;p.y=lib.terrain_height(p.x,p.z)+1.8;input_(slot,(1,.3 if slot&1 else 0));
  if slot==3:
   i,e=next((i,e) for i,e in enumerate(E[:n]) if e.hp and e.side==0 and e.kind==1 and e.x<3800)
   p.x,p.z=e.x+2,e.z;p.y=lib.terrain_height(p.x,p.z)+1.8
   assert lib.vehicle_enter(slot)==0 and V[slot]==i
   controllers.append((e,3.55,slot))
  else:controllers.append((p,.55,slot))
 initial=faults=checks=0;controller_pair_checks=controller_pair_faults=0;moves=0;hp0=sum(e.hp for e in E[:n]);dead0=sum(e.hp==0 for e in E[:n]);initial_pairs=set();trace=hashlib.sha256()
 for t in range(a.dense_ticks):
  army=[(i,pos(e),e.kind,e.generation,e.hp) for i,e in enumerate(E[:n]) if e.hp and e.kind<3];old=[pos(x[0]) for x in controllers];lib.sim_tick()
  for c,(body,r,slot) in enumerate(controllers):
   if not body.hp:continue
   new=pos(body);intent(old[c],new,(1,.3 if slot&1 else 0),.6 if slot==3 else .3,'dense',t);moves+=math.dist(old[c],new)>.001;trace.update(struct.pack('<ff',*new))
   for i,b0,k,g,hp in army:
    e=E[i]
    if V[slot]==i:continue
    if not e.hp or e.generation!=g:continue
    # Independent distance broadphase; maximal real army/controller tick displacement.
    rr=r+R[k]
    if abs(old[c][0]-b0[0])>rr+1.3 or abs(old[c][1]-b0[1])>rr+1.3:continue
    checks+=1;key=(slot,i,g);d0=math.dist(old[c],b0);d=closest(old[c],new,b0,pos(e))
    if t==0 and d0<rr-TOL:initial_pairs.add(key)
    if key in initial_pairs:
     initial+=1
     if not a.legacy:assert math.dist(new,pos(e))>=d0-TOL,('dense initial overlap deepened',n,t,slot,i,d0,math.dist(new,pos(e)))
     if math.dist(new,pos(e))>=rr-TOL:initial_pairs.remove(key)
    elif d<rr-TOL:
     faults+=1
     if not a.legacy:raise AssertionError(('dense controller/army swept overlap',n,t,slot,i,d,rr))
  for c,(body,r,slot) in enumerate(controllers):
   if not body.hp:continue
   for j,(other,rr,oslot) in enumerate(controllers[:c]):
    if not other.hp:continue
    controller_pair_checks+=1
    d0=math.dist(old[c],old[j]);d1=math.dist(pos(body),pos(other));d=closest(old[c],pos(body),old[j],pos(other))
    if d0<r+rr-TOL:
     if not a.legacy:assert d1>=d0-TOL,('dense existing controller overlap deepened',n,t,slot,oslot,d0,d1)
    elif d<r+rr-TOL:
     controller_pair_faults+=1
     if not a.legacy:raise AssertionError(('dense controller/controller swept overlap',n,t,slot,oslot,d,r+rr))
 assert moves>=a.dense_ticks*2,('dense no useful human motion',n,moves)
 hp1=sum(e.hp for e in E[:n]);assert hp1<hp0,('real combat absent',n,hp0,hp1)
 return dict(units=n,ticks=a.dense_ticks,near_relative_sweep_checks=checks,controller_pair_sweep_checks=controller_pair_checks,controller_pair_new_overlap_ticks=controller_pair_faults,new_overlap_ticks=faults,initial_overlap_ticks=initial,controller_moving_ticks=moves,army_hp_before=hp0,army_hp_after=hp1,dead_before=dead0,dead_after=sum(e.hp==0 for e in E[:n]),trace_sha256=trace.hexdigest(),checksum=f'{lib.sim_checksum():016x}')
dense=[census(n) for n in (8192,16384)]
report=dict(suite='controller-crowd-outcomes',status='PASS',passed=True,legacy=a.legacy,library_sha256=hashlib.sha256(Path(a.library).read_bytes()).hexdigest(),observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=rows,four_controllers=four,slot_physical_trace_invariance=slot_trace_invariance,placements=placement_rows,dense=dense,limits=['Planar nominal body circles; full limbs/oriented mesh/vertical separation excluded.','Dense checks controller-to-army only, not every army mutual pair.','Dense uses three humans plus one legitimately boarded tank; nearest-army relative sweeps preserve real combat.','Deployment uses current authored site/near-field candidate set; no streamed-map claim.'])
if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
