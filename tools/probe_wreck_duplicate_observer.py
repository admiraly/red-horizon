#!/usr/bin/env python3
"""Replay retained authentic wreck payloads; distinguish duplicate from first delivery."""
import argparse,base64,ctypes as C,gzip,hashlib,json,pathlib,socket,struct,sys
p=argparse.ArgumentParser();p.add_argument('library',type=pathlib.Path);p.add_argument('capture',type=pathlib.Path);p.add_argument('--protocol-root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);a=p.parse_args()
sys.path.insert(0,str(a.protocol_root/'tests'))
from test_coop import HEADER,MAGIC,VERSION,SCHEMA,CONTENT
raw=gzip.decompress(a.capture.read_bytes());rows=json.loads(raw);assert rows
lib=C.CDLL(str(a.library.resolve()));lib.net_client_open.argtypes=[C.c_char_p,C.c_uint]
remote=(C.c_ubyte*65536).in_dll(lib,'net_wrecks');relay=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);relay.bind(('127.0.0.1',0));relay.settimeout(1)
try:
 assert lib.net_client_open(b'127.0.0.1',relay.getsockname()[1])==0
 _,target=relay.recvfrom(1200)
 def send(kind,payload,tick):
  relay.sendto(HEADER.pack(MAGIC,VERSION,SCHEMA,CONTENT,kind,0,1 if kind==2 else 0,tick,len(payload),9)+payload,target);lib.net_client_poll()
 send(2,struct.pack('<4I',0,0,8192,100),0);applied=[]
 for row in rows:
  if row['applied']:
   send(106,base64.b64decode(row['payload']),row['tick']);applied.append(row)
 saved=bytes(remote);assert any(saved)
 for row in (applied[0],applied[len(applied)//2],applied[-1]):
  send(106,base64.b64decode(row['payload']),row['tick']);assert bytes(remote)==saved
 row=rows[-1];assert not row['applied'],'This diagnostic requires the retained dropped-last capture'
 payload=base64.b64decode(row['payload']);send(106,payload,row['tick']);after=bytes(remote)
 changed=[slot for slot in range(1024) if saved[slot*64:(slot+1)*64]!=after[slot*64:(slot+1)*64]]
 assert changed,'Retained first-delivery causal control no longer reproduces'
 for slot in changed:
  assert not any(saved[slot*64:(slot+1)*64])
  wire=next(payload[i+4:i+68] for i in range(0,len(payload),68) if struct.unpack_from('<I',payload,i)[0]==slot)
  assert after[slot*64:(slot+1)*64]==wire
 send(106,payload,row['tick']);assert bytes(remote)==after
 print(json.dumps({'passed':True,'original_immutability_assertion_contradicted':True,'duplicate_samples_previously_delivered_unchanged':True,'delayed_first_delivery_slots':changed,'first_delivery_duplicate_unchanged':True,'packets':len(rows),'source_capture_sha256':hashlib.sha256(raw).hexdigest(),'library_sha256':hashlib.sha256(a.library.read_bytes()).hexdigest(),'wire_version':VERSION,'scope':'Retained genuine server payloads, reconstructed loopback headers; no simulation writes, fresh world or graphics acceptance.'}))
finally:lib.net_client_close();relay.close()
