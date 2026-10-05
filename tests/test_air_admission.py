#!/usr/bin/env python3
"""Actual NASM bounded queues with controlled launch, not production flight."""
import ctypes as C
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if len(sys.argv)>1:
    libpath=sys.argv[1]
else:
    tmp=tempfile.TemporaryDirectory(prefix='rh-air-admission-')
    nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
    objects=[]
    for source in ['src/sim/air_admission.asm','tests/air_admission_probe.asm']:
        obj=Path(tmp.name)/(Path(source).stem+'.o')
        subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(obj)],check=True)
        objects.append(str(obj))
    libpath=str(Path(tmp.name)/'air-admission.so')
    subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',libpath],check=True)
lib=C.CDLL(libpath)
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front','target','generation')]
class Air(C.Structure):
    _fields_=[(n,C.c_float) for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_int) for n in ('role','mode','target','cooldown','ammo','generation')]+[(n,C.c_float) for n in ('vx','vy','vz')]+[(n,C.c_int) for n in ('pass_ticks','flags')]
actors=(Entity*32768).in_dll(lib,'sim_entities')
air=(Air*32768).in_dll(lib,'sim_aircraft')
metrics=(C.c_uint64*16).in_dll(lib,'air_admission_metrics')
cursors=(C.c_int*4).in_dll(lib,'air_admission_cursors')
sources=(C.c_uint*32768).in_dll(lib,'test_sources')
roles=(C.c_uint*32768).in_dll(lib,'test_roles')
def word(name):return C.c_uint.in_dll(lib,name)
count=word('sim_count');tick=word('sim_tick_count');pool=word('sim_projectile_count')
calls=word('test_calls');fail=word('test_fail');dropped=word('test_dropped');badabi=word('test_bad_abi')
enabled=word('air_admission_enabled')
lib.air_admission_request.argtypes=[C.c_uint,C.c_uint]
lib.test_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_hash.restype=C.c_uint64
FNV=1099511628211;SEED=14695981039346656037

def hash_state():return lib.test_hash(SEED,FNV)
def reset(n=128, all_fighters=False):
    count.value=n if all_fighters else n+4
    tick.value=0;pool.value=0;calls.value=0;fail.value=0;dropped.value=0;badabi.value=0
    C.memset(C.addressof(actors),0,C.sizeof(actors));C.memset(C.addressof(air),0,C.sizeof(air))
    for i in range(count.value):
        e=actors[i];e.hp=100;e.side=(i%4)//2;e.kind=3 if i<n else 0;e.generation=i+1
        e.x=1000+i;e.z=2000
        a=air[i];a.role=1 if all_fighters else i%2;a.mode=1;a.target=target(i,n,all_fighters)
        a.ammo=64;a.flags=1;a.generation=e.generation
    lib.air_admission_init()
def target(i,n=128,all_fighters=False):
    side=(i%4)//2
    if all_fighters or i%2:return 3 if side==0 else 1
    return n+2 if side==0 else n

def requests(n,all_fighters=False):
    for i in range(n):assert lib.air_admission_request(i,target(i,n,all_fighters))==0,i

def unchanged_request(i,j,result):
    before=(bytes(actors),bytes(air),pool.value,hash_state(),tuple(metrics),tuple(cursors))
    assert lib.air_admission_request(i,j)==result,(i,j)
    assert before==(bytes(actors),bytes(air),pool.value,hash_state(),tuple(metrics),tuple(cursors))

def rearm(n):
    # Recreate ready geometry/FSM externally for this queue-only stress fixture.
    for i in range(n):
        air[i].cooldown=0;air[i].pass_ticks=0;air[i].mode=1;air[i].target=target(i,n)

reset()
basehash=hash_state();requests(128)
assert list(metrics)[::4]==[32]*4 and hash_state()==basehash
unchanged_request(0,130,-1)
assert lib.test_flush_abi()==1 and badabi.value==0
assert calls.value==128 and pool.value==128
assert list(metrics)[1::4]==[32]*4 and all(air[i].ammo==63 and air[i].cooldown==3 for i in range(128))
assert len(set(sources[:calls.value]))==128
for i in range(128):
    assert roles[i]==air[sources[i]].role+3
    if i%2==0:assert (air[i].mode,air[i].pass_ticks,air[i].target)==(2,210,-1)
    else:assert (air[i].mode,air[i].pass_ticks,air[i].target)==(1,0,target(i))
expected=SEED
for byte in struct.pack('<I4i',enabled.value,*cursors):expected=((expected^byte)*FNV)&((1<<64)-1)
assert hash_state()==expected and hash_state()!=basehash
for i in range(16):metrics[i]+=7
assert hash_state()==expected
lib.air_admission_begin();assert hash_state()==expected

# Maximum valid source population: all fighters can target each other.
reset(32768,True);requests(32768,True);assert lib.test_flush_abi()==1
assert calls.value==32768 and pool.value==480 and dropped.value==32768-480 and badabi.value==0
assert list(metrics)[1::4]==[0,240,0,240]
assert list(metrics)[2::4]==[0,16384-240,0,16384-240]
assert len(set(sources[:32768]))==32768
assert sum(64-air[i].ammo for i in range(32768))==480
# Four mixed groups use four actual nonair bomber target records.
reset(32764);requests(32764);assert lib.test_flush_abi()==1
assert calls.value==32764 and pool.value==480 and dropped.value==32764-480
assert list(metrics)[1::4]==[120]*4
assert list(metrics)[2::4]==[8191-120]*4 and list(metrics)[3::4]==[0]*4
assert len(set(sources[:32764]))==32764 and list(sources[:8])==list(range(8))
assert sum(64-air[i].ammo for i in range(32764))==480
for i in range(480,32764):
    assert (air[i].ammo,air[i].cooldown,air[i].mode,air[i].pass_ticks,air[i].target)==(64,0,1,0,target(i,32764))

# Persistent success cursor grants every source one slot under pressure.
reset();seen=set();round_order=[]
for t in range(128):
    tick.value=t;pool.value=479;calls.value=0;rearm(128)
    lib.air_admission_begin();requests(128);lib.air_admission_flush()
    assert calls.value==128 and pool.value==480
    winner=int(sources[0]);seen.add(winner);round_order.append(winner)
    assert winner%4==t%4
assert len(seen)==128 and round_order==list(range(128)),round_order
assert list(metrics)[1::4]==[32]*4
first_hash=hash_state()
reset()
for t in range(128):
    tick.value=t;pool.value=479;calls.value=0;rearm(128)
    lib.air_admission_begin();requests(128);lib.air_admission_flush()
    assert sources[0]==round_order[t]
assert hash_state()==first_hash

# Entire attempt sequence, including refusals, invariant under global label flip.
def symmetry_run(n,swapped,sparse=False):
    reset(n)
    if swapped:
        for i in range(count.value):actors[i].side ^= 1
    sequences=[]
    for t in range(24):
        tick.value=t;calls.value=0;pool.value=479-t%5;rearm(n)
        lib.air_admission_begin()
        for i in range(n):
            if sparse and (i%4 in (2,3) or (i+t)%7==0):continue
            assert lib.air_admission_request(i,target(i,n))==0
        lib.air_admission_flush();sequences.append(tuple(sources[:calls.value]))
    state=tuple(cursors);counters=tuple(tuple(metrics[g*4:g*4+4]) for g in range(4))
    if swapped:
        state=tuple(state[g^2] for g in range(4));counters=tuple(counters[g^2] for g in range(4))
    return sequences,state,counters
for n,sparse in [(128,False),(128,True),(32764,False)]:
    assert symmetry_run(n,False,sparse)==symmetry_run(n,True,sparse),(n,sparse)

# Malformed/not ready submissions must preserve all policy/gameplay/metrics state.
for field,value in [('hp',0),('kind',0),('kind',4),('side',2),('generation',0)]:
    reset();setattr(actors[0],field,value);unchanged_request(0,130,-1)
for field,value in [('hp',0),('kind',3),('side',0),('side',2),('generation',0)]:
    reset();setattr(actors[130],field,value);unchanged_request(0,130,-1)
for field,value in [('flags',0),('generation',999),('role',2),('role',-1),('mode',0),('mode',2),('mode',3),('target',131),('ammo',0),('ammo',-1),('cooldown',1),('pass_ticks',1)]:
    reset();setattr(air[0],field,value);unchanged_request(0,130,-1)
reset();actors[3].kind=0;unchanged_request(1,3,-1)
reset()
for i,j in [(132,130),(0,132),(2**32-1,130),(0,2**32-1),(0,0)]:unchanged_request(i,j,-1)
reset();count.value=32769;unchanged_request(0,130,-1)
reset();enabled.value=0;unchanged_request(0,130,-1);lib.air_admission_flush();assert calls.value==0

# Revalidate every accepted node before launch, including matching target sidecar.
mutations=[lambda:setattr(actors[0],'generation',999),lambda:setattr(actors[130],'generation',999),lambda:setattr(actors[0],'hp',0),lambda:setattr(actors[130],'hp',0),lambda:setattr(actors[0],'kind',0),lambda:setattr(actors[0],'side',1),lambda:setattr(actors[0],'side',2),lambda:setattr(actors[130],'side',0),lambda:setattr(actors[130],'kind',3)]
mutations += [lambda f=f,v=v:setattr(air[0],f,v) for f,v in [('flags',0),('generation',999),('role',1),('mode',2),('target',131),('ammo',0),('ammo',-1),('cooldown',1),('pass_ticks',1)]]
for mutation in mutations:
    reset();assert lib.air_admission_request(0,130)==0;mutation()
    before=bytes(air);lib.air_admission_flush()
    assert calls.value==0 and metrics[3]==1 and cursors[0]==-1 and bytes(air)==before
reset();assert lib.air_admission_request(0,130)==0;count.value=0;lib.air_admission_flush()
assert calls.value==0 and metrics[3]==1
reset();assert lib.air_admission_request(0,130)==0;count.value=32769;lib.air_admission_flush()
assert calls.value==0 and metrics[3]==1
# Actual primitive refusal below capacity is diagnostic invalidation, no FSM/store commit.
reset();assert lib.air_admission_request(0,130)==0;fail.value=1
before=bytes(air);lib.air_admission_flush()
assert calls.value==1 and metrics[2]==0 and metrics[3]==1 and cursors[0]==-1 and bytes(air)==before
# Clearing drops stale work. Disabled flush leaves queued gameplay untouched.
reset();assert lib.air_admission_request(0,130)==0;lib.air_admission_begin();lib.air_admission_flush();assert calls.value==0
reset();assert lib.air_admission_request(0,130)==0;enabled.value=0;before=bytes(air);lib.air_admission_flush();assert calls.value==0 and bytes(air)==before
# Init resets future-affecting state as well as diagnostics.
lib.air_admission_init();assert enabled.value==1 and tuple(cursors)==(-1,)*4 and not any(metrics)
print(json.dumps({'suite':'air-admission','passed':True,'maximum_requests':32768,'mixed_requests':32764,'controlled_capacity':480,'equal_group_admissions':[120]*4,'pressure_rounds':128,'unique_pressure_winners':128,'side_label_attempt_symmetry':True,'production_trajectories':False}))
