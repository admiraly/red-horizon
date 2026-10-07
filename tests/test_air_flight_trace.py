#!/usr/bin/env python3
"""Public-tick roll/yaw/pitch coupling and untouched stores through edge/corner turns."""
import ctypes as C,hashlib,json,math,sys
path=sys.argv[1];lib=C.CDLL(path);lib.sim_checksum.restype=C.c_uint64
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float),('hp',C.c_uint),('side',C.c_uint),('kind',C.c_uint),('front',C.c_uint),('target',C.c_int),('generation',C.c_uint)]
class Air(C.Structure):
 _fields_=[(n,C.c_float) for n in ('y','heading','pitch','bank','speed')]+[(n,C.c_uint) for n in ('role','mode')]+[('target',C.c_int)]+[(n,C.c_uint) for n in ('cooldown','ammo','generation')]+[(n,C.c_float) for n in ('vx','vy','vz')]+[(n,C.c_uint) for n in ('pass_ticks','flags')]
E=(Entity*32768).in_dll(lib,'sim_entities');A=(Air*32768).in_dll(lib,'sim_aircraft');lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
fixtures=[(6800,6800,math.pi/4),(1200,1200,-3*math.pi/4),(6800,1200,3*math.pi/4),(1200,6800,-math.pi/4),(7300,4000,math.pi/2),(700,4000,-math.pi/2),(4000,7300,0),(4000,700,math.pi)]
def run():
 assert lib.sim_init(96,42)==0
 for e in E[:96]:e.hp=0
 for side in (0,1):
  for front in range(3):assert lib.sim_order(side,front,1)==0
 for j,(x,z,heading) in enumerate(fixtures):
  i=15+j*8;role=j%2;speed=(5,7)[role];E[i]=Entity(x,z,200,0,3,0,-1,1);A[i]=Air(lib.terrain_height(x,z)+(110,140)[role],heading,0,0,speed,role,0,-1,0,(8,180)[role],1,speed*math.sin(heading),0,speed*math.cos(heading),0,1)
 checks=0;maximum_error=0;minimum_edge=8000;hashes=[]
 for tick in range(1,2001):
  previous={15+j*8:(E[15+j*8].x,E[15+j*8].z,A[15+j*8].heading,A[15+j*8].bank,A[15+j*8].y,A[15+j*8].vy) for j in range(8)};lib.sim_tick()
  for j in range(8):
   i=15+j*8;old=previous[i];role=j%2;speed=(5,7)[role]
   assert E[i].hp==200 and A[i].ammo==(8,180)[role]
   assert 0<=E[i].x<=8000 and 0<=E[i].z<=8000,(tick,i,E[i].x,E[i].z)
   assert abs(math.dist((old[0],old[4],old[1]),(E[i].x,A[i].y,E[i].z))-speed)<.001
   assert abs(A[i].vy-old[5])<=(.012002,.024002)[role]
   assert abs(math.sqrt(A[i].vx**2+A[i].vy**2+A[i].vz**2)-speed)<1e-5
   assert abs(A[i].bank-old[3])<=(.060002,.100002)[role]
   yaw=(A[i].heading-old[2]+math.pi)%(2*math.pi)-math.pi;oracle=-.0109*math.tan(A[i].bank)/speed;error=abs(yaw-oracle);maximum_error=max(maximum_error,error)
   assert error<1e-6,(tick,i,yaw,oracle)
   assert abs(yaw)<=(.02501,.04001)[role]
   assert abs(A[i].pitch-math.atan2(A[i].vy,math.hypot(A[i].vx,A[i].vz)))<1e-6
   minimum_edge=min(minimum_edge,E[i].x,E[i].z,8000-E[i].x,8000-E[i].z);checks+=1
  if tick%100==0:hashes.append(f'{lib.sim_checksum():016x}')
 return checks,maximum_error,minimum_edge,hashes
first=run();assert run()==first
print(json.dumps({'suite':'air-flight-trace','passed':True,'public_ticks':4000,'coupled_actor_steps':first[0]*2,'maximum_yaw_equation_error':first[1],'minimum_edge_clearance_m':first[2],'replay_hashes':first[3],'initial_edge_and_corner_births':fixtures,'no_inflight_pose_hp_ammo_clock_writes':True,'library_sha256':hashlib.sha256(open(path,'rb').read()).hexdigest(),'limits':['Controlled eight-aircraft empty-opposition boundary/hold flight; no collision, stall/fuel, graphics or dense performance acceptance.']}))
