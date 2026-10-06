#!/usr/bin/env python3
"""Read-only own producer and atomic remote cache against actual NASM."""
import ctypes as C,hashlib,json,pathlib,sys
source=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(source));l.sim_checksum.restype=C.c_uint64
for name in ('player_ammunition_report','net_player_ammunition_report'):getattr(l,name).argtypes=[C.c_uint,C.c_void_p,C.c_uint]
l.net_player_ammunition_receive.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint];l.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
players=(C.c_uint*64).in_dll(l,'sim_players');stock=(C.c_uint*32).in_dll(l,'player_ammunition');tick=C.c_uint.in_dll(l,'sim_tick_count');record=(C.c_uint*10).in_dll(l,'net_player_ammunition_record');remote_tick=C.c_uint.in_dll(l,'net_player_ammunition_tick');valid=C.c_uint.in_dll(l,'net_player_ammunition_valid')
assert l.sim_init(2,73)==0 and l.player_join(0,1)==0;l.sim_tick()
queries=0
def report(remote=False,player=0,capacity=40,expected=0):
 global queries
 out=(C.c_ubyte*56)(*([0xa6]*56));before=l.sim_checksum();rc=(l.net_player_ammunition_report if remote else l.player_ammunition_report)(player,C.byref(out,8),capacity);queries+=1
 assert rc==expected and l.sim_checksum()==before and bytes(out[:8])+bytes(out[48:])==bytes([0xa6]*16)
 if rc:assert bytes(out)==bytes([0xa6]*56);return None
 return tuple((C.c_uint*10).from_buffer(out,8))
def receive(values,stamp,recipient=0,capacity=40,expected=0):
 payload=(C.c_uint*10)(*values);before=l.sim_checksum();old=(tuple(record),remote_tick.value,valid.value);rc=l.net_player_ammunition_receive(payload,capacity,stamp,recipient)
 assert rc==expected and l.sim_checksum()==before
 if rc:assert (tuple(record),remote_tick.value,valid.value)==old
initial=report();assert initial==(0,1,30,90,0,0,0,120,1,0);receive(initial,tick.value);assert report(True)==initial
malformed=[]
for index,value,label in [(0,1,'foreign owner'),(1,0,'generation'),(2,31,'magazine'),(3,91,'reserve'),(4,144121,'spent bound'),(4,1,'conservation'),(5,144001,'receipt bound'),(6,1,'receipt timestamp without credit'),(7,0,'initial'),(8,2,'flags'),(9,1,'reserved')]:
 row=list(initial);row[index]=value;receive(row,tick.value+1,expected=-1);malformed.append(label)
for capacity in (0,39,41):receive(initial,tick.value+1,capacity=capacity,expected=-1)
receive(initial,tick.value+1,recipient=1,expected=-1);receive(initial,tick.value,expected=-1)
unknown=(0,1,0,0,0,0,0,0,0,0)
for index in (2,3,4,5,6,7):
 row=list(unknown);row[index]=1;receive(row,tick.value+1,expected=-1)
row=list(initial);row[4]=30;row[5]=30;row[6]=tick.value+3;receive(row,tick.value+1,expected=-1)
# Actual two rifle shots invalidate the older magazine-correlated cached view;
# publication of the current actual producer report restores it.
assert l.player_input(0,1,0.,0.,0.,0.)==0
for _ in range(5):l.sim_tick()
assert players[6]==28 and stock[2]==2;report(True,expected=-1)
current=report();assert current[2:6]==(28,90,2,0);receive(current,tick.value);assert report(True)==current
# Real body reuse, no snapshot renewal: old generation is unavailable, a newer
# current report is usable; a later-tick old generation cannot replace it.
assert l.player_leave(0)==0 and l.player_join(0,1)==0;l.sim_tick();report(True,expected=-1)
new=report();assert new[1]==2 and new[2:6]==(30,90,0,0);receive(new,tick.value);assert report(True)==new
receive(initial,tick.value+1,expected=-1)
for _ in range(90):l.sim_tick()
assert report(True)==new;l.sim_tick();report(True,expected=-1)
l.net_player_ammunition_reset();assert tuple(record)==(0,)*10 and remote_tick.value==valid.value==0;report(True,expected=-1)
# Explicit unknown producer result for corruption never fabricates empty/full.
stock[6]=1;unknown=report();assert unknown==(0,2,0,0,0,0,0,0,0,0);receive(unknown,tick.value);assert report(True)==unknown;stock[6]=0
for remote in (False,True):
 report(remote,capacity=39,expected=-1);report(remote,player=4,expected=-1)
for index,value in ((11,0),(15,0),(10,3),(5,101)):
 old=players[index];players[index]=value;report(False,expected=-1);report(True,expected=-1);players[index]=old
print(json.dumps({'suite':'player-ammunition-producer-and-remote-cache','passed':True,'readonly_guarded_reports':queries,'malformed_cases':malformed,'whole_payload_atomic':True,'actual_shot_magazine_corroboration':True,'actual_new_body_generation_reordering':True,'actual90tick_age_boundary':True,'explicit_unknown_zero_quantities':True,'reset_clears':True,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['Actual CPU producer/cache and genuine shots/new body/age ticks; malformed field fixtures are separate.','No transport authentication, actual UDP delivery or GL feedback acceptance from these cache calls alone.']}))
