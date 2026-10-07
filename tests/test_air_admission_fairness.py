#!/usr/bin/env python3
"""Production aircraft release allocation, finite stores and physical contacts."""
import argparse, collections, ctypes as C, hashlib, json, math, pathlib
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('library');ap.add_argument('--legacy',action='store_true');ap.add_argument('--report');ap.add_argument('--dense-ticks',type=int,default=120)
args=ap.parse_args()
assert 1<=args.dense_ticks<=10000
lib=C.CDLL(args.library);lib.sim_checksum.restype=C.c_uint64
lib.terrain_height.argtypes=[C.c_float,C.c_float];lib.terrain_height.restype=C.c_float
lib.terrain_los.argtypes=[C.c_float]*6
lib.projectile_launch.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float,C.c_float]
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in('cooldown','ammo','generation')]+[(n,C.c_float)for n in('vx','vy','vz')]+[(n,C.c_uint)for n in('pass_ticks','flags')]
class Shell(C.Structure):
 _fields_=[(n,C.c_float)for n in('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint)for n in('source','generation','active','source_generation','reserved')]
e=(Entity*32768).in_dll(lib,'sim_entities');a=(Air*32768).in_dll(lib,'sim_aircraft');p=(Shell*512).in_dll(lib,'sim_projectiles')
alive=(C.c_uint*2).in_dll(lib,'sim_alive');count=C.c_uint.in_dll(lib,'sim_projectile_count');dropped=C.c_uint.in_dll(lib,'sim_projectile_dropped')
try:enabled=C.c_uint.in_dll(lib,'air_admission_enabled')
except ValueError:enabled=None
if not args.legacy:assert enabled is not None,'candidate policy is not integrated; use --legacy for baseline capture'
def setup(units,role=None,mirror=False,negative=None,preload=0):
 assert lib.sim_init(units,42)==0
 C.c_uint.in_dll(lib,'hazard_enabled').value=0
 if enabled is not None:enabled.value=int(not args.legacy)
 ids=[i for i in range(units)if e[i].kind==3 and (role is None or ((i>>4)&1)==role)]
 originals={i:e[i].side for i in ids}
 targets=[0,units//2]
 keep=set(ids+targets)
 for i in range(units):
  if i not in keep:e[i].hp=0
 for side,t in enumerate(targets):
  e[t].x=(2810.3379,1639.6621)[side];e[t].z=2000;e[t].side=side^mirror;e[t].hp=100;e[t].target=-1
 for i in ids:e[i].x=(2100,2350)[originals[i]];e[i].z=2000
 lib.air_tick() # initialize original roles, finite stores and matching generations
 for i in ids:
  physical=originals[i];x=(2100,2350)[physical];direction=1 if physical==0 else -1
  e[i].x=x;e[i].z=2000;e[i].side=physical^mirror;e[i].front=0
  t=targets[physical^1]
  # Ground target must lie ahead by actual ballistic lead, not a guessed range.
  if not a[i].role:
   tx=x+direction*5*math.sqrt(220/.0109);e[t].x=tx
   a[i].y=lib.terrain_height(tx,2000)+110
   e[i].target=t;a[i].target=t
  else:a[i].y=140
  a[i].heading=direction*math.pi/2;a[i].vx=direction*a[i].speed;a[i].vy=0;a[i].vz=0
  a[i].mode=1;a[i].cooldown=0;a[i].pass_ticks=0
  assert a[i].ammo==(180 if a[i].role else 8) and a[i].flags==1 and a[i].generation==e[i].generation
  if negative=='ammo':a[i].ammo=0
  elif negative=='cooldown':a[i].cooldown=100
  elif negative=='pass':a[i].pass_ticks=100
  elif negative=='behind':a[i].vx*=-1;a[i].heading*=-1
  elif negative=='stale':a[i].generation+=1
  elif negative=='dead':e[i].hp=0
  elif negative=='no-los':
   # Real authored wall blocks below-roof sightlines; source/target heights
   # and bomb lead are development deployment inputs only.
   e[i].x=(3970,4030)[physical];e[i].z=1300;a[i].y=2
   e[t].x=(4030,3970)[physical];e[t].z=1300
 for side in(0,1):alive[side]=sum(bool(e[i].hp)and e[i].side==side for i in keep)
 if preload:
  # Real tank launches reserve ground's416 total-count slots. These sources
  # are original tank actors with finite original64-round shell stores.
  for i in [j for j in range(units) if j%16==13][:preload]:
   assert i not in keep
   e[i].hp=100;e[i].side=0^mirror;e[i].x=e[targets[1]].x-300;e[i].z=2000
   sy=lib.terrain_height(e[i].x,e[i].z)+2
   ty=lib.terrain_height(e[targets[1]].x,e[targets[1]].z)+2
   assert lib.terrain_los(e[i].x,sy,e[i].z,e[targets[1]].x,ty,e[targets[1]].z)
   assert lib.projectile_spawn(i,targets[1])==0
  assert count.value==preload
 return ids

def volley(units,role=None,mirror=False,negative=None,preload=0):
 ids=setup(units,role,mirror,negative,preload);before={i:a[i].ammo for i in ids}
 lib.air_combat_tick()
 launches=collections.Counter();sources=set()
 for s in p:
  if not s.active or s.kind not in(3,4):continue
  assert s.source in before and s.source not in sources;sources.add(s.source)
  assert s.source_generation==e[s.source].generation and s.kind==a[s.source].role+3 and s.side==e[s.source].side
  launches[(s.side,s.kind)]+=1
  if s.kind==3:
   assert abs(s.vx-a[s.source].vx)<.001 and abs(s.vz-a[s.source].vz)<.001
 for i in ids:
  spent=before[i]-a[i].ammo;assert spent==int(i in sources)
  if i in sources:
   assert a[i].cooldown==3
   if not a[i].role:assert a[i].mode==2 and a[i].pass_ticks==210 and a[i].target==-1
  elif negative is None:
   assert a[i].cooldown==a[i].pass_ticks==0 and a[i].target>=0 and a[i].mode==1
 grants=[sum(launches[(side,k)]for k in(3,4))for side in(0,1)]
 groups=[launches[(side,k)]for side in(0,1)for k in(3,4)]
 spent=[sum(before[i]-a[i].ammo for i in ids if e[i].side==side)for side in(0,1)]
 assert grants==spent and count.value==preload+sum(grants)
 eligible=len(ids)
 if negative:
  assert grants==[0,0] and dropped.value==0,(negative,grants,dropped.value)
 else:
  assert sum(grants)==min(eligible,480-preload),(units,role,grants,preload)
  assert dropped.value==max(0,eligible-(480-preload))
  if args.legacy:
   first=min(eligible//2,480-preload);expected=[first,min(eligible//2,480-preload-first)]
   if mirror:expected.reverse()
   assert grants==expected,(grants,expected)
  else:
   assert abs(grants[0]-grants[1])<=1,grants
   if role is None:assert max(groups)-min(groups)<=1,groups
 return {'initialized_entities':units,'initial_living_aircraft':eligible,'role':role,'side_labels_mirrored':bool(mirror),'fixed_physical_deployment':True,'negative':negative,'ground_preload_real_projectiles':preload,'launches_by_side':grants,'launches_by_side_kind':groups,'finite_ammunition_spent':spent,'retained_physical_source_ids':sorted(sources),'pool_count':count.value,'dropped':dropped.value,'checksum':f'{lib.sim_checksum():016x}'}
reports=[]
for units in(16384,32768):
 for role in(None,0,1):
  pair=[]
  for mirror in(False,True):
   row=volley(units,role,mirror);assert volley(units,role,mirror)==row;reports.append(row);pair.append(row)
  assert pair[0]['retained_physical_source_ids']==pair[1]['retained_physical_source_ids'],'labels changed the physical release sequence'
for negative in('ammo','cooldown','pass','behind','stale','dead','no-los'):
 for role in(0,1):reports.append(volley(16384,role,negative=negative))
for mirror in(False,True):reports.append(volley(16384,None,mirror,preload=416))
# At the480 air ceiling the direct/player weapon primitive can still use the
# remaining32 physical slots. These are actual original tank stores, not forged
# retained projectiles. This tests the primitive reservation, not a GUI action.
reserves=[]
for mirror in(False,True):
 volley(16384,None,mirror)
 original_tanks=[i for i in range(16384)if i%16==13][:33]
 ammo=(C.c_uint*32768).in_dll(lib,'sim_shell_ammo')
 cooldown=(C.c_uint*32768).in_dll(lib,'sim_shell_cooldown')
 for i in original_tanks:
  e[i].hp=100;e[i].side=int(mirror);e[i].x=1100;e[i].z=2000
  assert ammo[i]==64 and cooldown[i]==0
 for i in original_tanks[:32]:
  assert lib.projectile_launch(i,1,1400,2,2000)==0
  assert ammo[i]==63 and cooldown[i]==30
 assert count.value==512
 i=original_tanks[-1];prior=dropped.value
 assert lib.projectile_launch(i,1,1400,2,2000)==-1
 assert count.value==512 and ammo[i]==64 and cooldown[i]==0 and dropped.value==prior+1
 reserves.append({'side_labels_mirrored':bool(mirror),'air_count':480,'actual_direct_weapon_launches':32,'physical_pool_count':count.value,'513th_launch_rejected':True})
# Sparse real flight fixtures continue with the production world; no fabricated
# projectile retirement, event, damage or hit callbacks are used.
# Preserve the formerly incidental airborne bomb collision as its own physical
# contact proof. Crossing births are deliberate; no live pose/damage/event writes.
airborne=[]
for replay in range(2):
 ids=setup(64,0);lib.air_combat_tick();born_rounds={i:a[i].ammo for i in ids}
 for tick in range(1,241):
  lib.sim_tick()
  if any(e[i].hp<200 for i in ids):break
 assert [e[i].hp for i in ids]==[60,60] and [e[0].hp,e[32].hp]==[100,100]
 assert all(a[i].ammo==born_rounds[i] for i in ids) and count.value==0
 assert all(s.kind==3 and s.ttl>0 for s in p if s.generation)
 airborne.append({'tick':tick,'actor_ids':ids,'real_bomb_contact_air_hp':[e[i].hp for i in ids],'ground_hp':[e[0].hp,e[32].hp],'remaining_bomb_stores':[a[i].ammo for i in ids],'checksum':f'{lib.sim_checksum():016x}'})
assert airborne[0]==airborne[1]
physical=[]
for role in(0,1):
 traces=[]
 for replay in range(2):
  ids=setup(64,role)
  if role==0:
   # Distinct declared initial lanes isolate ground-contact admission from
   # opposing bombers physically intercepting each other's bombs mid-air.
   # The full-army admission/fairness deployments above remain unchanged.
   for i in ids:
    lane=(1800.,2200.)[e[i].side];target=(32,0)[e[i].side]
    e[i].z=lane;e[target].z=lane
    a[i].y=lib.terrain_height(e[target].x,lane)+110
  initial_hp=[e[i].hp for i in range(64)]
  lib.air_combat_tick();launch_tick=0
  assert count.value and all(e[i].hp==initial_hp[i]for i in range(64))
  damaged=None
  for tick in range(1,241):
   lib.sim_tick()
   victims=([0,32] if role==0 else ids)
   if any(e[i].hp<initial_hp[i]for i in victims):damaged=tick;break
  assert damaged is not None,(role,count.value)
  traces.append({'role':role,'launch_tick':launch_tick,'first_real_damage_tick':damaged,'checksum':f'{lib.sim_checksum():016x}'})
 assert traces[0]==traces[1];physical.append(traces[0])
dense=[]
for mode,name in((2,'scale-front'),(3,'scale-hotspot')):
 traces=[]
 for replay in range(2):
  assert lib.sim_init(8192,42)==0
  if enabled is not None:enabled.value=int(not args.legacy)
  assert lib.sim_scenario(mode)==0
  original_air=[i for i in range(8192)if e[i].kind==3];original_generations={i:e[i].generation for i in original_air}
  previous={};counts=collections.Counter();sources=collections.defaultdict(set);peak=0
  for _ in range(args.dense_ticks):
   lib.sim_tick();peak=max(peak,count.value)
   for slot,s in enumerate(p):
    if not s.active or s.kind not in(3,4)or previous.get(slot)==s.generation:continue
    previous[slot]=s.generation;assert s.source_generation==e[s.source].generation
    counts[(s.side,s.kind)]+=1;sources[(s.side,s.kind)].add(s.source)
  spent=collections.Counter()
  for i in original_air:
   assert e[i].generation==original_generations[i]
   role=(i>>4)&1;initial=180 if role else 8
   assert a[i].generation==e[i].generation and a[i].ammo<=initial
   spent[(e[i].side,role+3)]+=initial-a[i].ammo
  assert all(spent[key]>=value for key,value in counts.items())
  traces.append({'scenario':name,'seed':42,'ticks':args.dense_ticks,'initialized_entities':8192,'initial_living_army':[4096,4096],'retained_new_generations':[counts[(s,k)]for s in(0,1)for k in(3,4)],'distinct_retained_sources':[len(sources[(s,k)])for s in(0,1)for k in(3,4)],'all_actual_launches_from_finite_ammo':[spent[(s,k)]for s in(0,1)for k in(3,4)],'pool_peak':peak,'dropped':dropped.value,'checksum':f'{lib.sim_checksum():016x}'})
 assert traces[0]==traces[1];dense.append(traces[0])
output={'suite':'air-admission-fairness','passed':True,'mode':'legacy-fixed-index'if args.legacy else'fair-acceptance','library_sha256':hashlib.sha256(pathlib.Path(args.library).read_bytes()).hexdigest(),'production_volley_controls':reports,'physical_delayed_contacts':physical,'physical_airborne_bomb_contact':airborne[0],'physical_reservation_controls':reserves,'dense_world_samples':dense,'limits':['allocation fixture deliberately overlaps same-side sources; no crowd/navigation acceptance','direct air_combat_tick isolates readiness from movement and uses production acquisition/alignment/LOS','ground preload uses actual production tank launches with original tank sources','dense samples omit same-tick launch and retirement','no graphics/audio/network/whole-operation acceptance']}
if args.report:pathlib.Path(args.report).write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output));print('PASS: production air release, finite stores, labels-only mirrors, negative controls and delayed contacts')
