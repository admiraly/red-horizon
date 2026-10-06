#!/usr/bin/env python3
"""Development-only four stationary driver helper cost, including ctypes overhead."""
import ctypes as C,hashlib,json,statistics,sys,time
from pathlib import Path
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class P(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint) for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
rows=[]
for arg in sys.argv[1:]:
 path=Path(arg).resolve();lib=C.CDLL(str(path));lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float;lib.vehicle_tick_player.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float];lib.sim_checksum.restype=C.c_uint64
 lib.sim_init(32,1);entities=(E*32768).in_dll(lib,'sim_entities');players=(P*4).in_dll(lib,'sim_players');V=(C.c_int*4).in_dll(lib,'sim_player_vehicle')
 # Declared initial births only; no position/HP writes after boarding begins.
 for i in range(32):entities[i].x=1000+i*20;entities[i].z=1000
 for i in range(12,16):entities[i].x=3500+(i-12)*30;entities[i].z=2000;entities[i].kind=1;entities[i].side=0;entities[i].hp=400
 lib.ground_init()
 for slot in range(4):
  assert lib.player_join(slot,0)==0;players[slot].x=entities[12+slot].x+6;players[slot].z=2000;players[slot].y=lib.terrain_height(players[slot].x,2000)+1.8
  assert lib.vehicle_enter(slot)==0 and V[slot]==12+slot
 for _ in range(100):
  for slot in range(4):assert lib.vehicle_tick_player(slot,0,0,0)==1
 before=lib.sim_checksum();samples=[]
 for _ in range(10000):
  start=time.perf_counter_ns()
  for slot in range(4):assert lib.vehicle_tick_player(slot,0,0,0)==1
  samples.append((time.perf_counter_ns()-start)/1e6)
 assert lib.sim_checksum()==before
 samples.sort();rows.append({'library':str(path),'library_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'four_driver_groups':len(samples),'actual_driver_helper_calls':40000,'mean_ms':statistics.mean(samples),'p95_ms':samples[9499],'p99_ms':samples[9899],'max_ms':samples[-1],'authority_unchanged':True})
print(json.dumps({'scope':'Four genuinely boarded stationary helpers, includes Python/ctypes overhead; no world tick, graphics, network or hardware acceptance; no optimized-runtime-only overhead inference','results':rows},indent=2))
