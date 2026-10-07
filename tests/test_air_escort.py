#!/usr/bin/env python3
"""Actual public-tick escort flight, perceived threat priority and mission validity."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ.get('RED_HORIZON_NASM','nasm')
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float) for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint) for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint) for n in ('cooldown','ammo','generation')]+[(n,C.c_float) for n in ('vx','vy','vz')]+[(n,C.c_uint) for n in ('pass_ticks','flags')]
class Mission(C.Structure):_fields_=[(n,C.c_uint) for n in ('leader','leader_generation','owner_generation','until')]
with tempfile.TemporaryDirectory(prefix='rh-air-escort-') as name:
 td=pathlib.Path(name);probe=td/'probe.o';subprocess.run([nasm,'-f','elf64','tests/probe_air_escort.asm','-o',str(probe)],cwd=root,check=True)
 objects=[root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o') for folder in ('sim','nav','ai','game') for p in sorted((root/'src'/folder).glob('*.asm'))]
 so=td/'escort.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*map(str,objects),str(root/'build/terrain_probe.o'),str(probe),'-lm'],check=True)
 lib=C.CDLL(str(so));lib.sim_checksum.restype=C.c_uint64;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];lib.probe_air_escort_goal.argtypes=[C.c_uint,C.c_void_p,C.c_void_p]
 E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');M=(Mission*32768).in_dll(lib,'sim_air_escorts')
 def reset():
  assert lib.sim_init(96,42)==0
  for e in E[:96]:e.hp=0
  for side in (0,1):
   for front in range(3):assert lib.sim_order(side,front,1)==0
  assert lib.sim_waypoint(0,0,7000.,4000.)==0 and lib.sim_waypoint(1,0,1000.,4000.)==0
 def plane(i,x,z,side,role,heading=math.pi/2):
  E[i]=Entity(x,z,200,side,3,0,-1,1);speed=(5.,7.)[role];A[i]=Air(lib.terrain_height(x,z)+(110,140)[role],heading,0,0,speed,role,0,-1,0,(8,180)[role],1,speed*math.sin(heading),0,speed*math.cos(heading),0,1)
 def goal(i):
  out=C.create_string_buffer(b'Z'*8,8);regs=(C.c_uint64*7)();before=lib.sim_checksum();rc=lib.probe_air_escort_goal(i,out,regs);assert lib.sim_checksum()==before;assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,)
  if not rc:assert out.raw==b'Z'*8
  return rc,struct.unpack('<2f',out.raw) if rc else None
 def follow_run():
  reset();plane(15,3400,4000,0,0);plane(31,2700,4000,0,1);initial=math.dist((E[15].x,E[15].z),(E[31].x,E[31].z));closest=initial;travel=0.;banks=0;samples=[]
  for tick in range(1,301):
   old=[(E[i].x,A[i].y,E[i].z,A[i].heading,A[i].speed) for i in (15,31)];lib.sim_tick()
   for j,i in enumerate((15,31)):
    moved=math.dist(old[j][:3],(E[i].x,A[i].y,E[i].z));assert abs(moved-A[i].speed)<.001
    assert 5<=A[i].speed<=7 and -(.009002,.012002)[j]<=A[i].speed-old[j][4]<=(.006002,.010002)[j]
    yaw=(A[i].heading-old[j][3]+math.pi)%(2*math.pi)-math.pi;assert abs(yaw)<=(.02501,.04001)[j]
    assert A[i].ammo==(8,180)[j] and E[i].hp==200
    travel+=moved
   banks+=abs(A[31].bank)>.01;closest=min(closest,math.dist((E[15].x,E[15].z),(E[31].x,E[31].z)))
   if tick%30==0:samples.append(f'{lib.sim_checksum():016x}')
  assert M[31].leader==15 and M[31].leader_generation==1 and M[31].owner_generation==1
  assert closest<200 and banks and travel>3500,(closest,banks,travel)
  return {'initial_gap_m':initial,'minimum_gap_m':closest,'travel_m':travel,'banked_ticks':banks,'hashes':samples}
 first=follow_run();assert follow_run()==first
 # Independently computed moving trailing/flank goal, public mission getter.
 rc,out=goal(31);assert rc==1
 expected=(E[15].x-A[15].vx*16+A[15].vz/math.hypot(A[15].vx,A[15].vz)*80,E[15].z-A[15].vz*16-A[15].vx/math.hypot(A[15].vx,A[15].vz)*80)
 assert max(abs(a-b) for a,b in zip(out,expected))<.001,(out,expected)
 # Separate declared climbing-velocity getter fixture: lateral spacing must
 # remain80m rather than contracting with the horizontal/total speed ratio.
 saved_velocity=(A[15].vx,A[15].vy,A[15].vz,A[15].pitch)
 horizontal=math.sqrt(A[15].speed**2-.5**2);old_horizontal=math.hypot(A[15].vx,A[15].vz)
 A[15].vx*=horizontal/old_horizontal;A[15].vz*=horizontal/old_horizontal;A[15].vy=.5;A[15].pitch=math.atan2(.5,horizontal)
 rc,climbing_goal=goal(31);assert rc==1
 trail_center=(E[15].x-A[15].vx*16,E[15].z-A[15].vz*16)
 climbing_lane_width=math.dist(climbing_goal,trail_center)
 assert abs(climbing_lane_width-80)<.001,climbing_lane_width
 A[15].vx,A[15].vy,A[15].vz,A[15].pitch=saved_velocity
 # Corrupt/stale fixture guards are separate from the physical flight trace.
 guards=[]
 for owner,field,bad in [(E[15],'hp',0),(E[15],'hp',60),(E[31],'hp',60),(E[15],'side',1),(E[15],'front',1),(E[15],'generation',2),(A[15],'generation',2),(A[15],'ammo',0),(A[15],'role',1),(A[15],'speed',0),(A[15],'speed',math.inf),(E[31],'generation',2),(A[31],'ammo',0)]:
  old=getattr(owner,field);setattr(owner,field,bad);assert goal(31)[0]==0;setattr(owner,field,old);guards.append(field)
 for i in (96,32768,0xffffffff):assert goal(i)[0]==0
 # Valid mission scores a farther threat near its bomber over a nearer decoy.
 targets=[]
 for flip in (0,1):
  reset();plane(15,3400,4000,0^flip,0);plane(31,2900,4000,0^flip,1);plane(63,3500,4000,1^flip,1,0);plane(95,2700,4400,1^flip,1,0)
  lib.sim_tick();assert M[31].leader==15 and A[31].target==63,(flip,M[31].leader,A[31].target);targets.append(A[31].target)
 # Range recovery:650m spans more than the old adjacent-cell envelope.
 range_targets=[]
 for direction in ((1,0),(-1,0),(0,1),(0,-1)):
  reset();plane(31,3000,4000,0,1,math.atan2(direction[0],direction[1]));plane(63,3000+direction[0]*650,4000+direction[1]*650,1,1,0);lib.sim_tick();assert A[31].target==63;range_targets.append(A[31].target)
 # Source/target separation beyond the original750m cannot be made visible.
 reset();plane(31,3000,4000,0,1,0);plane(63,3800,4000,1,1,0);lib.sim_tick();assert A[31].target==-1
 # Causal spatial control: only restore the old adjacent-cell bounds.
 good_lib=lib;flight_source=(root/'src/ai/aircraft.asm').read_text();narrow=flight_source
 for before,after in [('mov r14d,-AIR_ACQUIRE_CELLS','mov r14d,-1'),('mov r15d,-AIR_ACQUIRE_CELLS','mov r15d,-1'),('cmp r15d,AIR_ACQUIRE_CELLS','cmp r15d,1'),('cmp r14d,AIR_ACQUIRE_CELLS','cmp r14d,1')]:
  assert narrow.count(before)==1;narrow=narrow.replace(before,after,1)
 asm=td/'narrow_air.asm';asm.write_text(narrow);obj=td/'narrow_air.o';subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(asm),'-o',str(obj)],check=True)
 narrow_so=td/'narrow_air.so';narrow_objects=[obj if p.name=='src_ai_aircraft.asm.o' else p for p in objects];subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(narrow_so),*map(str,narrow_objects),str(root/'build/terrain_probe.o'),'-lm'],check=True)
 lib=C.CDLL(str(narrow_so));lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
 E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');M=(Mission*32768).in_dll(lib,'sim_air_escorts')
 for direction in ((1,0),(-1,0),(0,1),(0,-1)):
  reset();plane(31,3000,4000,0,1,math.atan2(direction[0],direction[1]));plane(63,3000+direction[0]*650,4000+direction[1]*650,1,1,0);lib.sim_tick();assert A[31].target==-1
 lib=good_lib;E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');M=(Mission*32768).in_dll(lib,'sim_air_escorts')
 # Actual contested bomber run; only declared births precede public ticks.
 # Both candidates start inside the pilot view: decoy447m at116.6degrees
 # is nearer than threat600m, but806m from the bomber, outside its750m
 # protected-threat radius. The old directly rear decoy is now unseen.
 # Fixed forward cannon removes the old incidental vertical auto-aim damage.
 # Keep these original full-180-round births and causal priority/damage gates;
 # damaged-bomber abort/retry is separately exercised by test_air_strike.
 # Priority-disabled NASM control keeps all planes, stores and physical limits.
 source=(root/'src/ai/air_escort.asm').read_text();bad_source=source.replace('air_escort_threat:\n','air_escort_threat:\n xor eax,eax\n ret\n',1)
 asm=td/'no_priority.asm';asm.write_text(bad_source);obj=td/'no_priority.o';subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(asm),'-o',str(obj)],check=True)
 bad_so=td/'no_priority.so';bad_objects=[obj if p.name=='src_ai_air_escort.asm.o' else p for p in objects];subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(bad_so),*map(str,bad_objects),str(root/'build/terrain_probe.o'),'-lm'],check=True)
 good_lib=lib;combat=[];bank_physics=hasattr(good_lib,'air_bank_step');combat_limit=1500 if bank_physics else 600
 for tag,current in [('no_priority',C.CDLL(str(bad_so))),('escort',good_lib)]:
  lib=current;lib.sim_checksum.restype=C.c_uint64;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
  E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');M=(Mission*32768).in_dll(lib,'sim_air_escorts')
  reset();plane(15,3400,4000,0,0);plane(31,2900,4000,0,1);plane(63,3500,4000,1,1,-math.pi/2);plane(95,2700,4400,1,1);E[32]=Entity(4300,4000,100,1,0,0,-1,1)
  tick600=None;first_target=None;bomb_release=None;ground_death=None;gun_sources=set();shell_generations=set()
  for tick in range(1,combat_limit+1):
   lib.sim_tick()
   if tick==1:first_target=A[31].target
   pool=bytes((C.c_ubyte*(512*64)).in_dll(lib,'sim_projectiles'))
   for slot in range(512):
    ttl,side,kind,damage,radius,source_id,generation,active=struct.unpack_from('<4If3I',pool,slot*64+24)
    if active and (slot,generation) not in shell_generations:
     shell_generations.add((slot,generation))
     if kind==4:gun_sources.add(source_id)
     if kind==3 and source_id==15 and bomb_release is None:bomb_release=tick;assert E[32].hp==100
   if not E[32].hp and ground_death is None:ground_death=tick
   assert A[15].ammo<=8 and all(A[i].ammo<=180 for i in (31,63,95))
   if tick==600:
    tick600={'bomber_hp':E[15].hp,'bomber_ammo':A[15].ammo,'bomb_release_tick':bomb_release,'ground_death_tick':ground_death}

  assert bomb_release and ground_death and ground_death>bomb_release and gun_sources,(tag,E[15].hp,A[15].ammo,bomb_release,ground_death,sorted(gun_sources))
  combat.append({'policy':tag,'tick600':tick600,'first_fighter_target':first_target,'bomber_hp':E[15].hp,'bomber_ammo':A[15].ammo,'escort_hp':E[31].hp,'escort_ammo':A[31].ammo,'protected_threat_hp':E[63].hp,'bomb_release_tick':bomb_release,'ground_death_tick':ground_death,'actual_gun_sources':sorted(gun_sources)})
 assert combat[0]['first_fighter_target']==95 and combat[1]['first_fighter_target']==63,combat
 assert combat[1]['protected_threat_hp']<combat[0]['protected_threat_hp'],combat
 print(json.dumps({'suite':'air-escort','passed':True,'physical_public_ticks':600+2*combat_limit,'contested_tick_limit':combat_limit,'first_pass_abort_required':False,'contested_bombing_and_priority_control':combat,'negative_control_source_sha256':hashlib.sha256(bad_source.encode()).hexdigest(),'follow':first,'climbing_lane_width_m':climbing_lane_width,'side_label_priority_targets':targets,'full_range_targets':range_targets,'old_adjacent_cell_control_misses':4,'narrow_control_source_sha256':hashlib.sha256(narrow.encode()).hexdigest(),'original_out_of_range_rejected':True,'generation_role_side_front_ammo_guards':guards,'query_ABI_and_authority_unchanged':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'escort_source_sha256':hashlib.sha256((root/'src/ai/air_escort.asm').read_bytes()).hexdigest(),'limits':['Controlled following and contested one-bomber/two-enemy-fighter run; priority control proves threat selection and damage, not universal bomber survival or timed company support.','Initial births only during physical traces; stale/corrupt getter fixtures are distinct.','No graphics/UDP/performance/full-game acceptance.']}))
