#!/usr/bin/env python3
"""Bounded real event-emitter consumer, delayed receipt and frame expiry fixtures."""
import ctypes as C,json,struct,sys
l=C.CDLL(sys.argv[1]);l.sim_checksum.restype=C.c_uint64;l.effects_update.argtypes=[C.c_uint,C.c_float];l.combat_event.argtypes=[C.c_uint,C.c_uint]+[C.c_float]*4
class Record(C.Structure):_fields_=[(n,C.c_float)for n in ('x','y','z','ttl','radius')]+[('seed',C.c_uint),('reserved',C.c_uint),('kind',C.c_uint)]
records=(Record*64).in_dll(l,'effects_records');cursor=C.c_uint.in_dll(l,'effects_event_cursor');quads=C.c_uint.in_dll(l,'effects_particle_quads');sequence=C.c_uint.in_dll(l,'sim_event_sequence')
assert l.sim_init(64,7)==0
entities=(C.c_uint*(64*8)).in_dll(l,'sim_entities')
for i in range(64):entities[i*8+2]=0
assert l.player_join(0,0)==0
player=(C.c_float*16).in_dll(l,'sim_players');player[0],player[1],player[2]=2000,100,2000
l.effects_update(0,0)
def emit():l.combat_event(9,1,2000,150,2000,2)
def update(dt):
 before=l.sim_checksum();l.effects_update(0,dt);assert l.sim_checksum()==before,'cosmetic consumer changed authority'
def live():return [r for r in records if r.ttl>0]
emit();identity=sequence.value;update(0);initial=[(r.kind,r.ttl,r.radius,r.seed)for r in live()]
assert sorted(r.kind for r in live())==[2,8,9],initial
assert all(r.seed==identity and r.radius==8 for r in live()if r.kind in (8,9))
assert quads.value==25,quads.value
original=bytes(records);update(0);assert bytes(records)==original,'repeated snapshot spawned particles'
for _ in range(840):update(1/120)
assert not live(),'six-second smoke did not expire'
# Event produced now, then received three seconds later by the cosmetic consumer.
emit();identity=sequence.value
for _ in range(90):l.sim_tick()
update(0);late=[(r.kind,r.ttl,r.radius,r.seed)for r in live()]
assert len(late)==1 and late[0]==(8,3.,8.,identity),late
for _ in range(840):update(1/120)
# Delayed beyond maximum lifetime: cannot rekindle fire, fragments or smoke.
emit()
for _ in range(181):l.sim_tick()
update(0);assert not live()
# Genuine emitter saturation. No invented cosmetic pool writes or allocation.
for _ in range(100):emit()
update(0);assert len(live())==64
assert all(r.kind in (2,8,9) and r.ttl<=6 for r in live())
assert cursor.value==sequence.value
count=len(live());saturated_quads=quads.value;assert saturated_quads<=1024
before=bytes(records);update(0);assert bytes(records)==before
for bad in (float('nan'),float('inf'),-float('inf'),-1):update(bad)
assert bytes(records)==before,'invalid render delta moved the particle clock'
for _ in range(840):update(1/120)
assert not live()
emit();update(0);assert live()
assert l.sim_init(64,7)==0
update(0);assert not live() and quads.value==0,'old stream particles survived reset'
print(json.dumps({'suite':'air-burst-event-consumer','passed':True,'initial_layers':initial,'three_second_late_layers':late,'frame_updates':2520,'saturation_events':100,'bounded_records':count,'saturated_particle_quads':saturated_quads,'absolute_quads_cap':1024,'authority_unchanged':True,'duplicate_invalid_delta_expiry_and_stream_reset':True,'scope':'Production event-emitter kernel fixtures; real physical cannon death is separately verified in client aircraft GL. No network or artistic acceptance from this test.'}))
