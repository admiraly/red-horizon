#!/usr/bin/env python3
"""Development-only actual old/new authority byte comparison, excluding new registry."""
import ctypes as C,hashlib,json,sys
from pathlib import Path
paths=[Path(p).resolve() for p in sys.argv[1:]];assert len(paths)==2
libs=[C.CDLL(str(p)) for p in paths]
for lib in libs:lib.sim_init.argtypes=[C.c_uint,C.c_uint]
rows=[]
for n in (8192,16384):
 arenas={'sim_entities':n*32,'sim_ground_motion':n*32,'sim_aircraft':n*64,'sim_players':4*64,'sim_projectiles':512*64,'sim_shell_ammo':n*4,'sim_shell_cooldown':n*4,'sim_events':256*32,'sim_alive':8,'sim_engaged':4,'sim_projectile_count':4,'sim_event_count':4,'sim_event_sequence':4}
 pointers=[{k:C.addressof(C.c_byte.in_dll(lib,k)) for k in arenas} for lib in libs];trace=hashlib.sha256()
 for lib in libs:assert lib.sim_init(n,42)==0 and lib.sim_scenario(3)==0
 for tick in range(120):
  for lib in libs:lib.sim_tick()
  for name,size in arenas.items():
   actual=[C.string_at(ptr[name],size) for ptr in pointers]
   assert actual[0]==actual[1],(n,tick+1,name)
   trace.update(actual[1])
 rows.append({'units':n,'ticks':120,'seed':42,'scenario':'scale-hotspot','compared_arenas':arenas,'authority_trace_sha256':trace.hexdigest(),'bitwise_equal':True})
print(json.dumps({'scope':'Actual prior accepted and candidate modules, every observed authoritative arena byte equal at every tick; new registry deliberately excluded. No cover/render acceptance.','libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],'cases':rows},indent=2))
