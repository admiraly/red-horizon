#!/usr/bin/env python3
"""Development-only timing of real assembly ticks with four living controllers."""
import argparse
import ctypes as C
import hashlib
import json
import math
import platform
import statistics
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('library')
p.add_argument('--ticks', type=int, default=900)
p.add_argument('--report')
a = p.parse_args()
assert 30 <= a.ticks <= 10000
library = Path(a.library).resolve()
lib = C.CDLL(str(library))

class Entity(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float)] + [
        (n, C.c_uint) for n in ('hp', 'side', 'kind', 'front', 'target', 'generation')]

class Player(C.Structure):
    _fields_ = [(n, C.c_float) for n in ('x', 'y', 'z', 'yaw', 'pitch')] + [
        (n, C.c_uint) for n in ('hp', 'ammo', 'reload', 'cooldown', 'respawn', 'front',
                               'connected', 'shots', 'hits', 'suppression', 'generation')]

entities = (Entity * 32768).in_dll(lib, 'sim_entities')
players = (Player * 4).in_dll(lib, 'sim_players')
vehicles = (C.c_int * 4).in_dll(lib, 'sim_player_vehicle')
metrics = (C.c_uint64 * 8).in_dll(lib, 'crowd_metrics')
ticks = C.c_uint.in_dll(lib, 'sim_tick_count')
lib.sim_init.argtypes = [C.c_uint, C.c_uint]
lib.player_input.argtypes = [C.c_uint, C.c_uint] + [C.c_float] * 4
lib.terrain_height.argtypes = [C.c_float, C.c_float]
lib.terrain_height.restype = C.c_float
lib.sim_checksum.restype = C.c_uint64

def run(n, mode):
    assert lib.sim_init(n, 42) == 0 and lib.sim_scenario(3) == 0
    claims = []
    for slot in range(4):
        assert lib.player_join(slot, slot % 3) == 0 and players[slot].hp
        if mode == 'tank':
            # Initial fixture positioning only. No army relocation/HP/ammo writes;
            # all ownership and subsequent motion use production assembly APIs.
            candidates = sorted((e.x, e.z, i) for i, e in enumerate(entities[:n])
                                if e.hp and e.side == 0 and e.kind == 1)
            for x, z, i in candidates:
                if i in claims:
                    continue
                players[slot].x, players[slot].z = x, z
                players[slot].y = lib.terrain_height(x, z) + 1.8
                if lib.vehicle_enter(slot) == 0:
                    assert vehicles[slot] >= 0 and vehicles[slot] not in claims
                    claims.append(vehicles[slot])
                    break
            else:
                raise AssertionError('No legitimate tank available for four-driver fixture')
        assert lib.player_input(slot, 4, -1, .3 if slot & 1 else 0, 0, 0) == 0
    initial_alive = [sum(e.hp > 0 and e.side == side for e in entities[:n])
                     for side in (0, 1)]
    before_metrics = list(metrics)
    samples = []
    foot_frames = driver_frames = 0
    for _ in range(a.ticks):
        start = time.perf_counter_ns()
        lib.sim_tick()
        samples.append((time.perf_counter_ns() - start) / 1e6)
        for slot in range(4):
            if players[slot].connected and players[slot].hp:
                if vehicles[slot] >= 0:
                    driver_frames += 1
                else:
                    foot_frames += 1
    assert ticks.value == a.ticks
    assert all(math.isfinite(p.x) and math.isfinite(p.z) for p in players)
    ordered = sorted(samples)
    p95 = ordered[math.ceil(len(ordered) * .95) - 1]
    names = ('snapshot_actors', 'move_queries', 'inspected_neighbors',
             'corrected_endpoints', 'yielded_moves', 'overlap_recoveries',
             'truncated_queries', 'maximum_inspected_per_query')
    return dict(units=n, scenario='scale-hotspot', seed=42, ticks=a.ticks,
                initial_controller_kind=mode, initial_connected_humans=4,
                initially_boarded_tank_ids=claims, initial_living_army=initial_alive,
                final_living_army=[sum(e.hp > 0 and e.side == side for e in entities[:n])
                                   for side in (0, 1)],
                observed_living_foot_controller_ticks=foot_frames,
                observed_living_driver_ticks=driver_frames,
                final_living_humans=sum(p.hp > 0 for p in players),
                tick_mean_ms=statistics.mean(samples), tick_p95_ms=p95,
                tick_p99_ms=ordered[math.ceil(len(ordered) * .99) - 1],
                cpu_only_server_p95_target_met=p95 < 1000 / 30,
                crowd={name: int(metrics[i] if i == 7 else metrics[i] - before_metrics[i])
                       for i, name in enumerate(names)},
                checksum=f'{lib.sim_checksum():016x}')

report = dict(suite='controller-crowd-bench', passed=True,
              library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
              tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              platform=platform.platform(),
              cpu_model=next((line.split(':', 1)[1].strip()
                              for line in Path('/proc/cpuinfo').read_text().splitlines()
                              if line.startswith('model name')), 'unknown'),
              rows=[run(n, mode) for n in (8192, 16384) for mode in ('foot', 'tank')],
              scope='One assembly simulation thread. Timers include ctypes call overhead; '
                    'fixture setup and Python observation excluded. Real combat/losses remain. '
                    'Four connected controllers initially; living/boarded counts measured, '
                    'not held alive. No rendered/replicated clients or GPU/audio budgets.',
              rendered=0, replicated=0, runtime_threads=1)
if a.report:
    Path(a.report).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
