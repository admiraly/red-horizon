#!/usr/bin/env python3
"""Small real-core combat/replay/CLI checks; scale coverage remains in the full suite."""
import ctypes as C
import json
import subprocess
import sys
import time
exe,library=sys.argv[1:]
lib=C.CDLL(library)
lib.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
entities=(Entity*32768).in_dll(lib,'sim_entities')
alive=(C.c_uint*2).in_dll(lib,'sim_alive')
lib.sim_tick() # no initialized world is safe

def fight(swapped=False):
    assert lib.sim_init(128,19)==0
    assert {e.kind for e in entities[:128]}=={0,1,2,3}
    assert {e.front for e in entities[:128]}=={0,1,2}
    # Fixed-position hold/side-swap negative control. Imminent danger may
    # interrupt hold in gameplay; enabled physical evasion has its own oracle.
    C.c_uint.in_dll(lib,'hazard_enabled').value=0
    for e in entities[:128]:
        if e.kind==3:e.kind=0
        e.x,e.z=(3500 if e.side==0 else 3520),1300
        if swapped:e.side^=1
    for side in (0,1):
        for front in range(3):assert lib.sim_order(side,front,1)==0
    original=[(e.x,e.z) for e in entities[:128] if e.kind!=3]
    for _ in range(120):lib.sim_tick()
    assert original==[(e.x,e.z) for e in entities[:128] if e.kind!=3]
    assert sum(alive)<128
    assert list(alive)==[sum(e.hp>0 and e.side==side for e in entities[:128]) for side in (0,1)]
    assert all(-1<=e.target<128 for e in entities[:128])
    return [e.hp for e in entities[:128]],list(alive),lib.sim_checksum()
first=fight();repeat=fight();swapped=fight(True)
assert first==repeat,'small combat replay diverged'
assert first[0]==swapped[0] and first[1]==swapped[1][::-1],'side/index combat bias'
assert lib.sim_init(32,1)==0
before=lib.sim_checksum()
for count in (0,1,3,32769,0xffffffff):
    assert lib.sim_init(count,1)==-1 and lib.sim_checksum()==before
for args in ((2,0,0),(0,3,0),(0,0,3)):assert lib.sim_order(*args)==-1
assert lib.sim_fire(16,100)==0 and entities[16].hp==0 and alive[1]==15
assert lib.sim_fire(16,1)==-1 and alive[1]==15
for args in (['--units','1'],['--ticks','0'],['--seed','-1'],['--units'],['--bogus','2']):
    assert subprocess.run([exe,*args],capture_output=True).returncode==2
start=time.monotonic()
real=json.loads(subprocess.check_output([exe,'--realtime','--ticks','3','--units','32']))
assert real['ticks']==3 and time.monotonic()-start>=.09
plain=json.loads(subprocess.check_output([exe,'--ticks','3','--units','32']))
assert real['checksum']==plain['checksum']
print(json.dumps({'suite':'fast-combat','passed':True,'fixture_units':128,'checks':['roles/fronts','physical combat/counts','same-run replay','side-swap symmetry','invalid-state preservation','guarded damage','CLI','fixed-tick pacing'],'scale_coverage':False}))
