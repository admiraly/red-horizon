#!/usr/bin/env python3
"""Real regional combat in the full army; no renderer/visibility acceptance claim."""
import collections
import ctypes as C
import json
import math
import sys

lib = C.CDLL(sys.argv[1])
lib.sim_checksum.restype = C.c_uint64
lib.terrain_blocked.argtypes = [C.c_float, C.c_float, C.c_uint]
lib.terrain_height.argtypes = [C.c_float, C.c_float]
lib.terrain_height.restype = C.c_float
lib.terrain_los.argtypes = [C.c_float] * 6


class Entity(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float)] + [
        (n, C.c_uint) for n in ('hp', 'side', 'kind', 'front')
    ] + [('target', C.c_int), ('generation', C.c_uint)]


class Event(C.Structure):
    _fields_ = [(n, C.c_float) for n in ('x', 'y', 'z')] + [
        (n, C.c_uint) for n in ('kind', 'side', 'tick')
    ] + [('radius', C.c_float), ('sequence', C.c_uint)]


entities = (Entity * 32768).in_dll(lib, 'sim_entities')
events = (Event * 256).in_dll(lib, 'sim_events')
projectiles = (C.c_ubyte * (512 * 64)).in_dll(lib, 'sim_projectiles')
count = C.c_uint.in_dll(lib, 'sim_count')
alive = (C.c_uint * 2).in_dll(lib, 'sim_alive')
projectile_count = C.c_uint.in_dll(lib, 'sim_projectile_count')
projectile_dropped = C.c_uint.in_dll(lib, 'sim_projectile_dropped')
event_sequence = C.c_uint.in_dll(lib, 'sim_event_sequence')
shell_ammo = (C.c_uint * 32768).in_dll(lib, 'sim_shell_ammo')
shell_cooldown = (C.c_uint * 32768).in_dll(lib, 'sim_shell_cooldown')


def snapshot():
    return [(e.x, e.z, e.hp, e.side, e.kind, e.front, e.target, e.generation)
            for e in entities[:count.value]]


def rejected(mode):
    checksum = lib.sim_checksum()
    before = snapshot()
    ring, pool = bytes(events), bytes(projectiles)
    assert lib.sim_scenario(mode) == -1
    assert lib.sim_checksum() == checksum and snapshot() == before
    assert bytes(events) == ring and bytes(projectiles) == pool


def physical_targets(regional):
    """Count actual living ground attackers/targets, not sim_engaged telemetry."""
    result = collections.Counter()
    for i in regional:
        e = entities[i]
        if not e.hp or e.kind == 3 or not 0 <= e.target < count.value:
            continue
        target = entities[e.target]
        if not target.hp or target.side == e.side or target.kind == 3:
            continue
        distance2 = (target.x - e.x) ** 2 + (target.z - e.z) ** 2
        # Independently enforce documented physical weapon ranges (metres).
        if distance2 > (240, 450, 650)[e.kind] ** 2 + .01:
            continue
        if lib.terrain_los(e.x, lib.terrain_height(e.x, e.z) + 2, e.z,
                           target.x, lib.terrain_height(target.x, target.z) + 2,
                           target.z):
            result[e.side] += 1
    return result


reports = []
for mode, name in ((2, 'scale-front'), (3, 'scale-hotspot')):
    replays = []
    for replay in range(2):
        assert lib.sim_init(8192, 42) == 0
        for invalid in (-1, 4, 99):
            rejected(invalid)
        unchanged = lib.sim_checksum()
        assert lib.sim_scenario(0) == 0 and lib.sim_checksum() == unchanged
        before = snapshot()
        ring, pool = bytes(events), bytes(projectiles)
        ground_stores = bytes(shell_ammo), bytes(shell_cooldown)
        assert lib.sim_scenario(mode) == 0
        initial = snapshot()
        assert count.value == 8192 and list(alive) == [4096, 4096]
        assert [e[2:] for e in initial] == [e[2:] for e in before], \
            'fixture changed health, side, role, front, target or generation'
        assert bytes(events) == ring and bytes(projectiles) == pool, \
            'fixture fabricated ordnance or combat events'
        assert ground_stores == (bytes(shell_ammo), bytes(shell_cooldown)), \
            'fixture changed ground ammunition or firing cadence'
        roles = collections.Counter((e[3], e[4]) for e in initial)
        assert roles == collections.Counter({(side, kind): amount
            for side in (0, 1) for kind, amount in ((0, 3072), (1, 512),
                                                   (2, 256), (3, 256))})
        regional = {i for i, (old, new) in enumerate(zip(before, initial))
                    if old[:2] != new[:2] and new[4] != 3}
        assert len(regional) >= 2048
        assert min(collections.Counter(initial[i][3] for i in regional).values()) >= 1024
        # One genuinely concentrated regional offensive rather than full-map totals.
        assert max(initial[i][0] for i in regional) - min(initial[i][0] for i in regional) <= 1500
        assert max(initial[i][1] for i in regional) - min(initial[i][1] for i in regional) <= 1500
        assert all(math.isfinite(e.x) and math.isfinite(e.z)
                   and 0 <= e.x <= 8000 and 0 <= e.z <= 8000
                   and not lib.terrain_blocked(e.x, e.z, e.kind)
                   for e in entities[:8192])
        engaged_samples = []
        observed_events = collections.Counter()
        peak_projectiles = 0
        for tick in range(1, 121):
            lib.sim_tick()
            assert count.value == 8192
            peak_projectiles = max(peak_projectiles, projectile_count.value)
            for event in events:
                if event.sequence and event.tick == tick:
                    observed_events[event.kind] += 1
            if tick in (1, 8, 16, 30):
                valid = physical_targets(regional)
                engaged_samples.append({'tick': tick,
                    'living_regional_target_valid': sum(valid.values()),
                    'per_side': [valid[0], valid[1]]})
        assert max(s['living_regional_target_valid'] for s in engaged_samples) >= 2048, engaged_samples
        assert all(max(s['per_side'][side] for s in engaged_samples) >= 512
                   for side in (0, 1)), engaged_samples
        final = snapshot()
        moved = sum(e[:2] != initial[i][:2] for i, e in enumerate(final) if i in regional)
        damaged = sum(e[2] < initial[i][2] for i, e in enumerate(final) if i in regional)
        assert moved >= 1024 and damaged > 0, (moved, damaged)
        assert observed_events[1] > 0 and observed_events[2] > 0, observed_events
        assert observed_events[3] + observed_events[4] > 0, observed_events
        assert peak_projectiles > 0
        for side in (0, 1):
            assert alive[side] == sum(e[2] > 0 and e[3] == side for e in final)
        assert all(math.isfinite(e.x) and math.isfinite(e.z)
                   and 0 <= e.x <= 8000 and 0 <= e.z <= 8000
                   and not lib.terrain_blocked(e.x, e.z, e.kind)
                   for e in entities[:8192] if e.hp)
        result = {'scenario': name, 'army_initial': 8192,
                  'initial_per_side': [4096, 4096],
                  'initial_role_counts_per_side': [3072, 512, 256, 256],
                  'relocated_ground_actors': len(regional),
                  'physical_engagement_samples': engaged_samples,
                  'regional_moved_120ticks': moved,
                  'regional_damaged_120ticks': damaged,
                  'retained_actual_combat_events_120ticks': dict(observed_events),
                  'total_events_emitted_120ticks': event_sequence.value,
                  'projectile_peak': peak_projectiles,
                  'projectile_dropped': projectile_dropped.value,
                  'alive_120ticks': list(alive),
                  'checksum_120ticks': hex(lib.sim_checksum())}
        replays.append(result)
        rejected(mode)  # A running battle cannot be silently re-laid out.
    assert replays[0] == replays[1], (name, replays)
    reports.append(replays[0])
    for too_small in (2048, 8190):
        assert lib.sim_init(too_small, 42) == 0
        rejected(mode)

print(json.dumps({'suite': 'dense-scenarios', 'passed': True, 'seed': 42,
                  'ticks_per_replay': 120, 'replays_per_scenario': 2,
                  'reports': reports,
                  'oracle': 'living actual enemy targets; independent range and production terrain LOS',
                  'visible_actors': 'unmeasured: this headless test does not establish pixel visibility',
                  'individually_detailed_actors': 'unmeasured',
                  'no_fixture_damage_ordnance_or_event_fabrication': True}))
