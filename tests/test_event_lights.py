#!/usr/bin/env python3
"""Real NASM cosmetic selection, real event producer, finite-budget controls."""
import ctypes as C, json, math, sys
l=C.CDLL(sys.argv[1]);l.event_lights_update.argtypes=[C.c_float]*3
l.effects_update.argtypes=[C.c_uint,C.c_float];l.combat_event.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
l.sim_checksum.restype=C.c_uint64
class Record(C.Structure):
 _fields_=[(n,C.c_float)for n in ('x','y','z','ttl','radius')]+[('seed',C.c_uint),('reserved',C.c_uint),('kind',C.c_uint)]
r=(Record*64).in_dll(l,'effects_records');count=C.c_uint.in_dll(l,'event_light_count')
p=(C.c_float*32).in_dll(l,'event_light_positions');c=(C.c_float*32).in_dll(l,'event_light_colours')
slots=(C.c_uint*8).in_dll(l,'event_light_slots');gain=C.c_float.in_dll(l,'event_lights_gain');enabled=C.c_uint.in_dll(l,'event_lights_enabled')
cases=0
assert l.sim_init(64,7)==0;assert l.player_join(0,0)==0
player=(C.c_float*16).in_dll(l,'sim_players');player[0],player[1],player[2]=2000,100,2000
l.effects_update(0,0)
def update(x=2000,y=100,z=2000,expected=0):
 global cases
 before=bytes(r);authority=l.sim_checksum();assert l.event_lights_update(x,y,z)==expected
 assert bytes(r)==before and l.sim_checksum()==authority,'lighting changed source or authority'
 assert count.value<=8 and all(math.isfinite(v)for v in (*p,*c));cases+=1
# Production event emitter -> production effects consumer -> new light consumer.
l.combat_event(9,1,2000,150,2000,2);authority=l.sim_checksum();l.effects_update(0,0);assert l.sim_checksum()==authority
update();assert count.value==1 and r[slots[0]].kind==2
assert abs(c[0]-8)<1e-5 and p[3]>=8
l.effects_update(0,.225);update();assert abs(c[0]-2)<1e-4,'half-life quadratic fade'
for _ in range(70):l.effects_update(0,1/120)
update();assert count.value==0,'expired flash persists'
l.combat_event(9,1,2000,150,2000,2)
for _ in range(90):l.sim_tick()
l.effects_update(0,0);update();assert count.value==0,'late event reignites light'
# Declared pool fixtures independently check selector; not invented gameplay.
def clear():C.memset(C.addressof(r),0,C.sizeof(r))
def put(i,x=2000,y=100,z=2000,ttl=.45,radius=2,kind=2):
 r[i]=Record(x,y,z,ttl,radius,17,0,kind)
clear()
for i in range(64):put(i,x=2000+63-i)
update();assert count.value==8 and list(slots)==list(range(63,55,-1))
for i in range(64):put(i)
update();assert list(slots)==list(range(8)),'unstable equal-distance selection'
for kind in (0,1,3,4,5,7,8,9,10):
 clear();put(0,kind=kind);update();assert count.value==0
for field,values in [('x',(-1000,-.01,8000.01,float('nan'),float('inf'))),('z',(-1000,-.01,8000.01,float('nan'))),('y',(-1000.01,1000.01,float('nan'),float('inf'))),('ttl',(-1,0,.451,float('nan'),float('inf'))),('radius',(-1,.249,12.01,float('nan'),float('inf')))]:
 for value in values:
  clear();put(0);setattr(r[0],field,value);update();assert count.value==0,(field,value)
clear();put(0,x=0,y=-1000,z=8000,radius=12);update();assert count.value==1 and p[3]==72
clear();put(0,radius=.25,ttl=.065);update();assert count.value==1 and p[3]==8 and abs(p[1]-100.5)<1e-5 and abs(c[0]-3)<1e-5
for value in (-.1,1.01,float('nan'),float('inf')):
 gain.value=value;update(expected=-1);assert count.value==0 and not any(p)and not any(c)
gain.value=.5;update();assert abs(c[0]-1.5)<1e-5
gain.value=1
for camera in ((float('nan'),0,0),(0,float('inf'),0),(0,0,16000.1)):
 update(*camera,expected=-1);assert count.value==0
enabled.value=0;update(float('nan'),0,0);assert count.value==0
clear();enabled.value=1;update();assert count.value==0
observations=(C.c_uint64*6)();l.probe_event_lights_update.argtypes=[C.c_void_p]+[C.c_float]*3
assert l.probe_event_lights_update(observations,2000,100,2000)==0
assert list(observations)==list(range(0x123401,0x123407))
print(json.dumps(dict(suite='event-lights-native',passed=True,cases=cases,cap=8,producer='production combat_event and effects_update',expiry_late_receipt=True,nearest_stable=True,invalid_records_and_controls=True,authority_and_source_unchanged=True,register_stack_abi=True,scope='NASM selection and lifecycle; synthetic pool fixtures declared separately from real event producer. No GPU or artistic acceptance.')))
