#!/usr/bin/env python3
"""Production conserved shots publish one source event; rejected shots publish none."""
import ctypes as C,hashlib,json,pathlib,sys
# Reuse only the declared physical fixture, never the feature assertions.
prefix=(pathlib.Path(__file__).with_name('test_infantry_human_targets.py')).read_text().split('closer=run(')[0]
exec(compile(prefix,'<actual infantry fixture>','exec'))
events=(C.c_ubyte*8192).in_dll(l,'sim_events');sequence=C.c_uint.in_dll(l,'sim_event_sequence');cases=[]
for name,army,human,stock in [('human',(7000.,7000.),(2000.,3900.),None),('army',(2070.,3900.),(2000.,3900.),None),('empty',(7000.,7000.),(2000.,3900.),[1,0,0,0,120,0,0,0]),('reload',(7000.,7000.),(2000.,3900.),[1,0,90,60,30,0,0,0]),('corrupt',(7000.,7000.),(2000.,3900.),[1,31,90,0,0,0,0,0]),('hidden',(4030.,1450.),(3970.,1300.),None)]:
 setup(army,(human,),enemy=(4030.,1300.) if name=='hidden' else (2050.,3900.))
 if name=='hidden':e[0].x,e[0].z=7000.,7000.
 if stock is not None:w[136:144]=stock
 actual=[]
 for t in range(1,81):
  before_seq=sequence.value;before_spent=w[140];l.sim_tick();delta=w[140]-before_spent
  assert sequence.value-before_seq==delta,(name,t,before_seq,sequence.value,delta)
  if delta:
   row=__import__('struct').unpack_from('<3f3IfI',events,(sequence.value&255)*32)
   assert row[0]==e[17].x and row[2]==e[17].z and row[3:6]==(10,1,t) and row[6]==.25 and row[7]==sequence.value,row
   assert abs(row[1]-(l.terrain_height(e[17].x,e[17].z)+2))<.0001,row
   actual.append(t)
 assert (len(actual)==10 if name in ('human','army') else len(actual)==3 if name=='reload' else len(actual)==0),(name,actual)
 cases.append({'case':name,'shots_and_events':actual,'army_hp':e[0].hp,'human_hp':p[0].hp,'authority_hash':f'{l.sim_checksum():016x}'})
print(json.dumps({'suite':'actual-infantry-rifle-events','passed':True,'ticks_per_case':80,'cases':cases,'core_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['Sparse initial finite stock/poses, no live health/ammo/clock renewal.','Event source body eye approximates muzzle; no aim direction, trajectory or hit claims.']}))
