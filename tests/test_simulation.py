#!/usr/bin/env python3
"""Development-only ABI and combat checks. Usage: test_simulation.py HEADLESS LIBSIM."""
import ctypes as C
import json
import subprocess
import sys

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
    original = [(e.x, e.z) for e in entities[:count]]
    assert set(e.kind for e in entities[:count]) == {0, 1, 2, 3}
    assert set(e.front for e in entities[:count]) == {0, 1, 2}
    assert list(alive) == [count // 2] * 2
    for side in (0, 1):
        for front in range(3):
            assert lib.sim_order(side, front, 1) == 0
    lib.sim_tick()
    assert original == [(e.x, e.z) for e in entities[:count]]
    for side in (0, 1):
        for front in range(3):
            assert lib.sim_order(side, front, 2) == 0
    lib.sim_tick()
    assert all(e.x < original[i][0] if e.side == 0 else e.x > original[i][0]
               for i, e in enumerate(entities[:count]) if e.hp > 0)
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
results = []
for _ in range(2):
    result = json.loads(subprocess.check_output([exe, '--units', '8192', '--ticks', '600', '--seed', '1']))
    assert result['units'] == 8192 and sum(result['alive']) < 8192 and result['engaged'] > 0
    assert 0 <= result['tick_mean_ms'] and 0 <= result['tick_p95_ms']
    results.append(result)
assert results[0]['checksum'] == results[1]['checksum']
print('PASS: baseline/stretch replay, counts, roles, fronts, orders, casualties, bounds, local fire and CLI')
