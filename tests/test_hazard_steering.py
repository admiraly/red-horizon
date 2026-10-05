#!/usr/bin/env python3
"""Physical read-only local hazard steering; requires hazard_steering_probe.o."""
import ctypes as C, json, math, random, struct, sys
lib=C.CDLL(sys.argv[1])
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Result(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('status',C.c_int),('reason',C.c_uint)]
actors=(Entity*32768).in_dll(lib,'sim_entities')
lib.test_hazard_choose_goal.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.POINTER(Result)]
lib.test_hazard_steering_abi.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float]
lib.test_terrain_move.argtypes=[C.c_float]*5+[C.c_uint]
lib.test_terrain_move.restype=C.c_uint64
lib.terrain_path_clear.argtypes=[C.c_float]*4
lib.terrain_los.argtypes=[C.c_float]*6
lib.terrain_height.argtypes=[C.c_float]*2
lib.terrain_height.restype=C.c_float
lib.sim_checksum.restype=C.c_uint64
assert lib.sim_init(32,923)==0

def choose(i,center,radius):
    before=lib.sim_checksum()
    raw=bytes(actors)
    result=Result()
    lib.test_hazard_choose_goal(i,*center,radius,C.byref(result))
    assert before==lib.sim_checksum() and bytes(actors)==raw, 'helper mutated authority'
    return result

def set_actor(i,p,kind=0):
    actors[i].x,actors[i].z=p
    actors[i].kind=kind
    actors[i].hp=100

def physical(i,r,center,stepsize):
    start=(actors[i].x,actors[i].z)
    goal=(r.x,r.z)
    assert r.status==0 and r.reason in (1,2)
    assert math.dist(start,goal)<=36.0002
    assert lib.terrain_path_clear(*start,*goal)==1
    position=start
    for tick in range(700):
        prior=position
        position=struct.unpack('<ff',struct.pack('<Q',lib.test_terrain_move(*position,*goal,stepsize,actors[i].kind)))
        assert math.dist(prior,position)<=stepsize+.002
        assert lib.terrain_path_clear(*start,*position)==1
        if math.dist(position,goal)<0.01:break
    assert math.dist(position,goal)<0.01
    if r.reason==1:assert math.dist(position,center)>math.dist(start,center)
    else:
        ground=lib.terrain_height(*center)
        body=lib.terrain_height(*position)
        assert lib.terrain_los(center[0],ground+1,center[1],position[0],body+2,position[1])==0
    return tick+1

# Co-located individuals spread over eight directions at actual role-speed steps.
center=(3500.,2000.)
angles=[]
for i in range(8):
    set_actor(i,center,i%3)
    r=choose(i,center,20.)
    assert lib.test_hazard_steering_abi(i,*center,20)==1
    assert r.status==0 and r.reason==1
    assert abs(math.dist(center,(r.x,r.z))-32)<0.002
    physical(i,r,center,(.12,.5,.2)[i%3])
    angles.append(round(math.atan2(r.z-center[1],r.x-center[0]),5))
assert len(set(angles))==8
# Nonzero radius cap still moves away when escape cannot fit in one response.
set_actor(0,(3501.,2000.))
r=choose(0,center,100)
assert r.reason==1 and abs(math.dist((3501.,2000.),(r.x,r.z))-36)<0.002
physical(0,r,center,.12)
# Actual central wall geometry: reachable north-face shelter around its corner.
wall_examples=[]
for p,c in [((3980.,1090.),(4018.,1110.)),((3980.,1510.),(4018.,1490.)),((4020.,1090.),(3982.,1110.))]:
    set_actor(0,p)
    r=choose(0,c,60)
    if r.status==0 and r.reason==2:
        physical(0,r,c,.12)
        wall_examples.append({'actor':p,'impact':c,'goal':[r.x,r.z]})
assert wall_examples, 'no physically reachable actual-wall shelter selected'
# Blocked radial escape chooses a clear tangent instead of crossing a wall.
set_actor(0,(3980.,1300.))
r=choose(0,(3970.,1300.),24)
assert r.status==0 and r.reason==1
physical(0,r,(3970.,1300.),.12)
assert r.x<3988
# Independent double-precision segment/rectangle oracle around real obstacles.
records=(C.c_float*40).in_dll(lib,'terrain_obstacles')
boxes=[tuple(records[i*8:i*8+4]) for i in range(5)]
def intersects(start,end,box):
    lo,hi=0.,1.
    for p,q,mn,mx in ((start[0],end[0],box[0],box[2]),(start[1],end[1],box[1],box[3])):
        if p==q:
            if p<mn or p>mx:return False
        else:
            a,b=sorted(((mn-p)/(q-p),(mx-p)/(q-p)))
            lo,hi=max(lo,a),min(hi,b)
            if lo>hi:return False
    return True
rng=random.Random(923)
random_valid=0
for trial in range(240):
    b=boxes[trial%5]
    p=(rng.uniform(b[0]-45,b[2]+45),rng.uniform(b[1]-45,b[3]+45))
    if any(intersects(p,p,box) for box in boxes):continue
    c=(p[0]+rng.uniform(-35,35),p[1]+rng.uniform(-35,35))
    set_actor(0,p,trial%3)
    p=(actors[0].x,actors[0].z)
    r=choose(0,c,40)
    if r.status!=0:continue
    goal=(r.x,r.z)
    assert 0<=r.x<=8000 and 0<=r.z<=8000
    assert math.dist(p,goal)<=36.002
    assert not any(intersects(p,goal,box) for box in boxes)
    if r.reason==1:assert math.dist(goal,c)>math.dist(p,c)
    if random_valid<24:physical(0,r,c,(.12,.5,.2)[trial%3])
    random_valid+=1
assert random_valid>=60
# No output when no candidate is reachable or request is outside local danger.
set_actor(0,(0.,0.))
assert choose(0,(1.,1.),30).status==-1
set_actor(0,(3500.,2000.))
assert choose(0,(3200.,2000.),20).status==-1
for bad in (float('nan'),float('inf'),-1.,8001.):
    assert choose(0,(bad,2000.),20).status==-1
for bad in (float('nan'),float('inf'),0.,-1.,513.):
    assert choose(0,center,bad).status==-1
for i in (32,32768,0xffffffff):
    assert choose(i,center,20).status==-1
    assert lib.test_hazard_steering_abi(i,*center,20)==1
for badhp in (0,101,0xffffffff):
    actors[0].hp=badhp
    assert choose(0,center,20).status==-1
for kind in (3,4,0xffffffff):
    set_actor(0,center,kind)
    assert choose(0,center,20).status==-1
for p in ((float('nan'),2000.),(3500.,float('inf')),(-1.,2000.),(3500.,8001.),(4000.,1300.)):
    set_actor(0,p)
    assert choose(0,center,20).status==-1
print(json.dumps({'suite':'hazard-steering','passed':True,'seed':923,'center_directions':8,'independent_random_geometry_cases':random_valid,'actual_role_steps':[.12,.5,.2],'maximum_goal_distance':36,'reachable_occluded_shelter_examples':wall_examples,'authority_immutable':True,'limitations':'Straight reachable face candidates and five radial/tangent choices; no planned multi-corner route, no guaranteed shelter in open terrain.'}))
