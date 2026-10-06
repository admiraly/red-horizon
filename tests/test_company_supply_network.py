#!/usr/bin/env python3
"""Real UDP parser faults plus unmodified8k server/production client supply view."""
import ctypes as C,hashlib,json,pathlib,socket,struct,subprocess,sys,tempfile,time
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT,Peer
library,server=map(lambda s:pathlib.Path(s).resolve(),sys.argv[1:3])
with tempfile.TemporaryDirectory(prefix='rh-supply-udp-') as td:
 private=pathlib.Path(td)/'client.so';private.write_bytes(library.read_bytes());lib=C.CDLL(str(private))
 lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
 lib.net_client_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
 lib.net_supply_report.argtypes=[C.c_uint,C.c_void_p,C.c_uint]
 lib.sim_checksum.restype=C.c_uint64
 remote=(C.c_ubyte*44).in_dll(lib,'net_supply_record');valid=C.c_uint.in_dll(lib,'net_supply_valid');clock=C.c_uint.in_dll(lib,'net_supply_tick')
 players=(C.c_uint*64).in_dll(lib,'sim_players');tick=C.c_uint.in_dll(lib,'sim_tick_count')
 sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('127.0.0.1',0));sock.settimeout(1)
 def report(expected=0):
  out=(C.c_ubyte*56)(*([0xa7]*56));rc=lib.net_supply_report(0,C.byref(out,8),40);assert rc==expected
  if expected:assert bytes(out)==bytes([0xa7]*56);return
  assert bytes(out[:8])+bytes(out[48:])==bytes([0xa7]*16)
  return struct.unpack('<10I',bytes(out[8:48]))
 try:
  assert lib.net_client_open(b'127.0.0.1',sock.getsockname()[1])==0
  _,destination=sock.recvfrom(1200)
  def send(payload,kind=108,stamp=10,**kw):
   h=[MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,stamp,len(payload),1]
   for i,v in kw.items():h[int(i)]=v
   sock.sendto(HEADER.pack(*h)+payload,destination);lib.net_client_poll()
  send(struct.pack('<4I',0,0,8192,100),kind=2,stamp=0)
  row=[1,0,1,19,4,2,1,140,1,0,0];payload=struct.pack('<11I',*row)
  baseline=bytes(remote);authority=lib.sim_checksum();rejected=0
  bad=[payload[:-1],payload+b'X']
  for field,value in ((0,0),(1,1),(2,0),(3,768),(4,129),(5,4),(6,3),(7,151),(7,31),(7,0),(8,5),(9,1),(10,1)):
   r=row.copy();r[field]=value;bad.append(struct.pack('<11I',*r))
  for p in bad:
   send(p);assert bytes(remote)==baseline and not valid.value and lib.sim_checksum()==authority;rejected+=1
  for field,value in ((1,VERSION-1),(2,SCHEMA^1),(3,CONTENT^1),(5,1),(9,2)):
   send(payload,**{str(field):value});assert bytes(remote)==baseline and not valid.value;rejected+=1
  lib.net_supply_receive.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint]
  raw=C.create_string_buffer(payload)
  assert lib.net_supply_receive(raw,44,10,0)==0 and lib.sim_checksum()==authority
  lib.net_supply_reset()
  send(payload);assert bytes(remote)==payload and valid.value==1 and clock.value==10
  assert tick.value==10
  report(-1) # No corroborating player/company metadata.
  rows=[struct.pack('<10I',0,19,1,1,0,0,0,0,0,0)]+[struct.pack('<10I',i,0xffffffff,0,0,0,0,0,0,0,0)for i in range(1,4)]
  send(struct.pack('<I',4)+b''.join(rows)+bytes(192),kind=107)
  players[10]=0;players[11]=1;players[15]=1
  assert report()==tuple(row[1:])
  # Bounded depot packets, exact conservation and state-correlated display.
  depots=(C.c_ubyte*304).in_dll(lib,'net_depot_records');dv=C.c_uint.in_dll(lib,'net_depot_valid');dc=C.c_uint.in_dll(lib,'net_depot_tick')
  site_words=(C.c_uint*96).in_dll(lib,'sim_sites')
  depot_rows=[]
  for i in range(12):
   if site_words[i*8+2]!=0 or site_words[i*8+4]!=1:continue
   flags=1+(2 if site_words[i*8+5]==1 else 0)+(4 if site_words[i*8+7]&4 else 0)+(8 if site_words[i*8+6]==0 else 0)
   if flags==3:flags|=16
   depot_rows.append([i,12000,0,12000,flags,0])
  assert len(depot_rows)==2
  depot_payload=struct.pack('<4I',0,1,2,0)+b''.join(struct.pack('<6I',*r)for r in depot_rows)+bytes(240)
  depot_before=bytes(depots);depot_authority=lib.sim_checksum();depot_bad=[]
  for offset,value in ((0,1),(4,0),(8,13),(12,1),(16,12),(20,12001),(24,1),(28,1),(32,0),(36,1),(40,depot_rows[0][0]),(64,1)):
   b=bytearray(depot_payload);struct.pack_into('<I',b,offset,value);depot_bad.append(bytes(b))
  depot_bad.extend([depot_payload[:-1],depot_payload+b'X'])
  for b in depot_bad:
   send(b,kind=109,stamp=10);assert bytes(depots)==depot_before and not dv.value and lib.sim_checksum()==depot_authority
  send(depot_payload,kind=109,stamp=10);assert bytes(depots)==depot_payload and dv.value==1 and dc.value==10
  lib.net_depot_report.argtypes=[C.c_uint,C.c_void_p,C.c_uint]
  out=(C.c_ubyte*304)();assert lib.net_depot_report(0,out,304)==0 and bytes(out)==depot_payload
  for stamp in (9,10):send(depot_payload,kind=109,stamp=stamp);assert dc.value==10
  old=site_words[depot_rows[0][0]*8+2];site_words[depot_rows[0][0]*8+2]=1
  out=(C.c_ubyte*304)(*([0xab]*304));assert lib.net_depot_report(0,out,304)==-1 and bytes(out)==bytes([0xab]*304)
  site_words[depot_rows[0][0]*8+2]=old
  saved=bytes(remote)
  for stamp in (9,10):
   r=row.copy();r[7]=139;send(struct.pack('<11I',*r),stamp=stamp);assert bytes(remote)==saved and clock.value==10
  for index in (10,11,15):
   prior=players[index];players[index]=prior+1;report(-1);players[index]=prior
  companies=(C.c_uint*40).in_dll(lib,'net_company_records')
  companies[3]=2;report(-1);companies[3]=1
  companies[1]=20;report(-1);companies[1]=19
  companies[2]=2;report(-1);companies[2]=1
  for stamp,values in ((11,[1,0,1,19,4,4,4,0,0,0,0]),(12,[1,0,1,19,4,0,0,0,4,0,0]),(13,row)):
   send(struct.pack('<11I',*values),stamp=stamp);assert report()==tuple(values[1:])
  tick.value=104;report(-1);tick.value=103;assert report()==tuple(row[1:]);tick.value=9;report(-1)
  buf=(C.c_ubyte*40)(*([0xcc]*40));assert lib.net_supply_report(0,buf,39)==-1 and bytes(buf)==bytes([0xcc]*40)
  assert lib.net_supply_report(0,None,40)==-1
  lib.net_client_close();assert not valid.value and not clock.value and not any(remote) and not dv.value and not any(depots)
  assert lib.net_client_open(b'127.0.0.1',sock.getsockname()[1])==0
  _,destination=sock.recvfrom(1200);send(struct.pack('<4I',0,0,8192,100),kind=2,stamp=0);send(payload)
  time.sleep(3.05);lib.net_client_poll();assert not valid.value and not any(remote)
 finally:lib.net_client_close();sock.close()
 print(json.dumps({'suite':'company-supply-udp-parser','passed':True,'malformed_foreign_packets':rejected,'malformed_depot_packets':len(depot_bad),'depot_atomic_conservation_ownership_gates':True,'whole_packet_atomic':True,'authority_checksum_preserved':True,'stale_equal_rejected':True,'lease_key_body_front_connected_age_gates':True,'close_reconnect_timeout_clear':True,'unknown_preserved':True,'client_sha256':hashlib.sha256(private.read_bytes()).hexdigest()}))
 # Production server, four endpoints, unchanged initial world. No memory writes.
 host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','180'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[]
 try:
  ready=json.loads(host.stdout.readline());address=('127.0.0.1',ready['port'])
  for _ in range(3):
   p=Peer(address);assert p.request(1)[0]==0;peers.append(p)
  assert lib.net_client_open(b'127.0.0.1',ready['port'])==0
  deadline=time.monotonic()+5;observations=[];last_keep=0
  while time.monotonic()<deadline:
   lib.net_client_poll()
   for p in peers:p.receive(0)
   if time.monotonic()-last_keep>.25:
    for p in peers:p.input()
    lib.net_client_input(0,0,C.c_float(0),C.c_float(0),C.c_float(0),C.c_float(0));last_keep=time.monotonic()
   owner=C.c_uint.in_dll(lib,'net_player_id').value
   out=(C.c_uint*10)()
   if lib.net_supply_report(owner,out,40)==0:
    r=list(out);assert owner==3 and r[0]==owner and r[1]>0 and r[2]<768 and r[3]<=128 and r[5]<=r[4]<=r[3]-r[7] and r[6]<=(r[3]-r[7]-r[5])*120 and r[8:]==[0,0]
    depot_out=(C.c_ubyte*304)()
    if lib.net_depot_report(owner,depot_out,304)!=0:
     time.sleep(.002);continue
    h=struct.unpack_from('<4I',depot_out);assert h[0]==3 and h[1]==r[1] and h[2]==2 and h[3]==0
    if not observations or observations[-1]['tick']!=clock.value:observations.append({'tick':clock.value,'report':r})
    if len({x['tick']for x in observations})>=3:break
   assert host.poll() is None
   time.sleep(.002)
  assert len({x['tick']for x in observations})>=3,'production supply view never corroborated'
  lib.net_client_close()
  for p in peers:p.request(5);p.socket.close()
  peers=[]
  stdout,stderr=host.communicate(timeout=12);assert host.returncode==0,stderr
  print(json.dumps({'suite':'company-supply-production-udp','passed':True,'units':8192,'endpoints':4,'samples':observations,'initial_world_unmodified':True,'production_depot_report_correlated':True,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'limits':['Production delivery and structurally checked ownership display; not an exact whole-world stock oracle or rendered HUD test.','No supply-aware routes or hardware-budget acceptance; exact world-to-wire stock oracle remains separate.']}))
 finally:
  lib.net_client_close()
  for p in peers:p.socket.close()
  if host.poll() is None:host.terminate();host.wait(timeout=5)
