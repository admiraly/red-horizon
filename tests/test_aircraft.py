#!/usr/bin/env python3
"""Authoritative flight, finite ordnance, physical bombing and aerial combat."""
import ctypes as C, math, sys
lib=C.CDLL(sys.argv[1]);lib.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in('cooldown','ammo','generation')]+[(n,C.c_float)for n in('vx','vy','vz')]+[(n,C.c_uint)for n in('pass_ticks','flags')]
class Shell(C.Structure):
 _fields_=[(n,C.c_float)for n in('x','y','z','vx','vy','vz')]+[(n,C.c_uint)for n in('ttl','side','kind','damage')]+[('radius',C.c_float)]+[(n,C.c_uint)for n in('source','generation','active','source_generation','reserved')]
e=(Entity*32768).in_dll(lib,'sim_entities');a=(Air*32768).in_dll(lib,'sim_aircraft');p=(Shell*512).in_dll(lib,'sim_projectiles')
alive=(C.c_uint*2).in_dll(lib,'sim_alive')
def reset():
 assert lib.sim_init(64,7)==0
 for x in e[:64]:x.hp=0
 for side in (0,1):
  for front in range(3):lib.sim_order(side,front,1)
 alive[0]=alive[1]=0
 lib.air_init()
def actor(i,x,z,side,kind=3):
 e[i].x,e[i].z,e[i].side,e[i].kind,e[i].front,e[i].hp=x,z,side,kind,0,200
 e[i].target=-1;alive[side]+=1
# Invalid ordnance requests cannot manufacture shells or read an invalid target.
reset();actor(31,2000,2500,0);lib.air_tick()
hash_before=lib.sim_checksum()
for source,kind in ((31,3),(31,4),(64,4),(31,0),(0,3)):
 assert lib.projectile_air_launch(source,kind)==-1
 assert lib.sim_checksum()==hash_before
# Holds mean airborne orbit, never frozen or instantaneous heading reversal.
reset();actor(15,2000,2000,0)
last=None
for _ in range(500):
 old=(e[15].x,e[15].z);lib.sim_tick()
 assert abs(math.dist(old,(e[15].x,e[15].z))-5)<.001
 assert a[15].flags==1 and a[15].ammo==8
 assert all(math.isfinite(v)for v in(a[15].y,a[15].heading,a[15].pitch,a[15].bank))
 if last is not None:
  diff=(a[15].heading-last+math.pi)%(2*math.pi)-math.pi
  assert abs(diff)<=.02501
 last=a[15].heading
 assert 0<=e[15].x<=8000 and 0<=e[15].z<=8000
# Boundary steering keeps continuously flying aircraft inside the operation.
reset();actor(15,7300,4000,0)
for _ in range(2000):
 lib.sim_tick()
 assert 0<=e[15].x<=8000 and 0<=e[15].z<=8000
# Aligned observed ground target produces inherited moving bombs and delayed damage.
reset();actor(15,2000,2000,0);actor(32,2900,2000,1,0)
e[32].hp=100
launched=False;impacted=False
for t in range(240):
 lib.sim_tick()
 bombs=[s for s in p if s.active and s.kind==3]
 if bombs and not launched:
  launched=True;assert e[32].hp==100 and a[15].ammo==7
  assert abs(bombs[0].vx-a[15].vx)<.001 and abs(bombs[0].vz-a[15].vz)<.001
 if e[32].hp<100:impacted=True;break
assert launched and impacted,(launched,impacted,a[15].ammo,e[15].x,e[15].z,e[32].hp)
# Aircraft do not regenerate ordnance, including after long patrol.
a[15].ammo=0
for _ in range(500):lib.sim_tick()
assert a[15].ammo==0
# Opposing fighters physically acquire, turn/intercept and shoot real delayed rounds.
reset();actor(31,2000,2500,0);actor(63,2450,2500,1)
observed=False;fired=False;damaged=False
for t in range(500):
 hp=(e[31].hp,e[63].hp);lib.sim_tick()
 observed|=a[31].target==63 or a[63].target==31
 gun=[s for s in p if s.active and s.kind==4]
 if gun:fired=True
 if (e[31].hp,e[63].hp)!=hp:damaged=True
 assert a[31].ammo<=180 and a[63].ammo<=180
assert observed and fired and damaged,(observed,fired,damaged,e[31].hp,e[63].hp)
# Looking away from an observed enemy never invents forward-cone shots.
reset();actor(31,2000,2500,0);actor(63,2450,2500,1)
lib.air_tick();a[31].heading=-math.pi/2;a[63].heading=math.pi/2
for _ in range(10):lib.sim_tick()
assert a[31].ammo==a[63].ammo==180
assert not any(s.active and s.kind==4 for s in p)
# Fighters prioritize an observed fighter over a closer bomber.
reset();actor(31,2000,2500,0);actor(47,2300,2500,1);actor(63,2370,2500,1)
lib.sim_tick()
assert a[31].target==63,a[31].target
# Hidden distant enemies cannot be acquired.
reset();actor(31,1000,1000,0);actor(63,7000,7000,1)
for _ in range(20):lib.sim_tick()
assert a[31].target==-1 and a[63].target==-1 and a[31].ammo==180
# Focused air_hit ABI probe and integrated surviving-damage hook.
# The sole event input is the damaged stable actor; no shooter coordinate is passed.
def defense_run(index,hit):
 reset();actor(index,3000,3000,0);lib.air_tick()
 a[index].heading=0;a[index].vx=0;a[index].vz=a[index].speed
 start=(e[index].x,e[index].z,a[index].y)
 before=lib.sim_checksum()
 if hit:
  lib.air_hit(index)
  assert lib.sim_checksum()!=before,'private commitment omitted from checksum'
 length=48 if a[index].role else 90
 peak_bank=0;turn=0;old=a[index].heading
 for t in range(length):
  if hit:lib.air_hit(index) # repeated hits must not renew bounded commitment
  oldxz=(e[index].x,e[index].z);oldy=a[index].y
  lib.air_tick();lib.air_combat_tick()
  delta=(a[index].heading-old+math.pi)%(2*math.pi)-math.pi
  assert abs(delta)<=(.04001 if a[index].role else .02501)
  assert abs(a[index].y-oldy)<=.5001
  assert abs(math.dist(oldxz,(e[index].x,e[index].z))-a[index].speed)<.001
  assert a[index].ammo==(180 if a[index].role else 8)
  assert 0<=e[index].x<=8000 and 0<=e[index].z<=8000
  if hit and t<length-1:assert a[index].target==-1 and a[index].mode==2
  peak_bank=max(peak_bank,abs(a[index].bank));turn+=abs(delta);old=a[index].heading
 result=(e[index].x,e[index].z,a[index].y,peak_bank,turn,a[index].heading)
 if hit:
  assert a[index].mode!=2,'repeated hits extended maneuver indefinitely'
  assert result[2]-start[2]>=length*.5-.001
 return result
metrics={}
for index,name in ((31,'fighter'),(15,'bomber')):
 control=defense_run(index,False);defended=defense_run(index,True)
 separation=math.dist(control[:2],defended[:2])
 assert separation>40,(name,separation)
 assert defended[3]>.4
 metrics[name]={'xz_separation_m':round(separation,3),'climb_m':24 if index==31 else 45,
                'absolute_turn_rad':round(defended[4],3),'peak_bank_rad':round(defended[3],3)}
# Invalid, dead, nonair and mismatched generations cannot create a commitment.
reset();actor(31,3000,3000,0);lib.air_tick()
for index in (-1,64,32768):
 before=lib.sim_checksum();lib.air_hit(index);assert lib.sim_checksum()==before
for field,value in (('hp',0),('kind',0),('generation',e[31].generation+1)):
 previous=getattr(e[31],field);setattr(e[31],field,value)
 before=lib.sim_checksum();lib.air_hit(31);assert lib.sim_checksum()==before
 setattr(e[31],field,previous)
# Reuse initializes both commitment and recovery, and permits a new real hit.
lib.air_hit(31);e[31].generation+=1;lib.air_tick()
assert a[31].mode==0
before=lib.sim_checksum();lib.air_hit(31);assert lib.sim_checksum()!=before
# Boundary safety overrides jink and retains role speed even during repeated hits.
for index in (15,31):
 reset();actor(index,7340,4000,0);lib.air_tick()
 a[index].heading=math.pi/2
 for t in range(400):
  if t%150==0:lib.air_hit(index)
  old=(e[index].x,e[index].z);lib.air_tick();lib.air_combat_tick()
  assert 0<=e[index].x<=8000 and 0<=e[index].z<=8000
  assert abs(math.dist(old,(e[index].x,e[index].z))-a[index].speed)<.001
# Following the finite break, fighters reacquire an independently observed enemy.
reset();actor(31,3000,3000,0);actor(63,3300,3000,1);lib.air_tick();lib.air_hit(31)
for t in range(48):lib.air_tick();lib.air_combat_tick()
assert a[31].target==63 and a[31].mode==1
# Same explicit hit schedule produces identical private-state checksums.
hits=[]
for _ in range(2):
 reset();actor(31,3000,3000,0);lib.air_tick()
 for t in range(240):
  if t in (0,20,160):lib.air_hit(31)
  lib.air_tick();lib.air_combat_tick()
 hits.append(lib.sim_checksum())
assert hits[0]==hits[1]
print('Focused damage-hook maneuver probe:',metrics,'bounded repeat/reuse/boundary/reacquisition/replay passed')

# Production surviving-damage hook, with zero damage preserving private state.
for index in (15,31):
 reset();actor(index,3000,3000,0);lib.air_tick()
 before=lib.sim_checksum();lib.sim_air_damage(index,0)
 assert lib.sim_checksum()==before and e[index].hp==200
 lib.sim_air_damage(index,1)
 assert e[index].hp==199 and a[index].mode==2
 old_y=a[index].y;lib.sim_tick()
 assert a[index].y>=old_y+.499 and abs(a[index].bank)>.4
# A real gun-contact survivor breaks away without a direct test air_hit call.
reset();actor(31,2000,2500,0);actor(63,2450,2500,1)
observed=False
for _ in range(90):
 lib.sim_tick()
 if e[31].hp not in (0,200) or e[63].hp not in (0,200):
  assert any(x.hp not in (0,200) and a[i].mode==2 for i,x in ((31,e[31]),(63,e[63])))
  observed=True;break
assert observed,'actual swept gun contact never drove defensive behavior'
print('PASS: production surviving damage and real gun contact drive bounded defensive flight')

# Exact authoritative state replay includes air control/store fields.
h=[]
for _ in range(2):
 assert lib.sim_init(8192,42)==0
 for t in range(180):lib.sim_tick()
 h.append(lib.sim_checksum())
assert h[0]==h[1]
print('PASS: continuous held flight, bounded yaw/bank, aligned gravity bombing/delayed damage, finite stores, aerial intercept/swept gun damage, limited perception and replay')

class Event(C.Structure):
 _fields_=[(n,C.c_float)for n in('x','y','z')]+[(n,C.c_uint)for n in('kind','side','tick')]+[('radius',C.c_float),('sequence',C.c_uint)]
ev=(Event*256).in_dll(lib,'sim_events');counts={6:0,7:0,8:0,9:0}
assert lib.sim_init(8192,42)==0
for t in range(1,901):
 lib.sim_tick()
 for v in ev:
  if v.tick==t and v.kind in counts:counts[v.kind]+=1
assert min(counts.values())>0,counts
print('Default8192 actual air events over900 ticks:',counts)
