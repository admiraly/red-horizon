#!/usr/bin/env python3
"""Development-only fixtures exercise the actual NASM cosmetic/authority modules."""
import ctypes as C
import json
import math
import sys
lib = C.CDLL(sys.argv[1])
lib.air_trails_update.argtypes = [C.c_uint, C.c_float]
lib.effects_update.argtypes = [C.c_uint, C.c_float]
lib.sim_checksum.restype = C.c_uint64
class Entity(C.Structure):
    _fields_ = [(n, C.c_float) for n in ('x', 'z')] + [(n, C.c_uint) for n in ('hp', 'side', 'kind', 'front', 'target', 'generation')]
class Air(C.Structure):
    _fields_ = [(n, C.c_float) for n in ('y', 'heading', 'pitch', 'bank', 'speed')] + [(n, C.c_uint) for n in ('role', 'mode', 'target', 'cooldown', 'ammo', 'generation')] + [(n, C.c_float) for n in ('vx', 'vy', 'vz')] + [(n, C.c_uint) for n in ('pass_ticks', 'flags')]
class Record(C.Structure):
    _fields_ = [(n, C.c_float) for n in ('x', 'y', 'z', 'ttl', 'radius', 'spare1', 'spare2')] + [('kind', C.c_uint)]
entities = (Entity * 32768).in_dll(lib, 'sim_entities')
air = (Air * 32768).in_dll(lib, 'sim_aircraft')
records = (Record * 128).in_dll(lib, 'air_trails_records')
fx = (Record * 64).in_dll(lib, 'effects_records')
player = (C.c_float * 64).in_dll(lib, 'sim_players')
player_u = (C.c_uint * 64).in_dll(lib, 'sim_players')
active = C.c_uint.in_dll(lib, 'air_trails_active')
emitted = C.c_uint.in_dll(lib, 'air_trails_emitted')
def init():
    assert lib.sim_init(32, 23) == 0
    for e in entities[:32]: e.hp = 0
    entities[15].hp = 200
    assert lib.player_join(0, 0) == 0
    player_u[11] = 0
    lib.air_trails_update(0, 0)  # legitimate disconnected observer clears cosmetics
    player_u[11] = 1
    player[0], player[2] = entities[15].x, entities[15].z
    lib.sim_tick()  # sidecar initialized by real aircraft authority
    assert air[15].generation == entities[15].generation and air[15].flags & 1

def snapshot():
    return (lib.sim_checksum(), bytes(entities), bytes(air), bytes((C.c_ubyte * 8192).in_dll(lib, 'sim_events')), bytes((C.c_ubyte * 32768).in_dll(lib, 'sim_projectiles')), bytes(player))
init()
before = snapshot()
lib.air_trails_update(0, .11)
assert snapshot() == before, 'cosmetic update wrote authority'
live = [r for r in records if r.ttl > 0]
assert len(live) == active.value == 1 and live[0].kind == 6
assert abs(live[0].y - (air[15].y - air[15].vy * 1.4)) < .001
assert abs(live[0].x - (entities[15].x - air[15].vx * 1.4)) < .001
n = emitted.value
for _ in range(400): lib.air_trails_update(0, 1/120)
assert emitted.value == n and active.value == 0, 'frozen authority replayed or trails failed expiry'
# Rates run identical real30Hz aircraft flight, without changing cosmetic state at ticks.
rates = []
for rate in (30, 60, 120):
    init(); start = emitted.value
    for frame in range(rate):
        if frame % (rate // 30) == 0: lib.sim_tick()
        before = lib.sim_checksum()
        lib.air_trails_update(0, 1 / rate)
        assert before == lib.sim_checksum()
    rates.append(emitted.value - start)
assert max(rates) - min(rates) <= 1, rates  # floating boundary within one sampling interval
init(); entities[15].hp = 75
lib.air_trails_update(0, .11)
assert any(r.ttl > 0 and r.kind == 7 for r in records), 'real damage did not smoke'
for bad in (-1., float('nan'), float('inf'), -float('inf')):
    saved = bytes(records)
    lib.air_trails_update(0, bad)
    assert bytes(records) == saved, ('invalid frame time', bad)
# Very large finite elapsed time is clipped: cannot turn negative or lengthen life.
saved = [r.ttl for r in records]
lib.air_trails_update(0, 1e30)
assert all(0 <= r.ttl <= old for r, old in zip(records, saved))
entities[15].generation += 1
lib.air_trails_update(0, 0)
assert active.value == 0, 'recycled actor kept predecessor smoke'
init(); lib.air_trails_update(0, .11); air[15].flags = 0
lib.air_trails_update(0, 0); assert active.value == 0
init(); lib.air_trails_update(0, .11); entities[15].hp = 0
lib.air_trails_update(0, 0); assert active.value == 0
init(); lib.air_trails_update(0, .11); player[0] += 1300
lib.air_trails_update(0, 0); assert active.value == 0
init(); lib.air_trails_update(0, .11); player_u[11] = 0
lib.air_trails_update(0, 0); assert active.value == 0
# Stress the emission cap and rotating scan:1,024actual aircraft sidecars.
assert lib.sim_init(1024, 23) == 0
for i, e in enumerate(entities[:1024]):
    e.x, e.z, e.hp, e.kind, e.side = 3500. + i % 16, 3500. + i // 16, 200, 3, 0
assert lib.player_join(0, 0) == 0
player[0], player[2] = 3500., 3500.
player_u[11] = 0; lib.air_trails_update(0, 0); player_u[11] = 1
for _ in range(10):
    lib.sim_tick(); start = emitted.value; before = snapshot()
    lib.air_trails_update(0, .11)
    assert snapshot() == before
    assert emitted.value - start == 32, 'unstable or unbounded sampling'
    assert active.value <= 128
assert active.value == 128 and all(math.isfinite(r.ttl) and r.ttl <= 2.5 for r in records)
# Real bomb/destruction event consumer; fixture only invokes production event emitter.
lib.combat_event.argtypes = [C.c_uint, C.c_uint, C.c_float, C.c_float, C.c_float, C.c_float]
init()
lib.combat_event(7, 0, player[0], 20., player[2], 9.)
lib.combat_event(9, 0, player[0], 150., player[2], 9.)
before = snapshot(); lib.effects_update(0, .01)
assert snapshot() == before
kinds = [r.kind for r in fx if r.ttl > 0]
assert 5 in kinds and kinds.count(4) == 8 and kinds.count(3) == 4, kinds
n = C.c_uint.in_dll(lib, 'effects_impacts').value
for _ in range(360): lib.effects_update(0, 1/120)
assert all(r.ttl == 0 for r in fx)
assert C.c_uint.in_dll(lib, 'effects_impacts').value == n
lib.combat_event(7, 0, player[0], 20., player[2], 9.)
for _ in range(30): lib.sim_tick()
before = snapshot(); lib.effects_update(0, .01)
assert snapshot() == before
assert not any(r.kind == 2 and r.ttl > 0 for r in fx), 'late impact restarted hot flash'
assert all(r.ttl <= 1.5 for r in fx), 'late event restarted smoke lifetime'
print(json.dumps({'suite':'air-trails','passed':True,'samples_at_30_60_120Hz':rates,'authority_bytes_unchanged':True,'invalid_time_generation_death_disconnect_expiry':True,'event_layers':kinds}))
