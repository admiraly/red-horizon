#!/usr/bin/env python3
"""Actual NASM crowd kernel + production swept terrain, development-only harness."""
import ctypes as C
import json, math, os, pathlib, shutil, struct, subprocess, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
tmp=tempfile.TemporaryDirectory(prefix='rh-crowd-')
nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
objs=[]
for path in ('src/nav/crowd.asm','src/nav/terrain.asm','tests/crowd_probe.asm'):
    obj=pathlib.Path(tmp.name)/(pathlib.Path(path).stem+'.o')
    subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/path),'-o',str(obj)],check=True)
    objs.append(str(obj))
so=pathlib.Path(tmp.name)/'crowd.so'
subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(so)],check=True)
lib=C.CDLL(str(so))
class E(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(k,C.c_uint) for k in ('hp','side','kind','front','target','gen')]
entities=(E*32768).in_dll(lib,'sim_entities'); count=C.c_uint.in_dll(lib,'sim_count')
enabled=C.c_uint.in_dll(lib,'crowd_enabled'); metrics=(C.c_uint64*8).in_dll(lib,'crowd_metrics')
drivers=(C.c_int*32768).in_dll(lib,'vehicle_entity_driver')
lib.test_move.argtypes=[C.c_uint,C.POINTER(C.c_float)];lib.test_move.restype=C.c_int
lib.test_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_hash.restype=C.c_uint64
R=(.55,2.5,2.0); S=(.12,.5,.2)
verify_readonly=True
def reset(rows):
    C.memset(C.addressof(entities),0,C.sizeof(entities));C.memset(C.addressof(drivers),255,C.sizeof(drivers))
    count.value=len(rows)
    for i,row in enumerate(rows):
        x,z,*kind=row;k=kind[0] if kind else 0
        entities[i]=E(x,z,100,i%2,k,0,0,i+1)
    lib.crowd_init();lib.crowd_begin()
def move(i,goal,step=None):
    e=entities[i];a=(C.c_float*5)(e.x,e.z,*goal,S[e.kind] if step is None else step)
    before=bytes(entities) if verify_readonly else None
    assert lib.test_move(i,a)==1,'SysV callee-saved ABI'
    if verify_readonly:assert bytes(entities)==before,'kernel wrote authoritative entities'
    return a[0],a[1]
def tick(goals):
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
for step in (0,-1,float('nan')):assert move(0,(1010,1000),step)==(1000,1000)
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
# Real role-sized held driven tank, infantry must pass beyond its 3.05 m footprint.
reset([(1000,1000),(1005,1000,1)]);drivers[1]=0
minimum=100
for t in range(200):
    tick({0:(1012,1000)})
    minimum=min(minimum,math.dist((entities[0].x,entities[0].z),(entities[1].x,entities[1].z)))
assert minimum>=3.0498 and entities[0].x>1011.5,(minimum,entities[0].x,entities[0].z)
# A genuine finite-width lane between held vehicle footprints remains usable.
reset([(1000,1000),(1006,996.3,1),(1006,1003.7,1)])
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
# Coincident pair breaks a symmetry without teleport or remaining stacked forever.
reset([(1000,1000),(1000,1000)])
for t in range(40):tick({0:(1010,1000),1:(1010,1000)})
coincident_gap=math.dist((entities[0].x,entities[0].z),(entities[1].x,entities[1].z))
assert coincident_gap>=1.0998,coincident_gap
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
# Neighbor generation retirement is observed safely, no stale body blocks source.
reset([(1000,1000),(1001.3,1000)])
entities[1].gen+=1
assert move(0,(1010,1000))[0]>1000.11
# Saturated local query: bounded inspection and explicit conservative yield.
reset([(1000,1000) for _ in range(32768)])
p=move(0,(1010,1000));assert p==(1000,1000)
assert metrics[6]==1 and metrics[7]==512 and metrics[2]==512,list(metrics)
count.value=32769;lib.crowd_begin();assert move(0,(1010,1000))==(1000,1000)
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
print(json.dumps({'suite':'crowd','status':'passed','passed':True,'held_pass_endpoint':held_end,'head_on':a,'coincident_recovery_gap':coincident_gap,
                  'overlap_chain_minimum_gap':min(chain_gaps),'kernel_benchmarks':bench,
                  'limitations':['512 inspected neighbors per query; denser 3x3-cell chains conservatively yield',
                  'ground AI only; driven bodies included but source driver control not changed',
                  'initial overlap recovery is gradual, crowded unsatisfiable layouts may yield',
                  'isolated kernel benchmark is not complete army performance']}))
