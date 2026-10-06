#!/usr/bin/env python3
"""Development synthetic server packets through the real UDP/parser path."""
import ctypes as C,hashlib,json,pathlib,socket,struct,sys,tempfile,time
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT
library=pathlib.Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='rh-own-ammo-faults-')as directory:
 private=pathlib.Path(directory)/'client.so';private.write_bytes(library.read_bytes());l=C.CDLL(str(private))
 l.net_client_open.argtypes=[C.c_char_p,C.c_uint];l.net_player_ammunition_report.argtypes=[C.c_uint,C.c_void_p,C.c_uint];l.sim_checksum.restype=C.c_uint64
 record=(C.c_uint*10).in_dll(l,'net_player_ammunition_record');valid=C.c_uint.in_dll(l,'net_player_ammunition_valid');tick=C.c_uint.in_dll(l,'net_player_ammunition_tick');players=(C.c_uint*64).in_dll(l,'sim_players')
 sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('127.0.0.1',0));sock.settimeout(1);foreign=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 try:
  assert l.net_client_open(b'127.0.0.1',sock.getsockname()[1])==0
  _,destination=sock.recvfrom(1200)
  def send(payload,kind=110,stamp=10,overrides=None,sender=None):
   header=[MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,stamp,len(payload),1]
   for i,value in (overrides or {}).items():header[i]=value
   (sender or sock).sendto(HEADER.pack(*header)+payload,destination);l.net_client_poll()
  send(struct.pack('<4I',0,0,8192,100),kind=2,stamp=0)
  row=[0,1,30,90,0,0,0,120,1,0];payload=struct.pack('<10I',*row);rejected=0
  cases=[payload[:-1],payload+b'X']
  for field,value in ((0,1),(1,0),(2,31),(3,91),(4,1),(4,144121),(5,144001),(6,1),(7,0),(8,2),(9,1)):
   bad=row.copy();bad[field]=value;cases.append(struct.pack('<10I',*bad))
  for bad in cases:
   before=(tuple(record),valid.value,tick.value,l.sim_checksum());send(bad);assert (tuple(record),valid.value,tick.value,l.sim_checksum())==before;rejected+=1
  for field,value in ((0,MAGIC^1),(1,VERSION-1),(2,SCHEMA^1),(3,CONTENT^1),(5,1),(9,2),(8,39)):
   before=(tuple(record),valid.value,tick.value,l.sim_checksum());send(payload,overrides={field:value});assert (tuple(record),valid.value,tick.value,l.sim_checksum())==before;rejected+=1
  send(payload,sender=foreign);assert not valid.value;rejected+=1
  send(payload);assert tuple(record)==tuple(row)and valid.value==1 and tick.value==10
  # Explicit static corroborating snapshot fixture, no gameplay trace claim.
  players[5]=100;players[6]=30;players[10]=0;players[11]=1;players[15]=1
  out=(C.c_uint*10)();assert l.net_player_ammunition_report(0,out,40)==0 and tuple(out)==tuple(row)
  for stamp in (9,10):send(payload,stamp=stamp);assert tick.value==10
  newer=row.copy();newer[1]=2;send(struct.pack('<10I',*newer),stamp=11);assert record[1]==2
  send(payload,stamp=12);assert record[1]==2 and tick.value==11
  unknown=[0,2,0,0,0,0,0,0,0,0];send(struct.pack('<10I',*unknown),stamp=12);assert tuple(record)==tuple(unknown)
  l.net_client_close();assert tuple(record)==(0,)*10 and valid.value==tick.value==0
  assert l.net_client_open(b'127.0.0.1',sock.getsockname()[1])==0
  # Drain any previous ACK; select the genuine new HELLO.
  while True:
   packet,destination=sock.recvfrom(1200)
   if HEADER.unpack_from(packet)[4]==1:break
  send(struct.pack('<4I',0,0,8192,100),kind=2,stamp=0);send(payload)
  assert valid.value==1;time.sleep(3.05);l.net_client_poll();assert not valid.value and not any(record)and tick.value==0
  print(json.dumps({'suite':'player-ammunition-real-udp-parser-faults','passed':True,'rejected_actual_udp_packets':rejected,'atomic_failure_authority_checksum':True,'wrong_endpoint_session_recipient_schema_content_length':True,'stale_equal_and_old_body_rejected':True,'explicit_unknown':True,'close_reconnect_real_timeout_clear':True,'adapter_sha256':hashlib.sha256(private.read_bytes()).hexdigest(),'limits':['Synthetic server packets and a declared static corroborating body fixture; genuine server firing/deployment and GL are separate.']}))
 finally:l.net_client_close();sock.close();foreign.close()
