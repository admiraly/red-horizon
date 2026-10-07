#!/usr/bin/env python3
"""Exact production sender: fixed MTU, full-ring fairness, four peer cursors."""
import ctypes as C,json,os,pathlib,socket,struct,subprocess,tempfile
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT
R=pathlib.Path(__file__).resolve().parents[1];nasm=os.environ['RED_HORIZON_NASM']
with tempfile.TemporaryDirectory(prefix='rh-crash-stream-')as d:
 td=pathlib.Path(d);objects=[]
 for p in [q for f in ('sim','nav','ai','game')for q in (R/'src'/f).glob('*.asm')]+[R/'tests/probe_air_crash_stream.asm']:
  obj=td/(p.name+'.o');subprocess.run([nasm,'-f','elf64','-I',str(R)+'/',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
 so=td/'stream.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-o',str(so),*objects,'-lm'],check=True);l=C.CDLL(str(so));l.send_air_crashes.argtypes=[C.c_uint,C.c_void_p]
 assert l.sim_init(256,42)==0
 e=(C.c_ubyte*(32768*32)).in_dll(l,'sim_entities');a=(C.c_ubyte*(32768*64)).in_dll(l,'sim_aircraft');pool=(C.c_ubyte*(128*96)).in_dll(l,'sim_air_crashes');cursors=(C.c_uint*4).in_dll(l,'air_crash_cursors')
 # Helper admission fixture only: initially dead matching-generation physical births.
 for i in range(128):
  C.memmove(C.addressof(e)+i*32,struct.pack('<2f6I',4000,4000,0,i%2,3,1,0xffffffff,1),32)
  C.memmove(C.addressof(a)+i*64,struct.pack('<5f2Ii3I3f2I',200,0,0,0,7,i%2,0,-1,0,180,1,0,0,7,0,1),64)
  assert l.air_crash_register(i)==0
 before=bytes(pool);sender=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);receiver=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);receiver.bind(('127.0.0.1',0));receiver.settimeout(1);C.c_int64.in_dll(l,'sock').value=sender.fileno()
 endpoint=C.create_string_buffer(struct.pack('<H',2)+struct.pack('!H',receiver.getsockname()[1])+socket.inet_aton('127.0.0.1')+bytes(8));maximum=0;counts=[]
 try:
  for peer in range(4):
   seen=set()
   for opportunity in range(12):
    l.send_air_crashes(peer,endpoint);packet,_=receiver.recvfrom(1200);h=HEADER.unpack_from(packet);assert h[:4]==(MAGIC,VERSION,SCHEMA,CONTENT) and h[4:6]==(119,peer) and h[8]==len(packet)-40
    assert (len(packet)-40)%100==0 and len(packet)<=1140
    slots=[struct.unpack_from('<I',packet,o)[0] for o in range(40,len(packet),100)];assert len(set(slots))==len(slots)
    for j,slot in enumerate(slots):assert packet[44+j*100:140+j*100]==before[slot*96:(slot+1)*96]
    seen.update(slots);maximum=max(maximum,len(packet))
   assert seen==set(range(128));counts.append(len(seen))
  assert bytes(pool)==before
  # Production tick expiry leaves used tombstones, also streamed globally.
  C.c_uint.in_dll(l,'sim_tick_count').value=1800;l.air_crash_tick();assert C.c_uint.in_dll(l,'sim_air_crash_count').value==0
  l.send_air_crashes(0,endpoint);packet,_=receiver.recvfrom(1200);assert all(struct.unpack_from('<I',packet,o+4+60)[0]==0 for o in range(40,len(packet),100))
  # Virgin registry emits no packet and scans only its fixed128 slots.
  l.air_crash_init();receiver.settimeout(.05);l.send_air_crashes(0,endpoint)
  try:receiver.recvfrom(1200);raise AssertionError('virgin stream emitted')
  except socket.timeout:pass
 finally:sender.close();receiver.close()
 print(json.dumps(dict(suite='air-crash-production-stream',passed=True,max_packet=maximum,peer_recovered_slots=counts,snapshot_opportunities=12,source_readonly=True,tombstone_and_virgin=True,scope='Unchanged production NASM sender over real UDP with helper-admitted initially dead128-record fixture; arbitrary source tick only for standalone expiry gate. Genuine real-time casualty/TTL separately tested.')))
