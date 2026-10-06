#!/usr/bin/env python3
"""Prepared world LOS, real production geometry and explicit source isolation."""
import ctypes as C,hashlib,json,pathlib,sys
PATH=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(PATH));l.sim_init.argtypes=[C.c_uint]*2;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float;l.sim_checksum.restype=C.c_uint64
l.world_los.argtypes=[C.c_float]*6;l.world_los_context.argtypes=[C.c_void_p,C.c_uint,C.c_uint64]+[C.c_float]*6
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
e=(E*32768).in_dll(l,'sim_entities');alive=(C.c_uint*2).in_dll(l,'sim_alive');wrecks=(C.c_byte*65536).in_dll(l,'sim_wrecks');calls=0
assert l.sim_init(64,42)==0
for entity in e[:64]:entity.hp=0
alive[0]=alive[1]=0;e[12]=E(5140,1570,1,1,1,0,-1,42);alive[1]=1;l.ground_init();l.sim_air_damage(12,1)
y=C.c_float.from_buffer_copy(bytes(wrecks)[4:8]).value+1.5
local=C.create_string_buffer(65536);remote=C.create_string_buffer(bytes(wrecks),65536)
def query(points,expected,context=None):
 global calls
 before=l.sim_checksum();source=bytes(context[0]) if context else None
 result=l.world_los_context(*context,*points) if context else l.world_los(*points)
 assert result==expected,(points,result,expected);assert l.sim_checksum()==before
 if context:assert bytes(context[0])==source
 calls+=1
query((0,100,5000,8000,100,5000),1)
query((0,60,5000,8000,60,5000),0)
query((5150,20,1570,5220,20,1570),0)
query((5150,60,1570,5220,60,1570),1)
ray=(5130,y,1570,5150,y,1570)
query(ray,0);query(ray,1,(local,0,79));query(ray,0,(remote,1,79));query(ray,1,(local,0,79));query(ray,0,(remote,1,79))
# Malformed declared alternate-source pose fails closed; authority is untouched.
C.c_float.from_buffer(remote,0).value=float('nan');query(ray,0,(remote,1,80))
print(json.dumps({'suite':'prepared-world-los-geometry','passed':True,'calls':calls,'genuine_casualty_wreck':True,'same_revision_source_switches':4,'readonly_authority_and_sources':True,'library_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'scope':'Prepared production geometry composition and explicit source isolation only. No gameplay callers/body/nav/network prediction/scale acceptance.'}))
