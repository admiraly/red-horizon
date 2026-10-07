#!/usr/bin/env python3
"""Real wing missions respect finite sortie fuel; omitted guard is causal control.
One-time births/fuel staging only in public flight traces, never live renewal.
"""
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NASM = os.environ['RED_HORIZON_NASM']

class Entity(C.Structure):
    _fields_ = [('x', C.c_float), ('z', C.c_float)] + [(n, C.c_uint) for n in
        ('hp', 'side', 'kind', 'front')] + [('target', C.c_int), ('gen', C.c_uint)]

class Air(C.Structure):
    _fields_ = [(n, C.c_float) for n in ('y', 'heading', 'pitch', 'bank', 'speed')] + \
        [(n, C.c_uint) for n in ('role', 'mode')] + [('target', C.c_int)] + \
        [(n, C.c_uint) for n in ('cooldown', 'ammo', 'gen')] + \
        [(n, C.c_float) for n in ('vx', 'vy', 'vz')] + \
        [(n, C.c_uint) for n in ('pass_ticks', 'flags')]

class Fuel(C.Structure):
    _fields_ = [(n, C.c_uint) for n in ('gen', 'units', 'tick', 'role')]

class Mission(C.Structure):
    _fields_ = [(n, C.c_uint) for n in ('leader', 'leader_gen', 'owner_gen', 'until')]

with tempfile.TemporaryDirectory(prefix='rh-escort-fuel-') as folder:
    temp = Path(folder)
    objects = []
    for source in sorted(p for group in ('sim', 'nav', 'ai', 'game')
                         for p in (ROOT / 'src' / group).glob('*.asm')) + \
                  [ROOT / 'tests/terrain_probe.asm', ROOT / 'tests/probe_air_escort.asm']:
        obj = temp / (source.name + '.o')
        subprocess.run([NASM, '-f', 'elf64', '-I', str(ROOT) + '/', str(source),
                        '-o', str(obj)], check=True, capture_output=True)
        objects.append(obj)

    def link(path, inputs):
        subprocess.run(['cc', '-shared', '-Wl,-Bsymbolic', '-o', str(path),
                        *map(str, inputs), '-lm'], check=True, capture_output=True)

    candidate = temp / 'candidate.so'
    link(candidate, objects)
    source = (ROOT / 'src/ai/air_escort.asm').read_text()
    assert source.count('.fuel:\n') == 1
    control_source = source.replace('.fuel:\n', '.fuel:\n xor eax,eax\n ret\n', 1)
    asm = temp / 'control.asm'
    asm.write_text(control_source)
    control_obj = temp / 'control.o'
    subprocess.run([NASM, '-f', 'elf64', '-I', str(ROOT) + '/', str(asm),
                    '-o', str(control_obj)], check=True, capture_output=True)
    control = temp / 'control.so'
    link(control, [control_obj if p.name == 'air_escort.asm.o' else p for p in objects])

    def bind(path):
        lib = C.CDLL(str(path))
        lib.sim_checksum.restype = C.c_uint64
        lib.sim_waypoint.argtypes = [C.c_uint, C.c_uint, C.c_float, C.c_float]
        lib.terrain_height.argtypes = [C.c_float, C.c_float]
        lib.terrain_height.restype = C.c_float
        lib.probe_air_escort_goal.argtypes = [C.c_uint, C.c_void_p, C.c_void_p]
        lib.air_escort_threat.argtypes = [C.c_uint, C.c_uint]
        return (lib, (Entity * 32768).in_dll(lib, 'sim_entities'),
                (Air * 32768).in_dll(lib, 'sim_aircraft'),
                (Fuel * 32768).in_dll(lib, 'sim_air_fuel'),
                (Mission * 32768).in_dll(lib, 'sim_air_escorts'),
                C.c_uint.in_dll(lib, 'sim_tick_count'),
                C.c_uint.in_dll(lib, 'sim_count'))

    lib, entities, air, fuel, missions, clock, count = bind(candidate)

    def reset(side=0):
        assert lib.sim_init(96, 42) == 0
        for i in range(96):
            entities[i].hp = 0
        for team in (0, 1):
            for front in range(3):
                assert lib.sim_order(team, front, 1) == 0
        assert lib.sim_waypoint(side, 1, 7000. if side == 0 else 1000., 4000.) == 0
        for ident, x, role in ((15, 3400., 0), (31, 3000., 1), (47, 3900., 0)):
            speed = (5., 7.)[role]
            entities[ident] = Entity(x, 4000., 200, side, 3, 1, -1, 1)
            air[ident] = Air(lib.terrain_height(x, 4000.) + (110., 140.)[role],
                math.pi / 2, 0, 0, speed, role, 0, -1, 0, (8, 180)[role],
                1, speed, 0, 0, 0, 1)
            assert lib.air_fuel_step(ident) == 0
        # Enemy threat is used only by the read-only getter tests, not flight traces.
        clock.value = 1

    def goal(ident=31):
        before = lib.sim_checksum()
        output = C.create_string_buffer(b'Z' * 8, 8)
        regs = (C.c_uint64 * 7)()
        result = lib.probe_air_escort_goal(ident, output, regs)
        assert tuple(regs) == tuple(0x123401 + i for i in range(6)) + (0,)
        assert lib.sim_checksum() == before
        if not result:
            assert output.raw == b'Z' * 8
        return result

    def threat():
        before = lib.sim_checksum()
        result = lib.air_escort_threat(31, 63)
        assert lib.sim_checksum() == before
        return result

    def enemy(side):
        entities[63] = Entity(3500., 4000., 200, side ^ 1, 3, 1, -1, 1)
        air[63] = Air(air[15].y, 0, 0, 0, 7, 1, 0, -1, 0, 180, 1, 0, 0, 7, 0, 1)

    cases = []
    for side in (0, 1):
        # Initial assignment excludes reserve/empty fighter and nearest bomber.
        for ident in (15, 31):
            for units in (3600, 1, 0):
                reset(side)
                fuel[ident].units = units
                physical = (bytes(entities), bytes(air), bytes(fuel))
                lib.air_escort_tick()
                assert physical == (bytes(entities), bytes(air), bytes(fuel))
                assert missions[31].owner_gen == (1 if ident == 15 else 0)
                if ident == 15:
                    assert missions[31].leader == 47 and goal() == 1
                else:
                    assert goal() == 0
                cases.append(dict(side=side, initial_owner=ident, units=units))
        # Commitment invalidates queries immediately, not after the30-tick review.
        for ident in (15, 31):
            for field, value in (('units', 3600), ('units', 0),
                                 ('units', (36001, 21601)[ident == 31]),
                                 ('role', 9)):
                reset(side)
                lib.air_escort_tick()
                enemy(side)
                assert missions[31].leader == 15 and goal() == 1 and threat() == 1
                setattr(fuel[ident], field, value)
                clock.value = 2
                mission_before = bytes(missions)
                assert goal() == 0 and threat() == 0
                lib.air_escort_tick()
                assert bytes(missions) == mission_before  # No off-schedule mutation.
                clock.value = 30
                lib.air_escort_tick()
                assert missions[31].owner_gen == (1 if ident == 15 else 0)
                if ident == 15:
                    assert missions[31].leader == 47 and goal() == 1
                else:
                    assert bytes(missions[31]) == bytes(16)
                cases.append(dict(side=side, committed_owner=ident, field=field, value=value))
        reset(side)
        lib.air_escort_tick()
        fuel[15].units = fuel[47].units = 3600
        clock.value = 30
        lib.air_escort_tick()
        assert bytes(missions[31]) == bytes(16) and goal() == 0
        cases.append(dict(side=side, no_eligible_bomber=True))

    reset()
    lib.air_escort_tick()
    for ident in (96, 32768, 0xffffffff):
        assert goal(ident) == 0
    count.value = 32769
    assert goal() == 0
    count.value = 96
    # A getter never births or refills a missing/new-generation fuel record.
    fuel[15].gen = 0
    before = bytes(fuel)
    assert goal() == 1 and bytes(fuel) == before
    fuel[15].gen = 1

    outcomes = []
    for side in (0, 1):
        for depleted in (15, 31):
            pair = []
            for label, library in (('candidate', candidate), ('omitted-wing-fuel-guard', control)):
                lib, entities, air, fuel, missions, clock, count = bind(library)
                reset(side)
                # One initial staging at normal3610units. Actual flight consumes
                # across reserve threshold. No subsequent health/stores/clock writes.
                clock.value = 0
                fuel[depleted].units = 3610
                traces = []
                crossing = None
                for tick in range(1, 61):
                    old = [(entities[i].x, air[i].y, entities[i].z) for i in (15, 31)]
                    lib.sim_tick()
                    for ident, previous, speed in zip((15, 31), old, (5., 7.)):
                        assert abs(math.dist(previous, (entities[ident].x, air[ident].y,
                                                        entities[ident].z)) - speed) < .002
                        assert entities[ident].hp == 200 and air[ident].ammo == (8, 180)[ident == 31]
                    if crossing is None and fuel[depleted].units <= 3600:
                        crossing = tick
                        assert goal() == (0 if label == 'candidate' else 1)
                    if tick in (1, 10, 30, 60):
                        traces.append(dict(tick=tick, units=fuel[depleted].units,
                            leader=missions[31].leader, committed=missions[31].owner_gen,
                            own_mode=air[depleted].mode, query=goal()))
                assert crossing and air[depleted].mode == 3
                if label == 'candidate':
                    if depleted == 15:
                        assert missions[31].leader == 47 and goal() == 1
                    else:
                        assert missions[31].owner_gen == 0 and goal() == 0
                else:
                    assert missions[31].leader == 15 and goal() == 1
                pair.append(dict(policy=label, crossed_reserve_tick=crossing, trace=traces))
            outcomes.append(dict(side=side, depleted=depleted, paired=pair))

    print(json.dumps(dict(suite='air-escort-fuel', passed=True, cases=len(cases),
        queries_preserve_authority_GPR_XMM_stack=True, own_record_only=True,
        causal_public_flight=outcomes,
        library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        negative_control_source_sha256=hashlib.sha256(control_source.encode()).hexdigest(),
        scope='Native production NASM wing planner/getters and real sim_tick, both sides/roles. '
              'One-time staging, constant role speed and actual reserve crossing, no live renewal. '
              'No landing/refill/traffic/full operation/GPU/UDP/performance acceptance.')))
