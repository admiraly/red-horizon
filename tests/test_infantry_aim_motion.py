#!/usr/bin/env python3
"""Actual moving rifleman and moving human: observed point, finite shots, no renewal."""
import ctypes as C,json,math,pathlib,sys,struct,hashlib
prefix=pathlib.Path(__file__).with_name('test_infantry_human_targets.py').read_text().split('closer=run(')[0];exec(compile(prefix,'<physical initial fixture>','exec'))
poses=(C.c_ubyte*(32768*32)).in_dll(l,'infantry_aims');l.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
setup();initial_source=(e[17].x,e[17].z);initial_human=(p[0].x,p[0].z)
assert l.sim_order(1,e[17].front,0)==0 and l.player_input(0,0,1.,0.,0.,0.)==0
trace=[]
for tick in range(1,25):
 seen=(p[0].x,p[0].y,p[0].z);l.sim_tick();row=struct.unpack_from('<2I5fI',poses,17*32)
 if row[1]==tick:
  assert row[0]==e[17].generation and row[4:7]==seen and row[7]==7,row
  expected=math.atan2(seen[0]-e[17].x,seen[2]-e[17].z)
  assert abs(row[2]-expected)<1e-6,(row,expected)
  trace.append({'tick':tick,'source':[e[17].x,e[17].z],'observed_human':seen,'heading':row[2],'spent':w[140]})
 assert w[137]+w[138]+w[140]==120
assert len(trace)==3 and (e[17].x,e[17].z)!=initial_source and (p[0].x,p[0].z)!=initial_human
assert w[140]==3 and p[0].hp==70
print(json.dumps({'suite':'actual-moving-infantry-human-aim','passed':True,'trace':trace,'body_movement_and_point_observation_real_ticks':True,'no_live_pose_HP_generation_stores_clock_writes':True,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}))
