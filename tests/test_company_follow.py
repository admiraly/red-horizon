#!/usr/bin/env python3
"""Follow current owner with distinct physical slots and unchanged movement rules.
Declared initial cohorts only; no live pose/HP/stores/tick renewal in traces.
"""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
with tempfile.TemporaryDirectory(prefix='rh-follow-')as name:
 td=pathlib.Path(name);probe=td/'probe.o';terrain=td/'terrain.o';so=td/'follow.so'
 for source,dest in [('tests/probe_company_control.asm',probe),('tests/terrain_probe.asm',terrain)]:subprocess.run([nasm,'-f','elf64',str(root/source),'-o',str(dest)],check=True)
 objects=[str(root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o'))for folder in ('sim','nav','ai','game')for p in (root/'src'/folder).glob('*.asm')]
 subprocess.run(['gcc','-shared','-Wl,-Bsymbolic','-o',str(so),*objects,str(probe),str(terrain),'-lm'],check=True)
 l=C.CDLL(str(so));l.sim_checksum.restype=C.c_uint64
 l.company_control_order.argtypes=[C.c_uint]*3+[C.c_float]*2
 l.player_input.argtypes=[C.c_uint,C.c_float,C.c_float,C.c_float,C.c_float,C.c_uint]
 P=(C.c_ubyte*256).in_dll(l,'sim_players');E=(C.c_ubyte*(32768*32)).in_dll(l,'sim_entities')
 A=(C.c_uint*16).in_dll(l,'player_companies');D=(C.c_ubyte*(1536*32)).in_dll(l,'company_controls')
 def player(i=0):return struct.unpack_from('<5f11I',P,i*64)
 def entity(i):return struct.unpack_from('<2f6I',E,i*32)
 def point(i):
  out=C.create_string_buffer(b'Z'*8,8);regs=(C.c_uint64*7)();h=l.sim_checksum()
  rc=l.probe_company_control_goal(i,out,regs)
  assert l.sim_checksum()==h and tuple(regs)==tuple(0x123401+j for j in range(6))+(0,)
  if rc:assert out.raw==b'Z'*8;return rc,None
  return rc,struct.unpack('<2f',out.raw)
 def setup(dead=False,edge=False):
  assert l.sim_init(256,42)==0;l.player_init()
  for i in range(256):struct.pack_into('<I',E,i*32+8,0)
  for i in range(1,17):
   kind=0 if i<13 else (1 if i<15 else 2)
   gx=2000-24-(i>>3)*12;gz=1300+((i&7)-3.5)*12
   struct.pack_into('<2f6I',E,i*32,gx+4,gz,100 if kind==0 else(400 if kind==1 else 160),0,kind,0,0xffffffff,11)
  for i in range(129,137):struct.pack_into('<2f6I',E,i*32,2400+(i-129)*12,3900,100,0,0,1,0xffffffff,11)
  assert l.player_join(0,0)==0 and l.player_join(1,1)==0
  l.company_release(0);l.company_release(1)
  struct.pack_into('<fff',P,0,2000.,18.,1300.)
  struct.pack_into('<fff',P,64,2400.,18.,3900.)
  if dead:struct.pack_into('<I',P,20,0);struct.pack_into('<I',P,36,1)
  assert l.company_assign(0,0)>=0 and l.company_assign(1,1)>=0
  key=l.company_for_player(0);assert key==0 and l.company_for_player(1)==257
  if edge:struct.pack_into('<fff',P,0,0.,18.,8000.)
  assert l.company_control_order(0,key,3,2200.,1800.)==0
  return key
 def physical(mode):
  key=setup()
  if mode==0:assert l.company_control_order(0,key,0,2200.,1800.)==0
  initial={i:entity(i)[:2]for i in range(1,17)};initial_goal=point(1)[1]
  hashes=[];max_steps={0:0.,1:0.,2:0.}
  for tick in range(240):
   # Actual public authoritative movement, with role speeds never altered.
   assert l.player_input(0,.1,0.,0.,0.,0)==0
   previous={i:entity(i)[:2]for i in initial};l.sim_tick()
   for i in initial:
    row=entity(i);max_steps[row[4]]=max(max_steps[row[4]],math.dist(previous[i],row[:2]))
   if tick%30==29:hashes.append(f'{l.sim_checksum():016x}')
  endpoint=player()[:3];goals=[point(i)[1]for i in initial]
  if mode==3:
   assert len(set(goals))==16 and all(point(i)[0]==0 for i in initial)
   assert abs((goals[0][0]-initial_goal[0])-(endpoint[0]-2000))<.01
   assert max(math.dist(entity(i)[:2],goals[i-1])for i in range(1,13))<.3
   assert all(math.dist(initial[i],entity(i)[:2])>15 for i in initial)
   for i in range(1,17):
    for j in range(i+1,17):assert math.dist(entity(i)[:2],entity(j)[:2])>7
  else:assert len(set(goals))==1 and goals[0]==(2200.,1800.)
  assert max_steps[0]<.121 and max_steps[1]<.501 and max_steps[2]<.201,max_steps
  return {'mode':mode,'player_movement_m':endpoint[0]-2000,'actor_travel_m':[math.dist(initial[i],entity(i)[:2])for i in initial],
          'unique_destinations':len(set(goals)),'maximum_steps_by_role':max_steps,'hashes':hashes}
 followed=physical(3);assert physical(3)==followed;fixed=physical(0)
 # Dead/redeployment and invalid-state fixtures are separate from all traces.
 key=setup(dead=True);assert all(point(i)[0]==1 for i in range(1,17))
 generation=player()[15]
 for _ in range(180):
  l.sim_tick()
  if player()[15]!=generation:break
 assert player()[15]==generation+1 and A[1]==player()[15] and struct.unpack_from('<I',D,key*32+8)[0]==3
 assert point(1)[0]==0
 key=setup(edge=True);edge_goals=[point(i)[1]for i in range(1,17)];assert all(0<x<8000 and 0<z<8000 for x,z in edge_goals)
 # Role-sized wall projection; declared initial owner poses precede any ticks.
 key=setup();struct.pack_into('<fff',P,0,4030.,18.,1300.)
 projected=[point(i)for i in range(1,17)]
 assert all(rc==0 for rc,g in projected)
 assert projected[0][1]==(3982.,1270.),projected[0]
 assert all(l.terrain_body_blocked(entity(i)[4],C.c_float(g[0]),C.c_float(g[1]))==0 for i,(rc,g)in enumerate(projected,1))
 # The actual steep western terrain face has no artillery candidate in the
 # bounded48m projection window. Its owner stands safely on the plateau.
 key=setup();struct.pack_into('<fff',P,0,5486.,18.,5230.)
 assert l.terrain_body_blocked(0,C.c_float(5486),C.c_float(5230))==0
 assert point(15)[0]==1
 initial=entity(15)[:2]
 for _ in range(30):l.sim_tick()
 assert math.dist(initial,entity(15)[:2])<.001
 for _ in range(480):
  assert l.player_input(0,.1,0.,0.,0.,0)==0;l.sim_tick()
 assert point(15)[0]==0 and math.dist(initial,entity(15)[:2])>5
 key=setup();aim_goals=[point(i)[1]for i in range(1,17)]
 assert l.player_input(0,0.,0.,1.5,0.,0)==0 and [point(i)[1]for i in range(1,17)]==aim_goals
 key=setup();P[60:64]=struct.pack('<I',player()[15]+1);assert point(1)[0]==-1
 key=setup();struct.pack_into('<f',P,0,math.nan);assert point(1)[0]==1
 key=setup();before_actors=bytes(E[:256*32]);before_bodies=[player(i)for i in range(2)]
 assert l.company_transfer(0,1,0,0)==0 and l.company_transfer(1,0,1,1)==0
 assert bytes(E[:256*32])==before_actors and all(player(i)[:5]==before_bodies[i][:5] and player(i)[15]==before_bodies[i][15] for i in range(2))
 assert [player(i)[10]for i in range(2)]==[1,0]
 goal=point(1)[1];assert abs(goal[0]-(2400-24))<.01 and abs(goal[1]-(3900-30))<.01
 start=entity(1)[:2];initial_error=math.dist(start,goal)
 for _ in range(120):
  prior=entity(1)[:2];l.sim_tick();assert math.dist(prior,entity(1)[:2])<.121
 transferred_travel=math.dist(start,entity(1)[:2]);assert transferred_travel>10 and math.dist(entity(1)[:2],point(1)[1])<initial_error-10
 assert struct.unpack_from('<I',D,key*32+8)[0]==3
 assert l.player_leave(1)==0 and point(1)[0]==-1
 print(json.dumps({'suite':'company-follow-physical','passed':True,'follow':followed,'fixed_waypoint_control':fixed,
                   'distinct_mixed_role_slots':16,'dead_owner_holds_genuine_redeployment_resumes':True,
                   'edge_margin_bounds':True,'mouse_aim_does_not_rotate_formation':True,'role_footprints_project_out_of_wall':True,'blocked_slots_hold_and_recover_after_owner_movement':True,'stale_generation_rejected':True,'invalid_pose_holds':True,
                   'consented_cross_front_transfer_follows_new_owner':True,'transfer_body_and_entity_poses_preserved':True,'transferred_company_travel_m':transferred_travel,'disconnect_restores_autonomy':True,'getter_readonly_ABI':True,
                   'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),
                   'limits':['Controlled declared initial cohorts and own-player public inputs; separate dead/corrupt fixtures.',
                             'Fixed world-axis slots; complex terrain route/traffic, target GPU, full scale/network/UI acceptance are separate.']}))
