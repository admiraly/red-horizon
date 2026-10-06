#!/usr/bin/env python3
"""Defend physical perimeter and rear artillery with unchanged movement rules.
Declared initial cohorts only; no live pose/HP/stores/tick renewal in traces.
"""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
with tempfile.TemporaryDirectory(prefix='rh-defend-')as name:
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
 def expected(i,kind,x=2000.,z=1300.):
  x=max(480.,min(7520.,x));z=max(480.,min(7520.,z));row=(i&127)>>3;col=i&7
  if kind==2:return x-240.-row*12,z+(col-3.5)*12
  angle=col*math.pi/4;radius=24.+row*12
  return x+radius*math.cos(angle),z+radius*math.sin(angle)
 def setup(x=2000.,z=1300.,enemy=False):
  assert l.sim_init(256,42)==0;l.player_init()
  for i in range(256):struct.pack_into('<I',E,i*32+8,0)
  for i in range(1,17):
   kind=0 if i<13 else (1 if i<15 else 2);gx,gz=expected(i,kind,x,z)
   struct.pack_into('<2f6I',E,i*32,gx+4,gz,100 if kind==0 else(400 if kind==1 else 160),0,kind,0,0xffffffff,11)
  if enemy:
   # Declared initial enemies are within visible rifle range, never refreshed.
   for i in range(129,133):struct.pack_into('<2f6I',E,i*32,2060.+(i-129)*5,1300.,100,1,0,0,0xffffffff,11)
  l.projectile_init() # Correct finite role stocks at declared birth, before any tick.
  assert l.player_join(0,0)==0;l.company_release(0)
  struct.pack_into('<fff',P,0,2000.,18.,1300.)
  assert l.company_assign(0,0)>=0;key=l.company_for_player(0);assert key==0
  assert l.company_control_order(0,key,4,x,z)==0
  return key
 def physical():
  key=setup();goals=[point(i)[1]for i in range(1,17)]
  assert len(set(goals))==16
  for i,g in enumerate(goals,1):assert math.dist(g,expected(i,entity(i)[4]))<.001
  initial={i:entity(i)[:2]for i in range(1,17)};max_steps={0:0.,1:0.,2:0.};hashes=[]
  for tick in range(240):
   prev={i:entity(i)[:2]for i in initial};l.sim_tick()
   for i in initial:max_steps[entity(i)[4]]=max(max_steps[entity(i)[4]],math.dist(prev[i],entity(i)[:2]))
   if tick%30==29:hashes.append(f'{l.sim_checksum():016x}')
  errors=[math.dist(entity(i)[:2],goals[i-1])for i in initial]
  assert max(errors)<.31,errors
  assert max_steps[0]<.121 and max_steps[1]<.501 and max_steps[2]<.201,max_steps
  for i in initial:
   for j in initial:
    if j>i:assert math.dist(entity(i)[:2],entity(j)[:2])>7
  assert struct.unpack_from('<2f',D,key*32+16)==(2000.,1300.)
  assert l.player_input(0,.1,0.,1.5,0.,0)==0;l.sim_tick()
  assert [point(i)[1]for i in initial]==goals,'defense anchor drifted with owner'
  return {'goals':goals,'maximum_steps_by_role':max_steps,'arrival_errors_m':errors,'hashes':hashes}
 trace=physical();assert physical()==trace
 setup(4030.,1300.);assert point(4)==(0,(3982.,1300.)),point(4)
 projected=[point(i)for i in range(1,17)]
 assert all(rc==1 or l.terrain_body_blocked(entity(i)[4],C.c_float(g[0]),C.c_float(g[1]))==0 for i,(rc,g)in enumerate(projected,1))
 setup(5702.,5230.);assert point(15)[0]==1,'steep artillery placement must hold'
 # Real hostile artillery launch, declared once before encounter. No projectile
 # fabrication or live updates: finite source stock is consumed by assembly.
 setup();gx,gz=expected(1,0)
 struct.pack_into('<2f6I',E,129*32,gx+280.,gz,160,1,2,0,0xffffffff,11)
 l.projectile_init();ammo=(C.c_uint*32768).in_dll(l,'sim_shell_ammo');ammo[129]=1
 l.projectile_launch.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float,C.c_float]
 l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float
 assert l.projectile_launch(129,2,gx,l.terrain_height(gx,gz),gz)==0 and ammo[129]==0
 initial=entity(1)[:2];defense=point(1)[1];hazards=(C.c_ubyte*(32768*32)).in_dll(l,'hazard_states');hazard_observed=False;departure=0.
 for _ in range(60):
  prior=entity(1)[:2];l.sim_tick()
  if entity(1)[2]:assert math.dist(prior,entity(1)[:2])<.121
  if struct.unpack_from('<I',hazards,1*32+4)[0]:hazard_observed=True
  departure=max(departure,math.dist(entity(1)[:2],defense))
 assert hazard_observed and departure>5,('defend ignored incoming shell',hazard_observed,departure)
 assert point(1)[0] in (0,-1) and ammo[129]==0
 hazard_report={'actual_hostile_launch_consumed_one_round':True,'hazard_observed':hazard_observed,'maximum_defense_departure_m':departure,'defender_HP_after':entity(1)[2]}

 edges=[]
 for x,z in [(0.,0.),(8000.,8000.),(0.,8000.),(8000.,0.)]:
  setup(x,z);goals=[point(i)[1]for i in range(1,17)]
  assert all(point(i)[0]==0 for i in range(1,17))
  assert all(0<gx<8000 and 0<gz<8000 for gx,gz in goals)
  assert all(l.terrain_body_blocked(entity(i)[4],C.c_float(g[0]),C.c_float(g[1]))==0 for i,g in enumerate(goals,1))
  edges.append({'requested':[x,z],'goals':goals})
 key=setup();before=l.sim_checksum();assert l.company_control_order(0,key,5,2000.,1300.)==-1 and l.sim_checksum()==before
 P[60:64]=struct.pack('<I',player()[15]+1);assert point(1)[0]==-1
 key=setup();assert l.player_leave(0)==0 and point(1)[0]==-1
 setup(enemy=True);enemy_hp=sum(entity(i)[2]for i in range(129,133));initial_hp=enemy_hp
 for _ in range(120):l.sim_tick()
 enemy_hp=sum(entity(i)[2]for i in range(129,133))
 assert enemy_hp<initial_hp,('defending actors did not damage observed enemies',enemy_hp)
 print(json.dumps({'suite':'company-defend-physical','passed':True,'trace':trace,'edge_cases':edges,
                   'distinct_role_goals':16,'wall_projected_valid_or_hold':True,'steep_artillery_slot_holds':True,'incoming_artillery':hazard_report,'accepted_raw_point_preserved':True,'owner_motion_does_not_move_defense':True,
                   'getter_readonly_ABI':True,'stale_owner_generation_rejected':True,'invalid_mode_atomic':True,
                   'disconnect_restores_autonomy':True,'observed_enemy_HP_before':initial_hp,'observed_enemy_HP_after':enemy_hp,
                   'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),
                   'limits':['Declared initial mixed cohort only; normal physical ticks with no live pose/HP/ammo/clock renewal.',
                             'Fixed formation with bounded westward projection; dynamic defensive cover selection and global route success not established.',
                             'UDP, UI, scale and hardware acceptance require separate evidence.']}))
