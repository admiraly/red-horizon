#!/usr/bin/env python3
"""Public world ticks: distant visible targets produce finite travelling rounds."""
import ctypes as C
import hashlib
import json
import pathlib
import sys
lib=C.CDLL(sys.argv[1])
class Entity(C.Structure):
    _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Shell(C.Structure):
    _fields_=[(n,C.c_float) for n in ('x','y','z','vx','vy','vz')]+[(n,C.c_uint) for n in ('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint) for n in ('source','generation','active','source_generation','reserved')]
e=(Entity*32768).in_dll(lib,'sim_entities');p=(Shell*512).in_dll(lib,'sim_projectiles')
ammo=(C.c_uint*32768).in_dll(lib,'sim_shell_ammo')
lib.sim_checksum.restype=C.c_uint64

def fixture(kind,side,sx,sz,tx,tz):
    assert lib.sim_init(32,42)==0
    for actor in e[:32]: actor.hp=0
    source=(12 if kind==1 else 14)+16*side; target=16*(1-side)
    e[source].x,e[source].z,e[source].hp,e[source].front=sx,sz,400,0
    e[target].x,e[target].z,e[target].hp,e[target].kind,e[target].front=tx,tz,400,1,0
    ammo[target]=0
    for s in range(2):
        for f in range(3): assert lib.sim_order(s,f,1)==0
    return source,target

def run(kind,side,coords,should_fire=True):
    source,target=fixture(kind,side,*coords); initial=ammo[source]
    trace=[]; first_fire=None; first_damage=None; max_active=0
    for tick in range(1,151):
        lib.sim_tick()
        if ammo[source]<initial and first_fire is None:first_fire=tick
        if e[target].hp<400 and first_damage is None:first_damage=tick
        max_active=max(max_active,sum(x.active for x in p))
        trace.append((lib.sim_checksum(),e[source].target,ammo[source],e[target].hp))
    if should_fire:
        assert first_fire is not None, ('no finite-ammo launch',kind,side,coords)
        assert first_damage is not None and first_damage>first_fire, ('no travelling impact',coords,first_fire,first_damage)
        assert max_active>0
    else:
        assert first_fire is None and first_damage is None and ammo[source]==initial, ('invalid acquisition',coords)
    return {'kind':kind,'side':side,'coordinates':coords,'first_launch':first_fire,'first_damage':first_damage,'ammo_spent':initial-ammo[source],'hp_remaining':e[target].hp,'trace_sha256':hashlib.sha256(repr(trace).encode()).hexdigest()}

cases=[]
# A tank two cells away, artillery three cells away: ordinary range, not an
# expanded weapon. Both sides and X/Z directions have the same opportunity.
for kind,delta in [(1,449),(2,649)]:
    for side in (0,1):
        for coords in [(1249,2000,1249+delta,2000),(1249+delta,2000,1249,2000),(2000,1249,2000,1249+delta),(2000,1249+delta,2000,1249)]:
            a=run(kind,side,coords); b=run(kind,side,coords)
            assert a==b, 'same-build replay differs'
            cases.append(a)
    for coords in [(1249,2000,1249+delta+2,2000),(1249,2000,1249+delta,2000+delta)]:
        cases.append(run(kind,0,coords,False))
# A target inside nominal range remains hidden by the physical bunker wall.
cases.append(run(1,0,(3700,1300,4100,1300),False))
print(json.dumps({'suite':'ground-acquisition','passed':True,'cases':cases,'library_sha256':hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(),'limits':['Initial sparse positions and ammunition set once; all launches/motion/damage use production sim_tick.','Range-complete cell envelope retains24 samples per dense cell; not exhaustive dense-target acquisition.','Not strategic intel, support designation, or performance acceptance.']}))
