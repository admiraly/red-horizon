#!/usr/bin/env python3
"""Independent expanded-solid sweeps over actual authoritative movement ticks."""
import argparse
import ctypes as C
import hashlib
import json
import math
import struct
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('library')
parser.add_argument('--legacy',action='store_true')
parser.add_argument('--report')
parser.add_argument('--dense-ticks',type=int,default=120)
a=parser.parse_args()
lib=C.CDLL(str(Path(a.library).resolve()))
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Player(C.Structure):
    _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
entities=(Entity*32768).in_dll(lib,'sim_entities')
players=(Player*4).in_dll(lib,'sim_players')
alive=(C.c_uint*2).in_dll(lib,'sim_alive')
lib.sim_init.argtypes=[C.c_uint,C.c_uint]
lib.sim_order.argtypes=[C.c_uint]*3
lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
lib.terrain_height.argtypes=[C.c_float]*2
lib.terrain_height.restype=C.c_float
lib.sim_checksum.restype=C.c_uint64
try: enabled=C.c_uint.in_dll(lib,'terrain_body_enabled')
except ValueError: enabled=None
assert a.legacy or enabled is not None,'candidate must expose production footprint policy'
RADII=(.55,3.55,4.49)
SPEED=(.12,.5,.2)
count=C.c_uint.in_dll(lib,'terrain_obstacle_count').value
raw=(C.c_uint*(count*8)).in_dll(lib,'terrain_obstacles')
boxes=[struct.unpack('<ffff',bytes(raw)[i*32:i*32+16]) for i in range(count) if raw[i*8+6]&1]
TOL=.002

def pose(e):return e.x,e.z

def expand(box,r):return box[0]-r,box[1]-r,box[2]+r,box[3]+r

def crosses(start,end,box):
    lo,hi=0.,1.
    for p,q,mn,mx in ((start[0],end[0],box[0],box[2]),(start[1],end[1],box[1],box[3])):
        d=q-p
        if not d:
            if not mn<=p<=mx:return False
        else:
            t,u=sorted(((mn-p)/d,(mx-p)/d))
            lo,hi=max(lo,t),min(hi,u)
            if lo>hi:return False
    return True

def violation(start,end,kind):
    r=RADII[kind]
    # Shrink only the expanded box by2mm to tolerate float32 arithmetic; this
    # does not convert visible decimetre/metre penetration into acceptance.
    wall=any(crosses(start,end,expand(b,r-TOL)) for b in boxes)
    edge=any(v<r-TOL or v>8000-r+TOL for v in (*start,*end))
    return wall or edge

def penetration(p,kind):
    r=RADII[kind]
    depth=max(0,r-p[0],r-p[1],p[0]-(8000-r),p[1]-(8000-r))
    for b in boxes:
        mnx,mnz,mxx,mxz=expand(b,r)
        if mnx<=p[0]<=mxx and mnz<=p[1]<=mxz:
            depth=max(depth,min(p[0]-mnx,mxx-p[0],p[1]-mnz,mxz-p[1]))
    return depth

def initialize(mirror=False,count=32):
    assert lib.sim_init(count,42)==0
    if enabled is not None:enabled.value=0 if a.legacy else 1
    C.c_uint.in_dll(lib,'hazard_enabled').value=0
    for e in entities[:count]:e.hp=0
    alive[0]=alive[1]=0
    for side in (0,1):
        for front in range(3):assert lib.sim_order(side,front,1)==0

def record(name,kind,start,ticks,goal=None,mode='army',intent=None,mirror=False,invalid=False):
    initialize(mirror)
    e=entities[12]
    if mode!='player':
        e.x,e.z,e.kind,e.hp,e.side,e.front,e.target=*start,kind,100,int(mirror),0,-1
        alive[int(mirror)]=1
    if mode=='army':
        assert lib.sim_waypoint(int(mirror),0,*goal)==0
        assert lib.sim_order(int(mirror),0,0)==0
        actor=e
        speed=SPEED[kind]
    else:
        assert lib.player_join(0,0)==0
        p=players[0]
        p.x,p.z=start
        p.y=lib.terrain_height(*start)+1.8
        if mode=='driver':
            p.x=start[0]+2
            assert lib.vehicle_enter(0)==0
            actor=e
            speed=.6
        else:
            actor=p
            speed=1/12 if intent[0]&32 else (.3 if intent[0]&4 else 1/6)
        assert lib.player_input(0,intent[0],intent[1],intent[2],0,0)==0
    assert invalid or not violation(start,start,kind),(name,'fixture starts with body overlap')
    trace=hashlib.sha256()
    collision_ticks=0
    intent_fault_ticks=0
    contact_slide_steps=0
    maximum_penetration=penetration(start,kind)
    samples=[]
    for tick in range(ticks):
        before=pose(actor)
        before_depth=penetration(before,kind)
        lib.sim_tick()
        after=pose(actor)
        assert actor.hp==100,(name,'movement fixture polluted by damage',tick,actor.hp)
        assert math.dist(before,after)<=speed+.0015,(name,'speed bound',tick,before,after)
        if mode!='army':
            requested=(intent[1],intent[2])
            norm=max(1,math.hypot(*requested))
            delta=tuple(q-p for p,q in zip(before,after))
            fault=any((abs(d)>1e-6 if v==0 else d*v<-TOL or abs(d)>speed*abs(v)/norm+.0015) for d,v in zip(delta,requested))
            intent_fault_ticks+=fault
            if not a.legacy:assert not fault,(name,'unrequested, reversed or amplified input component',tick,before,after,requested)
            if requested[0] and requested[1] and abs(delta[0])<1e-6 and delta[1]*requested[1]>.001:
                contact_slide_steps+=1
        trace.update(struct.pack('<ff',*after))
        collision_ticks+=violation(before,after,kind)
        depth=penetration(after,kind)
        maximum_penetration=max(maximum_penetration,depth)
        if not a.legacy:
            if invalid:
                assert depth<=before_depth+TOL,(name,'initial penetration deepened',tick,before,after,before_depth,depth)
                if before_depth<=TOL:assert not violation(before,after,kind),(name,'reentered static body')
            else:assert not violation(before,after,kind),(name,'expanded static-solid sweep',tick,before,after,depth)
        if mode=='driver':assert pose(players[0])==after,(name,'driver detached from actual hull')
        if tick in (29,119,ticks-1):samples.append({'tick':tick+1,'pose':after})
    end=pose(actor)
    if not a.legacy and goal is not None:
        if name.endswith('_edge_goal'):
            # Center-goal0 is intentionally unreachable to a finite body.
            assert abs(end[0]-RADII[kind])<.02,(name,'failed useful advance to body map inset',end)
        else:assert math.dist(end,goal)<.6,(name,'failed body-safe route progress',end,goal)
    if not a.legacy and mode!='army' and not invalid:
        assert math.dist(start,end)>1,(name,'controller frozen before physical obstruction',start,end)
        if name.endswith('_diagonal_wall'):assert contact_slide_steps>0,(name,'diagonal contact failed requested legal slide',end)
    return {'name':name,'mode':mode,'kind':kind,'radius_m':RADII[kind],'ticks':ticks,'start':start,'goal':goal,
            'final':end,'final_goal_error':None if goal is None else math.dist(end,goal),
            'body_collision_ticks':collision_ticks,'maximum_penetration_m':maximum_penetration,
            'input':intent,'intent_fault_ticks':intent_fault_ticks,'diagonal_contact_slide_steps':contact_slide_steps,
            'initial_invalid':invalid,'samples':samples,'physical_trace_sha256':trace.hexdigest(),
            'checksum':f'{lib.sim_checksum():016x}'}

cases=[
 ('infantry_wall_skirt',0,(3970,1099.6),800,(4030,1099.6)),
 ('tank_wall_skirt',1,(3970,1097),400,(4030,1097)),
 ('artillery_wall_skirt',2,(3970,1096),800,(4030,1096)),
 ('tank_wall_route',1,(3970,1300),1800,(4030,1300)),
 ('artillery_wall_route',2,(3970,1300),4200,(4030,1300)),
 ('tank_structure_route',1,(5150,1570),600,(5250,1570)),
 ('infantry_edge_goal',0,(5,2000),100,(0,2000)),
 ('tank_edge_goal',1,(10,2000),100,(0,2000)),
 ('artillery_edge_goal',2,(10,2000),100,(0,2000)),
 ('player_wall_skirt',0,(3970,1099.6),240,None,'player',(4,1,0)),
 ('player_jump_wall_skirt',0,(3970,1099.6),240,None,'player',(4|64,1,0)),
 ('player_crouch_wall_skirt',0,(3970,1099.6),800,None,'player',(32,1,0)),
 ('player_wall',0,(3980,1300),90,None,'player',(4,1,0)),
 ('player_jump_wall',0,(3980,1300),90,None,'player',(4|64,1,0)),
 ('player_crouch_wall',0,(3980,1300),180,None,'player',(32,1,0)),
 ('driven_tank_wall',1,(3980,1300),90,None,'driver',(0,1,0)),
 ('player_diagonal_wall',0,(3980,1300),90,None,'player',(4,1,1)),
 ('driven_tank_diagonal_wall',1,(3980,1300),90,None,'driver',(0,1,1)),
 ('player_edge',0,(5,2000),90,None,'player',(4,-1,0)),
 ('driven_tank_edge',1,(10,2000),90,None,'driver',(0,-1,0)),
 ('player_initial_invalid',0,(3987.8,1300),60,None,'player',(4,1,0),False,True),
]
reports=[]
for case in cases:
    row=record(*case)
    assert row==record(*case),(case[0],'deterministic replay differs')
    if row['mode']=='army':
        # Only faction metadata changes; coordinates, IDs, fronts and commands
        # retain their actual values. Compare every physical movement tick.
        mirror=record(*case,mirror=True)
        assert row['physical_trace_sha256']==mirror['physical_trace_sha256'],(case[0],'label-dependent movement')
    reports.append(row)
if a.legacy:
    assert all(r['body_collision_ticks']>0 for r in reports if r['name'] not in ('player_wall','player_jump_wall','player_crouch_wall','player_diagonal_wall')),[(r['name'],r['body_collision_ticks']) for r in reports]

def census(n):
    assert lib.sim_init(n,42)==0 and lib.sim_scenario(3)==0
    if enabled is not None:enabled.value=0 if a.legacy else 1
    initial={i:pose(e) for i,e in enumerate(entities[:n]) if e.hp and e.kind<3}
    initial_invalid={i for i in initial if violation(initial[i],initial[i],entities[i].kind)}
    invalid_steps=reentries=0
    initial_count=len(initial_invalid)
    for _ in range(a.dense_ticks):
        before={i:pose(e) for i,e in enumerate(entities[:n]) if e.hp and e.kind<3}
        lib.sim_tick()
        for i,old in before.items():
            e=entities[i]
            if e.hp and violation(old,pose(e),e.kind):
                invalid_steps+=1
                if not violation(old,old,e.kind):reentries+=1
    living=[i for i in initial if entities[i].hp and entities[i].kind<3]
    return {'entities':n,'scenario':'scale-hotspot','ticks':a.dense_ticks,'seed':42,
            'initial_living_ground':len(initial),'initial_invalid_ground':initial_count,
            'final_living_ground':len(living),'final_invalid_ground':sum(violation(pose(entities[i]),pose(entities[i]),entities[i].kind) for i in living),
            'invalid_ground_sweep_steps':invalid_steps,'newly_invalid_clear_start_steps':reentries,
            'surviving_ground_moved_over_1m':sum(math.dist(initial[i],pose(entities[i]))>1 for i in living),
            'alive':list(alive),'checksum':f'{lib.sim_checksum():016x}',
            'scope':'Natural authored deployment; initial overlap and casualties are reported, not treated as clear-start acceptance'}
dense=[]
for n in (8192,16384):
    row=census(n)
    assert row==census(n),(n,'natural army replay differs')
    if not a.legacy:assert row['newly_invalid_clear_start_steps']==0,(n,'natural army crossed expanded wall')
    dense.append(row)
report={'suite':'terrain-body-outcomes','passed':True,'legacy':a.legacy,'terrain_body_module_present':enabled is not None,
        'library_sha256':hashlib.sha256(Path(a.library).read_bytes()).hexdigest(),
        'oracle_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'expanded_rectangle_radii_m':RADII,'solid_boxes':boxes,'controlled_encounters':reports,'dense':dense,
        'deterministic_replay':True,'physical_faction_label_swap':True,
        'candidate_controller_input_components_preserved':not a.legacy,
        'scope':'Production sim_tick orders, human input and actual driven hulls; planar conservative expanded AABB footprint policy. No claim of oriented hulls, vertical vault geometry or full operation acceptance.'}
if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
