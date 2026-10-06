#!/usr/bin/env python3
"""Atomic blast/body gates, genuine boarding/death/redeployment against NASM."""
import ctypes as C,hashlib,json,pathlib,sys
source=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(source));l.sim_checksum.restype=C.c_uint64
l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float;l.player_blast.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;l.player_apply_damage.argtypes=[C.c_uint,C.c_uint,C.c_uint]
players=(C.c_uint*64).in_dll(l,'sim_players');poses=(C.c_float*64).in_dll(l,'sim_players');stock=(C.c_uint*32).in_dll(l,'player_ammunition');motion=(C.c_ubyte*128).in_dll(l,'player_motion');vehicles=(C.c_int*4).in_dll(l,'sim_player_vehicle');entities=(C.c_uint*(32768*8)).in_dll(l,'sim_entities');entity_poses=(C.c_float*(32768*8)).in_dll(l,'sim_entities');deaths=C.c_uint.in_dll(l,'player_deaths')
def pose(player,x,z):
 index=player*16;poses[index]=x;poses[index+2]=z;poses[index+1]=l.terrain_height(x,z)+1.8
assert l.sim_init(32,47)==0 and l.player_join(0,1)==0;pose(0,2005.,3900.)
def unchanged(args,expected=-1):
 before=l.sim_checksum();assert l.player_blast(*args)==expected and l.sim_checksum()==before,args
cases=0
for index,values in ((0,(2,0xffffffff)),(1,(0,1001)),(2,(-1.,8001.,float('nan'),float('inf'))),(3,(-1.,8001.,float('nan'),float('-inf'))),(4,(0.,-1.,257.,float('nan'),float('inf'))),(5,(-2001.,2001.,float('nan'),float('inf')))):
 for value in values:
  args=[1,80,2000.,3900.,18.,l.terrain_height(2000.,3900.)+1.];args[index]=value;unchanged(args);cases+=1
unchanged((0,80,2000.,3900.,18.,l.terrain_height(2000.,3900.)+1.),0)
for args in ((4,80,1),(0xffffffff,80,1),(0,0,1),(0,1001,1),(0,80,2)):
 before=l.sim_checksum();assert l.player_apply_damage(*args)==-1 and l.sim_checksum()==before;cases+=1
for word,value in ((5,101),(10,3),(15,0),(11,0)):
 old=players[word];players[word]=value;unchanged((1,80,2000.,3900.,18.,l.terrain_height(2000.,3900.)+1.),0);players[word]=old
pose(0,3970.,1300.);unchanged((1,80,4030.,1300.,80.,l.terrain_height(4030.,1300.)+1.),0)
pose(0,2005.,3900.);assert l.player_join(1,1)==0;pose(1,2007.,3900.)
before_stock=bytes(stock);assert l.player_blast(1,20,2000.,3900.,18.,l.terrain_height(2000.,3900.)+1.)==2
assert players[5]==players[21]==80 and bytes(stock)==before_stock
# New independent body fixture for real armour boarding, then physical blast.
assert l.sim_init(32,47)==0 and l.player_join(0,1)==0;pose(0,2005.,3900.)
entity_poses[12*8]=2000.;entity_poses[12*8+1]=3900.;assert entities[12*8+4]==1
assert l.vehicle_enter(0,12)==0 and vehicles[0]==12
unchanged((1,80,2000.,3900.,18.,l.terrain_height(2000.,3900.)+1.),0);assert players[5]==100
assert l.vehicle_exit(0)==0 and vehicles[0]==-1
before_stock=bytes(stock);generation=players[15];old_deaths=deaths.value
assert l.player_apply_damage(0,100,1)==1 and players[5]==0 and players[9]==30 and players[7]==0
assert bytes(motion[:32])==bytes(32)and bytes(stock)==before_stock and deaths.value==old_deaths+1
before=l.sim_checksum();assert l.player_apply_damage(0,100,1)==0 and l.sim_checksum()==before and deaths.value==old_deaths+1
for _ in range(30):l.sim_tick()
assert players[5]==100 and players[15]==generation+1 and players[6]==30 and stock[1]==90
print(json.dumps({'suite':'player-blast-atomic-lifecycle-gates','passed':True,'invalid_cases':cases,'friendly_damage_preserves':True,'corrupt_disconnected_bodies_skipped':True,'actual_wall_no_damage':True,'two_humans_same_blast':True,'genuine_boarding_shields_crew':True,'actual_death_clears_motion_without_ammo_birth':True,'no_duplicate_death':True,'actual30tick_redeployment_equips_only_new_body':True,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['Declared static body/geometry gates, genuine public boarding/exit/damage/deployment lifecycle. Cannon/bomb physical traces are separate.','Eye point and on-foot blasts; full body shape/armour penetration/fighter contact/hardware are separate.']}))
