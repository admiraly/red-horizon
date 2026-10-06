#!/usr/bin/env python3
"""Production join/deploy uses exterior, clear, nonthreatened site positions."""
import ctypes as C,json,math,pathlib,struct,sys
lib=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()));negative='--expect-centre' in sys.argv
entities=(C.c_ubyte*1048576).in_dll(lib,'sim_entities');sites=(C.c_ubyte*384).in_dll(lib,'sim_sites');players=(C.c_ubyte*256).in_dll(lib,'sim_players');alive=(C.c_uint*2).in_dll(lib,'sim_alive')
def fixture():
 assert lib.sim_init(32,42)==0
 for i in range(32):C.c_uint.from_buffer(entities,i*32+8).value=0
 alive[0]=alive[1]=0
 for i in range(12):C.c_uint.from_buffer(sites,i*32+20).value=0
 C.c_uint.from_buffer(sites,20).value=1
 assert struct.unpack_from('<2f',sites)==(1000,1300)
def pos(i):return struct.unpack_from('<3f',players,i*64)
fixture();poses=[]
for i in range(4):
 assert lib.player_join(i,1)==0
 assert C.c_uint.from_buffer(players,i*64+20).value==100
 x,y,z=pos(i)
 if negative:
  assert i==0 and (x,z)==(1000,1300);break
 assert max(abs(x-1000),abs(z-1300))>=80,(i,pos(i))
 for px,py,pz in poses:assert math.hypot(x-px,z-pz)>1.1
 poses.append((x,y,z))
if not negative:
 fixture();C.memmove(C.addressof(entities),struct.pack('<2f6I',900,1300,100,1,0,0,0xffffffff,1),32);alive[1]=1
 assert lib.player_join(0,1)==0
 assert C.c_uint.from_buffer(players,20).value==0 and C.c_uint.from_buffer(players,36).value==30,'unsafe fallback published'
print(json.dumps({'suite':'exterior-site-deployment','passed':True,'negative_centre':negative,'clear_four_player_poses':poses,'unsafe_exterior_candidates_rejected':not negative,'initial_fixture_only':True,'limits':['Authored site-model centres; no full physical building/nav/destruction integration claim.']}))
