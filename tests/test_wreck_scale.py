#!/usr/bin/env python3
"""Census genuine vehicle casualties/registry state in unchanged massive combat."""
import argparse,ctypes as C,hashlib,json,time,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('library');p.add_argument('--ticks',type=int,default=120);a=p.parse_args();path=Path(a.library).resolve();lib=C.CDLL(str(path))
class E(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
entities=(E*32768).in_dll(lib,'sim_entities');wrecks=(W*1024).in_dll(lib,'sim_wrecks');count=C.c_uint.in_dll(lib,'sim_wreck_count');seq=C.c_uint.in_dll(lib,'sim_wreck_sequence');lib.sim_init.argtypes=[C.c_uint,C.c_uint];lib.sim_checksum.restype=C.c_uint64
rows=[]
assert 1<=a.ticks<1800
for n in (8192,16384):
 assert lib.sim_init(n,42)==0 and lib.sim_scenario(3)==0
 hp0=sum(e.hp for e in entities[:n]);ids=[i for i in range(n) if entities[i].kind in (1,2)];deaths={};samples=[];max_count=0
 for tick in range(1,a.ticks+1):
  old=[(i,entities[i].hp,entities[i].generation) for i in ids if entities[i].hp]
  start=time.perf_counter_ns();lib.sim_tick();samples.append((time.perf_counter_ns()-start)/1e6)
  for i,hp,g in old:
   e=entities[i]
   if not e.hp and e.generation==g:deaths[i]=(tick,g,e.x,e.z,e.kind,e.side)
  assert seq.value==len(deaths),(n,tick,'casualty registration mismatch',seq.value,len(deaths))
  assert count.value==min(seq.value,1024)
  current=[w for w in wrecks if w.flags&1];assert len(current)==count.value;max_count=max(max_count,count.value)
  assert len({(w.entity,w.generation) for w in current})==len(current)
  assert {w.sequence for w in current}==set(range(max(1,seq.value-1023),seq.value+1))
  for w in current:
   assert (w.birth,w.generation,w.x,w.z,w.kind,w.side)==deaths[w.entity]
   assert w.expiry==w.birth+1800 and w.flags in (1,3)
 hp1=sum(e.hp for e in entities[:n]);assert hp1<hp0 and deaths,'real combat casualty fixture is absent'
 rows.append(dict(units=n,ticks=a.ticks,seed=42,scenario='scale-hotspot',initial_ground_vehicles=len(ids),actual_vehicle_deaths=len(deaths),active_wrecks=count.value,peak_wrecks=max_count,retired_wrecks=max(0,len(deaths)-1024),army_hp_before=hp0,army_hp_after=hp1,tick_mean_ms=statistics.mean(samples),tick_p95_ms=sorted(samples)[int(len(samples)*.95)-1],checksum=f'{lib.sim_checksum():016x}'))
print(json.dumps({'suite':'wreck-mass-casualties','passed':True,'cases':rows,'library_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'Actual unchanged8k/16k combat, no HP/motion injections; verifies casualty registration and bounded registry only. Timing includes ctypes and overlaps development; no graphics, cover or network acceptance.'}))
