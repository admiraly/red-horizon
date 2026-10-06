#!/usr/bin/env python3
"""Queue real malformed/valid UDP inputs for the same production receive batch."""
import hashlib,json,os,pathlib,signal,struct,subprocess,sys,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tests'))
from test_coop import Peer
server=pathlib.Path(sys.argv[1]).resolve()
host=subprocess.Popen([str(server),'--port','0','--units','64'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
peer=None
try:
 ready=json.loads(host.stdout.readline());peer=Peer(('127.0.0.1',ready['port']));assert peer.request(1)[0]==0
 os.kill(host.pid,signal.SIGSTOP);os.waitpid(host.pid,os.WUNTRACED)
 peer.sequence+=1;badseq=peer.sequence
 peer.socket.sendto(peer.packet(3,struct.pack('<I4f',128,0,0,0,0)),peer.address)
 peer.sequence+=1;goodseq=peer.sequence
 peer.socket.sendto(peer.packet(3,struct.pack('<I4f',32,0,0,0,0)),peer.address)
 os.kill(host.pid,signal.SIGCONT);rows={};end=time.monotonic()+1.5
 while len(rows)<2 and time.monotonic()<end:
  r=peer.receive(.04)
  if r and r[0][4]==2 and r[0][6] in (badseq,goodseq):rows[r[0][6]]={'status':struct.unpack('<4I',r[1])[0],'tick':r[0][7]}
 assert rows[badseq]['status']==1 and rows[goodseq]['status']==7 and rows[badseq]['tick']==rows[goodseq]['tick'],rows
 peer.snapshot(rows[goodseq]['tick']+1);normal=peer.input(buttons=32);assert normal[0]==0,normal
 print(json.dumps({'passed':True,'queued_same_tick':rows,'valid_after_observed_next_tick':normal,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'limits':['SIGSTOP queues two real UDP inputs for one server receive batch; no pose/HP/store/tick writes.','Causal rate-budget reproduction; original full failure had a bare assertion without captured ACK status.']}))
finally:
 if peer:peer.socket.close()
 if host.poll() is None:os.kill(host.pid,signal.SIGCONT);host.terminate()
 host.communicate(timeout=5)
