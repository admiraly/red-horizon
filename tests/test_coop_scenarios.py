#!/usr/bin/env python3
"""Real dedicated authored starts, unchanged authority replay, and four UDP peers."""
import ctypes as C,json,pathlib,subprocess,sys,time
from test_coop import Peer,VERSION
server=pathlib.Path(sys.argv[1]).resolve();lib=C.CDLL(str(pathlib.Path(sys.argv[2]).resolve()));lib.sim_checksum.restype=C.c_uint64
count=C.c_uint.in_dll(lib,'sim_count');tick=C.c_uint.in_dll(lib,'sim_tick_count');alive=(C.c_uint*2).in_dll(lib,'sim_alive');engaged=C.c_uint.in_dll(lib,'sim_engaged');events=C.c_uint.in_dll(lib,'sim_event_sequence')
scenarios=('scale-open','air-battle','scale-front','scale-hotspot');reports=[]
for mode,name in enumerate(scenarios):
 run=subprocess.run([str(server),'--port','0','--units','8192','--ticks','120','--scenario',name],cwd=server.parent,text=True,capture_output=True,timeout=25)
 assert run.returncode==0,(name,run.stdout,run.stderr)
 ready,report=map(json.loads,run.stdout.splitlines());assert ready['scenario']==mode and ready['units']==8192 and ready['protocol']==VERSION
 assert lib.sim_init(8192,42)==0;lib.player_init();assert lib.sim_scenario(mode)==0
 for _ in range(120):lib.sim_tick()
 expected=f'0x{lib.sim_checksum():016x}';assert report['checksum']==expected,(name,report['checksum'],expected)
 assert report['ticks']==tick.value==120 and report['simulated']==count.value==8192
 assert report['alive']==list(alive) and report['engaged']==engaged.value and report['event_sequence']==events.value
 if mode>=2:assert sum(alive)<8192 and events.value>1000,'authored dense armies did not fight'
 reports.append({'scenario':name,'actual_server':report,'same_shared_authority_replay':True,'initial_units_per_side':4096})
invalid=[['--scenario'],['--scenario','unknown'],['--scenario','scale-open','--scenario','scale-front'],['--units','2','--scenario','scale-front'],['--units','2','--scenario','scale-hotspot'],['--units','2','--scenario','air-battle']]
for args in invalid:
 run=subprocess.run([str(server),*args],cwd=server.parent,capture_output=True,text=True,timeout=5);assert run.returncode==2 and not run.stdout,(args,run.returncode,run.stdout)
# Actual four-client packet admission and snapshots; no live authority writes.
for mode in (2,3):
 process=subprocess.Popen([str(server),'--port','0','--units','8192','--ticks','240','--scenario',scenarios[mode]],cwd=server.parent,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);peers=[]
 try:
  ready=json.loads(process.stdout.readline());address=('127.0.0.1',ready['port']);join_ticks=[]
  for slot in range(4):
   peer=Peer(address);peers.append(peer);ack=peer.request(1);assert ack[0]==0 and peer.id==slot;join_ticks.append(ack[2])
  snapshots=[p.snapshot(max(join_ticks)+3) for p in peers]
  assert all(s['units']==8192 for s in snapshots)
  assert all(s['players'][i][11]==1 for i,s in enumerate(snapshots))
  assert all(all(s['players'][i][15]>0 for i in range(4)) for s in snapshots)
  # Remain real clients long enough for fair interest updates and actual aircraft.
  minimum=max(s['tick'] for s in snapshots)+30;deadline=time.monotonic()+5
  while time.monotonic()<deadline and not all(p.state and p.state['tick']>=minimum for p in peers):
   for p in peers:p.receive(.02)
  assert all(p.state and p.state['tick']>=minimum for p in peers),'four-peer fair snapshot window timed out'
  assert all(p.entities for p in peers) and any(p.aircraft for p in peers)
  known=[len(p.entities) for p in peers];max_packet=max(p.max_packet for p in peers)
  out,err=process.communicate(timeout=20);assert process.returncode==0,(out,err);terminal=json.loads(out)
  assert terminal['ticks']==240 and terminal['simulated']==8192 and terminal['entity_records']>0 and terminal['aircraft_records']>0
  reports.append({'scenario':scenarios[mode],'four_real_UDP_peers':True,'known_actor_counts':known,'packet_max_bytes':max_packet,'actual_server':terminal,'scope':'Default threat-checked join positions, regional interest; not four graphical fronts/dense visibility/fault stress.'})
 finally:
  for p in peers:p.socket.close()
  if process.poll() is None:process.terminate();process.communicate(timeout=5)
print(json.dumps({'suite':'actual-coop-authored-scenarios','passed':True,'reports':reports,'invalid_prebind_cases':len(invalid),'no_live_authority_writes':True,'scope':'One-time production8192 births,120-tick shared-authority exact checksums, four actual UDP clients and gameplay snapshots. No camera/health/clock renewal or rendered1024-visible/whole-operation acceptance.'}))
