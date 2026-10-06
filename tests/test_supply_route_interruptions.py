#!/usr/bin/env python3
"""Production shell interruption and opaque-wall resupply journeys.
Startup fixtures only; subsequent launches/commands/ticks use actual NASM APIs.
No live pose, HP, stock or clock renewal. Original scale acceptance is separate.
"""
import ctypes as C,hashlib,json,math,pathlib,sys,tempfile
source=pathlib.Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='rh-supply-interrupt-')as directory:
 private=pathlib.Path(directory)/'core.so';private.write_bytes(source.read_bytes());l=C.CDLL(str(private))
 l.sim_checksum.restype=C.c_uint64;l.sim_waypoint.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];l.company_control_order.argtypes=[C.c_uint]*3+[C.c_float]*2
 l.projectile_launch.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*3;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float
 class Entity(C.Structure):
  _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
 e=(Entity*32768).in_dll(l,'sim_entities');w=(C.c_uint*262144).in_dll(l,'infantry_weapons');sites=(C.c_float*96).in_dll(l,'sim_sites');depots=(C.c_uint*48).in_dll(l,'depot_ammunition');keys=(C.c_uint*16).in_dll(l,'player_companies');controls=(C.c_ubyte*49152).in_dll(l,'company_controls');waypoints=(C.c_ubyte*48).in_dll(l,'sim_waypoints');ammo=(C.c_uint*32768).in_dll(l,'sim_shell_ammo');cooldown=(C.c_uint*32768).in_dll(l,'sim_shell_cooldown');hazard=C.c_uint.in_dll(l,'hazard_enabled');alive=(C.c_uint*2).in_dll(l,'sim_alive');count=C.c_uint.in_dll(l,'sim_count')
 def pose(i):return e[i].x,e[i].z
 def total():return sum(w[i*8+1]+w[i*8+2]+w[i*8+4]for i in range(count.value))+sum(depots[i*4]for i in range(12))
 def incoming(on):
  assert l.sim_init(32,73)==0;hazard.value=on
  for row in e[:32]:row.hp=0
  e[14].x,e[14].z,e[14].hp,e[14].side,e[14].kind,e[14].front=650,3867,160,1,2,2
  e[16].x,e[16].z,e[16].hp,e[16].side,e[16].kind,e[16].front=900,3900,100,0,0,1
  alive[:]=[1,1];w[129]=12;w[130]=0;w[132]=108;ammo[14]=1;cooldown[14]=1
  for side in (0,1):
   for front in range(3):assert l.sim_order(side,front,1)==0
  assert l.sim_order(0,1,0)==0 and l.sim_waypoint(0,1,900.,4200.)==0
  intent=bytes(waypoints);initial=total();l.sim_tick();assert ammo[14]==1 and cooldown[14]==0
  assert l.projectile_launch(14,2,900.,l.terrain_height(900.,3867.),3867.)==0 and ammo[14]==0
  previous=pose(16);first_danger=None;first_credit=None;expiry=None;samples=[];peak_z=3900.
  for tick in range(2,1401):
   l.sim_tick();current=pose(16);assert math.dist(previous,current)<=.1205;previous=current
   assert total()==initial and bytes(waypoints)==intent and e[16].generation==1 and ammo[14]==0
   danger=l.hazard_entity_goal(16)
   if danger and first_danger is None:first_danger=tick
   if first_danger and not danger and expiry is None:expiry=tick
   if w[134]and first_credit is None:
    first_credit=tick;assert w[134]==90 and depots[16:19]==[11910,90,12000] and math.dist(current,(1000,3900))<=60
   peak_z=max(peak_z,current[1])
   if tick in (8,30,60,120,360,600,1000,1400)or tick==first_credit:samples.append([tick,*current,e[16].hp,danger,w[134]])
  if on:
   assert first_danger==8 and expiry and first_credit==374 and e[16].hp==100
   assert peak_z>3904 and current[1]>4020 and current[0]<940 and w[129]+w[130]==102
  else:assert first_danger is None and first_credit is None and e[16].hp==0 and w[134]==0
  return {'danger_enabled':bool(on),'first_danger_tick':first_danger,'danger_expiry_tick':expiry,'first_credit_tick':first_credit,'final_hp':e[16].hp,'peak_z':peak_z,'samples':samples,'conserved_rounds':initial,'checksum':f'{l.sim_checksum():016x}'}
 control=incoming(0);active=incoming(1);assert incoming(1)==active
 # Closed double-precision slab oracle for the actual canonical solid's body
 # expansion, independent of all runtime terrain query/planner implementations.
 def intersects(a,b,box):
  enter,leave=0.,1.
  for axis in (0,1):
   d=b[axis]-a[axis];lo,hi=box[axis],box[axis+2]
   if d==0:
    if a[axis]<lo or a[axis]>hi:return False
   else:
    near,far=sorted(((lo-a[axis])/d,(hi-a[axis])/d));enter=max(enter,near);leave=min(leave,far)
    if enter>leave:return False
  return True
 assert l.sim_init(2,73)==0
 e[0].x,e[0].z,e[0].front=3970,3900,1;e[1].x,e[1].z=7000,6500
 w[1]=12;w[2]=0;w[4]=108;sites[32]=4030.;sites[33]=3900.
 assert l.player_join(0,1)==0 and l.company_control_order(0,keys[0],0,3970.,4200.)==0
 key=keys[0];intent=bytes(controls[key*32:key*32+32]);initial=total();previous=pose(0);box=(3988-.551,3700-.551,4012+.551,4100+.551);credit=None;min_z=3900.;max_z=3900.;samples=[]
 assert math.dist(previous,(4030,3900))==60 and intersects(previous,(4030,3900),box)
 for tick in range(1,12001):
  l.sim_tick();current=pose(0)
  assert math.dist(previous,current)<=.1206 and not intersects(previous,current,box),(tick,previous,current)
  previous=current;min_z=min(min_z,current[1]);max_z=max(max_z,current[1])
  assert total()==initial and bytes(controls[key*32:key*32+32])==intent and e[0].hp==100 and e[0].generation==1
  if w[6]and credit is None:
   credit=tick;assert tick==3150 and w[6]==90 and depots[16:19]==[11910,90,12000]
   assert math.dist(current,(4030,3900))<=60 and not intersects(current,(4030,3900),box)
  if tick%1000==0 or tick==credit:samples.append([tick,*current,w[6],depots[16]])
  if math.dist(current,(3970,4200))<.01:
   arrival=tick;break
 else:raise AssertionError('body-safe supply/primary journey did not arrive')
 for _ in range(30):l.sim_tick();assert pose(0)==current and w[6]==90
 assert credit and min_z<3700 and max_z>4100 and arrival==6223
 wall={'initial_distance_m':60,'initial_direct_path_opaque':True,'credit_tick':credit,'primary_arrival_tick':arrival,'post_arrival_hold_ticks':30,'minimum_z':min_z,'maximum_z':max_z,'independent_expanded_wall_segment_checks':arrival,'samples':samples,'conserved_rounds':initial,'primary_order_preserved':True}
 print(json.dumps({'suite':'supply-route-hazard-and-wall-outcomes','passed':True,'actual_single_artillery_negative_control':control,'actual_hazard_evasion_then_resupply':active,'active_same_build_replay':True,'opaque_wall_journey':wall,'library_sha256':hashlib.sha256(private.read_bytes()).hexdigest(),'limits':['Sparse independent initial fixtures and one public actual shell launch, then genuine ticks with no live HP/pose/clock/stock renewal.','Terrain fixture declares a depot at a new startup position to exercise an unchanged canonical wall; not streamed-world/site-layout or original-scale acceptance.','No hardware-budget, convoy or wider unit rearm claim.']}))
