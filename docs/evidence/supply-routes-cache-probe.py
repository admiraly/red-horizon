#!/usr/bin/env python3
"""Development-only static cache admission oracle. Pass actual core library."""
import ctypes as C, hashlib, json, pathlib, sys
source=pathlib.Path(sys.argv[1]);lib=C.CDLL(str(source.resolve()));lib.sim_init(4,73)
e=(C.c_uint*262144).in_dll(lib,'sim_entities');m=(C.c_uint*8).in_dll(lib,'nav_metrics')
for actor in (1,2):
 e[actor*8+3]=0;e[actor*8+4]=0;e[actor*8+5]=1
lib.nav_init();lib.nav_entity_goal.argtypes=[C.c_uint,C.c_float,C.c_float];lib.nav_supply_goal.argtypes=[C.c_uint,C.c_uint,C.c_float,C.c_float]
lib.nav_entity_goal(1,900.,4200.);assert m[0]==1
lib.nav_supply_goal(1,4,1000.,3900.);assert m[0]==2
for _ in range(100):
 lib.nav_entity_goal(2,900.,4200.);lib.nav_supply_goal(1,4,1000.,3900.);assert m[0]==2
lib.nav_supply_goal(1,5,1000.,6500.);assert m[0]==3
lib.nav_supply_goal(1,12,1000.,6500.);assert m[0]==3
print(json.dumps({'suite':'supply-route-cache-isolation','passed':True,'ordinary_same_squad_and_site4_supply_requests':2,'repeated_interleaved_calls':200,'distinct_site5_requests':3,'invalid_site_rejected':True,'core_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':'Static navigation query fixture, no physical movement or original scale acceptance.'}))
