#!/usr/bin/env python3
"""Prepared world LOS, real production geometry and explicit source isolation."""
import ctypes as C,hashlib,json,pathlib,sys
PATH=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(PATH));l.sim_init.argtypes=[C.c_uint]*2;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float;l.sim_checksum.restype=C.c_uint64
l.world_los.argtypes=[C.c_float]*6;l.world_los_context.argtypes=[C.c_void_p,C.c_uint,C.c_uint64]+[C.c_float]*6
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
e=(E*32768).in_dll(l,'sim_entities');alive=(C.c_uint*2).in_dll(l,'sim_alive');wrecks=(C.c_byte*65536).in_dll(l,'sim_wrecks');calls=0
l.world_body_path_clear.argtypes=[C.c_uint]+[C.c_float]*4
l.world_body_path_clear_context.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint64]+[C.c_float]*4
l.world_body_blocked.argtypes=[C.c_uint]+[C.c_float]*2
l.world_body_blocked_context.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint64]+[C.c_float]*2
assert l.sim_init(64,42)==0
for entity in e[:64]:entity.hp=0
alive[0]=alive[1]=0;e[12]=E(3500,2000,1,1,1,0,-1,42);alive[1]=1;l.ground_init();l.sim_air_damage(12,1)
local=C.create_string_buffer(65536);remote=C.create_string_buffer(bytes(wrecks),65536)
def query(role,points,expected,context=None,blocked=False):
 global calls
 before=l.sim_checksum();source=bytes(context[0]) if context and context[0] is not None else None
 name='world_body_blocked' if blocked else 'world_body_path_clear'
 result=getattr(l,name+'_context')(role,*context,*points) if context else getattr(l,name)(role,*points)
 assert result==expected,(role,points,result,expected,context);assert l.sim_checksum()==before
 if context and context[0] is not None:assert bytes(context[0])==source
 calls+=1
for role in (0,1,2):
 query(role,(3480,2000,3520,2000),0)
 query(role,(3480,2010,3520,2010),1)
 query(role,(3480,2004.5,3520,2004.5),int(role==0))
 query(role,(3500,2000),1,blocked=True)
 query(role,(3480,2000),0,blocked=True)
 query(role,(3498.5,2000,3490,2000),1)
 query(role,(3498.5,2000,3501.5,2000),0)
 query(role,(5150,1570,5250,1570),0) # Authored solid, independently of wreck.
 query(role,(5370,5200,5500,5200),int(role==0)) # Original grade limits.
 ray=(3480,2000,3520,2000)
 query(role,ray,1,(local,0,79));query(role,ray,0,(remote,1,79));query(role,ray,1,(local,0,79));query(role,ray,0,(remote,1,79))
 query(role,(3500,2000),0,(local,0,79),blocked=True)
 query(role,(3500,2000),1,(remote,1,79),blocked=True)
 for index in range(4):
  points=list(ray);points[index]=float('nan');query(role,points,0)
 query(role,ray,0,(None,0,80));query(role,ray,0,(local,1025,80))
C.c_float.from_buffer(remote,0).value=float('nan');query(0,ray,0,(remote,1,80))
for role in (3,4,0xffffffff):query(role,ray,0);query(role,(3500,2000),1,blocked=True)
print(json.dumps({'suite':'prepared-world-body-geometry','passed':True,'calls':calls,'genuine_casualty_wreck':True,'same_revision_source_switches':12,'original_radii': [.551,3.551,4.491],'readonly_authority_and_sources':True,'library_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'scope':'Prepared terrain/body/grade and explicit wreck source composition only. No gameplay movement/nav/controller/network prediction/scale acceptance.'}))
