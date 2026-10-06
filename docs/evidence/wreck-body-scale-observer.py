#!/usr/bin/env python3
"""Development-only natural-army timing and dynamic route budget observer."""
import ctypes as C,hashlib,json,math,os,pathlib,platform,statistics,sys,time
library=pathlib.Path(sys.argv[1]).resolve();output=pathlib.Path(sys.argv[2]);lib=C.CDLL(str(library))
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
e=(E*32768).in_dll(lib,'sim_entities');m=(C.c_uint*8).in_dll(lib,'wreck_nav_metrics');wc=C.c_uint.in_dll(lib,'sim_wreck_count');alive=(C.c_uint*2).in_dll(lib,'sim_alive')
lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_checksum.restype=C.c_uint64
reports=[]
for units,scenario in ((8192,0),(16384,0),(8192,3)):
 assert lib.sim_init(units,42)==0
 if scenario:assert lib.sim_scenario(scenario)==0
 births=[(x.x,x.z,x.gen,x.kind) for x in e[:units]];samples=[];times=[];peak_wrecks=peak_pending=peak_builds=0
 started=time.monotonic()
 for tick in range(1,901):
  t=time.perf_counter_ns();lib.sim_tick();times.append((time.perf_counter_ns()-t)/1e6)
  peak_wrecks=max(peak_wrecks,wc.value);peak_pending=max(peak_pending,m[0]);peak_builds=max(peak_builds,m[6])
  assert m[0]<=512 and m[6]<=8
  if tick in (30,120,300,600,900):samples.append({'tick':tick,'alive':list(alive),'wrecks':wc.value,'route_metrics':list(m)})
 survivors=moved=0
 for initial,x in zip(births,e[:units]):
  assert math.isfinite(x.x) and math.isfinite(x.z)
  if x.hp and x.gen==initial[2] and x.kind<3:
   survivors+=1;moved+=math.dist(initial[:2],(x.x,x.z))>1
 ordered=sorted(times)
 reports.append({'units_initial':units,'initial_per_side':[units//2]*2,'scenario':'scale-hotspot' if scenario else 'scale-open','ticks':900,'seed':42,'seconds':time.monotonic()-started,'tick_ms_mean':statistics.mean(times),'tick_ms_p95':ordered[math.ceil(.95*len(times))-1],'tick_ms_p99':ordered[math.ceil(.99*len(times))-1],'tick_ms_max':max(times),'peak_pending':peak_pending,'peak_builds_per_tick':peak_builds,'peak_wrecks':peak_wrecks,'final_route_metrics':list(m),'surviving_original_ground':survivors,'surviving_ground_moved_over_1m':moved,'samples':samples,'checksum':f'{lib.sim_checksum():016x}'})
 output.write_text(json.dumps({'suite':'natural-army-wreck-route-timing','passed':True,'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'platform':platform.platform(),'processor':platform.processor(),'cpus_available':len(os.sched_getaffinity(0)),'concurrent_frozen_verification':True,'reports':reports,'limits':['Single-thread actual sim_tick wall times; Python observation is outside each timed call.','Concurrent full and software-GL jobs may affect timings; not isolated target-hardware acceptance.','Natural HP/combat/pose/clock/ordnance remain unchanged by the observer.','Visible, detailed, replicated and audio counts unmeasured in this headless run.','Motion over900ticks is descriptive, not a substitute for original95percent tests.']},indent=2)+'\n')
print(output.read_text())
