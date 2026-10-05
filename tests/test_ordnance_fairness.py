#!/usr/bin/env python3
"""Independent production shell allocation oracle, with explicit legacy capture."""
import argparse
import collections
import ctypes as C
import hashlib
import json
import pathlib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('library')
parser.add_argument('--legacy', action='store_true', help='verify and record fixed-index baseline bias')
parser.add_argument('--report')
parser.add_argument('--dense-ticks', type=int, default=120)
args = parser.parse_args()
if not 1 <= args.dense_ticks <= 10000:
    parser.error('--dense-ticks must be in1..10000')
lib = C.CDLL(args.library)
lib.sim_checksum.restype = C.c_uint64
lib.sim_entity_height.argtypes = [C.c_uint]
lib.sim_entity_height.restype = C.c_float
lib.terrain_los.argtypes = [C.c_float] * 6

class Entity(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float)] + [(n, C.c_uint) for n in
        ('hp', 'side', 'kind', 'front')] + [('target', C.c_int), ('generation', C.c_uint)]

class Shell(C.Structure):
    _fields_ = [(n, C.c_float) for n in ('x','y','z','vx','vy','vz')] + [
        (n,C.c_uint) for n in ('ttl','side','kind','damage')] + [('radius',C.c_float)] + [
        (n,C.c_uint) for n in ('source','generation','active','source_generation','reserved')]

assert C.sizeof(Entity) == 32 and C.sizeof(Shell) == 64
entities = (Entity * 32768).in_dll(lib, 'sim_entities')
shells = (Shell * 512).in_dll(lib, 'sim_projectiles')
ammo = (C.c_uint * 32768).in_dll(lib, 'sim_shell_ammo')
cooldown = (C.c_uint * 32768).in_dll(lib, 'sim_shell_cooldown')
alive = (C.c_uint * 2).in_dll(lib, 'sim_alive')
count = C.c_uint.in_dll(lib, 'sim_projectile_count')
dropped = C.c_uint.in_dll(lib, 'sim_projectile_dropped')
hazard_enabled = C.c_uint.in_dll(lib, 'hazard_enabled')
try:
    ordnance_enabled = C.c_uint.in_dll(lib, 'ordnance_enabled')
except ValueError:
    ordnance_enabled = None


def fixture(units, kind, mirror=False, negative=None):
    """Keep finite original stores/roles; only initial deployment/health changes."""
    assert lib.sim_init(units, 42) == 0
    hazard_enabled.value = 0  # isolate allocation from the separately tested evasion policy
    if ordnance_enabled is not None:
        ordnance_enabled.value = int(not args.legacy)
    # Original kind1 index13 and kind2 index14 share one firing phase per class.
    index_mod = 13 if kind == 1 else 14
    ids = [i for i in range(units) if (i % 16 in (12, 13, 14) if kind == 0 else
                                      i % 16 == index_mod)]
    id_set = set(ids)
    for i, e in enumerate(entities[:units]):
        if i not in id_set:
            entities[i].hp = 0
            continue
        side = e.side ^ int(mirror)
        entities[i].side = side
        # Every source has an enemy in the adjacent250m spatial cell, within
        # both weapon ranges. Overlap is deliberate for an allocation stress,
        # and is not evidence for navigation/formation/crowd acceptance.
        entities[i].x = (1100, 1400)[side]
        entities[i].z = 2000
        entities[i].front = 0
        assert (e.kind == kind or kind == 0) and ammo[i] == 64 and cooldown[i] == 0
        if negative == 'no-los':
            entities[i].x = (3970, 4030)[side]
            entities[i].z = 1300
        elif negative == 'ammo':
            ammo[i] = 0
        elif negative == 'cooldown':
            cooldown[i] = 100
        elif negative == 'dead':
            entities[i].hp = 0
    side_ids = [[i for i in ids if entities[i].side == side] for side in (0, 1)]
    alive[0], alive[1] = ((0, 0) if negative == 'dead' else
                         (len(side_ids[0]), len(side_ids[1])))
    for side in (0, 1):
        for front in range(3):
            assert lib.sim_order(side, front, 1) == 0
    first, second = side_ids[0][0], side_ids[1][0]
    e, t = entities[first], entities[second]
    los = lib.terrain_los(e.x, lib.sim_entity_height(first), e.z,
                          t.x, lib.sim_entity_height(second), t.z)
    assert bool(los) == (negative != 'no-los')
    assert count.value == dropped.value == 0 and not any(p.active for p in shells)
    initial_ammo = {i: ammo[i] for i in ids}
    ticks = (4 if kind == 0 else 3 if kind == 1 else 2) if args.legacy else 1
    for _ in range(ticks):
        lib.sim_tick()
    launches = collections.Counter()
    group_launches = collections.Counter()
    sources = collections.Counter()
    for p in shells:
        if p.active:
            assert (p.kind == kind or kind == 0) and p.source in id_set
            assert p.kind == entities[p.source].kind
            group_launches[(p.side, p.kind)] += 1
            assert p.source_generation == entities[p.source].generation
            assert p.side == entities[p.source].side
            launches[p.side] += 1
            sources[p.source] += 1
    assert all(n == 1 for n in sources.values())
    spent = [sum(initial_ammo[i] - ammo[i] for i in side_ids[side]) for side in (0, 1)]
    grants = [launches[side] for side in (0, 1)]
    assert grants == spent and count.value == sum(grants)
    for i in ids:
        if i in sources:
            assert cooldown[i] > 0
        if negative is None:
            target = entities[i].target
            assert 0 <= target < units and entities[target].hp > 0
            assert entities[target].side != entities[i].side
            assert lib.terrain_los(entities[i].x, lib.sim_entity_height(i), entities[i].z,
                entities[target].x, lib.sim_entity_height(target), entities[target].z)
    result = {'units': units, 'initialized_entities': units,
        'initial_living_sources': [0,0] if negative == 'dead' else [len(x) for x in side_ids],
        'kind': kind, 'side_labels_mirrored': mirror,
        'negative': negative, 'eligible_sources': [len(x) for x in side_ids],
        'actual_retained_launches': grants, 'actual_ammunition_spent': spent,
        'pool_count': count.value, 'dropped': dropped.value,
        'actual_launches_by_side_kind': {f'{s}:{k}': group_launches[(s,k)]
                                       for s in (0,1) for k in (1,2)},
        'checksum': f'{lib.sim_checksum():016x}'}
    if negative is not None:
        assert grants == [0, 0] and dropped.value == 0
    else:
        assert sum(grants) == 416
        assert dropped.value == len(ids) - 416
        if args.legacy:
            per_side_first_phase = units // 32
            expected = [min(per_side_first_phase, 416), max(0, 416-per_side_first_phase)]
            if mirror:
                expected.reverse()
            assert grants == expected, result
        else:
            assert abs(grants[0] - grants[1]) <= 1, result
            if kind == 0:
                assert [group_launches[(s,k)] for s in (0,1) for k in (1,2)] == [104]*4, result
    return result


reports = []
for units in (8192, 16384):
    for kind in (0, 1, 2):
        for mirror in (False, True):
            report = fixture(units, kind, mirror)
            assert fixture(units, kind, mirror) == report, 'same-build replay differs'
            reports.append(report)
for negative in ('ammo', 'cooldown', 'no-los', 'dead'):
    for kind in (1, 2):
        reports.append(fixture(8192, kind, negative=negative))

# Continue a saturated original-role fixture through real travel, impacts and
# cooldowns. Record outcomes without forcing health, ammo, pool retirement or
# equal casualties. This is sustained physical pressure evidence, not a claim
# of equal grants after the two armies have different living/ready populations.
sustained = []
for mirror in (False, True):
    replay_reports = []
    for replay in range(2):
        initial = fixture(16384, 1, mirror)
        ids = [i for i in range(16384) if i % 16 == 13]
        initial_ammo = {i: 64 for i in ids}
        physically_ready_samples = [0, 0]
        pressure_ticks = 0
        for _ in range(120):
            for i in ids:
                e = entities[i]
                target = e.target
                if not e.hp or not ammo[i] or cooldown[i] or not 0 <= target < 16384:
                    continue
                t = entities[target]
                if t.hp and t.side != e.side and lib.terrain_los(
                        e.x, lib.sim_entity_height(i), e.z,
                        t.x, lib.sim_entity_height(target), t.z):
                    physically_ready_samples[e.side] += 1
            if count.value >= 416:
                pressure_ticks += 1
            lib.sim_tick()
        launches = [sum(initial_ammo[i] - ammo[i] for i in ids
                        if entities[i].side == side) for side in (0, 1)]
        survivors = [sum(bool(entities[i].hp) for i in ids
                         if entities[i].side == side) for side in (0, 1)]
        assert min(physically_ready_samples) > 0 and pressure_ticks > 0
        if not args.legacy:
            assert min(launches) > 0, 'one physically ready side starved for120 ticks'
        report = {'initialized_entities': 16384, 'initial_living_sources': [512,512],
            'side_labels_mirrored': mirror, 'continued_ticks': 120,
            'initial_volley': initial['actual_retained_launches'],
            'all_actual_launches_from_finite_ammo': launches,
            'physical_ready_source_tick_samples': physically_ready_samples,
            'ticks_starting_at_AI_ground_limit': pressure_ticks,
            'surviving_original_sources': survivors, 'dropped': dropped.value,
            'checksum': f'{lib.sim_checksum():016x}'}
        replay_reports.append(report)
    assert replay_reports[0] == replay_reports[1], 'sustained pressure replay differs'
    sustained.append(replay_reports[0])

# Natural seeded dense scenarios, with hazard response left enabled. New physical
# launch generations are sampled after real ticks, not inferred from dropped or
# engagement counters. Same-tick launch+retirement is intentionally unobserved.
dense = []
for mode, name in ((2, 'scale-front'), (3, 'scale-hotspot')):
    replay_reports = []
    for replay in range(2):
        assert lib.sim_init(8192, 42) == 0
        hazard_enabled.value = 1
        if ordnance_enabled is not None:
            ordnance_enabled.value = int(not args.legacy)
        assert lib.sim_scenario(mode) == 0
        previous = {}
        launch_counts = collections.Counter()
        source_sets = collections.defaultdict(set)
        peak = 0
        for _ in range(args.dense_ticks):
            lib.sim_tick()
            peak = max(peak, count.value)
            for slot, p in enumerate(shells):
                if not p.active or previous.get(slot) == p.generation:
                    continue
                previous[slot] = p.generation
                assert p.source < 8192 and p.side in (0, 1) and p.kind in (1, 2, 3, 4)
                assert p.source_generation == entities[p.source].generation
                launch_counts[(p.side, p.kind)] += 1
                source_sets[(p.side, p.kind)].add(p.source)
        report = {'scenario': name, 'seed': 42, 'ticks': args.dense_ticks,
            'initialized_entities': 8192, 'initial_living_army': [4096,4096],
            'retained_new_generations': {f'{s}:{k}': launch_counts[(s,k)]
                                        for s in (0,1) for k in (1,2,3,4)},
            'distinct_retained_sources': {f'{s}:{k}': len(source_sets[(s,k)])
                                         for s in (0,1) for k in (1,2,3,4)},
            'pool_peak': peak, 'dropped': dropped.value,
            'checksum': f'{lib.sim_checksum():016x}'}
        replay_reports.append(report)
    assert replay_reports[0] == replay_reports[1], 'dense replay differs'
    dense.append(replay_reports[0])
output = {'library_sha256': hashlib.sha256(pathlib.Path(args.library).read_bytes()).hexdigest(),
    'mode': 'legacy-fixed-index' if args.legacy else 'fair-acceptance',
    'isolated_world_allocations': reports, 'sustained_physical_pressure': sustained,
    'dense_world_samples': dense,
    'limits': ['dense launch samples omit same-tick retirement',
               'isolated allocation fixture uses overlapping initial sources',
               'no graphics/audio/network/combined-arms acceptance claim']}
if args.report:
    pathlib.Path(args.report).write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps(output))
print('PASS: actual world allocation, mirrored labels, eligibility negatives, finite ammo and replay')
