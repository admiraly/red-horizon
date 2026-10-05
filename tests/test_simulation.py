#!/usr/bin/env python3
"""Development-only ABI and combat checks. Usage: test_simulation.py HEADLESS LIBSIM."""
import ctypes as C
import json
import subprocess
import sys
import time

exe, library = sys.argv[1:]
lib = C.CDLL(library)
lib.sim_init.argtypes = [C.c_uint, C.c_uint]
lib.sim_init.restype = C.c_int
lib.sim_order.argtypes = [C.c_uint, C.c_uint, C.c_uint]
lib.sim_fire.argtypes = [C.c_uint, C.c_uint]
lib.sim_checksum.restype = C.c_uint64
class Entity(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float), ('hp', C.c_uint),
                ('side', C.c_uint), ('kind', C.c_uint), ('front', C.c_uint),
                ('target', C.c_int), ('generation', C.c_uint)]
entities = (Entity * 32768).in_dll(lib, 'sim_entities')
alive = (C.c_uint * 2).in_dll(lib, 'sim_alive')
assert C.sizeof(Entity) == 32
lib.sim_tick()  # empty-state guard
assert isinstance(lib.sim_checksum(), int)
for edge_count in (2, 32768):
    assert lib.sim_init(edge_count, 0) == 0
    lib.sim_tick()
    assert sum(alive) <= edge_count
for count in (8192, 16384):
    assert lib.sim_init(count, 7) == 0
    # Exact order-direction checks isolate imminent danger interruptions.
    # The following fresh default-world replay keeps danger enabled.
    C.c_uint.in_dll(lib,'hazard_enabled').value=0
    original = [(e.x, e.z) for e in entities[:count]]
    assert set(e.kind for e in entities[:count]) == {0, 1, 2, 3}
    assert set(e.front for e in entities[:count]) == {0, 1, 2}
    assert list(alive) == [count // 2] * 2
    for side in (0, 1):
        for front in range(3):
            assert lib.sim_order(side, front, 1) == 0
    lib.sim_tick()
    assert all(original[i]==(e.x,e.z) for i,e in enumerate(entities[:count]) if e.kind!=3)
    assert all(original[i]!=(e.x,e.z) for i,e in enumerate(entities[:count]) if e.kind==3)
    for side in (0, 1):
        for front in range(3):
            assert lib.sim_order(side, front, 2) == 0
    lib.sim_tick()
    assert all(e.x < original[i][0] if e.side == 0 else e.x > original[i][0]
               for i, e in enumerate(entities[:count]) if e.hp > 0 and e.kind!=3)
    assert lib.sim_init(count, 7) == 0
    lib.sim_tick()
    assert any((e.x, e.z) != original[i] for i, e in enumerate(entities[:count]))
    for _ in range(299):
        lib.sim_tick()
    assert sum(alive) < count
    assert list(alive) == [sum(e.hp > 0 and e.side == side for e in entities[:count])
                           for side in (0, 1)]
    assert all(0 <= e.x <= 8000 and 0 <= e.z <= 8000 and e.generation == 1
               and -1 <= e.target < count for e in entities[:count])
    checksum = lib.sim_checksum()
    assert lib.sim_init(count, 7) == 0
    for _ in range(300):
        lib.sim_tick()
    assert lib.sim_checksum() == checksum
# Side-label swap at identical defensive positions must preserve every actor's
# health and exchange casualty totals. This catches side/index targeting bias.
fixture_count = 8192
outcomes = []
for swapped in (False, True):
    assert lib.sim_init(fixture_count, 19) == 0
    # Ground hold symmetry is isolated from side-dependent aircraft approach goals.
    for entity in entities[:fixture_count]:
        if entity.kind==3:entity.kind=0
    if swapped:
        for entity in entities[:fixture_count]:
            entity.side ^= 1
    for side in (0, 1):
        for front in range(3):
            assert lib.sim_order(side, front, 1) == 0
    for _ in range(400):
        lib.sim_tick()
    outcomes.append(([e.hp for e in entities[:fixture_count]], list(alive)))
assert outcomes[0][0] == outcomes[1][0]
assert outcomes[0][1] == outcomes[1][1][::-1]
assert sum(outcomes[0][1]) < fixture_count
assert lib.sim_init(32, 1) == 0
previous = lib.sim_checksum()
for invalid in (0, 1, 3, 32769, 0xffffffff):
    assert lib.sim_init(invalid, 1) == -1
    assert lib.sim_checksum() == previous
for args in ((2, 0, 0), (0, 3, 0), (0, 0, 3)):
    assert lib.sim_order(*args) == -1
for args in ((0, 1), (32, 1), (16, 0), (16, 101)):
    assert lib.sim_fire(*args) == -1
assert lib.sim_fire(16, 100) == 0
assert entities[16].hp == 0 and alive[1] == 15
assert lib.sim_fire(16, 1) == -1 and alive[1] == 15
for args in (['--units', '1'], ['--ticks', '0'], ['--seed', '-1'],
             ['--seed', '4294967296'], ['--ticks', 'x'], ['--units'], ['--bogus', '2']):
    assert subprocess.run([exe, *args], capture_output=True).returncode == 2
started = time.monotonic()
realtime = json.loads(subprocess.check_output([exe, "--realtime", "--ticks", "3", "--units", "32"]))
assert realtime["ticks"] == 3 and time.monotonic() - started >= 0.09
unpaced = json.loads(subprocess.check_output([exe, "--ticks", "3", "--units", "32"]))
assert realtime["checksum"] == unpaced["checksum"]
results = []
for _ in range(2):
    result = json.loads(subprocess.check_output([exe, '--units', '8192', '--ticks', '600', '--seed', '1']))
    assert result['units'] == 8192 and sum(result['alive']) < 8192 and result['engaged'] > 0
    assert 0 <= result['tick_mean_ms'] and 0 <= result['tick_p95_ms']
    results.append(result)
assert results[0]['checksum'] == results[1]['checksum']
print('PASS: baseline/stretch replay, counts, roles, fronts, orders, casualties, bounds, local fire, side-swap symmetry, realtime pacing and CLI')
