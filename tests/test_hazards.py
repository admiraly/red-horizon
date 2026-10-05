#!/usr/bin/env python3
"""Focused actual NASM hazard cache/query/lifecycle checks (LIB argument).
No claim about production steering, survival, terrain scenarios or scale timing.
"""
import ctypes as C
import json
import math
import sys
lib=C.CDLL(sys.argv[1])
class Projectile(C.Structure):
    _fields_=[(n,C.c_float) for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint) for n in ('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint) for n in ('source','generation','active','source_generation','reserved')]
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front','target','generation')]
class Hazard(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('radius',C.c_float),('side',C.c_uint)]+[(n,C.c_float) for n in ('px','py','pz')]+[(n,C.c_uint) for n in ('projectile','generation','kind')]+[('eta',C.c_float),('active',C.c_uint)]+[('reserved',C.c_uint*4)]
pool=(Projectile*512).in_dll(lib,'sim_projectiles')
cache=(Hazard*512).in_dll(lib,'hazards')
entities=(Entity*32768).in_dll(lib,'sim_entities')
states=(C.c_uint*(32768*8)).in_dll(lib,'hazard_states')
metrics=(C.c_uint64*8).in_dll(lib,'hazard_metrics')
tick=C.c_uint.in_dll(lib,'sim_tick_count')
enabled=C.c_uint.in_dll(lib,'hazard_enabled')
count=C.c_uint.in_dll(lib,'sim_count')
lib.hazard_query.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float]
lib.terrain_height.argtypes=[C.c_float,C.c_float]
lib.terrain_height.restype=C.c_float
lib.hazard_entity_goal.argtypes=[C.c_uint]

def reset():
    if hasattr(lib,'sim_init'):assert lib.sim_init(32,19)==0
    else:
        count.value=32
        lib.test_init()
    for e in entities[:32]:e.hp=0
    C.memset(C.addressof(pool),0,C.sizeof(pool))
    tick.value=0
    lib.hazard_init()

def explosive(i=0,kind=3,side=1):
    p=pool[i]
    p.x,p.z,p.y=1000,1300,ground+25
    p.vx,p.vy,p.vz=0,-1,0
    p.ttl,p.side,p.kind,p.damage,p.radius=120,side,kind,100,35
    p.source,p.generation,p.active=31,17,1
    return p

def query(side=0,x=1000,y=None,z=1300):
    return lib.hazard_query(side,x,ground+2 if y is None else y,z)

def unchanged_query(*args):
    before=(bytes(pool),bytes(cache),bytes(states),tuple(metrics))
    answer=query(*args)
    assert before==(bytes(pool),bytes(cache),bytes(states),tuple(metrics))
    return answer
reset()
ground=lib.terrain_height(1000,1300)
for kind in (2,3):
    reset();p=explosive(kind=kind);lib.hazard_tick()
    assert cache[0].active==1 and 0<cache[0].eta<=120
    assert unchanged_query()==0 and unchanged_query(1)==-1
    # Actual discrete step predicts ground interception within one tick.
    t=int(cache[0].eta)
    y=p.y+p.vy*t-.0109*t*(t-1)/2
    prev=p.y+p.vy*(t-1)-.0109*(t-1)*(t-2)/2
    assert y<=ground+.0001 and prev>ground-.0001,(kind,t,y,ground)
    assert unchanged_query(0,1100)==-1
    assert unchanged_query(0,1000,ground+400)==-1
    assert unchanged_query(0,math.nan)==-1
    assert unchanged_query(0,1000,math.inf)==-1
    p.active=0;assert unchanged_query()==-1
    p.active=1;p.generation+=1;assert unchanged_query()==-1
    p.generation-=1;p.ttl=0;assert unchanged_query()==-1
    p.ttl=120;p.side=0;assert unchanged_query()==-1
    p.side=1;p.kind=1;assert unchanged_query()==-1
    p.kind=kind;p.y=math.nan;assert unchanged_query()==-1
# Input validation rejects unusable predictions before spatial insertion.
for field,value in [('vx',math.inf),('vy',math.nan),('vz',math.inf),('radius',math.nan),('radius',51),('radius',0),('ttl',0),('generation',0),('kind',1),('side',2),('active',0)]:
    reset();p=explosive();setattr(p,field,value);lib.hazard_tick()
    assert cache[0].active==0 and unchanged_query()==-1,(field,value)
# No lookahead beyond expiry/horizon, including a rising projectile.
reset();p=explosive();p.vy=20;lib.hazard_tick();assert cache[0].active==0
reset();p=explosive();p.ttl=2;lib.hazard_tick();assert cache[0].active==0
# Full pool in one spatial cell remains <=8 candidates; rotating scan gives
# every live projectile an opportunity, rather than permanently lowest IDs.
reset()
for i in range(512):explosive(i)
seen=set()
for frame in range(0,512,8):
    tick.value=frame;lib.hazard_tick();selected=unchanged_query()
    assert selected>=0
    seen.add(selected)
assert len(seen)>=32 and metrics[1]>0,len(seen)
if hasattr(lib,'test_query_los'):
    lib.test_query_los.argtypes=lib.hazard_query.argtypes
    assert lib.test_query_los(0,1000,ground+2,1300)<=8
    blocked=C.c_uint.in_dll(lib,'los_blocked');blocked.value=1
    assert unchanged_query()==-1
    assert lib.test_query_los(0,1000,ground+2,1300)<=8
    blocked.value=0
# Controlled blocked LOS forces the full eight-candidate cost. All8,192
# actors remain initialized while the authoritative LOS budget caps at1,024.
if hasattr(lib,'los_blocked'):
    reset();count.value=8192
    for e in entities[:8192]:
        e.x,e.z,e.hp,e.side,e.kind,e.generation=1000,1300,100,0,0,1
    for i in range(8):explosive(i)
    blocked=C.c_uint.in_dll(lib,'los_blocked');blocked.value=1
    lib.hazard_tick() # initialize every generation before observation
    tick.value=1;before=metrics[5];lib.hazard_tick()
    assert metrics[5]-before==1024 and metrics[6]>=896
    blocked.value=0
# Generation/death/aircraft/driving invalidate read-only goal access.
reset();e=entities[0]
e.x,e.z,e.hp,e.side,e.kind,e.generation=1000,1300,100,0,0,21
for frame in range(17):
    tick.value=frame;explosive();lib.hazard_tick()
assert metrics[2]>=1 and lib.hazard_entity_goal(0)==1
snapshot=bytes(states)
for _ in range(10):assert lib.hazard_entity_goal(0)==1
assert snapshot==bytes(states)
e.generation+=1;assert lib.hazard_entity_goal(0)==0
e.generation-=1;e.hp=0;assert lib.hazard_entity_goal(0)==0
e.hp=100;e.kind=3;assert lib.hazard_entity_goal(0)==0
e.kind=0
drivers=(C.c_int*32768).in_dll(lib,'vehicle_entity_driver');drivers[0]=0
assert lib.hazard_entity_goal(0)==0
drivers[0]=-1
tick.value=100;assert lib.hazard_entity_goal(0)==0
enabled.value=0;lib.hazard_tick();assert not any(states)
print(json.dumps({'suite':'hazards','passed':True,'projectile_capacity':512,'per_query_LOS_bound':8,'fair_overflow_selected_ids':len(seen),'checks':['actual discrete gravity intercept','hostile visibility gates','read-only query','finite validation','expiry generation','full-pool fairness','committed goal lifecycle']}))
