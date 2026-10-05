#!/usr/bin/env python3
"""Bounded actual NASM queues with controlled spawn; no physical-fire claim.
Self builds the assembly development probe when no LIB is supplied.
"""
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
    tmp=tempfile.TemporaryDirectory(prefix='rh-ordnance-')
    nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(ROOT/'.tools/nasm/nasm')
    objects=[]
    for source in ['src/sim/ordnance_admission.asm','tests/ordnance_admission_probe.asm']:
        obj=Path(tmp.name)/(Path(source).stem+'.o')
        subprocess.run([nasm,'-f','elf64','-I',str(ROOT)+'/',str(ROOT/source),'-o',str(obj)],check=True)
        objects.append(str(obj))
    libpath=str(Path(tmp.name)/'ordnance.so')
    subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',libpath],check=True)
lib=C.CDLL(libpath)
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front','target','generation')]
actors=(Entity*32768).in_dll(lib,'sim_entities')
ammo=(C.c_uint*32768).in_dll(lib,'sim_shell_ammo')
cooldown=(C.c_uint*32768).in_dll(lib,'sim_shell_cooldown')
drivers=(C.c_int*32768).in_dll(lib,'vehicle_entity_driver')
metrics=(C.c_uint64*16).in_dll(lib,'ordnance_metrics')
cursors=(C.c_int*4).in_dll(lib,'ordnance_cursors')
sources=(C.c_uint*32768).in_dll(lib,'test_sources')
def word(name):return C.c_uint.in_dll(lib,name)
count=word('sim_count');tick=word('sim_tick_count');pool=word('sim_projectile_count')
calls=word('test_calls');fail=word('test_fail');dropped=word('test_dropped')
enabled=word('ordnance_enabled')
lib.ordnance_request.argtypes=[C.c_uint,C.c_uint]
lib.test_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_hash.restype=C.c_uint64
FNV=1099511628211;SEED=14695981039346656037

def hash_state():return lib.test_hash(SEED,FNV)
def reset(n=128):
    count.value=n;tick.value=0;pool.value=0;calls.value=0;fail.value=0;dropped.value=0
    C.memset(C.addressof(actors),0,C.sizeof(actors))
    C.memset(C.addressof(drivers),255,C.sizeof(drivers))
    C.memset(C.addressof(ammo),0,C.sizeof(ammo))
    C.memset(C.addressof(cooldown),0,C.sizeof(cooldown))
    for i in range(n):
        e=actors[i];e.hp=100;e.side=(i%4)//2;e.kind=i%2+1;e.generation=i+1
        e.x=1000+i;e.z=2000;ammo[i]=64
    lib.ordnance_init()
def target(i):return 2 if actors[i].side==0 else 0
def requests(n):
    for i in range(n):assert lib.ordnance_request(i,target(i))==0,i

def unchanged_request(i,j,result):
    before=(bytes(actors),bytes(ammo),bytes(cooldown),bytes(drivers),pool.value,hash_state())
    assert lib.ordnance_request(i,j)==result,(i,j)
    assert before==(bytes(actors),bytes(ammo),bytes(cooldown),bytes(drivers),pool.value,hash_state())

reset()
basehash=hash_state();requests(128)
assert list(metrics)[::4]==[32]*4
assert hash_state()==basehash
unchanged_request(0,2,-1)
assert lib.test_flush_abi()==1
assert calls.value==128 and pool.value==128
assert list(metrics)[1::4]==[32]*4 and all(ammo[i]==63 for i in range(128))
assert len(set(sources[:calls.value]))==128
assert hash_state()!=basehash
# Actual future-affecting bytes alone form the hash. Diagnostics/queues excluded.
expected=SEED
for byte in struct.pack('<I4i',enabled.value,*cursors):expected=((expected^byte)*FNV)&((1<<64)-1)
assert hash_state()==expected
for i in range(16):metrics[i]+=7
assert hash_state()==expected
lib.ordnance_begin();assert hash_state()==expected

# Saturated bounded maximum: exactly four-way interleaving, no repeated submits.
reset(32768);requests(32768);assert lib.test_flush_abi()==1
assert calls.value==32768 and pool.value==416 and dropped.value==32768-416
assert list(metrics)[1::4]==[104]*4
assert list(metrics)[2::4]==[8192-104]*4
assert list(metrics)[3::4]==[0]*4
assert len(set(sources[:32768]))==32768
assert list(sources[:8])==list(range(8))
assert sum(64-ammo[i] for i in range(32768))==416

# Persistent success cursor grants every source a slot under extreme pressure.
reset(128);seen=set();round_order=[]
for t in range(128):
    tick.value=t;pool.value=415;calls.value=0
    C.memset(C.addressof(cooldown),0,C.sizeof(cooldown))
    lib.ordnance_begin();requests(128);lib.ordnance_flush()
    assert calls.value==128 and pool.value==416
    winner=int(sources[0]);seen.add(winner);round_order.append(winner)
    assert (winner%4)==t%4
assert len(seen)==128 and round_order==list(range(128)),round_order
assert list(metrics)[1::4]==[32]*4
# Repeat identical commands/state produces identical ordering and final hash.
first_hash=hash_state()
reset(128)
for t in range(128):
    tick.value=t;pool.value=415;calls.value=0
    C.memset(C.addressof(cooldown),0,C.sizeof(cooldown))
    lib.ordnance_begin();requests(128);lib.ordnance_flush()
    assert sources[0]==round_order[t]
assert hash_state()==first_hash

# Label symmetry: identical physical actors/roles/requests must retain the entire
# spawn attempt sequence under a global side-label flip, including refusals and
# the next-tick success cursor. Compare diagnostics/cursors after group remapping.
def symmetry_run(n, swapped, sparse=False):
    reset(n)
    if swapped:
        for i in range(n):actors[i].side ^= 1
    sequences=[]
    for t in range(24):
        tick.value=t;calls.value=0;pool.value=415-(t%5)
        C.memset(C.addressof(cooldown),0,C.sizeof(cooldown))
        lib.ordnance_begin()
        for i in range(n):
            # Eligibility changes are physical-ID based and identical in both.
            if sparse and (i%4 in (2,3) or (i+t)%7==0):continue
            target_id=2 if (i%4)//2==0 else 0
            assert lib.ordnance_request(i,target_id)==0
        lib.ordnance_flush()
        sequences.append(tuple(sources[:calls.value]))
    state=tuple(cursors)
    counters=tuple(tuple(metrics[g*4:g*4+4]) for g in range(4))
    if swapped:
        state=tuple(state[g^2] for g in range(4))
        counters=tuple(counters[g^2] for g in range(4))
    return sequences,state,counters
for n,sparse in [(128,False),(128,True),(32768,False)]:
    assert symmetry_run(n,False,sparse)==symmetry_run(n,True,sparse),(n,sparse)

# Requests reject malformed IDs, sides, state, generations and boarded sources.
for field,value in [('hp',0),('kind',0),('kind',3),('side',2),('generation',0)]:
    reset();setattr(actors[0],field,value);unchanged_request(0,2,-1)
for field,value in [('hp',0),('side',0),('side',2),('generation',0)]:
    reset();setattr(actors[2],field,value);unchanged_request(0,2,-1)
reset()
for i,j in [(128,2),(0,128),(2**32-1,2),(0,2**32-1),(0,0)]:unchanged_request(i,j,-1)
for array,value in [(ammo,0),(cooldown,1),(drivers,0)]:
    reset();array[0]=value;unchanged_request(0,2,-1)
reset();count.value=32769;unchanged_request(0,2,-1)
reset();enabled.value=0;unchanged_request(0,2,-1);lib.ordnance_flush();assert calls.value==0

# Queue time generation/ownership/stores may change; flush never fires stale node.
for mutation in [lambda: setattr(actors[0],'generation',999),lambda: setattr(actors[2],'generation',999),lambda: setattr(actors[0],'hp',0),lambda: setattr(actors[2],'hp',0),lambda: setattr(actors[0],'kind',2),lambda: setattr(actors[2],'side',0),lambda: ammo.__setitem__(0,0),lambda: cooldown.__setitem__(0,1),lambda: drivers.__setitem__(0,0)]:
    reset();assert lib.ordnance_request(0,2)==0;mutation();lib.ordnance_flush()
    assert calls.value==0 and metrics[3]==1 and cursors[0]==-1
# Production refusal below the capacity threshold is not falsely called pressure.
reset();assert lib.ordnance_request(0,2)==0;fail.value=1;lib.ordnance_flush()
assert calls.value==1 and metrics[2]==0 and metrics[3]==1 and cursors[0]==-1
# Clearing drops stale work; no request persistence or automatic source reselection.
reset();assert lib.ordnance_request(0,2)==0;lib.ordnance_begin();lib.ordnance_flush();assert calls.value==0
print(json.dumps({'suite':'ordnance-admission','passed':True,'ordnance_admission':'passed','maximum_requests':32768,'controlled_capacity':416,'equal_group_admissions':[104]*4,'pressure_rounds':128,'unique_pressure_winners':128,'side_label_attempt_symmetry':True,'production_trajectories':False}))
