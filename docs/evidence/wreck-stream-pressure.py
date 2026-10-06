#!/usr/bin/env python3
"""Development-only full-ring serializer pressure fixture; not combat acceptance."""
import ctypes as C,hashlib,json,os,pathlib,signal,struct,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tests'))
from test_coop import server_addresses
from wreck_stream_observer import RecordingPeer as Peer
server=pathlib.Path(sys.argv[1]).resolve();library=pathlib.Path(sys.argv[2]).resolve();lib=C.CDLL(str(library));lib.wreck_receive.argtypes=[C.c_void_p,C.c_uint,C.c_uint];cache=(C.c_ubyte*65536).in_dll(lib,'net_wrecks');lib.wreck_remote_reset()
host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','450'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peer=None;memory=None
try:
 ready=json.loads(host.stdout.readline());symbols={s[2]:int(s[0],16) for line in subprocess.check_output(['nm','-g','--defined-only',str(server)],text=True).splitlines() if len(s:=line.split())==3};addresses=server_addresses(host,server);base=addresses['sim_entities']-symbols['sim_entities'];memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
 os.kill(host.pid,signal.SIGSTOP)
 try:
  # Canonical protocol-state pressure, explicitly synthetic registry rows.
  # No actor health, position, motion or clock is written or refreshed.
  raw=b''.join(struct.pack('<6f10I',100+i%32*200,30,100+i//32*200,0,0,0,1+i%2,i%2,i,1,0,1800,i+1,1,0,0) for i in range(1024))
  os.pwrite(memory,raw,base+symbols['sim_wrecks']);os.pwrite(memory,struct.pack('<I',1024),base+symbols['sim_wreck_count']);os.pwrite(memory,struct.pack('<I',1024),base+symbols['sim_wreck_sequence'])
 finally:os.kill(host.pid,signal.SIGCONT)
 peer=Peer(('127.0.0.1',ready['port']));assert peer.request(1)[0]==0
 seen=set();packets=0;maxbytes=0;captured=[];nextinput=0;deadline=time.monotonic()+10
 while len(seen)<1024 and time.monotonic()<deadline:
  if time.monotonic()>=nextinput:peer.input();nextinput=time.monotonic()+.3
  row=peer.receive(.02)
  if not row or row[0][4]!=106:continue
  h,payload=row;assert len(payload)==17*68;indices=[struct.unpack_from('<I',payload,i)[0] for i in range(0,len(payload),68)];assert len(indices)==len(set(indices));seen.update(indices);captured.append((h[7],payload));packets+=1;maxbytes=max(maxbytes,len(payload)+40)
  data=C.create_string_buffer(payload);assert lib.wreck_receive(data,len(payload),h[7])>=0
 assert len(seen)==1024 and packets<=61,(len(seen),packets)
 saved=bytes(cache)
 for tick,payload in reversed(captured):
  data=C.create_string_buffer(payload);assert lib.wreck_receive(data,len(payload),tick)>=0
 assert bytes(cache)==saved
 print(json.dumps({'suite':'wreck-full-ring-stream-pressure','passed':True,'simulated_units':8192,'synthetic_canonical_wreck_slots':1024,'snapshot_packets_to_cover_all_slots':packets,'records_per_packet':17,'max_packet_bytes':maxbytes,'authentic_serializer_payload_reorder_preserved_cache':True,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'adapter_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'scope':'Actual server serializer+client cache under explicitly synthetic full-ring protocol-state pressure. No entity health/pose/motion/clock writes. Does not establish1024natural casualties, gameplay cover, rendering budgets or loss-completion latency.'}))
finally:
 if peer:peer.socket.close()
 if memory is not None:os.close(memory)
 if host.poll() is None:
  host.terminate()
  try:host.wait(timeout=3)
  except subprocess.TimeoutExpired:host.kill();host.wait(timeout=3)
