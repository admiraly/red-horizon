#!/usr/bin/env python3
"""Last-observed bomber mission recall: real sight, defensive abort and own-only query."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
nasm=os.environ.get('RED_HORIZON_NASM',str(root/'.tools/nasm/nasm'))
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float) for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint) for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint) for n in ('cooldown','ammo','generation')]+[(n,C.c_float) for n in ('vx','vy','vz')]+[(n,C.c_uint) for n in ('pass_ticks','flags')]
class Strike(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float),('target',C.c_uint),('target_generation',C.c_uint),('owner_generation',C.c_uint),('until',C.c_uint),('dx',C.c_float),('dz',C.c_float),('stage',C.c_uint),('reserved',C.c_uint)]
with tempfile.TemporaryDirectory(prefix='rh-strike-oracle-') as temporary:
 td=pathlib.Path(temporary);probe=td/'probe.o'
 subprocess.run([nasm,'-f','elf64',str(root/'tests/probe_air_strike.asm'),'-o',str(probe)],check=True)
 objects=[root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o') for folder in ('sim','nav','ai','game') for p in sorted((root/'src'/folder).glob('*.asm'))]
 so=td/'strike.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*map(str,objects),str(root/'build/terrain_probe.o'),str(probe),'-lm'],check=True)
 lib=C.CDLL(str(so));lib.sim_checksum.restype=C.c_uint64;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.probe_air_strike_goal.argtypes=[C.c_uint,C.c_void_p,C.c_void_p]
 E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');M=(Strike*32768).in_dll(lib,'sim_air_strikes');clock=C.c_uint.in_dll(lib,'sim_tick_count')
 assert lib.sim_init(64,42)==0
 for e in E[:64]:e.hp=0
 for side in (0,1):
  for front in range(3):lib.sim_order(side,front,1)
 E[15]=Entity(3400,4000,200,0,3,0,32,1);E[32]=Entity(4300,4000,100,1,0,0,-1,1)
 A[15]=Air(lib.terrain_height(3400,4000)+110,math.pi/2,0,0,5,0,0,32,0,8,1,5,0,0,0,1)
 def goal(i):
  out=C.create_string_buffer(b'Z'*8,8);regs=(C.c_uint64*7)();before=lib.sim_checksum();memory=bytes(M[15]);rc=lib.probe_air_strike_goal(i,out,regs)
  assert lib.sim_checksum()==before and bytes(M[15])==memory
  assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,)
  if not rc:assert out.raw==b'Z'*8
  return rc,struct.unpack('<2f',out.raw) if rc else None
 assert goal(15)[0]==0
 lib.sim_tick();assert M[15].target==32 and M[15].target_generation==1 and M[15].owner_generation==1
 assert goal(15)==(1,(4300.,4000.))
 # Production surviving-damage entry point, finite commitment, then public flight.
 lib.sim_air_damage(15,24);assert E[15].hp==176 and M[15].stage==0
 rc,ingress=goal(15);assert rc==1 and abs(ingress[0]-2500)<.001 and abs(ingress[1]-4000)<.001
 hashes=[];travel=0.
 for tick in range(90):
  old=(E[15].x,E[15].z);lib.sim_tick();travel+=math.dist(old,(E[15].x,E[15].z));assert abs(A[15].pitch-math.atan2(A[15].vy,A[15].speed))<1e-6
  if tick%10==0:hashes.append(f'{lib.sim_checksum():016x}')
 assert abs(travel-450)<.01 and E[15].hp==176 and A[15].ammo==8
 defensive_travel=travel
 # Distinct malformed/hidden-target fixtures: recall must not use hidden truth.
 saved=bytes(E[32]);first=goal(15)
 E[32]=Entity(7900,200,0,0,3,2,-1,999)
 assert goal(15)==first
 C.memmove(C.addressof(E[32]),saved,len(saved))
 guards=[]
 for owner,field,bad in [(E[15],'hp',0),(E[15],'kind',0),(E[15],'generation',2),(A[15],'generation',2),(A[15],'role',1),(A[15],'ammo',0),(A[15],'flags',0),(M[15],'owner_generation',2),(M[15],'until',clock.value),(M[15],'until',clock.value+2401),(M[15],'x',math.nan),(M[15],'z',math.inf),(M[15],'x',-1),(M[15],'z',8001)]:
  old=getattr(owner,field);setattr(owner,field,bad);assert goal(15)[0]==0,(field,bad);setattr(owner,field,old);guards.append(field)
 for i in (64,32768,0xffffffff):assert goal(i)[0]==0
 # Assembled causal control, same births/physics/stores/ticks, only recall disabled.
 source=(root/'src/ai/aircraft.asm').read_text();control=source.replace('air_strike_goal:\n','air_strike_goal:\n xor eax,eax\n ret\n',1);assert control!=source
 asm=td/'no_recall.asm';obj=td/'no_recall.o';bad_so=td/'no_recall.so';asm.write_text(control)
 subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(asm),'-o',str(obj)],check=True)
 replacements=[obj if p.name=='src_ai_aircraft.asm.o' else p for p in objects]
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(bad_so),*map(str,replacements),str(root/'build/terrain_probe.o'),'-lm'],check=True)
 good_lib=lib;retry=[]
 for tag,current in [('no_recall',C.CDLL(str(bad_so))),('recall',good_lib)]:
  lib=current;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
  E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');M=(Strike*32768).in_dll(lib,'sim_air_strikes')
  assert lib.sim_init(96,42)==0
  for e in E[:96]:e.hp=0
  for side in (0,1):
   for front in range(3):assert lib.sim_order(side,front,1)==0
  assert lib.sim_waypoint(0,0,7000.,4000.)==0 and lib.sim_waypoint(1,0,1000.,4000.)==0
  for i,x,z,side,role,heading in [(15,3400,4000,0,0,math.pi/2),(31,3000,4000,0,1,math.pi/2),(63,3500,4000,1,1,-math.pi/2),(95,2600,4000,1,1,math.pi/2)]:
   E[i]=Entity(x,z,200,side,3,0,-1,1);speed=(5,7)[role];A[i]=Air(lib.terrain_height(x,z)+(110,140)[role],heading,0,0,speed,role,0,-1,0,(8,180)[role],1,speed*math.sin(heading),0,speed*math.cos(heading),0,1)
  E[32]=Entity(4300,4000,100,1,0,0,-1,1);release=None;death=None;seen=set();travel=0.;at600=None
  for tick in range(1,1501):
   old=(E[15].x,E[15].z);lib.sim_tick();moved=math.dist(old,(E[15].x,E[15].z));assert abs(moved-5)<.001;travel+=moved
   pool=bytes((C.c_ubyte*(512*64)).in_dll(lib,'sim_projectiles'))
   for slot in range(512):
    kind,source_id,generation,active=struct.unpack_from('<I8x3I',pool,slot*64+32)
    if active and (slot,generation) not in seen:
     seen.add((slot,generation))
     if kind==3 and source_id==15 and release is None:release=tick;assert E[32].hp==100
   if not E[32].hp and death is None:death=tick
   if tick==600:at600=[E[15].hp,A[15].ammo,E[32].hp];assert at600[0]<200 and at600[1:]==[8,100] and release is None
  if tag=='no_recall':assert release is None and death is None and A[15].ammo==8
  else:assert release and death and 600<release<death<=1500 and A[15].ammo==7
  retry.append({'policy':tag,'tick600_bomber_hp_stores_ground_hp':at600,'bomb_release_tick':release,'ground_death_tick':death,'travel_m':travel,'bomber_hp':E[15].hp,'remaining_stores':A[15].ammo})
 lib=good_lib;E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');M=(Strike*32768).in_dll(lib,'sim_air_strikes')
 # Actual new generation clears the entire old sidecar and remembered mission.
 E[15].generation+=1;E[15].target=-1;E[32].hp=0;lib.sim_tick();assert bytes(M[15])==bytes(40)
 print(json.dumps({'suite':'air-strike-memory','passed':True,'public_flight_ticks':3092,'staged_retry_and_no_recall_control':retry,'no_recall_source_sha256':hashlib.sha256(control.encode()).hexdigest(),'genuine_surviving_damage_hp':176,'defensive_travel_m':defensive_travel,'initial_ingress':ingress,'hidden_enemy_truth_does_not_change_recall':True,'guards':guards,'new_generation_clears_memory':True,'ABI_and_query_state_preserved':True,'hash_samples':hashes,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Controlled contested retry and no-recall comparison; does not establish universal survival, arbitrary ingress geometry, scale, graphics or network acceptance.','Hidden/malformed fixture writes are separate from genuine public-tick flight.']}))
