#!/usr/bin/env python3
"""Meaningful development-only tests of real assembly census reduction (no GL claim).
Usage: python3 tests/test_visibility_reduce.py LIBRARY
The library links census asm + stub authority globals + native GL entry points.
"""
import ctypes as C,json,sys
lib=C.CDLL(sys.argv[1])
lib.visibility_reduce.argtypes=[C.POINTER(C.c_uint32),C.c_uint32]
lib.visibility_reduce.restype=C.c_int
count=C.c_uint32.in_dll(lib,'sim_count')
entities=(C.c_uint32*(32768*8)).in_dll(lib,'sim_entities')
flags=(C.c_uint8*32768).in_dll(lib,'visibility_actor_flags')
keys=['actors','high','low','markers','models','invalid']
def counters():return [C.c_uint32.in_dll(lib,'visibility_'+k).value for k in keys]
def run(words):
 a=(C.c_uint32*len(words))(*words)
 assert lib.visibility_reduce(a,len(a))==0
 return counters()
def code(actor,detail):return (actor+1)|(detail<<16)
count.value=32768
for i in [0,1,2,3,32767]:
 entities[i*8+2]=100;entities[i*8+3]=i%2;entities[i*8+4]=i%4;entities[i*8+7]=1
assert run([0,code(0,1),code(0,1),code(1,2),code(2,3),code(32767,2)])==[4,1,2,1,3,0]
assert flags[0]==1 and flags[1]==2 and flags[2]==4 and flags[32767]==2
# Missing/occluded IDs are not inferred from living authority or submitted geometry.
assert run([code(1,2),0])==[1,0,1,0,1,0]
assert flags[0]==0 and flags[32767]==0
# Each class independent, detailed count is union, actor count always unique.
assert run([code(0,1),code(0,2),code(0,3)])==[1,1,1,1,1,0]
assert flags[0]==7
bad=[1,0x10000,0x40001,0x80000001,code(4,1),0x1ffff]
assert run(bad)==[0,0,0,0,0,len(bad)]
count.value=2
assert run([code(2,3),code(1,2)])==[1,0,1,0,1,1]
for offset,val in [(2,0),(2,0xffffffff),(3,2),(4,4),(7,0)]:
 prior=entities[8+offset];entities[8+offset]=val
 assert run([code(1,1)])==[0,0,0,0,0,1]
 entities[8+offset]=prior
count.value=32769
assert lib.visibility_reduce((C.c_uint32*1)(code(0,1)),1)==-1
count.value=32768
assert lib.visibility_reduce(None,1)==-1 and counters()==[0]*6
assert lib.visibility_reduce(None,3840*2160+1)==-1
assert lib.visibility_reduce(None,0)==0
# Fully saturated readback has bounded storage and deduplicates repeated IDs.
a=(C.c_uint32*(3840*2160))()
a[0]=code(32767,1);a[-1]=code(0,2)
assert lib.visibility_reduce(a,len(a))==0 and counters()==[2,1,1,0,2,0]
print(json.dumps({'suite':'visibility_reduce','passed':True,'maximum_pixel_words':len(a),'duplicate_and_class_union':True,'dead_invalid_stale_rejected':True,'absent_ids_not_inferred':True,'null_and_oversize_bounds':True}))
