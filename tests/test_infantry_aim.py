#!/usr/bin/env python3
"""Actual nearest-visible decisions publish poses independent of finite fire/movement."""
import ctypes as C,json,math,pathlib,sys,struct,hashlib
prefix=pathlib.Path(__file__).with_name('test_infantry_human_targets.py').read_text().split('closer=run(')[0];exec(compile(prefix,'<actual physical fixture>','exec'))
l.infantry_aim_mark.argtypes=[C.c_uint]*3;poses=(C.c_ubyte*(32768*32)).in_dll(l,'infantry_aims')
def pose(i):return struct.unpack_from('<2I5fI',poses,i*32)
reports=[]
for name,army,human,empty in [('near-human',(2110.,3900.),(2000.,3900.),False),('near-army',(2070.,3900.),(2000.,3900.),False),('exact-tie',(2100.,3900.),(2000.,3900.),False),('empty-human',(2110.,3900.),(2000.,3900.),True)]:
 setup(army,(human,))
 if empty:w[136:144]=[1,0,0,0,120,0,0,0]
 initial=tuple((v.x,v.z)for v in e[:32])
 for _ in range(7):l.sim_tick()
 row=pose(17);expected_human=name in ('near-human','empty-human');target=(p[0].x,p[0].y,p[0].z)if expected_human else(e[0].x,l.terrain_height(e[0].x,e[0].z)+2,e[0].z)
 assert row[0:2]==(1,7)and row[4:7]==target,row
 heading=math.atan2(target[0]-e[17].x,target[2]-e[17].z);pitch=math.atan2(target[1]-l.terrain_height(e[17].x,e[17].z)-2,math.hypot(target[0]-e[17].x,target[2]-e[17].z))
 assert abs(row[2]-heading)<1e-6 and abs(row[3]-pitch)<1e-6,row
 assert row[7]==(3 if empty else 7 if expected_human else 5),row
 assert all((v.x,v.z)==initial[i]for i,v in enumerate(e[:32])if v.hp>0),'aim changed held locomotion'
 reports.append({'case':name,'pose':row,'weapon_spent':w[140],'human_hp':p[0].hp,'army_hp':e[0].hp})
# Publication gates are static API fixtures, never live health/weapon renewal.
setup();before=bytes(poses);authority=l.sim_checksum()
for args in [(32,0,0),(17,32,0),(17,4,1),(17,0,2),(0,0,1)]:assert l.infantry_aim_mark(*args)==-1 and bytes(poses)==before and l.sim_checksum()==authority,args
setup((4030.,1450.),((3970.,1300.),),enemy=(4030.,1300.));e[0].x,e[0].z=7000.,7000.
for _ in range(16):l.sim_tick()
assert pose(17)[7]==0,'hidden target acquired an aim pose'
print(json.dumps({'suite':'actual-visible-infantry-aim','passed':True,'cases':reports,'invalid_publication_atomic':True,'hidden_target_not_aimed':True,'core_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':['Declared sparse initial poses/finite expenditure; actual visibility/arbitration/ticks thereafter.','Aim is cosmetic last observation, not a new firing cone or strategic perception model.']}))
