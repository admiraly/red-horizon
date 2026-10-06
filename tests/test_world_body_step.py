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
import random,math,struct
for name in ('probe_world_body_step_context','probe_terrain_body_step'):
 getattr(l,name).argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint64,C.c_void_p]+[C.c_float]*5
rng=random.Random(901);radii=(.551,3.551,4.491);rows=[]
f=lambda v:C.c_float(v).value
# Refresh the genuine captured-pose bounds, then model the planar swept contract.
assert l.world_body_path_clear(0,3480,2000,3520,2000)==0
bounds=list((C.c_float*6).in_dll(l,'wreck_query_bounds'))
def clear(role,start,end):
 radius=f(radii[role]);lo=(f(bounds[0]-radius),f(bounds[2]-radius));hi=(f(bounds[3]+radius),f(bounds[5]+radius));d=(f(end[0]-start[0]),f(end[1]-start[1]))
 if all(lo[i]<=start[i]<=hi[i] for i in (0,1)) and any(d):
  depths=[f(start[0]-lo[0]),f(hi[0]-start[0]),f(start[1]-lo[1]),f(hi[1]-start[1])];minimum=min(depths)
  if any(depth==minimum and derivative<=0 for depth,derivative in zip(depths,(d[0],-d[0],d[1],-d[1]))):return True
 entry,exit=0.,1.
 for i in (0,1):
  delta=end[i]-start[i]
  if not delta:
   if not lo[i]<=start[i]<=hi[i]:return True
   continue
  t0,t1=sorted(((lo[i]-start[i])/delta,(hi[i]-start[i])/delta));entry=max(entry,t0);exit=min(exit,t1)
  if entry>exit:return True
 return False
def move(name,role,start,goal,step,context=(remote,1,79)):
 before=l.sim_checksum();source=bytes(context[0]) if context[0] is not None else None;regs=C.create_string_buffer(56)
 rc=getattr(l,name)(role,*context,regs,*start,*goal,step);assert rc!=-99
 assert struct.unpack('<6Q',regs.raw[:48])==tuple(0x123401+i for i in range(6));assert l.sim_checksum()==before
 if source is not None:assert bytes(context[0])==source
 return struct.unpack('<2f',regs.raw[48:56])
for i in range(1500):
 role=i%3;start=tuple(map(f,(3500+rng.uniform(-12,12),2000+rng.uniform(-12,12))))
 delta=(rng.uniform(-3,3),0) if i%5==0 else ((0,rng.uniform(-3,3)) if i%5==1 else (rng.uniform(-3,3),rng.uniform(-3,3)))
 goal=tuple(f(start[j]+delta[j]) for j in (0,1));step=f(rng.uniform(.01,.75));candidate=move('probe_terrain_body_step',role,start,goal,step)
 fragments=(candidate,(candidate[0],start[1]),(start[0],candidate[1]));expected=next((v for v in fragments if clear(role,start,v)),start)
 actual=move('probe_world_body_step_context',role,start,goal,step)
 assert actual==expected,(i,role,start,goal,candidate,actual,expected,bounds)
 assert math.dist(start,actual)<=step+.0007
 if delta[0]==0:assert actual[0]==start[0]
 if delta[1]==0:assert actual[1]==start[1]
 for j in (0,1):assert abs(actual[j]-start[j])<=abs(candidate[j]-start[j])+.000001
 if actual!=start:assert clear(role,start,actual)
 rows.append(actual!=start)
# Exact source selection and fail-closed state; no in-flight actor writes.
start=(3480.,2000.);goal=(3520.,2000.)
for role in (0,1,2):
 actual=move('probe_world_body_step_context',role,start,goal,.55,(local,0,79));expected=move('probe_terrain_body_step',role,start,goal,.55,(local,0,79));assert actual==expected
 assert move('probe_world_body_step_context',role,start,goal,.55,(None,0,80))==start
 for step in (0.,-1.,float('nan'),float('inf')):assert move('probe_world_body_step_context',role,start,goal,step)==start
for role in (3,4,0xffffffff):assert move('probe_world_body_step_context',role,start,goal,.55)==start
print(json.dumps({'suite':'prepared-world-body-manual-step','passed':True,'random_manual_intents':1500,'moving_results':sum(rows),'original_radii':radii,'readonly_sources_and_authority':True,'GPRs_stack_and_component_limits':True,'library_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'limits':['Independent slab/escape oracle uses the separately verified production captured bounds','Proposal helper only; no actor movement, hull application, navigation detour, remote prediction, graphics or scale acceptance']}))
