#!/usr/bin/env python3
"""Derived end-of-tick marker has no authority hash or future behavior effects."""
import ctypes as C,hashlib,json,pathlib,sys
source=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(source));l.sim_checksum.restype=C.c_uint64
stamp=C.c_uint.in_dll(l,'sim_tick_completed');tick=C.c_uint.in_dll(l,'sim_tick_count');traces=[]
for tamper in (False,True):
 assert l.sim_init(2,47)==0 and stamp.value==tick.value==0
 trace=[]
 for _ in range(100):
  before=l.sim_checksum()
  if tamper:stamp.value=0xffffffff
  assert l.sim_checksum()==before
  l.sim_tick();assert stamp.value==tick.value;trace.append(l.sim_checksum())
 traces.append(trace)
assert traces[0]==traces[1]
before=l.sim_checksum();prior=stamp.value;assert l.sim_init(1,47)==-1 and l.sim_checksum()==before and stamp.value==prior
print(json.dumps({'suite':'derived-completed-tick-publication','passed':True,'actual_tick_pairs':100,'static_marker_tamper_checksum_and_future_independent':True,'invalid_init_preserves_marker':True,'marker_final':stamp.value,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['Derived diagnostic marker, never read by gameplay and excluded from authority hash. Sparse paired100tick replay; physical server movement/cadence remains separate.']}))
