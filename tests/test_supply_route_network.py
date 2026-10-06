#!/usr/bin/env python3
"""Actual8192/four-peer UDP authority; one declared startup infantry detour.
Only setup writes. Read-only observations never renew poses/HP/stocks/clocks.
"""
import hashlib,json,math,os,pathlib,signal,struct,subprocess,sys,time
from test_coop import Peer
server=pathlib.Path(sys.argv[1]).resolve()
host=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','510'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
peers=[];memory=None
try:
 ready=json.loads(host.stdout.readline());symbols={r[2]:int(r[0],16)for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines()if len(r:=line.split())==3}
 os.kill(host.pid,signal.SIGSTOP)
 try:
  setup=os.open(f'/proc/{host.pid}/mem',os.O_RDWR)
  try:
   birth=struct.unpack('<I',os.pread(setup,4,symbols['sim_tick_count']))[0];assert birth<=3,birth
   entity=os.pread(setup,32,symbols['sim_entities']);record=struct.unpack('<2f6I',entity)
   stock=struct.unpack('<8I',os.pread(setup,32,symbols['infantry_weapons']))
   assert record[2:5]==(100,0,0) and record[7]==1 and stock[:5]==(1,30,90,0,0),(record,stock)
   # One independent birth position/front and conserved pre-battle stock.
   os.pwrite(setup,struct.pack('<2f',900.,3900.),symbols['sim_entities'])
   os.pwrite(setup,struct.pack('<I',1),symbols['sim_entities']+20)
   os.pwrite(setup,struct.pack('<8I',1,12,0,0,108,0,0,0),symbols['infantry_weapons'])
   os.pwrite(setup,struct.pack('<2f',900.,4200.),symbols['sim_waypoints']+8)
   os.pwrite(setup,struct.pack('<I',0),symbols['orders']+4)
   os.pwrite(setup,struct.pack('<I',1),symbols['ai_fronts']+64+24)
   assert os.pread(setup,4,symbols['sim_entities']+8)==entity[8:12]
   assert os.pread(setup,4,symbols['sim_entities']+28)==entity[28:32]
  finally:os.close(setup)
 finally:os.kill(host.pid,signal.SIGCONT)
 memory=os.open(f'/proc/{host.pid}/mem',os.O_RDONLY)
 for _ in range(4):
  p=Peer(('127.0.0.1',ready['port']));assert p.request(1)[0]==0;peers.append(p)
 last_input=0;retries=0;transaction_retries=0;samples=[];first=None;previous=None
 def pump():
  global last_input
  for p in peers:
   for _ in range(8):
    if p.receive(0)is None:break
  if time.monotonic()-last_input>.2:
   for p in peers:p.input()
   last_input=time.monotonic()
 def observe():
  global retries,transaction_retries
  # Start/end counters distinguish a whole completed tick from a preempted
  # world pass; two identical /proc reads alone are not a publication barrier.
  completed=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_completed']))[0]
  tick=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0]
  if completed!=tick:retries+=1;return None
  entities=os.pread(memory,32,symbols['sim_entities']);raw=os.pread(memory,8192*32,symbols['infantry_weapons']);depots=os.pread(memory,192,symbols['depot_ammunition'])
  if raw!=os.pread(memory,len(raw),symbols['infantry_weapons'])or depots!=os.pread(memory,192,symbols['depot_ammunition'])or entities!=os.pread(memory,32,symbols['sim_entities'])or tick!=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_count']))[0]or tick!=struct.unpack('<I',os.pread(memory,4,symbols['sim_tick_completed']))[0]:retries+=1;return None
  rows=[struct.unpack_from('<8I',raw,i*32)for i in range(8192)];stores=[struct.unpack_from('<4I',depots,i*16)for i in range(12)]
  for i,row in enumerate(rows):
   if i%16<12:
    assert row[0]==1 and row[1]<=30 and row[2]<=90,(i,row)
    if row[1]+row[2]+row[4]!=120+row[6]:transaction_retries+=1;return None
   else:assert row==(0,)*8
  # An OS preemption between the short debit/credit writes can expose a
  # consistent read of a transaction in progress. Retry within the same
  # bounded observation deadline; persistent corruption cannot pass.
  if sum(row[6]for row in rows)!=sum(row[1]for row in stores)or not all(r[0]+r[1]==r[2]and r[3]==0 for r in stores)or sum(r[1]+r[2]+r[4]for r in rows)+sum(r[0]for r in stores)!=6144*120+48000:
   transaction_retries+=1;return None
  assert os.pread(memory,8,symbols['sim_waypoints']+8)==struct.pack('<2f',900.,4200.)
  actor=struct.unpack('<2f6I',entities);assert actor[2:6]==(100,0,0,1)and actor[7]==1
  return tick,actor,rows[0],stores[4]
 deadline=time.monotonic()+45
 while time.monotonic()<deadline:
  pump();row=observe()
  if row:
   tick,actor,weapon,depot=row
   if previous and tick>previous[0]:assert math.dist(actor[:2],previous[1][:2])<=(tick-previous[0])*.1205+.001,(previous,row)
   previous=row
   if weapon[6]and first is None:
    first=row;assert weapon[6]==90 and weapon[7]==360 and depot[:3]==(11910,90,12000),(row,birth)
    assert weapon[1]+weapon[2]==102 and math.dist(actor[:2],(1000,3900))<=60
   if not samples or tick>=samples[-1][0]+60:samples.append([tick,*actor[:2],weapon[1]+weapon[2],weapon[6],depot[0]])
   if tick>=480:
    assert first and actor[1]>3910 and actor[0]<first[1][0] and weapon[6]==90,row
    samples.append([tick,*actor[:2],weapon[1]+weapon[2],weapon[6],depot[0]]);break
  assert host.poll()is None,'server terminated before route observations'
  time.sleep(.003)
 else:raise AssertionError('actual UDP route observation timed out')
 for p in peers:p.command(5);p.socket.close()
 peers=[];stdout,stderr=host.communicate(timeout=20);assert host.returncode==0,(stdout,stderr)
 print(json.dumps({'suite':'physical-supply-route-four-peer-udp','passed':True,'units':8192,'endpoints':4,'startup_tick':birth,'declared_initial_carried':12,'declared_prior_expenditure':108,'actual_credit_tick':first[2][7],'credited_rounds':90,'depot_remaining':11910,'resumed_primary_goal':[900,4200],'samples':samples,'all6144_infantry_and12_depots_conserved':True,'observer_writes_after_setup':False,'complete_tick_publication_checked':True,'stable_read_retries':retries,'in_progress_transaction_retries':transaction_retries,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'limits':['One explicit startup actor pose/front/stock and front objective; no live state renewal or identity/health changes.','Exact stocks and travel observed read-only on actual server; not an exact wire-stock oracle, production adapter or rendered detour feedback test.']}))
finally:
 for p in peers:p.socket.close()
 if memory is not None:os.close(memory)
 if host.poll()is None:host.kill();host.communicate()
