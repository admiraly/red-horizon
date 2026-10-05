#!/usr/bin/env python3
"""Development operation scenarios over assembly state, not a Python simulation."""
import ctypes as C
import sys
lib = C.CDLL(sys.argv[1])
lib.sim_init.argtypes = [C.c_uint, C.c_uint]
lib.sim_spend.argtypes = [C.c_uint, C.c_uint]
lib.sim_checksum.restype = C.c_uint64
class Entity(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float), ('hp', C.c_uint), ('side', C.c_uint),
                ('kind', C.c_uint), ('front', C.c_uint), ('target', C.c_int), ('generation', C.c_uint)]
class Site(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float), ('owner', C.c_uint), ('capture', C.c_int),
                ('role', C.c_uint), ('connected', C.c_uint), ('health', C.c_uint), ('flags', C.c_uint)]
assert C.sizeof(Site) == 32
entities = (Entity * 32768).in_dll(lib, 'sim_entities')
sites = (Site * 12).in_dll(lib, 'sim_sites')
req = (C.c_uint * 2).in_dll(lib, 'sim_requisition')
supply = (C.c_uint * 2).in_dll(lib, 'sim_supply')
state = C.c_uint.in_dll(lib, 'sim_operation_state')
tick = C.c_uint.in_dll(lib, 'sim_tick_count')
alive = (C.c_uint * 2).in_dll(lib, 'sim_alive')
def reset():
    assert lib.sim_init(32, 1) == 0
    for e in entities[:32]:
        e.hp = 0
    alive[0] = alive[1] = 0
    assert list(supply) == [600, 600] and state.value == 0

def occupy(indices, side):
    for e in entities[:32]:
        e.hp = 0
    alive[0] = alive[1] = 0
    for i, site_index in enumerate(indices):
        e, site = entities[i], sites[site_index]
        e.x, e.z, e.side, e.hp = site.x, site.z, side, 100
        alive[side] += 1

def seconds(n):
    for _ in range(n):
        tick.value += 30
        lib.operation_tick()

reset()
assert lib.sim_spend(0, 0) == -1
assert lib.sim_spend(2, 1) == -1
assert lib.sim_spend(0, 101) == -1 and req[0] == 100
assert lib.sim_spend(0, 100) == 0 and req[0] == 0
assert lib.sim_spend(0, 0xffffffff) == -1 and req[0] == 0
req[0] = 0xffffffff - 1
seconds(1)
assert req[0] == 0xffffffff  # saturating income, no wrap
assert lib.sim_spend(0, 0xffffffff) == 0 and req[0] == 0
# Dead presence cannot capture; contested living presence pauses progress.
reset()
occupy([2], 0)
entities[0].hp = 0
seconds(25)
assert sites[2].owner == 1 and sites[2].capture == 10
occupy([2], 0)
entities[1].hp, entities[1].side = 100, 1
entities[1].x, entities[1].z = sites[2].x, sites[2].z
seconds(4)
assert sites[2].capture == 10 and sites[2].flags & 4
# Capture an enemy corridor; cutting all parallel roads isolates owned sites.
reset()
occupy([2, 6, 10], 0)
seconds(19)
assert sites[2].owner == 1
seconds(1)
assert all(sites[i].owner == 0 and sites[i].connected for i in (2, 6, 10))
assert supply[0] == 900
income_before_cut = req[0]
occupy([1, 5, 9], 1)
seconds(20)
assert all(sites[i].owner == 1 for i in (1, 5, 9))
assert all(not sites[i].connected for i in (2, 6, 10))
assert supply[0] == 300
req[0] = 0
seconds(1)
assert req[0] == 9  # only the three still-connected left-column sites
occupy([1, 5, 9], 0)
seconds(20)
assert supply[0] == 900
req[0] = 0
seconds(1)
assert req[0] == 48  # three production sites restore connected capacity/income
# Enemy command captured by living allies ends the operation in victory.
reset()
occupy([3], 0)
seconds(20)
assert sites[3].owner == 0 and state.value == 1
seconds(1)
assert state.value == 1
# Allied command loss exposes thirty visible evaluations of final defense.
reset()
occupy([0], 1)
seconds(20)
assert state.value == 3 and supply[0] == 0
seconds(28)
assert state.value == 3
seconds(1)
assert state.value == 2
# Reclaim within the warning window through actual allied occupation.
reset()
occupy([0], 1)
seconds(20)
assert state.value == 3
# The 30-second warning allows a full 20-second recapture.
occupy([0], 0)
seconds(20)
assert sites[0].owner == 0 and state.value == 0 and supply[0] == 600
# Full world ticks invoke capture at the fixed cadence, with no Python updates.
reset()
occupy([3], 0)
assert lib.sim_order(0, 0, 1) == 0
for _ in range(600):
    lib.sim_tick()
assert state.value == 1 and sites[3].owner == 0
# Operation ownership, resources and warning counters affect replay checksum.
reset()
hash_before = lib.sim_checksum()
assert lib.sim_spend(0, 1) == 0
assert lib.sim_checksum() != hash_before
hashes = []
for _ in range(2):
    reset()
    occupy([2, 6, 10], 0)
    seconds(20)
    hashes.append(lib.sim_checksum())
assert hashes[0] == hashes[1]
print('PASS: real occupancy capture/contest, connectivity cut/restoration, income/spend bounds, victory, final defense/defeat and operation replay')
