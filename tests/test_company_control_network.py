#!/usr/bin/env python3
"""Actual four UDP players, exclusive same-front orders, lost ACK and lease recovery."""
import json,pathlib,subprocess,os,struct,sys,math,time,hashlib
from test_coop import Peer,VERSION
server=pathlib.Path(sys.argv[1]).resolve();symbols={}
for line in subprocess.check_output(['nm','-n',str(server)],text=True).splitlines():
 row=line.split()
 if len(row)==3 and row[2] in ('company_controls','player_companies','sim_entities','sim_tick_count','ai_fronts','hazard_states'):symbols[row[2]]=int(row[0],16)
assert len(symbols)==6
process=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','360'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);peers=[];memory=None
try:
 ready=json.loads(process.stdout.readline());assert ready['protocol']==VERSION and ready['units']==8192
 memory=os.open(f'/proc/{process.pid}/mem',os.O_RDONLY)
 def read(name,count,offset=0):return os.pread(memory,count,symbols[name]+offset)
 def tick():return struct.unpack('<I',read('sim_tick_count',4))[0]
 def assignment(i):return struct.unpack('<4I',read('player_companies',16,i*16))
 def control(key):return struct.unpack('<4I2f2I',read('company_controls',32,key*32))
 def entities():
  for _ in range(5):
   before=tick();data=read('sim_entities',8192*32)
   if before==tick():return [struct.unpack_from('<2f4IiI',data,i*32)for i in range(8192)]
  raise AssertionError('could not obtain one authoritative-tick entity read')
 def members(key,rows):return [i for i,e in enumerate(rows)if e[2] and e[3]==0 and e[4]<3 and e[5]*256+(i>>7)==key]
 def wait_ticks(until):
  heartbeat=tick()
  while tick()<until:
   for p in peers:p.receive(.015)
   if tick()-heartbeat>=30:
    for p in peers:
     if assignment(p.id)[0]!=0xffffffff:assert p.input()[0] in (0,7)
    heartbeat=tick()
 for _ in range(4):
  p=Peer(('127.0.0.1',ready['port']));assert p.request(1)[0]==0;peers.append(p)
 keys=[assignment(i)[0]for i in range(4)];assert len(set(keys))==4
 assert peers[0].front==peers[3].front==0 and keys[0]//256==keys[3]//256==0
 rows=entities();held=members(keys[0],rows);moving=members(keys[3],rows);assert len(held)>=16 and len(moving)>=16
 mean_x=sum(rows[i][0]for i in moving)/len(moving);mean_z=sum(rows[i][1]for i in moving)/len(moving)
 goal=(min(7300,mean_x+150),mean_z)
 manual_before=read('ai_fronts',384)
 status,balance,accepted=peers[0].command(4,struct.pack('<IIff',0,1,mean_x,mean_z));assert status==0
 status,balance_d,accepted_d=peers[3].command(4,struct.pack('<IIff',0,0,*goal),lose_ack=True);assert status==0
 assert control(keys[0])[2:4]==(1,1) and control(keys[3])[2:4]==(0,1)
 assert control(keys[0])[6]==control(keys[3])[6]==1
 duplicate=peers[3].request(4,struct.pack('<IIff',0,0,*goal));assert duplicate[0]==0 and duplicate[1]==balance_d and control(keys[3])[6]==1
 assert all(control(k)[3]==0 for k in keys[1:3])
 assert all(struct.unpack_from('<I',manual_before,64*f+24)[0]==struct.unpack_from('<I',read('ai_fronts',384),64*f+24)[0]for f in range(6))
 # Ownership denial preserves both companies; ordinary autonomous fronts continue.
 before=[control(keys[j])for j in (0,3)]
 assert peers[3].command(4,struct.pack('<IIff',1,0,*goal))[0]==5
 assert [control(keys[j])for j in (0,3)]==before
 initial=entities();start=tick();wait_ticks(start+60);after=entities()
 held_travel=[math.dist(initial[i][:2],after[i][:2])for i in held if after[i][2] and after[i][7]==initial[i][7]]
 moving_travel=[math.dist(initial[i][:2],after[i][:2])for i in moving if after[i][2] and after[i][7]==initial[i][7]]
 hazard_ids=[];held_quiet=[]
 for i in held:
  if not after[i][2] or after[i][7]!=initial[i][7]:continue
  generation,until=struct.unpack('<2I',read('hazard_states',8,i*32))
  if generation==after[i][7] and until>start:hazard_ids.append(i)
  elif after[i][4]==0:held_quiet.append(math.dist(initial[i][:2],after[i][:2]))
 assert len(held_quiet)>=16 and max(held_quiet)<.01,(held_quiet,hazard_ids)
 # Genuine observed explosive avoidance remains above human hold priority.
 assert all(math.dist(initial[i][:2],after[i][:2])<=8 for i in hazard_ids)

 assert moving_travel and max(moving_travel)>5,moving_travel
 old_generation=peers[0].generation;old_packet=peers[0].packet(4,struct.pack('<IIff',0,0,*goal),sequence=peers[0].sequence+1)
 assert peers[0].command(5)[0]==0
 assert assignment(0)[0]==0xffffffff and control(keys[0])[0]==0xffffffff and control(keys[0])[3]==0
 start=tick();wait_ticks(start+60);recovered=entities()
 autonomy=[math.dist(after[i][:2],recovered[i][:2])for i in held if recovered[i][2] and recovered[i][7]==after[i][7]]
 assert autonomy and max(autonomy)>1,autonomy
 peers[0].id=0xffffffff;peers[0].generation=0;peers[0].sequence=1;assert peers[0].request(1)[0]==0 and peers[0].generation>old_generation
 new_key=assignment(0)[0];before=control(new_key);peers[0].socket.sendto(old_packet,peers[0].address);peers[0].snapshot(tick()+6);assert control(new_key)==before
 report={'suite':'company-exclusive-actual-udp','passed':True,'initial_army':8192,'four_assignment_keys':keys,'same_front_exclusive':True,'company_live_member_counts':[len(held),len(moving)],'held_quiet_infantry_count':len(held_quiet),'held_quiet_infantry_max_travel_m':max(held_quiet),'held_hazard_reaction_ids':hazard_ids,'held_total_max_travel_m':max(held_travel),'ordered_max_travel_m':max(moving_travel),'released_max_autonomous_travel_m':max(autonomy),'actual_lost_ack_repeat_one_charge_and_sequence':True,'cross_front_rejection_preserves_intent':True,'stale_endpoint_generation_command_rejected':True,'front_manual_flags_unchanged':True,'server_sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'observer_writes':False,'limits':['Read-only /proc observer on genuine NASM server and actual UDP peers.','Company replication/UI/transfer/assistance and broad fault/scale acceptance remain separate.']}
 # These peers deliberately own this child process; close them before finite run end.
 for p in peers:p.socket.close()
 peers=[]
 stdout,stderr=process.communicate(timeout=20);assert process.returncode==0,(stdout,stderr);report['server']=json.loads(stdout.strip().splitlines()[-1]);print(json.dumps(report))
finally:
 if memory is not None:os.close(memory)
 for p in peers:p.socket.close()
 if process.poll() is None:process.kill();process.communicate()
