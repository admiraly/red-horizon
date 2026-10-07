#!/usr/bin/env python3
"""Every public living aircraft pose at original dense army sizes and hotspots."""
import ctypes as C,hashlib,json,sys,math
lib=C.CDLL(sys.argv[1]);lib.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float)for n in('y','heading','pitch','bank','speed')]+[(n,C.c_uint)for n in('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint)for n in('cooldown','ammo','generation')]+[(n,C.c_float)for n in('vx','vy','vz')]+[(n,C.c_uint)for n in('pass_ticks','flags')]
E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');reports=[]
for count,scenario in [(8192,3),(16384,0)]:
 assert lib.sim_init(count,42)==0
 if scenario:assert lib.sim_scenario(scenario)==0
 ids=[i for i in range(count)if E[i].kind==3];checks=0;minimum_clearance=8000.;hashes=[]
 for tick in range(1,901):
  previous={i:(E[i].x,E[i].z,E[i].generation,A[i].ammo,A[i].y,A[i].vy,A[i].speed)for i in ids};lib.sim_tick()
  for i in ids:
   if not E[i].hp:continue
   assert 0<=E[i].x<=8000 and 0<=E[i].z<=8000,(count,scenario,tick,i,E[i].x,E[i].z)
   assert all(math.isfinite(v)for v in(A[i].y,A[i].heading,A[i].bank,A[i].pitch))
   old=previous[i]
   if tick>1 and E[i].generation==old[2]:
    assert abs(math.dist((old[0],old[4],old[1]),(E[i].x,A[i].y,E[i].z))-A[i].speed)<.001
    assert abs(A[i].vy-old[5])<=(.012002,.024002)[A[i].role]
    assert abs(math.sqrt(A[i].vx**2+A[i].vy**2+A[i].vz**2)-A[i].speed)<1e-5
    assert 5<=A[i].speed<=7 and -(.009,.012)[A[i].role]-.000002<=A[i].speed-old[6]<=(.006,.010)[A[i].role]+.000002
    assert A[i].ammo<=old[3],(count,scenario,tick,i,A[i].ammo,old[3])
   minimum_clearance=min(minimum_clearance,E[i].x,E[i].z,8000-E[i].x,8000-E[i].z);checks+=1
  if tick%100==0:hashes.append(f'{lib.sim_checksum():016x}')
 reports.append({'units':count,'scenario':scenario,'ticks':900,'every_living_aircraft_steps':checks,'minimum_map_clearance_m':minimum_clearance,'hash_samples':hashes})
print(json.dumps({'suite':'air-world-bounds','passed':True,'reports':reports,'library_sha256':hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),'limits':['Actual full army and finite air stores/physical motion; CPU timing, GL/network, separation and unsafe artificial births not established.']}))
