#!/usr/bin/env python3
"""Actual UDP adapter: bounded pose-only admission, ordering and body safety."""
import ctypes as C,hashlib,json,pathlib,socket,struct,sys,time
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT
library=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(library));l.net_client_open.argtypes=[C.c_char_p,C.c_uint]
a=(C.c_ubyte*(32768*32)).in_dll(l,'infantry_aims');e=(C.c_ubyte*(32768*32)).in_dll(l,'sim_entities')
l.infantry_aim_pose.argtypes=[C.c_uint]*3
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('127.0.0.1',0));sock.settimeout(1)
def record(i=7,gen=1,observed=10,heading=.4,pitch=.1,flags=7,reserved=(0,0,0)):
 return struct.pack('<3I2f4I',i,gen,observed,heading,pitch,*reserved,flags)
def batch(*rows):return struct.pack('<I',len(rows))+b''.join(rows)
try:
 assert l.net_client_open(b'127.0.0.1',sock.getsockname()[1])==0
 _,address=sock.recvfrom(1200)
 def send(data,tick=10,kind=118):
  sock.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(data),1)+data,address);return l.net_client_poll()
 send(struct.pack('<4I',0,0,64,100),kind=2)
 body=bytes(e);initial=bytes(a)
 invalid=[batch(record(i=64)),batch(record(gen=0)),batch(record(observed=11)),batch(record(observed=2)),batch(record(flags=0)),batch(record(flags=8)),batch(record(reserved=(1,0,0))),batch(record(reserved=(0,1,0))),batch(record(reserved=(0,0,1))),batch(record(heading=float('nan'))),batch(record(pitch=float('inf'))),batch(record(heading=-float('inf'))),batch(record(heading=3.15)),batch(record(pitch=1.58)),batch(record(),record()),batch(record(),record(i=8,gen=0)),struct.pack('<I',33)+record()*33,struct.pack('<I',1),batch(record())[:-1]]
 for data in invalid:
  send(data);assert bytes(a)==initial and bytes(e)==body,'invalid aim batch mutated pose/body'
 send(batch(record()));assert bytes(a[224:256])==record()[4:] and bytes(e)==body
 # Pose can arrive before ordinary body; it never creates a live body itself.
 assert l.infantry_aim_pose(7,10,12)==0
 sparse=struct.pack('<I',1)+struct.pack('<I2f6I',7,100.,100.,100,0,0,0,0xffffffff,1)
 send(sparse,kind=101);assert l.infantry_aim_pose(7,10,8)==7
 body=bytes(e);accepted=bytes(a)
 for row,tick in [(record(observed=9,heading=.8),9),(record(observed=9,heading=.9),11),(record(gen=0),12)]:
  send(batch(row),tick);assert bytes(a)==accepted and bytes(e)==body
 assert l.infantry_aim_pose(7,17,8)==7 and l.infantry_aim_pose(7,18,8)==0
 assert l.infantry_aim_pose(7,21,12)==7 and l.infantry_aim_pose(7,22,12)==0
 for age in (0,13,0xffffffff):assert l.infantry_aim_pose(7,10,age)==0
 send(batch(record(gen=2,observed=9,heading=.8)),9)
 assert struct.unpack_from('<I',a,224)[0]==2 and l.infantry_aim_pose(7,10,12)==0 and bytes(e)==body
 accepted=bytes(a);send(batch(record()),12);assert bytes(a)==accepted
 # A tombstone received through the normal body protocol remains dead.
 dead=bytearray(sparse);struct.pack_into('<I',dead,16,0);struct.pack_into('<I',dead,36,2)
 send(dead,13,101);deadbody=bytes(e)
 send(batch(record(gen=2,observed=14)),14);assert bytes(e)==deadbody and l.infantry_aim_pose(7,14,12)==0
 # Exact full MTU-bound batch validates without body publication.
 send(batch(*(record(i=i,observed=15)for i in range(32))),15)
 assert struct.unpack_from('<I',a,31*32+28)[0]==7 and bytes(e)==deadbody
 l.net_client_close();assert not any(a)
 assert l.net_client_open(b'127.0.0.1',sock.getsockname()[1])==0
 _,address=sock.recvfrom(1200);send(struct.pack('<4I',0,0,64,100),kind=2);send(batch(record()));time.sleep(3.05);l.net_client_poll();assert not any(a)
 print(json.dumps({'suite':'infantry-aim-production-parser','passed':True,'malformed_atomic_batches':len(invalid),'maximum_packet_bytes':1196,'body_never_published_by_pose':True,'generations_ordering_expiry_tombstones_lifecycle':True,'adapter_sha256':hashlib.sha256(library.read_bytes()).hexdigest()}))
finally:l.net_client_close();sock.close()
