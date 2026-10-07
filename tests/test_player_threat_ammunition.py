#!/usr/bin/env python3
"""Sparse initial finite-stock fixtures; actual sim_tick/player damage thereafter."""
import ctypes as C,hashlib,json,pathlib,sys
source=pathlib.Path(sys.argv[1]).resolve();l=C.CDLL(str(source));l.sim_checksum.restype=C.c_uint64
l.player_input.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4;l.terrain_height.argtypes=[C.c_float,C.c_float];l.terrain_height.restype=C.c_float
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint)for n in ('hp','side','kind','front','target','generation')]
class Player(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','yaw','pitch')]+[(n,C.c_uint)for n in ('hp','ammo','reload','cooldown','respawn','front','connected','shots','hits','suppression','generation')]
e=(Entity*32768).in_dll(l,'sim_entities');p=(Player*4).in_dll(l,'sim_players');w=(C.c_uint*(32768*8)).in_dll(l,'infantry_weapons');manual=(C.c_uint*(6*16)).in_dll(l,'ai_fronts')
def run(kind,magazine,reserve,spent,reload=0,corrupt=False,blocked=False):
 assert l.sim_init(2,47)==0 and l.player_join(0,1)==0
 p[0].x,p[0].z=2000.,3900.;p[0].y=l.terrain_height(2000.,3900.)+1.8
 e[0].x,e[0].z=7000.,7000.;e[0].side=0
 e[1].x,e[1].z=2050.,3900.;e[1].side=1;e[1].kind=kind;e[1].front=0
 if blocked:
  p[0].x,p[0].z=3970.,1300.;p[0].y=l.terrain_height(3970.,1300.)+1.8;e[1].x,e[1].z=4030.,1300.
 assert l.sim_order(1,0,1)==0;manual[3*16+6]=1
 w[8:16]=[e[1].generation,magazine,reserve,reload,spent,0,0,0]
 initial=tuple(w[8:16]);trace=[]
 for t in range(1,81):
  l.sim_tick()
  if t%16==0:trace.append([t,p[0].hp,p[0].suppression,*tuple(w[9:13])])
  if kind==0 and not corrupt:assert w[9]+w[10]+w[12]==120
 return {'kind':kind,'initial_stock':initial,'final_stock':tuple(w[8:16]),'final_hp':p[0].hp,'player_generation':p[0].generation,'trace':trace,'checksum':f'{l.sim_checksum():016x}'}
armed=run(0,30,90,0);empty=run(0,0,0,120);reloading=run(0,0,90,30,60);corrupt=run(0,31,90,0,corrupt=True)
if '--baseline' in sys.argv:
 assert armed['final_hp']==empty['final_hp']==50 and armed['final_stock'][4]==0
 print(json.dumps({'suite':'player-threat-ammunition-baseline-diagnosis','observed_bug':True,'armed':armed,'exhausted':empty,'reload':reloading,'corrupt':corrupt,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}));sys.exit(0)
blocked=run(0,30,90,0,blocked=True);noninf=run(1,0,0,120)
assert blocked['final_hp']==100 and blocked['final_stock']==blocked['initial_stock'],blocked
assert noninf['final_hp']==100 and noninf['final_stock']==noninf['initial_stock'],noninf
assert run(0,30,90,0)==armed,'active same-build replay'
assert armed['final_hp']==0 and armed['final_stock'][4]==10,armed
assert empty['final_hp']==100 and empty['final_stock']==empty['initial_stock'],empty
assert reloading['trace'][2][1]==100 and reloading['final_hp']==70 and reloading['final_stock'][4]==33,reloading
assert corrupt['final_hp']==100 and corrupt['final_stock']==corrupt['initial_stock'],corrupt
print(json.dumps({'suite':'player-threat-finite-infantry-ammunition','passed':True,'physical_ticks_per_case':80,'armed':armed,'exhausted':empty,'real_reload':reloading,'corrupt_gate':corrupt,'actual_wall_no_debit':blocked,'noninfantry_no_synthetic_rifle_control':noninf,'active_same_build_replay':True,'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['Declared sparse startup poses/prior expenditure/reload or malformed stock; actual damage/movement/weapon countdown thereafter, no live renewal.','Physical noninfantry weapon blasts are separate tests; Single actor8tick rifle arbitration owns human/army cadence.','Not full-scale/UDP/graphics/performance acceptance.']}))
