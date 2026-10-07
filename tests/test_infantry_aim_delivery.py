#!/usr/bin/env python3
"""Real original8192/four endpoints: actual finite NPC event reaches production adapter."""
import ctypes as C,hashlib,json,os,pathlib,signal,struct,subprocess,sys,tempfile,time
from test_coop import Peer
server,library=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:3]);symbols={r[2]:int(r[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(r:=line.split())==3}
with tempfile.TemporaryDirectory(prefix='rh-aim-wire-')as directory:
 private=pathlib.Path(directory)/'adapter.so';private.write_bytes(library.read_bytes());l=C.CDLL(str(private));l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','180'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
 try:
  ready=json.loads(host.stdout.readline());assert l.net_client_open(b'127.0.0.1',ready['port'])==0
  connected=C.c_uint.in_dll(l,'net_connected');deadline=time.monotonic()+5
  while not connected.value and time.monotonic()<deadline:l.net_client_poll();time.sleep(.002)
  assert connected.value
  for _ in range(3):
   peer=Peer(('127.0.0.1',ready['port']));assert peer.request(1)[0]==0;peers.append(peer)
  memory=os.open(f'/proc/{host.pid}/mem',os.O_RDWR);os.kill(host.pid,signal.SIGSTOP);_,status=os.waitpid(host.pid,os.WUNTRACED);assert os.WIFSTOPPED(status)
  try:
   army=bytearray(os.pread(memory,8192*32,symbols['sim_entities']));stocks=os.pread(memory,8192*32,symbols['infantry_weapons']);source=next(i for i in range(8192)if struct.unpack_from('<6I',army,i*32+8)[0]>0 and struct.unpack_from('<6I',army,i*32+8)[1:3]==(1,0) and struct.unpack_from('<I',stocks,i*32+4)[0]>=4);target=next(i for i in range(8192)if struct.unpack_from('<6I',army,i*32+8)[0]>0 and struct.unpack_from('<6I',army,i*32+8)[1:3]==(0,0))
   for i in range(8192):struct.pack_into('<ff',army,i*32,1000. if struct.unpack_from('<I',army,i*32+12)[0]==0 else 7000.,7000.)
   struct.pack_into('<ff',army,source*32,2000.,4000.);struct.pack_into('<ff',army,target*32,2000.,4100.)
   os.pwrite(memory,army,symbols['sim_entities']);os.pwrite(memory,struct.pack('<fff',1950.,17.805,4000.),symbols['sim_players'])
   for slot in range(6):
    os.pwrite(memory,struct.pack('<I',1),symbols['orders']+slot*4);os.pwrite(memory,struct.pack('<I',1),symbols['ai_fronts']+slot*64+24)
   initial=struct.unpack_from('<8I',stocks,source*32)
  finally:os.kill(host.pid,signal.SIGCONT)
  os.close(memory);memory=os.open(f'/proc/{host.pid}/mem',os.O_RDONLY)
  poses=(C.c_ubyte*(32768*32)).in_dll(l,'infantry_aims');seen={};last_input=0;deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   l.net_client_poll()
   for peer in peers:
    for _ in range(12):
     if peer.receive(0)is None:break
   if time.monotonic()-last_input>.1:
    l.net_client_input(0,0,0.,0.,0.,0.)
    for peer in peers:peer.input()
    last_input=time.monotonic()
   row=struct.unpack_from('<2I2f4I',poses,source*32)
   if row[7]&3==3:
    assert row[0]==struct.unpack_from('<I',army,source*32+28)[0]
    assert abs(row[2]+1.57079632679)<1e-5,row
    assert row[4:7]==(0,0,0),'wire leaked last-observed target XYZ'
    seen[row[1]]=row
   if len(seen)>=3:break
   time.sleep(.002)
  assert len(seen)>=3,seen
  final=struct.unpack('<8I',os.pread(memory,32,symbols['infantry_weapons']+source*32));assert final[4]>=initial[4]+1 and final[1]+final[2]+final[4]==120+final[6]
  print(json.dumps({'suite':'actual-infantry-aim-production-udp','passed':True,'units':8192,'endpoints':4,'source':source,'initial_stock':initial,'observed_stock':final,'adapter_poses':list(seen.values()),'no_HP_kind_generation_stores_event_writes':True,'startup_positions_orders_only':True,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'adapter_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'limits':['Actual selected closer human determines heading, not the farther army entity target. No target coordinates travel on the wire; no full latency/bandwidth or remote pixel claim.']}))
 finally:
  if memory is not None:os.close(memory)
  for peer in peers:peer.socket.close()
  l.net_client_close()
  if host.poll()is None:host.terminate()
  host.communicate(timeout=5)
