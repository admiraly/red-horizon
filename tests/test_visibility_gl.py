#!/usr/bin/env python3
"""Independent, development-only pixel visibility oracle using production GL.

A private Xvfb client has its simulation clock frozen before explicit fixture
writes. These are rendering fixtures, not evidence of units produced by combat.
Expected visible classes come from controlled geometry, not submitted counts or
frustum estimates. No host desktop input is used. Every child is reconciled.
"""
import json
import errno
import os
import pathlib
import select
import signal
import struct
import subprocess
import sys
import tempfile
import time

EXE = pathlib.Path(sys.argv[1]).resolve()
SYMBOLS = {}
for line in subprocess.check_output(['nm', '-n', str(EXE)], text=True).splitlines():
    fields = line.split()
    if len(fields) == 3:
        SYMBOLS[fields[2]] = int(fields[0], 16)


def terminate(process):
    if process is not None and process.poll() is None:
        os.kill(process.pid, signal.SIGCONT)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_for(process, condition, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = condition()
        if value:
            return value
        assert process.poll() is None, 'client exited before fixture was ready'
        time.sleep(.01)
    raise AssertionError('private client condition timed out')


def stopped(process):
    os.kill(process.pid, signal.SIGSTOP)
    _, status = os.waitpid(process.pid, os.WUNTRACED)
    assert os.WIFSTOPPED(status)


# x displacement, forward distance, absolute altitude. Near/mid fighters and
# one distant infantry marker exercise all real classes without depending on
# a fixed distance cutoff for large aircraft.
VISIBLE = [(-15., 60., 100.), (70., 350., 100.), (-350., 1700., 100.)]
CASES = {
    'allied_site_no_army': ([], None, (0,0,0)),
    'enemy_site_no_army': ([], None, (0,0,0)),
    'three_classes': (VISIBLE, None, (1, 1, 1)),
    'offscreen': (VISIBLE + [(2000., 60., 100.)], None, (1, 1, 1)),
    'behind_camera': (VISIBLE + [(0., -60., 100.)], None, (1, 1, 1)),
    'below_terrain': (VISIBLE + [(0., 100., -20.)], None, (1, 1, 1)),
    # A large production bunker entirely covers the near aircraft's projection.
    'prop_occluded': ([(0., 60., 100.)], (1840., 3925., 2040., 3945., 60., 100., 0, 0), (0, 0, 0)),
    # A near sourced fighter covers its smaller, aligned far-LOD counterpart.
    'actor_occluded': ([(0., 60., 100.), (0., 350., 100.)], None, (1, 0, 0)),
    'no_army': ([], None, (0, 0, 0)),
    'remote_human_no_army': ([], None, (0, 0, 0)),
}


def run_fixture(env, folder, label, actors, obstacle, census=True):
    process = memory = None
    image = folder / (label + ('-census' if census else '-normal') + '.ppm')
    census_map = folder / (label + '.r32ui')
    try:
        command = [str(EXE), '--frames', '10000', '--screenshot', str(image)]
        if census:
            command += ['--census', '--census-map', str(census_map)]
        process = subprocess.Popen(command, cwd=EXE.parent, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
        memory = os.open(f'/proc/{process.pid}/mem', os.O_RDWR)

        def read(name, size):
            return os.pread(memory, size, SYMBOLS[name])

        def write(name, data):
            assert os.pwrite(memory, data, SYMBOLS[name]) == len(data)

        def u32(name):
            return struct.unpack('<I', read(name, 4))[0]

        # Initial startup runs the authentic game; freeze before installing
        # fixtures. Let an already-entered fixed tick finish before recording.
        def startup_ready():
            # Popen may return before exec maps the executable's fixed addresses.
            # Retry only this startup read; later fixture reads remain strict.
            try:
                data = read('frame_count', 4)
            except OSError as error:
                if error.errno == errno.EIO:
                    return False
                raise
            return len(data) == 4 and struct.unpack('<I', data)[0] >= 4

        wait_for(process, startup_ready)
        stopped(process)
        write('maxdt', struct.pack('<d', 0.))
        write('thirty', struct.pack('<d', 1e30))
        write('accum', struct.pack('<d', 0.))
        frame = u32('frame_count')
        os.kill(process.pid, signal.SIGCONT)
        wait_for(process, lambda: u32('frame_count') >= frame + 3)
        stopped(process)
        ticks = u32('local_sim_ticks')
        write('sim_count', struct.pack('<I', len(actors)))
        write('sim_entities', bytes(8192 * 32))
        write('sim_aircraft', bytes(8192 * 64))
        for index, (x, z, y) in enumerate(actors):
            kind=0 if index==2 and label in ('three_classes','offscreen','behind_camera','below_terrain') else 3
            entity = struct.pack('<2f6I', 2000. + x, 3900. + z, 100, index & 1, kind, 0, 0, 100 + index)
            aircraft = struct.pack('<5f6I3f2I', y, 0., 0., 0., 7., 1, 0, 0, 0, 180, 100 + index, 0., 0., 7., 0, 1)
            os.pwrite(memory, entity, SYMBOLS['sim_entities'] + index * 32)
            os.pwrite(memory, aircraft, SYMBOLS['sim_aircraft'] + index * 64)
        write('sim_projectiles', bytes(32768))
        write('sim_projectile_count', struct.pack('<I', 0))
        write('effects_records', bytes(2048))
        write('air_trails_visible', struct.pack('<I', 0))
        write('terrain_obstacle_count', struct.pack('<I', int(obstacle is not None)))
        if obstacle:
            write('terrain_obstacles', struct.pack('<6f2I', *obstacle))
        # Remove uncontrolled props from the test view, preserving fixed arrays.
        sites = bytearray(read('sim_sites', 12 * 32))
        for index in range(12):
            struct.pack_into('<2f', sites, index * 32, 7000., 7000.)
        if label in ('allied_site_no_army','enemy_site_no_army'):
            struct.pack_into('<2f',sites,0,2000.,4400.)
            struct.pack_into('<I',sites,8,int(label=='enemy_site_no_army'))
        write('sim_sites', sites)
        write('tree_positions', struct.pack('<32f', *([7000., 7000.] * 16)))
        player = bytearray(256)
        struct.pack_into('<5f11I', player, 0, 2000., 100., 3900., 0., 0., 100, 30, 0, 0, 0, 0, 1, 0, 0, 0, 1)
        if label == 'remote_human_no_army':
            struct.pack_into('<5f11I', player, 64, 2000., 100., 3960., 0., 0., 100, 30, 0, 0, 0, 0, 1, 0, 0, 0, 1)
        write('sim_players', player)
        write('camera', struct.pack('<3f', 2000., 100., 3900.))
        write('yaw', struct.pack('<f', 0.))
        write('pitch', struct.pack('<f', 0.))
        write('environment_weather', struct.pack('<4f', 0., .15, 0., .00008))
        write('mesh_clock', struct.pack('<f', 0.))
        write('sim_requisition', struct.pack('<2I', 200, 200))
        write('sim_supply', struct.pack('<2I', 900, 900))
        write('sim_operation_state', struct.pack('<I', 0))
        for name in ('damage_flash', 'recoil', 'hit_flash', 'shot_flash'):
            write(name, struct.pack('<f', 0.))
        write('last_hp', struct.pack('<I', 100))
        write('last_shots', struct.pack('<I', 0))
        write('last_hits', struct.pack('<I', 0))
        authority_names = [('sim_entities', 8192 * 32), ('sim_aircraft', 8192 * 64),
                           ('sim_projectiles', 32768), ('sim_players', 256), ('sim_sites', 384),
                           ('sim_requisition', 8), ('sim_supply', 8), ('sim_operation_state', 4)]
        authority = b''.join(read(name, size) for name, size in authority_names)
        frame = u32('frame_count')
        os.kill(process.pid, signal.SIGCONT)
        wait_for(process, lambda: u32('frame_count') >= frame + 3)
        stopped(process)
        assert u32('local_sim_ticks') == ticks, 'fixture simulation advanced'
        assert b''.join(read(name, size) for name, size in authority_names) == authority, 'rendering mutated authority'
        write('frame_limit', struct.pack('<I', u32('frame_count') + 2))
        os.kill(process.pid, signal.SIGCONT)
        stdout, stderr = process.communicate(timeout=20)
        assert process.returncode == 0, stdout + stderr
        blob = image.read_bytes()
        header, body = blob.split(b'\n255\n', 1)
        assert header == b'P6\n1280 720' and len(body) == 1280 * 720 * 3
        if not census:
            return body, None
        reports = [json.loads(line) for line in stdout.splitlines()
                   if line.startswith('{') and 'visibility_census' in line]
        assert len(reports) == 1, stdout
        raw = census_map.read_bytes()
        assert len(raw) == 1280 * 720 * 4
        encoded = set(struct.unpack('<' + 'I' * (1280 * 720), raw)) - {0}
        decoded = {}
        for value in encoded:
            assert value >> 18 == 0, ('unexpected census bits', value)
            actor = (value & 65535) - 1
            lod = (value >> 16) & 3
            assert actor >= 0 and lod in (1, 2, 3), value
            decoded.setdefault(actor, set()).add(lod)
        reports[0]['decoded_actor_classes'] = {actor: sorted(classes) for actor, classes in decoded.items()}
        return body, reports[0]
    finally:
        if memory is not None:
            os.close(memory)
        terminate(process)


read_fd, write_fd = os.pipe()
server = None
try:
    server = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0',
                               '1280x720x24', '-nolisten', 'tcp'], pass_fds=(write_fd,),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(write_fd)
    write_fd = None
    assert select.select([read_fd], [], [], 10)[0], 'private X server startup timeout'
    number = os.read(read_fd, 32).decode().strip()
    assert number.isdigit(), number
    env = dict(os.environ, DISPLAY=':' + number, LIBGL_ALWAYS_SOFTWARE='1', RH_AUDIO_DEVICE='null')
    env.pop('WAYLAND_DISPLAY', None)
    results = {}
    colours = {}
    with tempfile.TemporaryDirectory(prefix='rh-visibility-') as directory:
        folder = pathlib.Path(directory)
        for label, (actors, obstacle, expected) in CASES.items():
            colour, report = run_fixture(env, folder, label, actors, obstacle)
            colours[label] = colour
            # Stable report field contract is owned by the production module.
            observed = tuple(report[name] for name in ('visible_high', 'visible_low', 'visible_markers'))
            assert observed == expected, (label, observed, expected, report)
            assert report['visible_actors'] == sum(expected), (label, report)
            assert report['authority_readonly'] is True, (label, report)
            assert report['authority_before'] == report['authority_after'], (label, report)
            assert report['invalid_codes'] == 0, (label, report)
            expected_ids = ({0: [1], 1: [2], 2: [3]} if label in ('three_classes', 'offscreen', 'behind_camera', 'below_terrain') else {0: [1]} if label == 'actor_occluded' else {})
            assert report['decoded_actor_classes'] == expected_ids, (label, report['decoded_actor_classes'], expected_ids)
            results[label] = {'expected': list(expected), 'observed': list(observed),
                              'expected_actor_classes': expected_ids,
                              'observed_actor_classes': report['decoded_actor_classes'],
                              'authority_before': report['authority_before'],
                              'authority_after': report['authority_after']}
            if label in ('three_classes', 'allied_site_no_army', 'enemy_site_no_army'):
                normal, _ = run_fixture(env, folder, label, actors, obstacle, census=False)
                changed = sum(colour[i:i+3] != normal[i:i+3] for i in range(0, len(colour), 3))
                maximum = max(abs(a - b) for a, b in zip(colour, normal))
                # RGBA8 offscreen rendering then blitting can quantize/dither
                # differently from the default framebuffer. Bound the error to
                # two 8-bit steps; any changed silhouette fails this oracle.
                assert maximum <= 2, ('census changed presented colour', changed, maximum)
                results[label]['normal_colour_changed_pixels'] = changed
                results[label]['normal_colour_max_channel_error'] = maximum
    for label in ('allied_site_no_army', 'enemy_site_no_army'):
        changed = sum(colours[label][i:i+3] != colours['no_army'][i:i+3]
                      for i in range(0, len(colours[label]), 3))
        assert changed > 25, ('site fixture must actually render', label, changed)
        results[label]['scenery_pixels_changed_from_empty'] = changed
    print(json.dumps({'suite': 'visibility-actual-gl', 'passed': True, 'cases': results,
                      'render_authority_unchanged': True,
                      'context': 'Private Xvfb software OpenGL; frozen development-only poses; actual production source meshes, terrain, bunker and pixel readback. No performance or combat claim.'}))
finally:
    if read_fd is not None:
        os.close(read_fd)
    if write_fd is not None:
        os.close(write_fd)
    terminate(server)
