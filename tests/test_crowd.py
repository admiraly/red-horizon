#!/usr/bin/env python3
"""Actual NASM crowd kernel + production swept terrain, development-only harness."""
import ctypes as C
import json, math, os, pathlib, shutil, struct, subprocess, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
tmp=tempfile.TemporaryDirectory(prefix='rh-crowd-')
nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
objs=[]
for path in ('src/nav/crowd.asm','src/nav/terrain.asm','src/nav/terrain_body.asm','tests/crowd_probe.asm'):
    obj=pathlib.Path(tmp.name)/(pathlib.Path(path).stem+'.o')
    subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/path),'-o',str(obj)],check=True)
    objs.append(str(obj))
so=pathlib.Path(tmp.name)/'crowd.so'
subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(so)],check=True)
lib=C.CDLL(str(so))
class E(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(k,C.c_uint) for k in ('hp','side','kind','front','target','gen')]
entities=(E*32768).in_dll(lib,'sim_entities'); count=C.c_uint.in_dll(lib,'sim_count')
tick_count=C.c_uint.in_dll(lib,'sim_tick_count')
enabled=C.c_uint.in_dll(lib,'crowd_enabled'); metrics=(C.c_uint64*8).in_dll(lib,'crowd_metrics')
drivers=(C.c_int*32768).in_dll(lib,'vehicle_entity_driver')
lib.test_move.argtypes=[C.c_uint,C.POINTER(C.c_float)];lib.test_move.restype=C.c_int
lib.test_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_hash.restype=C.c_uint64
R=(.55,3.55,4.49); S=(.12,.5,.2)
verify_readonly=True
def reset(rows):
    C.memset(C.addressof(entities),0,C.sizeof(entities));C.memset(C.addressof(drivers),255,C.sizeof(drivers))
    C.memset(C.addressof((C.c_byte*256).in_dll(lib,"sim_players")),0,256)
    C.memset(C.addressof((C.c_int*4).in_dll(lib,"sim_player_vehicle")),255,16)
    C.memset(C.addressof((C.c_byte*128).in_dll(lib,"sim_vehicles")),0,128)
    count.value=len(rows);tick_count.value=0
    for i,row in enumerate(rows):
        x,z,*kind=row;k=kind[0] if kind else 0
        entities[i]=E(x,z,100,i%2,k,0,0,i+1)
    lib.terrain_body_init();lib.crowd_init();lib.crowd_begin()
def move(i,goal,step=None):
    e=entities[i];a=(C.c_float*5)(e.x,e.z,*goal,S[e.kind] if step is None else step)
    before=bytes(entities) if verify_readonly else None
    assert lib.test_move(i,a)==1,'SysV callee-saved ABI'
    if verify_readonly:assert bytes(entities)==before,'kernel wrote authoritative entities'
    return a[0],a[1]
def tick(goals):
    tick_count.value+=1
    lib.crowd_begin()
    old={i:(entities[i].x,entities[i].z) for i in goals}
    points={i:move(i,g) for i,g in goals.items()}
    for i,p in points.items():
        assert math.dist((entities[i].x,entities[i].z),p)<=S[entities[i].kind]+.00015
        entities[i].x,entities[i].z=p
    if len(goals)<=16:
        for i,p in points.items():
            for j,q in points.items():
                if j>=i:continue
                rx,rz=old[i][0]-old[j][0],old[i][1]-old[j][1]
                dx,dz=(p[0]-old[i][0])-(q[0]-old[j][0]),(p[1]-old[i][1])-(q[1]-old[j][1])
                l=dx*dx+dz*dz;t=max(0,min(1,-(rx*dx+rz*dz)/l)) if l else 0
                gap=math.hypot(rx+t*dx,rz+t*dz)
                required=min(math.hypot(rx,rz),R[entities[i].kind]+R[entities[j].kind])
                assert gap>=required-.003,('simultaneous sweep',i,j,gap,required)
    return points
# Clear movement, step clamp, ABI and read-only source/snapshot behavior.
reset([(1000,1000)])
p=move(0,(1010,1000),100);assert math.dist(p,(1000,1000))<=.1201 and p[0]>1000.11
assert move(0,(1000,1000))==(1000,1000)
for step in (0,-1,float('nan'),float('inf')):assert move(0,(1010,1000),step)==(1000,1000)
for goal in ((float('nan'),1000),(1000,float('inf')),(-1,1000),(8001,1000)):
    assert move(0,goal)==(1000,1000)
a=(C.c_float*5)(float('nan'),float('inf'),1010,1000,.12)
assert lib.test_move(0,a)==1 and tuple(a[:2])==(1000,1000)
a=(C.c_float*5)(1000,1000,1010,1000,.12)
assert lib.test_move(32768,a)==1 and a[0]==1000
entities[0].gen+=1;assert move(0,(1010,1000))==(1000,1000)
lib.crowd_begin();assert move(0,(1010,1000))[0]>1000
entities[0].kind=1;assert move(0,(1010,1000))==(1000,1000)
# Future state includes policy, excludes all derived diagnostics and snapshots.
seed=14695981039346656037;prime=1099511628211
h=seed
for b in struct.pack('<I',1):h=((h^b)*prime)&((1<<64)-1)
assert lib.test_hash(seed,prime)==h
metrics[0]+=123;lib.crowd_begin();assert lib.test_hash(seed,prime)==h
enabled.value=0;assert lib.test_hash(seed,prime)!=h
# Held infantry blocks direct route, moving infantry goes around and reaches goal.
reset([(1000,1000),(1004,1000)])
minimum=100
for t in range(130):
    tick({0:(1010,1000)})
    minimum=min(minimum,math.dist((entities[0].x,entities[0].z),(entities[1].x,entities[1].z)))
assert minimum>=1.0998 and entities[0].x>1009.5,(minimum,entities[0].x,entities[0].z)
held_end=(entities[0].x,entities[0].z)
# Real role-sized held driven tank, infantry must pass beyond its 4.10 m footprint.
reset([(1000,1000),(1005,1000,1)]);drivers[1]=0
minimum=100
for t in range(200):
    tick({0:(1012,1000)})
    minimum=min(minimum,math.dist((entities[0].x,entities[0].z),(entities[1].x,entities[1].z)))
assert minimum>=4.0998 and entities[0].x>1011.5,(minimum,entities[0].x,entities[0].z)
# A genuine finite-width lane between held vehicle footprints remains usable.
reset([(1000,1000),(1006,995.25,1),(1006,1004.75,1)])
for t in range(130):tick({0:(1012,1000)})
assert entities[0].x>1011.5 and abs(entities[0].z-1000)<.001
# Legacy terrain-only control really enters a held ally body on the same route.
reset([(1000,1000),(1004,1000)]);enabled.value=0
for t in range(34):tick({0:(1010,1000)})
assert math.dist((entities[0].x,entities[0].z),(1004,1000))<.12
# Opposing actual movement computed against immutable same-tick snapshots.
def head_on(mirror=False,reverse=False):
    reset([(1000,1000),(1010,1000)])
    if mirror:
        for e in entities[:2]:e.side^=1
    gap=100
    for t in range(130):
        goals={1:(998,1000),0:(1012,1000)} if reverse else {0:(1012,1000),1:(998,1000)}
        tick(goals)
        gap=min(gap,math.dist((entities[0].x,entities[0].z),(entities[1].x,entities[1].z)))
    return bytes(entities[:2]) if False else ((entities[0].x,entities[0].z),(entities[1].x,entities[1].z),gap)
a=head_on();assert a[2]>=1.0998 and a[0][0]>1011.5 and a[1][0]<998.5,a
assert head_on(True)==a and head_on(False,True)==a
# Initial coincident allied flank elements recover onto their real opposing
# approach corridors, rather than swapping sides and blocking each other's goal.
reset([(3500,1300),(3500,1300)])
for _ in range(89):tick({0:(5000,700),1:(5000,1900)})
flank_positions=[(entities[0].x,entities[0].z),(entities[1].x,entities[1].z)]
assert flank_positions[0][0]>3500 and flank_positions[0][1]<1300
assert flank_positions[1][0]>3500 and flank_positions[1][1]>1300
# Reverse the real flank intentions: physical priority must not swap corridors.
reset([(3500,1300),(3500,1300)])
for _ in range(89):tick({0:(5000,1900),1:(5000,700)})
reverse_flank_positions=[(entities[0].x,entities[0].z),(entities[1].x,entities[1].z)]
assert reverse_flank_positions[0][0]>3500 and reverse_flank_positions[0][1]>1300
assert reverse_flank_positions[1][0]>3500 and reverse_flank_positions[1][1]<1300
# Exact coincident explicit held allies at either physical ID do not starve movers.
for mover in (0,1):
    reset([(1000,1000),(1000,1000)])
    for _ in range(50):tick({mover:(1010,1000)})
    assert entities[mover].x>1004
    assert (entities[1-mover].x,entities[1-mover].z)==(1000,1000)
# Actual vehicle mesh-sized circles, including artillery, must pass head-on.
vehicle_pairs=[]
for kind,ticks in ((1,120),(2,230)):
    reset([(1000,1000,kind),(1020,1000,kind)])
    gap=100
    for _ in range(ticks):
        tick({0:(1025,1000),1:(995,1000)})
        gap=min(gap,math.dist((entities[0].x,entities[0].z),(entities[1].x,entities[1].z)))
    assert gap>=2*R[kind]-.003 and entities[0].x>1024 and entities[1].x<996,(kind,gap,[(e.x,e.z) for e in entities[:2]])
    vehicle_pairs.append({'kind':kind,'minimum_gap':gap,'source_x':entities[0].x,'opponent_x':entities[1].x})
# Coincident pair breaks a symmetry without teleport or remaining stacked forever.
reset([(1000,1000),(1000,1000)])
for t in range(40):tick({0:(1010,1000),1:(1010,1000)})
coincident_gap=math.dist((entities[0].x,entities[0].z),(entities[1].x,entities[1].z))
assert coincident_gap>=1.0998,coincident_gap
# Larger exact coincident moving cohorts must actually split, with every
# simultaneous relative sweep preserving any separation already recovered.
coincident_cohorts=[]
verify_readonly=False
for n in (3,5,8):
    reset([(1000,1000) for _ in range(n)])
    for _ in range(160):tick({i:(1030,1000) for i in range(n)})
    gaps=[math.dist((entities[i].x,entities[i].z),(entities[j].x,entities[j].z)) for i in range(n) for j in range(i)]
    assert min(gaps)>=1.0998,(n,min(gaps),[(e.x,e.z) for e in entities[:n]])
    assert all(math.dist((e.x,e.z),(1000,1000))>1 for e in entities[:n])
    coincident_cohorts.append({'actors':n,'ticks':160,'minimum_gap':min(gaps),'all_moved':True})
verify_readonly=True
# Partial overlap must genuinely increase simultaneous radial separation.
reset([(1000,1000),(1000,1000.4)])
for t in range(30):tick({0:(1010,1000),1:(1010,1000)})
assert math.dist((entities[0].x,entities[0].z),(entities[1].x,entities[1].z))>=1.0998
# Five partially overlapping actors must separate physically, not only against snapshots.
reset([(1000+i*.5,1000) for i in range(5)])
for t in range(240):tick({i:(1020,1000) for i in range(5)})
chain_gaps=[math.dist((entities[i].x,entities[i].z),(entities[j].x,entities[j].z)) for i in range(5) for j in range(i)]
assert min(chain_gaps)>=1.0998,(chain_gaps,[(e.x,e.z) for e in entities[:5]])
# Convoy advances without overlapping instead of freezing its entire column.
reset([(1000-2*i,1000) for i in range(8)])
for t in range(100):tick({i:(1030-2*i,1000) for i in range(8)})
assert all(entities[i].x>1011-2*i for i in range(8))
assert all(math.dist((entities[i].x,entities[i].z),(entities[j].x,entities[j].z))>=1.0998 for i in range(8) for j in range(i))
# Static terrain wall: normal role-bounded moves cannot pass through the wall.
reset([(3987.9,1200)])
for t in range(10):tick({0:(4020,1200)})
assert entities[0].x<3988 or entities[0].z<1100 or entities[0].z>1500
# Wall-adjacent held tank must choose the open detour side rather than oscillate.
wall_routes=[]
for start,goal,blocker,ticks in (((3978,1094),(4030,1094),(4000,1094),240),
                                  ((3970,1300),(4030,1300),(4000,1094),1600)):
    reset([(*start,1),(*blocker,1)])
    for _ in range(ticks):tick({0:goal})
    error=math.dist((entities[0].x,entities[0].z),goal)
    assert error<.6,(start,goal,error,(entities[0].x,entities[0].z))
    wall_routes.append({'start':start,'goal':goal,'ticks':ticks,'arrival_error':error})
# Neighbor generation retirement is observed safely, no stale body blocks source.
reset([(1000,1000),(1001.3,1000)])
entities[1].gen+=1
assert move(0,(1010,1000))[0]>1000.11
# Counter accounting depends on inspected records, never the grid coordinate.
# Same relative query translated over three unrelated grid rows has exactly6
# inspected records (one nearby body and one distant record in an adjacent cell).
for z in (80,1000,7200):
    reset([(1000,z),(1006,z),(1008,z+8)])
    before=list(metrics);move(0,(1010,z))
    assert metrics[2]-before[2]==6 and metrics[7]==6,(z,list(metrics))
# Saturated local query: bounded inspection and explicit conservative yield.
reset([(1000,1000) for _ in range(32768)])
p=move(0,(1010,1000));assert p==(1000,1000)
assert metrics[6]==1 and metrics[7]==512 and metrics[2]==512,list(metrics)
count.value=32769;lib.crowd_begin();assert move(0,(1010,1000))==(1000,1000)
# Public controller/placement kernel acceptance, using real player/claim layouts.
class P(C.Structure):
    _fields_=[('x',C.c_float),('y',C.c_float),('z',C.c_float),('yaw',C.c_float),('pitch',C.c_float)]+[(k,C.c_uint) for k in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','gen')]
players=(P*4).in_dll(lib,'sim_players')
player_vehicle=(C.c_int*4).in_dll(lib,'sim_player_vehicle')
vehicle_records=(C.c_uint*32).in_dll(lib,'sim_vehicles')
lib.test_step.argtypes=lib.test_move.argtypes;lib.test_step.restype=C.c_int
lib.test_occupied.argtypes=[C.c_int,C.c_uint,C.POINTER(C.c_float)];lib.test_occupied.restype=C.c_int
def human(slot,x,z):
    players[slot]=P(x=x,z=z,hp=100,connected=1,gen=slot+1)
def claim(slot,entity):
    player_vehicle[slot]=entity;drivers[entity]=slot
    for offset,value in enumerate((entity,entities[entity].gen,slot,1,0,0,slot+1,0)):
        vehicle_records[slot*8+offset]=value

def controlled(body,goal,cap=100):
    if body>=32768:
        p=players[body-32768];start=(p.x,p.z);role=0;maximum=.3
    else:
        p=entities[body];start=(p.x,p.z);role=p.kind;maximum=.6
    data=(C.c_float*5)(*start,*goal,cap)
    authoritative=(bytes(entities),bytes(players),bytes(vehicle_records),bytes(drivers))
    assert lib.test_step(body,data)==1,'controller SysV callee-saved ABI'
    assert authoritative==(bytes(entities),bytes(players),bytes(vehicle_records),bytes(drivers)),'controller wrote authoritative state'
    endpoint=tuple(data[:2]);delta=(endpoint[0]-start[0],endpoint[1]-start[1])
    intent=(goal[0]-start[0],goal[1]-start[1]);length=math.hypot(*intent)
    assert math.hypot(*delta)<=min(cap,maximum)+.0007
    for actual,wanted in zip(delta,intent):
        limit=min(length,cap,maximum)*abs(wanted)/length if length else 0
        assert abs(actual)<=limit+.0007 and actual*wanted>=-.0007,('manual component amplification/reversal',body,start,goal,endpoint)
        if not wanted:assert abs(actual)<.0007,'uncommanded axis'
    p.x,p.z=endpoint
    return endpoint

def occupied(point,role=0,ignore=-1):
    data=(C.c_float*2)(*point)
    authoritative=(bytes(entities),bytes(players),bytes(vehicle_records),bytes(drivers))
    result=lib.test_occupied(ignore,role,data)
    assert authoritative==(bytes(entities),bytes(players),bytes(vehicle_records),bytes(drivers)),'occupancy wrote authoritative state'
    assert result in (0,1)
    return result
# Invalid controller steps are rejected before minss can hide NaN/Inf values.
for tank in (False,True):
    reset([(1000,1000,1)] if tank else []);human(0,1000,1000)
    if tank:claim(0,0)
    lib.crowd_begin();body=0 if tank else 32768
    for badstep in (0,-1,float('nan'),float('inf')):
        data=(C.c_float*5)(1000,1000,1010,1000,badstep)
        assert lib.test_step(body,data)==1 and tuple(data[:2])==(1000,1000)
    for badgoal in ((float('nan'),1000),(1000,float('inf')),(-8001,1000),(16001,1000)):
        data=(C.c_float*5)(1000,1000,*badgoal,.3)
        assert lib.test_step(body,data)==1 and tuple(data[:2])==(1000,1000)
# A corrupted global army count also rejects virtual human movement before
# any snapshot/grid query; placement rejects conservatively, then valid recovery.
reset([]);human(0,1000,1000);lib.crowd_begin();count.value=32769
before=list(metrics)
data=(C.c_float*5)(1000,1000,1010,1000,.3)
assert lib.test_step(32768,data)==1 and tuple(data[:2])==(1000,1000)
assert list(metrics)==before,'malformed-count query inspected grid'
assert occupied((1000,1000),ignore=32768)==1
count.value=0
assert controlled(32768,(1010,1000))[0]>1000.29
controller_cases=[]
# Every army role blocks foot humans and legitimate driven tanks, with no
# autonomous lateral movement under straight input or swept overlap.
for controlled_role in (0,1):
    for blocker_role in (0,1,2):
        reset([(1007,1000,blocker_role)] if controlled_role==0 else [(1000,1000,1),(1012,1000,blocker_role)])
        human(0,1000,1000)
        if controlled_role:claim(0,0)
        body=32768 if controlled_role==0 else 0
        blocker=0 if controlled_role==0 else 1
        lib.crowd_begin();minimum=math.inf
        for _ in range(80):
            lib.crowd_begin();endpoint=controlled(body,(1030,1000))
            gap=math.dist(endpoint,(entities[blocker].x,entities[blocker].z));minimum=min(minimum,gap)
            assert gap>=R[controlled_role]+R[blocker_role]-.001,(controlled_role,blocker_role,endpoint,gap)
        assert endpoint[0]>1000.05,'clear approach must move'
        controller_cases.append({'source_role':controlled_role,'blocker_role':blocker_role,'minimum_gap':minimum,'endpoint':endpoint})
# Human-human clear starts, live late join/exit, disconnected/dead records,
# properly boarded duplicates, and stale claim links.
reset([]);human(0,1000,1000);lib.crowd_begin();human(1,1003,1000)
for _ in range(40):
    endpoint=controlled(32768,(1010,1000))
    assert math.dist(endpoint,(players[1].x,players[1].z))>=1.099
assert endpoint[0]>1000
players[1].hp=0
assert controlled(32768,(1010,1000))[0]>endpoint[0]+.29
players[1].hp=100;players[1].connected=0
assert occupied((1003,1000),ignore=32768)==0
players[1].connected=1;players[1].gen+=1
assert occupied((1003,1000),ignore=32768)==1
reset([(1000,1000,1)]);human(0,1000,1000);claim(0,0);lib.crowd_begin()
assert occupied((1000,1000),ignore=0)==0,'boarded duplicate excluded'
entities[0].side=1
assert occupied((1000,1000),ignore=0)==1,'enemy claim cannot hide foot human'
assert controlled(0,(1010,1000))==(1000,1000),'enemy faction claim cannot drive'
entities[0].side=0
assert occupied((1000,1000),ignore=0)==0,'restored valid allied claim'
vehicle_records[1]+=1
assert occupied((1000,1000),ignore=0)==1,'stale claim cannot hide human'
assert controlled(0,(1010,1000))==(1000,1000),'invalid driver claim'
# Exiting after snapshot makes the now-foot human visible through live fallback.
vehicle_records[1]=entities[0].gen;lib.crowd_begin()
player_vehicle[0]=-1;drivers[0]=-1;vehicle_records[3]=0
players[0].x=1010
assert occupied((1010,1000))==1
# Occupancy uses actual body radii, ignores own virtual human only, retains hull.
reset([(1000,1000,1)]);human(0,1010,1000);lib.crowd_begin()
assert occupied((1004,1000))==1 and occupied((1004.2,1000))==0
assert occupied((1010,1000),ignore=32768)==0
assert occupied((1000,1000),ignore=32768)==1
assert occupied((float('nan'),1000))==1 and occupied((1000,1000),3)==1
# Manual diagonal contact slide keeps original components (never full speed on
# free axis), and terrain/map-edge handling preserves the same constraint.
reset([(1002,1000)]);human(0,1000.7,1000);lib.crowd_begin()
slide_start=(players[0].x,players[0].z)
endpoint=controlled(32768,(1010,1005))
assert endpoint[1]>slide_start[1] and abs(endpoint[0]-slide_start[0])<.001
for source_role,start,goal in ((0,(.8,2000),(-1,2001)),(1,(3.8,2000),(-1,2001)),(0,(3987.4,1200),(4000,1201))):
    reset([] if source_role==0 else [(*start,1)]);human(0,*start)
    if source_role:claim(0,0)
    lib.crowd_begin();controlled(32768 if not source_role else 0,goal)
# Existing partial overlap: inward and pure tangent requests hold, outward
# genuinely recovers without teleporting. Human-human exact coincide may yield.
reset([]);human(0,1000,1000);human(1,1000.5,1000);lib.crowd_begin()
assert controlled(32768,(1010,1000))==(1000,1000)
assert controlled(32768,(1000,1010))==(1000,1000)
assert controlled(32768,(990,1000))[0]<999.71
# AI actually navigates around a held human, preserving its normal cap.
reset([(1000,1000)]);human(0,1004,1000);lib.crowd_begin()
for _ in range(140):
    tick({0:(1010,1000)})
    assert math.dist((entities[0].x,entities[0].z),(players[0].x,players[0].z))>=1.099
assert entities[0].x>1009.5
# Live sequential and independently proposed controller sweeps cannot cross.
# This exercises human-human and human-tank movement, not just held blockers.
controller_sweeps=0
for mixed in (False,True):
    reset([(1008,1000,1)] if mixed else [])
    human(0,1000,1000);human(1,1008,1000)
    if mixed:claim(1,0)
    ids=(32768,0 if mixed else 32769);radius_sum=.55+(3.55 if mixed else .55)
    for _ in range(80):
        lib.crowd_begin()
        def point(body):
            p=players[body-32768] if body>=32768 else entities[body]
            return p.x,p.z
        old=[point(body) for body in ids]
        endpoints=[controlled(ids[0],(1015,1000)),controlled(ids[1],(995,1000))]
        rx,rz=old[0][0]-old[1][0],old[0][1]-old[1][1]
        dx=(endpoints[0][0]-old[0][0])-(endpoints[1][0]-old[1][0])
        dz=(endpoints[0][1]-old[0][1])-(endpoints[1][1]-old[1][1])
        length=dx*dx+dz*dz;t=max(0,min(1,-(rx*dx+rz*dz)/length)) if length else 0
        assert math.hypot(rx+t*dx,rz+t*dz)>=radius_sum-.001
        controller_sweeps+=1
# Saturated controller/placement queries include four human records in512 cap.
reset([(1000,1000) for _ in range(32768)]);human(0,1000,1000);lib.crowd_begin()
assert controlled(32768,(1010,1000))==(1000,1000)
assert metrics[7]==512 and metrics[6]==1
assert occupied((1000,1000))==1 and metrics[7]==512 and metrics[6]==2
# Genuine causal disabled control allows body entry, but still uses terrain and
# the exact manual components/caps. Policy remains the sole hashed future state.
reset([(1002,1000)]);human(0,1000,1000);enabled.value=0
for _ in range(7):controlled(32768,(1010,1000))
assert players[0].x>1002
assert occupied((1002,1000))==0

# Assembly-loop isolated-kernel budgets exclude Python per-query/readonly overhead.
bench=[]
for n in (128,8192):
    reset([(1000+(i%128)*2,1000+(i//128)*2) for i in range(n)])
    times=[]
    for _ in range(30):
        start=time.perf_counter_ns();lib.crowd_begin();lib.test_tick();times.append((time.perf_counter_ns()-start)/1e6)
    assert metrics[6]==0 and metrics[7]<=512,list(metrics)
    bench.append({'actors':n,'ticks':30,'kernel_ms_mean':sum(times)/len(times),'kernel_ms_p95':sorted(times)[28],
                  'inspected':metrics[2],'maximum_inspected_query':metrics[7],'truncated':metrics[6]})
print(json.dumps({'suite':'crowd','status':'passed','passed':True,'held_pass_endpoint':held_end,'head_on':a,'coincident_recovery_gap':coincident_gap,'coincident_cohorts':coincident_cohorts,
                  'coincident_flank_positions':flank_positions,'reverse_flank_positions':reverse_flank_positions,'wall_routes':wall_routes,'vehicle_pairs':vehicle_pairs,'overlap_chain_minimum_gap':min(chain_gaps),'kernel_benchmarks':bench,'controller_cases':controller_cases,'controller_relative_sweeps':controller_sweeps,
                  'limitations':['512 inspected neighbors per query; denser 3x3 infantry or 5x5 vehicle cell chains conservatively yield',
                  'controller kernel verified independently; production player/vehicle hooks verified by integrator',
                  'initial overlap recovery is gradual, crowded unsatisfiable layouts may yield',
                  'isolated kernel benchmark is not complete army performance']}))
