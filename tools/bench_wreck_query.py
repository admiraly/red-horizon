#!/usr/bin/env python3
"""Read-only query-cost probe on naturally produced massive-world casualties."""
import argparse,ctypes as C,hashlib,json,pathlib,statistics,time
p=argparse.ArgumentParser();p.add_argument('library');p.add_argument('--groups',type=int,default=40);a=p.parse_args();assert 1<=a.groups<=1000
path=pathlib.Path(a.library).resolve();lib=C.CDLL(str(path))
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
Wrecks=(W*1024).in_dll(lib,'sim_wrecks');candidates=C.c_uint.in_dll(lib,'wreck_query_candidates');lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_checksum.restype=C.c_uint64;lib.wreck_query.argtypes=[C.c_void_p,C.c_uint]+[C.c_float]*6
out=C.create_string_buffer(24);rows=[]
for population in (8192,16384):
 assert lib.sim_init(population,42)==0 and lib.sim_scenario(3)==0
 for _ in range(120):lib.sim_tick()
 poses=[(w.x,w.y+1,w.z) for w in Wrecks if w.flags&1];before=lib.sim_checksum();samples=[];visits=[]
 for group in range(a.groups):
  start=time.perf_counter_ns()
  for x,y,z in poses:
   assert lib.wreck_query(out,24,x-10,y,z,x+10,y,z)==1;visits.append(candidates.value)
  samples.append((time.perf_counter_ns()-start)/1e6)
 assert lib.sim_checksum()==before
 rows.append({'units':population,'ticks':120,'seed':42,'scenario':'scale-hotspot','wrecks':len(poses),'groups':a.groups,'query_count':len(poses)*a.groups,'group_mean_ms':statistics.mean(samples),'group_p95_ms':sorted(samples)[int(len(samples)*.95)-1],'first_group_ms':samples[0],'mean_query_us':statistics.mean(samples)*1000/len(poses),'peak_candidates':max(visits),'mean_candidates':statistics.mean(visits),'authority_unchanged':True})
print(json.dumps({'suite':'wreck-query-cost','passed':True,'cases':rows,'library_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'Actual natural casualties, first group includes lazy rebuild; Python/ctypes+assert/diagnostic overhead included. Single-thread CPU only; not full cover/movement/server tick or graphics acceptance.'}))
