#!/usr/bin/env python3
"""Real dedicated server and assembly client crouch/jump; no state writes."""
import ctypes as C,json,math,pathlib,subprocess,sys,time
from test_coop import Peer,VERSION
server,library=(pathlib.Path(p).resolve() for p in sys.argv[1:3])
lib=C.CDLL(str(library));lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
lib.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
lib.net_client_close.argtypes=[]
players=(C.c_ubyte*256).in_dll(lib,'sim_players')
connected=C.c_uint.in_dll(lib,'net_connected');tick=C.c_uint.in_dll(lib,'net_server_tick')
snapshot_tick=C.c_uint.in_dll(lib,'sim_tick_count');pid=C.c_uint.in_dll(lib,'net_player_id')
def pose():
 import struct
 return struct.unpack_from('<5f11I',players,pid.value*64)
def height(x,z):
 qx,qz=x-4000,z-4000
 return 12+qx*qx*.000001+qz*qz*.0000005+max(0,1-abs(qx)/800)*18
host=subprocess.Popen([str(server),'--port','0','--units','64'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
peer=None
try:
 ready=json.loads(host.stdout.readline());assert ready['protocol']==VERSION
 assert lib.net_client_open(b'127.0.0.1',ready['port'])==0
 end=time.monotonic()+3
 while not connected.value and time.monotonic()<end:lib.net_client_poll();time.sleep(.01)
 assert connected.value
 end=time.monotonic()+3
 while pose()[5]==0 and time.monotonic()<end:
  lib.net_client_poll();lib.net_client_input(0,0,0,0,0,0);time.sleep(.01)
 assert pose()[5]>0,'joined player never received a live authoritative baseline'
 def sample(buttons=0,x=0,z=0,seconds=.5):
  rows=[];end=time.monotonic()+seconds;last=-1
  while time.monotonic()<end:
   assert host.poll() is None
   lib.net_client_poll();lib.net_client_input(0,buttons,x,z,0,0)
   if tick.value!=last:
    last=tick.value;p=pose();assert p[5]>0
    rows.append((last,p[0],p[1],p[2],p[1]-height(p[0],p[2])))
   time.sleep(.01)
  return rows
 base=sample(seconds=.3)[-1];assert abs(base[4]-1.8)<.01
 crouch=sample(32|4,z=1,seconds=.8)
 assert abs(crouch[-1][4]-1.1)<.01
 dx=crouch[-1][1]-crouch[0][1];dz=crouch[-1][3]-crouch[0][3]
 elapsed=(crouch[-1][0]-crouch[0][0])/30
 assert elapsed>0 and 1.9<math.hypot(dx,dz)/elapsed<3.1,'sprint overrode crouch speed'
 sample(seconds=.3)
 jump=sample(64,seconds=1.8)
 assert max(row[4] for row in jump)>3.2,'real server jump never rose'
 assert abs(jump[-1][4]-1.8)<.01,'held jump relaunched or failed landing'
 # Release/repress goes airborne again; crouch+held jump stays grounded.
 sample(seconds=.2);second=sample(64,seconds=.4)
 assert max(row[4] for row in second)>2.8
 sample(seconds=1);blocked=sample(32|64,seconds=.7)
 assert all(abs(row[4]-1.1)<.01 for row in blocked[-3:]),blocked
 assert lib.net_client_input(0,128,0,0,0,0)==-1
 peer=Peer(('127.0.0.1',ready['port']));assert peer.request(1)[0]==0
 assert peer.input(buttons=128)[0]==1
 assert peer.input(buttons=32)[0]==0
 assert snapshot_tick.value==tick.value
 print(json.dumps({'suite':'co-op-player-movement','passed':True,'authority':'actual64actor30Hzdedicatedserver; no fixture writes','crouch_eye':crouch[-1][4],'crouch_metres_per_second':math.hypot(dx,dz)/elapsed,'jump_peak_eye_offset':max(row[4]for row in jump),'held_jump_lands':True,'release_repress_jumps':True,'crouch_blocks_jump':True,'unknown_bits_rejected_adapter_and_server':True,'adapter_tick_matches_server':snapshot_tick.value==tick.value,'max_peer_packet':peer.max_packet}))
finally:
 lib.net_client_close()
 if peer:peer.socket.close()
 if host.poll() is None:host.terminate()
 host.communicate(timeout=5)
