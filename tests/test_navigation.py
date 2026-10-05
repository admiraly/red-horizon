#!/usr/bin/env python3
"""Proof of actual assembly corridors and integrated fixed-tick movement.
Pass libsim.so from a build containing src/nav/squads.asm. This test assembles only
an ABI adapter, never substitutes a Python route solver for the runtime.
"""
import ctypes as C
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import time
library=Path(sys.argv[1]).resolve()
lib=C.CDLL(str(library),mode=C.RTLD_GLOBAL)
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    (tmp/'probe.asm').write_text('''default rel
extern nav_entity_goal
section .text
global test_nav_goal
test_nav_goal:
 sub rsp,8
 call nav_entity_goal wrt ..plt
 add rsp,8
 movd eax,xmm0
 movd edx,xmm1
 shl rdx,32
 or rax,rdx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
''')
    nasm=os.environ.get('RED_HORIZON_NASM','nasm')
    subprocess.run([nasm,'-f','elf64',str(tmp/'probe.asm'),'-o',str(tmp/'probe.o')],check=True)
    subprocess.run(['gcc','-shared','-o',str(tmp/'probe.so'),str(tmp/'probe.o'),str(library)],check=True)
    probe=C.CDLL(str(tmp/'probe.so'))
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
entities=(Entity*32768).in_dll(lib,'sim_entities')
metrics=(C.c_uint*8).in_dll(lib,'nav_metrics')
tick=C.c_uint.in_dll(lib,'sim_tick_count')
fronts=(C.c_uint*(6*16)).in_dll(lib,'ai_fronts')
probe.test_nav_goal.argtypes=[C.c_float,C.c_float,C.c_uint]
probe.test_nav_goal.restype=C.c_uint64
lib.terrain_path_clear.argtypes=[C.c_float]*4
lib.test_terrain_move.argtypes=[C.c_float]*5+[C.c_uint]
lib.test_terrain_move.restype=C.c_uint64
lib.terrain_height.argtypes=[C.c_float]*2
lib.terrain_height.restype=C.c_float
lib.terrain_los.argtypes=[C.c_float]*6
lib.terrain_blocked.argtypes=[C.c_float,C.c_float,C.c_uint]
def unpack(bits):return struct.unpack('<ff',struct.pack('<Q',bits))
def goal(actor,end):return unpack(probe.test_nav_goal(*end,actor))
def init(n=2):
    assert lib.sim_init(n,1)==0
    lib.nav_init()
    for i in range(n):entities[i].target=-1
# Exact segment check, including long thin-wall intersection and corner grazing.
assert lib.terrain_path_clear(3950,1300,4050,1300)==0
assert lib.terrain_path_clear(3950,1096,4050,1096)==1
assert lib.terrain_path_clear(3988,1000,3988,1500)==0
assert lib.terrain_path_clear(float('nan'),0,0,0)==0
# Independent oracle copies physical bounds, not module decisions.
boxes=(C.c_float*40).in_dll(lib,'terrain_obstacles')
def crosses(a,b,box):
    low,high=0.,1.
    for p,q,mn,mx in ((a[0],b[0],box[0],box[2]),(a[1],b[1],box[1],box[3])):
        if p==q:
            if not mn<=p<=mx:return False
        else:
            u,v=sorted(((mn-p)/(q-p),(mx-p)/(q-p)))
            low,high=max(low,u),min(high,v)
            if low>high:return False
    return True
rng=random.Random(1041)
for _ in range(2000):
    a,b=[(rng.uniform(2000,6000),rng.uniform(900,6800)) for _ in range(2)]
    expected=not any(crosses(a,b,boxes[i*8:i*8+4]) for i in range(5))
    assert bool(lib.terrain_path_clear(*a,*b))==expected
# Native actual-motion driver uses nav_tick + nav_entity_goal + terrain_move,
# not teleportation to path nodes. Check each segment with independent oracle.
routes=[((3950.,1300.),(4050.,1300.)),
        ((5243.89013671875,1564.114990234375),(3125.11279296875,5204.44287109375)),
        ((2700.,3500.),(5300.,1700.)),
        ((4050.,3900.),(3950.,6500.))]
route_ticks=[]
for route_index,(start,end) in enumerate(routes):
    init(); e=entities[0];e.x,e.z=start;e.kind=1
    reached=False
    for t in range(16000):
        tick.value=t
        lib.nav_tick()
        interim=goal(0,end)
        before=e.x,e.z
        after=unpack(lib.test_terrain_move(*before,*interim,.5,e.kind))
        assert math.dist(before,after)<=.501
        assert not any(crosses(before,after,boxes[i*8:i*8+4]) for i in range(5))
        e.x,e.z=after
        if math.dist(after,end)<.002:
            reached=True;route_ticks.append(t+1);break
    assert reached,(start,end,(e.x,e.z),list(metrics))
    assert metrics[7]<=8 and metrics[1]==1
    if route_index<2:assert metrics[3]>0
# Exact final goals remain authoritative even below cache invalidation threshold.
init();e=entities[0];e.x,e.z=3950,1300;e.kind=1
goal(0,(4050,1300));lib.nav_tick()
e.x,e.z=4050,1300
assert goal(0,(4060,1300))==(4060,1300)
e.x,e.z=3950,1300
goal(0,(4050,1600));assert metrics[0]==1
lib.nav_tick();assert metrics[1]==2
# Side/front are distinct despite interleaved IDs in one 16-ID block.
init(16)
for i in range(6):
    e=entities[i];e.side=i//3;e.front=i%3;e.kind=1;e.x,e.z=3950,1300
    goal(i,(4050,1300))
assert metrics[0]==6
lib.nav_tick();assert metrics[1]==6 and metrics[6]==6
# Direct scouts and flank support in the same side/front/group must not churn
# one shared goal. Both actual corridors stay cached while actors alternate.
init(16)
for i in (0,3):
    e=entities[i];e.side=0;e.front=0;e.kind=0;e.x,e.z=3950,1300
for _ in range(100):
    goal(0,(4050,1250));goal(3,(4050,1350));lib.nav_tick()
assert metrics[1]==2 and metrics[0]==0,list(metrics)
scout_support_builds=metrics[1]
# Saturation: unique squads enter FIFO, retries do not corrupt pending requests.
init(16384)
for i in range(0,16384,16):
    e=entities[i];e.side=0;e.front=0;e.kind=1;e.x,e.z=3950,1300
    goal(i,(4050,1300))
assert metrics[0]==512 and metrics[2]==512
for i in range(64):
    lib.nav_tick();assert metrics[6]==8 and metrics[7]==8
assert metrics[0]==0 and metrics[1]==512
# Last admitted squad is served within64ticks; its path is physically usable.
assert goal(511*16,(4050,1300))!=(4050,1300)
for i in range(512*16,16384,16):goal(i,(4050,1300))
assert metrics[0]==512
for _ in range(64):lib.nav_tick()
assert metrics[1]==1024
# Cover is acquired from actual visible enemy, then retains only fixed shelter.
init();e=entities[0];enemy=entities[1]
e.x,e.z,e.kind=5165,1537,0;enemy.x,enemy.z=5250,1530
e.target=1;tick.value=0
assert lib.terrain_los(e.x,lib.terrain_height(e.x,e.z)+2,e.z,enemy.x,lib.terrain_height(enemy.x,enemy.z)+2,enemy.z)==1
shelter=goal(0,(5000,1300))
assert shelter==(5166.,1570.),shelter
assert lib.terrain_path_clear(e.x,e.z,*shelter)==1
assert lib.terrain_los(shelter[0],lib.terrain_height(*shelter)+2,shelter[1],enemy.x,lib.terrain_height(enemy.x,enemy.z)+2,enemy.z)==0
assert metrics[5]==1
# Lose sight while moving: commitment retains position, never hidden target data.
e.target=-1
for t in range(1,360):
    tick.value=t
    interim=goal(0,(5000,1300))
    assert interim==shelter
    before=e.x,e.z
    after=unpack(lib.test_terrain_move(*before,*interim,.12,e.kind))
    assert not any(crosses(before,after,boxes[i*8:i*8+4]) for i in range(5))
    e.x,e.z=after
assert math.dist((e.x,e.z),shelter)<.002
# Commitment expires to advance; no target prevents new shelter selection.
tick.value=360;assert goal(0,(5000,1300))!=shelter
# Explicit advance cancels an active commitment immediately.
e.x,e.z=5165,1537;e.target=1;tick.value=1080
goal(0,(5000,1300));assert metrics[5]==2
fronts[6]=1;assert goal(0,(5000,1300))!=shelter
# Aircraft bypasses solids, caches and shelter.
e.kind=3;assert goal(0,(5000,1300))==(5000.,1300.)
# Immobilised distant actors request a bounded corridor recovery after240calls.
init();e=entities[0];e.kind=1;e.x,e.z=3950,1300
for _ in range(242):
    lib.nav_tick();goal(0,(4050,1300))
assert metrics[4]==1,list(metrics)
stuck_replans=metrics[4]
# Integrated world hooks: no direct nav_tick/goal/terrain_move calls here.
# A real armor actor follows the bunker+wall corridor under an explicit order.
lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.sim_checksum.restype=C.c_uint64
world_checksums=[]
for replay in range(2):
    assert lib.sim_init(2,19)==0
    e=entities[0];enemy=entities[1]
    e.x,e.z,e.kind,e.hp=5243.89013671875,1564.114990234375,1,400
    enemy.x,enemy.z,enemy.kind=7000,7000,0
    assert lib.sim_order(1,0,1)==0
    final=(3125.11279296875,5204.44287109375)
    assert lib.sim_waypoint(0,0,*final)==0
    reached=False
    for world_tick in range(12000):
        before=e.x,e.z
        lib.sim_tick()
        after=e.x,e.z
        assert math.dist(before,after)<=.501
        assert not any(crosses(before,after,boxes[i*8:i*8+4]) for i in range(5))
        assert metrics[6]<=8 and metrics[7]<=8
        if math.dist(after,final)<.002:
            reached=True;break
    assert reached and metrics[1]>0 and metrics[3]>0,(after,list(metrics))
    world_checksums.append(lib.sim_checksum())
assert world_checksums[0]==world_checksums[1]
# Aircraft overhead neither capture nor contest ground sites, even in a fixture
# where ordinary ground movement is frozen and capture evaluates real records.
assert lib.sim_init(2,19)==0
sites=(C.c_uint*(12*8)).in_dll(lib,'sim_sites')
for i,e in enumerate(entities[:2]):
    e.kind=3;e.x,e.z=5000,1300;e.side=i;e.hp=200
before_owner=sites[2*8+2];before_progress=sites[2*8+3]
for step in range(1,22):
    tick.value=step*30
    lib.operation_tick()
assert sites[2*8+2]==before_owner and sites[2*8+3]==before_progress
assert sites[2*8+7]&4==0,'aircraft contested a ground site'
print(json.dumps({'suite':'navigation','passed':True,'oracle_cases':2000,
                  'route_arrival_ticks':route_ticks,'step_metres':.5,
                  'FIFO_admitted_requests':1024,'requests_per_tick_cap':8,
                  'saturation_fallbacks':512,'cover_physical_LOS':True,
                  'stuck_replans':stuck_replans,'scout_support_corridor_builds':scout_support_builds,
                  'driver':'actual assembly corridor queries plus integrated sim_tick movement/replay',
                  'integrated_route_ticks':world_tick+1,'integrated_replay_checksum':hex(world_checksums[0]),
                  'aircraft_ground_capture_excluded':True}))
