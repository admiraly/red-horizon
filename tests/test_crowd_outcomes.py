#!/usr/bin/env python3
"""Physical body avoidance over production NASM world ticks, never proxy movement."""
import argparse
import ctypes as C
import hashlib
import json
import math
import struct
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('library')
p.add_argument('--legacy', action='store_true', help='record collision-producing old movement')
p.add_argument('--report')
p.add_argument('--dense-ticks', type=int, default=120)
a = p.parse_args()
lib = C.CDLL(a.library)
lib.sim_init.argtypes = [C.c_uint, C.c_uint]
lib.sim_order.argtypes = [C.c_uint]*3
lib.sim_waypoint.argtypes = [C.c_uint, C.c_uint, C.c_float, C.c_float]
lib.sim_checksum.restype = C.c_uint64
lib.terrain_blocked.argtypes = [C.c_float, C.c_float, C.c_uint]

class Entity(C.Structure):
    _fields_ = [('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),
                ('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
entities = (Entity*32768).in_dll(lib,'sim_entities')
alive = (C.c_uint*2).in_dll(lib,'sim_alive')
drivers = (C.c_int*32768).in_dll(lib,'vehicle_entity_driver')
try:
    enabled = C.c_uint.in_dll(lib,'crowd_enabled')
except ValueError:
    enabled = None
assert a.legacy or enabled is not None, 'candidate must expose production crowd_enabled'
# Vehicle discs conservatively enclose the scale-one authored mesh radius;
# infantry uses a torso steering footprint, not its full animated weapon envelope.
RADII = (.55, 3.55, 4.49)
SPEED = (.12, .5, .2)
bake=Path(__file__).resolve().parents[1]/'content/models/bake-report.json'
mesh_records=json.loads(bake.read_text())['meshes']
vehicle_geometry={str(kind):{'maximum_baked_radius':max(m['radius'] for m in mesh_records if m['role']==kind),
                            'lod0_dimensions':next(m['dimensions'] for m in mesh_records if m['role']==kind and m['lod']==0)}
                  for kind in (1,2)}
assert all(RADII[kind]>=vehicle_geometry[str(kind)]['maximum_baked_radius'] for kind in (1,2))
boxes = [tuple((C.c_float*40).in_dll(lib,'terrain_obstacles')[i*8:i*8+4]) for i in range(5)]


def pos(e): return (e.x,e.z)
def segment_distance(point, start, end):
    dx,dz = end[0]-start[0],end[1]-start[1]
    den = dx*dx+dz*dz
    t = 0 if den == 0 else min(1,max(0,((point[0]-start[0])*dx+(point[1]-start[1])*dz)/den))
    return math.dist(point,(start[0]+t*dx,start[1]+t*dz))

def crosses(start,end,box):
    low,high=0.,1.
    for first,last,mn,mx in ((start[0],end[0],box[0],box[2]),(start[1],end[1],box[1],box[3])):
        delta=last-first
        if delta == 0:
            if not mn<=first<=mx: return False
        else:
            lo,hi=sorted(((mn-first)/delta,(mx-first)/delta))
            low,high=max(low,lo),min(high,hi)
            if low>high: return False
    return True

def setup(records, mirror=False):
    assert lib.sim_init(32,42)==0
    if enabled is not None: enabled.value = 0 if a.legacy else 1
    C.c_uint.in_dll(lib,'hazard_enabled').value = 0
    for e in entities[:32]: e.hp=0
    alive[0]=alive[1]=0
    for side in (0,1):
        for front in range(3): assert lib.sim_order(side,front,1)==0
    for i,x,z,kind,front,goal in records:
        e=entities[i]
        e.x,e.z,e.hp,e.side,e.kind,e.front,e.target=x,z,100,int(mirror),kind,front,-1
        alive[int(mirror)]+=1
        if goal is not None:
            assert lib.sim_waypoint(int(mirror),front,*goal)==0
            assert lib.sim_order(int(mirror),front,0)==0
    return {i:pos(entities[i]) for i,*_ in records}


def encounter(name,records,ticks,mirror=False,overlap=False,ignore=()):
    initial=setup(records,mirror)
    movable={r[0] for r in records if r[-1] is not None}
    if name=='driven_obstacle': drivers[records[1][0]]=0
    ids=[r[0] for r in records]
    pairs=[(i,j) for n,i in enumerate(ids) for j in ids[n+1:]
           if entities[i].kind<3 and entities[j].kind<3 and (i,j) not in ignore]
    initial_gaps={(i,j):math.dist(initial[i],initial[j])-RADII[entities[i].kind]-RADII[entities[j].kind] for i,j in pairs}
    initial_separation=min(initial_gaps.values(),default=0)
    minimum=initial_separation
    violations=0
    progress=[]
    trace=hashlib.sha256()
    ground_trace=hashlib.sha256()
    for tick in range(ticks):
        before={i:pos(entities[i]) for i in ids}
        if name=='generation_reuse' and tick==60:
            entities[ids[0]].generation+=1  # Same physical spawn pose, no teleport or endpoint fabrication.
        lib.sim_tick()
        for i in ids:
            e=entities[i]
            trace.update(bytes(e))
            if e.kind==3: continue  # Aircraft have their own continuous production controller.
            ground_trace.update(struct.pack("<ff",e.x,e.z))
            assert e.hp==100, (name,'combat polluted friendly movement fixture',i,e.hp)
            assert math.dist(before[i],pos(e))<=SPEED[e.kind]+.0015,(name,'speed',tick,i,before[i],pos(e))
            assert 0<=e.x<=8000 and 0<=e.z<=8000
            assert lib.terrain_blocked(e.x,e.z,e.kind)==0,(name,'blocked',tick,i,pos(e))
            assert not any(crosses(before[i],pos(e),box) for box in boxes),(name,'terrain tunnel',tick,i)
            if i not in movable: assert pos(e)==initial[i],(name,'explicit hold moved',tick,i)
        # Relative segment distance catches bodies swapping endpoints between ticks.
        for i,j in pairs:
            relative_start=(before[i][0]-before[j][0],before[i][1]-before[j][1])
            relative_end=(entities[i].x-entities[j].x,entities[i].z-entities[j].z)
            gap=segment_distance((0,0),relative_start,relative_end)-RADII[entities[i].kind]-RADII[entities[j].kind]
            minimum=min(minimum,gap)
            if gap<-.002: violations+=1
            if overlap and not a.legacy:
                assert gap>=min(0,initial_gaps[i,j])-.003,(name,'new or deepened overlap during recovery',tick,i,j,gap,initial_gaps[i,j])
        if tick in (29,119,ticks-1):
            progress.append({'tick':tick+1,'poses':{str(i):pos(entities[i]) for i in ids}})
    final_gap=min((math.dist(pos(entities[i]),pos(entities[j]))-RADII[entities[i].kind]-RADII[entities[j].kind] for i,j in pairs),default=0)
    arrivals={str(r[0]):math.dist(pos(entities[r[0]]),r[-1]) for r in records if r[-1] is not None}
    result={'name':name,'ticks':ticks,'initial':{str(i):v for i,v in initial.items()},
            'final':{str(i):pos(entities[i]) for i in ids},'arrival_error':arrivals,
            'initial_minimum_gap':initial_separation,'minimum_swept_gap':minimum,
            'final_minimum_gap':final_gap,'overlapping_pair_ticks':violations,
            'samples':progress,'physical_trace_sha256':trace.hexdigest(),
            'ground_pose_trace_sha256':ground_trace.hexdigest(),
            'checksum':f'{lib.sim_checksum():016x}',
            'source_generation_change_tick':61 if name=='generation_reuse' else None}
    if not a.legacy:
        if overlap: assert final_gap>=-.002,(name,'initial overlap never recovered',result)
        else: assert violations==0,(name,'body tunnelling',result)
        if name in ('convoy','initial_overlap'):
            required = 40 if name=='convoy' else 10
            assert all(entities[i].x-initial[i][0]>required for i in movable),(name,'cohort failed useful advance',result)
        else:
            assert all(error<.6 for error in arrivals.values()),(name,'movement frozen or failed detour',result)
    return result

# Controlled initial deployments, genuine explicit orders and whole production ticks.
# Common same-side membership removes damage confounds; mirror swaps labels only.
cases=[
 ('held_infantry',[(0,1000,2000,0,0,(1012,2000)),(1,1005,2000,0,1,None)],240,False,()),
 ('generation_reuse',[(0,1000,2000,0,0,(1012,2000)),(1,1005,2000,0,1,None)],240,False,()),
 ('held_armor',[(0,1000,2000,1,0,(1040,2000)),(1,1015,2000,1,1,None)],240,False,()),
 ('held_artillery',[(0,1000,2000,2,0,(1035,2000)),(1,1012,2000,2,1,None)],360,False,()),
 ('approaching_pair',[(0,1000,2000,0,0,(1012,2000)),(1,1012,2000,0,1,(1000,2000))],240,False,()),
 ('convoy',[(i,1000-i*8,2000,1,0,(1060,2000)) for i in range(5)],240,False,()),
 ('wall_edge_pass',[(0,3978,1094,1,0,(4030,1094)),(1,4000,1094,1,1,None)],240,False,()),
 ('wall_route',[(0,3970,1300,1,0,(4030,1300)),(1,4000,1094,1,1,None)],1600,False,()),
 ('initial_overlap',[(i,1000+i*.5,2000,0,0,(1020,2000)) for i in range(5)],400,True,()),
 ('driven_obstacle',[(0,1000,2000,0,0,(1012,2000)),(1,1005,2000,1,1,None)],300,False,()),
 ('air_exclusion',[(0,1000,2000,0,0,(1012,2000)),(1,1005,2000,3,1,None)],240,False,()),
]
# Convoy/cohort shared exact goals cannot all fit in one footprint. They must
# make useful progress and retain separation; arrivals apply only solo/pair goals.
reports=[]
for name,records,ticks,overlap,ignore in cases:
    row=encounter(name,records,ticks,overlap=overlap,ignore=ignore)
    replay=encounter(name,records,ticks,overlap=overlap,ignore=ignore)
    assert row==replay,(name,'same build replay mismatch')
    mirror=encounter(name,records,ticks,True,overlap,ignore)
    ground_ids=[str(r[0]) for r in records if r[3]<3]
    assert row['ground_pose_trace_sha256']==mirror['ground_pose_trace_sha256'] and all(row['final'][i]==mirror['final'][i] for i in ground_ids) and row['minimum_swept_gap']==mirror['minimum_swept_gap'],(name,'label-dependent ground movement',row,mirror)
    reports.append(row)
if a.legacy:
    assert all(row['overlapping_pair_ticks']>0 for row in reports if row['name']!='air_exclusion'), 'old movement stopped exposing traversal fault'
    assert all(row['final_minimum_gap']<-.002 for row in reports if row['name'] in ('convoy','initial_overlap'))


def close_pairs(count):
    bins={}
    pairs=overlaps=0
    minimum=math.inf
    for i in range(count):
        e=entities[i]
        if not e.hp or e.kind>=3 or drivers[i]!=-1: continue
        key=(int(e.x//8),int(e.z//8))
        for dx in (-2,-1,0,1,2):
            for dz in (-2,-1,0,1,2):
                for j in bins.get((key[0]+dx,key[1]+dz),()):
                    other=entities[j]
                    gap=math.dist(pos(e),pos(other))-RADII[e.kind]-RADII[other.kind]
                    if gap<4:
                        pairs+=1
                        minimum=min(minimum,gap)
                        overlaps+=int(gap<-.002)
        bins.setdefault(key,[]).append(i)
    return {'near_pairs':pairs,'overlapping_pairs':overlaps,'minimum_gap':None if math.isinf(minimum) else minimum}

def dense(mode,name):
    assert lib.sim_init(8192,42)==0 and lib.sim_scenario(mode)==0
    if enabled is not None: enabled.value=0 if a.legacy else 1
    initial=close_pairs(8192)
    starts={i:pos(e) for i,e in enumerate(entities[:8192]) if e.hp and e.kind<3}
    for _ in range(a.dense_ticks): lib.sim_tick()
    moved=sum(math.dist(starts[i],pos(entities[i]))>.01 for i in starts if entities[i].hp)
    return {'scenario':name,'seed':42,'initialized_entities':8192,'ticks':a.dense_ticks,
            'initial':initial,'final':close_pairs(8192),'surviving_ground_actors_moved':moved,
            'final_alive':list(alive),'engaged_last_tick':C.c_uint.in_dll(lib,'sim_engaged').value,
            'checksum':f'{lib.sim_checksum():016x}',
            'scope':'Independent spatial-bin current-pose census, not collision-free acceptance; initial deployment overlaps and genuine casualties affect pair counts'}
dense_reports=[]
for mode,name in ((2,'scale-front'),(3,'scale-hotspot')):
    dense_report=dense(mode,name)
    assert dense_report==dense(mode,name),'natural dense replay mismatch'
    dense_reports.append(dense_report)
report={'suite':'crowd-outcomes','passed':True,'legacy':a.legacy,'crowd_module_present':enabled is not None,
        'library_sha256':hashlib.sha256(Path(a.library).read_bytes()).hexdigest(),
        'oracle_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'footprint_radii_m':RADII,'vehicle_geometry':vehicle_geometry,'controlled_encounters':reports,'dense':dense_reports,
        'deterministic_replay':True,'physical_label_swap':True,
        'scope':'Production sim_tick navigation/terrain at real role speeds; controlled friendly deployments exclude weapons, player driving and full operation acceptance'}
if a.report: Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
