#!/usr/bin/env python3
"""Exclusive four-player ownership, real cohort orders and disconnect autonomy."""
import ctypes as C,json,pathlib,subprocess,tempfile,os,math,hashlib
root=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ.get('RED_HORIZON_NASM',str(root/'.tools/nasm/nasm'))
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Control(C.Structure):
 _fields_=[('owner',C.c_uint),('owner_generation',C.c_uint),('mode',C.c_uint),('ordered',C.c_uint),('x',C.c_float),('z',C.c_float),('sequence',C.c_uint),('tick',C.c_uint)]
class Assignment(C.Structure):
 _fields_=[('key',C.c_uint),('owner_generation',C.c_uint),('lease_serial',C.c_uint),('reserved',C.c_uint)]
with tempfile.TemporaryDirectory(prefix='rh-company-ownership-') as name:
 td=pathlib.Path(name);probe=td/'probe.o';subprocess.run([nasm,'-f','elf64',str(root/'tests/probe_company_control.asm'),'-o',str(probe)],check=True)
 objects=[root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o')for folder in ('sim','nav','ai','game')for p in sorted((root/'src'/folder).glob('*.asm'))]
 terrain=td/'terrain.o';subprocess.run([nasm,'-f','elf64',str(root/'tests/terrain_probe.asm'),'-o',str(terrain)],check=True)
 so=td/'company.so';subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*map(str,objects),str(terrain),str(probe),'-lm'],check=True)
 l=C.CDLL(str(so));l.sim_checksum.restype=C.c_uint64;l.company_control_order.argtypes=[C.c_uint]*3+[C.c_float]*2;l.probe_company_control_goal.argtypes=[C.c_uint,C.c_void_p,C.c_void_p]
 E=(Entity*32768).in_dll(l,'sim_entities');D=(Control*1536).in_dll(l,'company_controls');A=(Assignment*4).in_dll(l,'player_companies');req=(C.c_uint*2).in_dll(l,'sim_requisition');players=(C.c_uint*(4*16)).in_dll(l,'sim_players')
 def goal(i):
  output=C.create_string_buffer(b'Z'*8,8);regs=(C.c_uint64*7)();before=l.sim_checksum();rc=l.probe_company_control_goal(i,output,regs);assert l.sim_checksum()==before
  assert tuple(regs)==tuple(0x123401+j for j in range(6))+(0,)
  if rc!=0:assert output.raw==b'Z'*8
  return rc
 def prepare():
  assert l.sim_init(256,42)==0;l.player_init()
  for e in E[:256]:e.hp=0
  # Distinct genuine initial mixed cohorts. No later pose/health/store renewal.
  for start,x,z,front in [(1,1800,1800,0),(129,2100,1800,0),(33,1800,3900,1),(65,1800,6500,2)]:
   for j in range(16):E[start+j]=Entity(x+(j%8)*4,z+(j//8)*6,100,0,0,front,-1,1)
  for i,front in enumerate((0,1,2,0)):assert l.player_join(i,front)==0
  keys=[l.company_for_player(i)for i in range(4)];assert len(set(keys))==4 and all(0<=key<1536 for key in keys)
  assert keys[0]//256==keys[3]//256==0 and keys[0]!=keys[3]
  return keys
 keys=prepare();before=l.sim_checksum()
 for player,key,mode,x,z in [(0,keys[3],0,2200,1800),(3,keys[0],0,2200,1800),(4,keys[0],0,2200,1800),(0,1536,0,2200,1800),(0,keys[0],3,2200,1800),(0,keys[0],0,math.nan,1800),(0,keys[0],0,2200,math.inf),(0,keys[0],0,-1,1800),(0,keys[0],0,8001,1800),(0,keys[0],0,4000,1300)]:
  assert l.company_control_order(player,key,mode,x,z)<0
  assert l.sim_checksum()==before
 for i in (256,32768,0xffffffff):assert goal(i)==-1
 # Finite shared funds and invalid commands preserve complete ownership/world.
 old=req[0];req[0]=4;before=l.sim_checksum();assert l.company_control_order(0,keys[0],1,1800,1800)==-3 and l.sim_checksum()==before;req[0]=old
 def physical():
  keys=prepare();balance=req[0];assert l.company_control_order(0,keys[0],1,1800,1800)==0
  assert req[0]==balance-5 and D[keys[0]].sequence==1
  balance=req[0];assert l.company_control_order(3,keys[3],0,2200,1800)==0;assert req[0]==balance-5
  assert goal(1)==1 and goal(129)==0
  initial=[(E[i].x,E[i].z)for i in (1,129)];hashes=[]
  for tick in range(1,201):
   l.sim_tick()
   if tick%20==0:hashes.append(f'{l.sim_checksum():016x}')
  moved=[math.dist(start,(E[i].x,E[i].z))for start,i in zip(initial,(1,129))]
  assert moved[0]<.001 and moved[1]>15,(moved,initial)
  lease=A[0].lease_serial;assert l.player_leave(0)==0 and A[0].key==0xffffffff and D[keys[0]].owner==0xffffffff and D[keys[0]].ordered==0
  assert goal(1)==-1 and A[0].lease_serial>lease
  old=(E[1].x,E[1].z)
  for _ in range(120):l.sim_tick()
  recovered=math.dist(old,(E[1].x,E[1].z));assert recovered>1,recovered
  assert l.player_join(0,0)==0 and l.company_for_player(0)>=0 and A[0].owner_generation==players[15]
  return {'assignment_keys':keys,'physical_displacements_m':moved,'disconnected_cohort_autonomous_travel_m':recovered,'hash_samples':hashes}
 first=physical();assert physical()==first
 # Genuine death/redeployment renews only the body-generation binding; same
 # lease/cohort/intent persists and commands remain available while dead.
 keys=prepare();assert l.company_control_order(0,keys[0],1,1800,1800)==0
 original=players[15];serial=A[0].lease_serial;intent=bytes(D[keys[0]])
 players[5]=0;players[9]=1
 assert l.company_control_order(0,keys[0],1,1800,1800)==0
 sequence=D[keys[0]].sequence
 for _ in range(180):
  l.sim_tick()
  if players[15]!=original:break
 assert players[15]==original+1 and l.company_for_player(0)==keys[0]
 assert A[0].lease_serial==serial+1 and D[keys[0]].owner_generation==players[15]
 assert D[keys[0]].sequence==sequence and D[keys[0]].ordered==1 and goal(1)==1
 assert l.company_control_order(0,keys[0],0,2200,1800)==0
 # Genuine generation mismatch rejects stale ownership; fixtures distinct from movement.
 keys=prepare();original=players[15];players[15]+=1;before=l.sim_checksum();assert l.company_for_player(0)==-1 and l.company_control_order(0,keys[0],0,2200,1800)==-2 and l.sim_checksum()==before;players[15]=original
 print(json.dumps({'suite':'company-exclusive-control','passed':True,'physical':first,'public_movement_ticks':640,'all_four_players_assigned':True,'same_front_cohorts_exclusive':True,'invalid_commands_state_preserved':10,'atomic_cost':5,'stale_generation_rejected':True,'disconnect_returns_autonomy':True,'genuine_redeploy_preserves_company_and_intent':True,'goal_ABI_and_hash_preserved':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'limits':['Controlled initial cohorts/API commands; actual UDP/client UI, transfer/assistance, full army scale and full checkpoint remain separate.']}))
