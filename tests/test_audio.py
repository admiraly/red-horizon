#!/usr/bin/env python3
"""Development-only black-box verification of the assembly PCM mixer/ALSA pump."""
import argparse
import ctypes
import json
import hashlib
import os
import pathlib
import struct
import subprocess
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]


def verify(lib, work):
    lib.audio_load.argtypes = [ctypes.c_char_p]
    lib.audio_load.restype = ctypes.c_int
    lib.audio_mix.argtypes = [ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t]
    lib.audio_mix.restype = ctypes.c_int
    lib.audio_active.restype = ctypes.c_int
    lib.audio_listener.argtypes = [ctypes.c_float]*5
    lib.audio_listener.restype = ctypes.c_int
    lib.audio_emit.argtypes = [ctypes.c_float]*4
    lib.audio_emit.restype = ctypes.c_int
    lib.audio_mix_stereo.argtypes = [ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t]
    lib.audio_mix_stereo.restype = ctypes.c_int
    lib.audio_init.restype = ctypes.c_int
    for name in ('audio_shot', 'audio_update', 'audio_shutdown'):
        getattr(lib, name).restype = None
    fixture = work / 'test.pcm'

    def load(values):
        fixture.write_bytes(struct.pack('<' + 'h'*len(values), *values))
        assert lib.audio_load(os.fsencode(fixture)) == 0

    def mix(count):
        output = (ctypes.c_int16 * (count+2))()
        output[count] = 1234
        output[count+1] = -2345
        assert lib.audio_mix(output, count) == count
        assert list(output)[count:] == [1234, -2345], 'output guard overwritten'
        return list(output)[:count]

    load([1000, -2000, 3000])
    assert mix(3) == [0, 0, 0]
    lib.audio_shot()
    assert mix(1) == [1000]
    lib.audio_shot()
    assert mix(4) == [-1000, 1000, 3000, 0], 'overlap positions/persistent voice state'
    assert lib.audio_active() == 0
    load([30000, -30000])
    lib.audio_shot()
    lib.audio_shot()
    assert mix(3) == [32767, -32768, 0], 'signed saturation'
    load([100, 200])
    for _ in range(129):
        lib.audio_shot()
    assert lib.audio_active() == 128
    assert mix(3) == [12800, 25600, 0], 'bounded recycle'
    assert lib.audio_active() == 0
    load([32767, -32768])
    for _ in range(128):
        lib.audio_shot()
    assert mix(3) == [32767, -32768, 0], '32-bit accumulator bounds'
    for content in (b'', b'\0', b'\0' * 384002):
        fixture.write_bytes(content)
        assert lib.audio_load(os.fsencode(fixture)) == 1
        lib.audio_shot()
        assert mix(1) == [0]
    assert lib.audio_load(os.fsencode(work / 'missing.pcm')) == 1
    fixture.write_bytes(b'\0\0' * 192000)
    assert lib.audio_load(os.fsencode(fixture)) == 0, 'maximum accepted preload'
    output = (ctypes.c_int16 * 802)()
    output[0] = 456
    assert lib.audio_mix(output, 801) == -1 and output[0] == 456
    assert lib.audio_mix(output, ctypes.c_size_t(-1).value) == -1
    assert mix(0) == []
    load([5] * 800)
    lib.audio_shot()
    assert mix(800) == [5] * 800
    assert lib.audio_active() == 0
    spatial_blocks = 0

    def stereo(count):
        nonlocal spatial_blocks
        spatial_blocks += 1
        output = (ctypes.c_int16 * (count*2+2))()
        output[count*2] = 1234
        output[count*2+1] = -2345
        assert lib.audio_mix_stereo(output, count) == count
        assert list(output)[count*2:] == [1234, -2345], 'stereo output guard overwritten'
        return list(output)[:count*2]

    def counter(name):
        return ctypes.c_uint64.in_dll(lib, name).value

    assert lib.audio_listener(1000, 5, 1000, 1, 0) == 0
    load([2000])
    assert lib.audio_emit(1000, 5, 1000, 1) == 0
    assert stereo(1) == [1000, 1000], 'coincident source centered'
    load([2000])
    assert lib.audio_emit(1000, 5, 1025, 1) == 0
    assert stereo(1) == [500, 500], '25m inverse-distance reference'
    load([2000])
    assert lib.audio_emit(1025, 5, 1000, 1) == 0
    assert stereo(1) == [0, 1000], 'right pan'
    load([2000])
    assert lib.audio_emit(975, 5, 1000, 1) == 0
    assert stereo(1) == [1000, 0], 'left pan'
    load([2000])
    assert lib.audio_listener(1000, 5, 1000, -1, 0) == 0
    assert lib.audio_emit(1025, 5, 1000, 1) == 0
    assert stereo(1) == [1000, 0], 'listener orientation changes pan'
    load([2000])
    assert lib.audio_listener(1000, 5, 1000, 0, 2) == 0
    assert lib.audio_emit(1000, 5, 1025, 1) == 0
    assert stereo(1) == [0, 1000], 'right vector normalization/rotation'
    load([2000])
    assert lib.audio_listener(1000, 5, 1000, 1, 0) == 0
    assert lib.audio_emit(1100, 5, 1000, 1) == 0
    assert stereo(1) == [0, 399], '100m attenuation and Q15 rounding'
    load([2000])
    assert lib.audio_emit(1000, 30, 1000, 1) == 0
    assert stereo(1) == [500, 500], 'vertical distance attenuates without horizontal pan'
    load([2000])
    assert lib.audio_emit(1000, 5, 1000, 0.5) == 0
    assert stereo(1) == [500, 500], 'event gain'
    load([2000])
    assert lib.audio_emit(2500, 5, 1000, 1) == 1
    assert lib.audio_emit(1000, 5, 1000, 0) == 1
    assert counter('audio_culled') == 2 and counter('audio_submitted') == 0
    assert lib.audio_active() == 0
    load([2000, 4000, 6000])
    assert lib.audio_emit(1000, 5, 1000, 1) == 0
    assert lib.audio_listener(3000, 5, 1000, 1, 0) == 0
    assert stereo(1) == [0, 0]
    assert ctypes.c_uint.in_dll(lib, 'audio_virtualized').value == 1
    assert lib.audio_active() == 1
    assert lib.audio_listener(1000, 5, 1000, 1, 0) == 0
    assert stereo(1) == [2000, 2000], 'virtual voice advanced before audible return'
    assert stereo(2) == [3000, 3000, 0, 0]
    assert lib.audio_active() == 0
    load([30000, -30000])
    for _ in range(129):
        lib.audio_shot()
    assert counter('audio_submitted') == 129 and counter('audio_replaced') == 1
    assert lib.audio_active() == 128
    assert stereo(3) == [32767, 32767, -32768, -32768, 0, 0]
    assert stereo(0) == []
    load([5]*800)
    lib.audio_shot()
    assert stereo(800) == [5]*1600
    output = (ctypes.c_int16 * 1604)()
    output[0] = 456
    assert lib.audio_mix_stereo(output, 801) == -1 and output[0] == 456
    assert lib.audio_mix_stereo(output, ctypes.c_size_t(-1).value) == -1
    load([2000])
    rejected = [(float('nan'), 0, 1000, 1), (float('inf'), 0, 1000, 1),
                (-1, 0, 1000, 1), (8001, 0, 1000, 1), (1000, 2001, 1000, 1),
                (1000, -1001, 1000, 1), (1000, 0, -1, 1),
                (1000, 0, 1000, float('nan')), (1000, 0, 1000, 1.01)]
    for args in rejected:
        assert lib.audio_emit(*args) == -1 and counter('audio_submitted') == 0
    for args in [(1000, 0, 1000, 0, 0), (1000, 0, 1000, float('inf'), 0),
                 (1000, 0, 1000, float('nan'), 1), (float('nan'), 0, 1000, 1, 0)]:
        assert lib.audio_listener(*args) == -1
    # Rejected listener does not overwrite previously valid position/orientation.
    assert lib.audio_emit(1000, 5, 1000, 1) == 0 and stereo(1) == [1000, 1000]
    # Synthetic test data, not a claim of recorded sound quality.
    content = work / 'content/audio'
    content.mkdir(parents=True)
    (content / 'aircraft-engine.pcm').write_bytes((ROOT / 'content/audio/aircraft-engine.pcm').read_bytes())
    (content / 'footstep.pcm').write_bytes((ROOT / 'content/audio/footstep.pcm').read_bytes())
    (content / 'explosion.pcm').write_bytes((ROOT / 'content/audio/explosion.pcm').read_bytes())
    (content / 'rifle.pcm').write_bytes(struct.pack('<1000h', *([200] * 1000)))
    previous_cwd = pathlib.Path.cwd()
    previous_device = os.environ.get('RH_AUDIO_DEVICE')
    try:
        os.chdir(work)
        os.environ['RH_AUDIO_DEVICE'] = 'null'
        assert lib.audio_init() == 0, 'ALSA null backend unavailable'
        assert lib.audio_listener(1000, 5, 1000, 1, 0) == 0
        assert lib.audio_emit(1025, 5, 1000, 1) == 0
        lib.audio_shot()
        for _ in range(3):
            lib.audio_update()
        assert lib.audio_active() == 0, 'null pump consumes sample'
        lib.audio_shutdown()
        lib.audio_update()
        recorded = (ROOT / 'content/audio/rifle.pcm').read_bytes()
        manifest = json.loads((ROOT / 'content/asset-manifest.json').read_text())
        asset = next(a for a in manifest['assets'] if a['id'] == 'rifle-shot')
        assert asset['recorded'] and hashlib.sha256(recorded).hexdigest() == asset['derived_sha256']
        (content / 'rifle.pcm').write_bytes(recorded)
        assert lib.audio_init() == 0
        assert lib.audio_listener(1000, 5, 1000, 1, 0) == 0
        assert lib.audio_emit(1000, 5, 1000, 1) == 0
        expected = struct.unpack('<800h', recorded[:1600])
        assert any(expected), 'recorded fixture unexpectedly silent'
        assert stereo(800) == [sample >> 1 for sample in expected for _ in range(2)]
        for _ in range(65):
            lib.audio_update()
        assert lib.audio_active() == 0, 'recorded spatial sample null playback not drained'
        lib.audio_shutdown()
        # Profile only authored mixer execution; load/emit/preparation remain outside
        # these measurements. 20 blocks stay inside the recorded sample duration.
        assert lib.audio_load(os.fsencode(ROOT / 'content/audio/rifle.pcm')) == 0
        for _ in range(128):
            assert lib.audio_emit(1000, 5, 1000, 1) == 0
        profile_output = (ctypes.c_int16 * 1600)()
        mix_timings = []
        for _ in range(20):
            started = time.perf_counter_ns()
            assert lib.audio_mix_stereo(profile_output, 800) == 800
            mix_timings.append((time.perf_counter_ns()-started)/1000000)
        lib.audio_shutdown()
        os.environ['RH_AUDIO_DEVICE'] = 'red_horizon_missing_device'
        assert lib.audio_init() == 2, 'unavailable device is nonfatal'
        lib.audio_update()
        lib.audio_shutdown()
        (content / 'footstep.pcm').unlink()
        assert lib.audio_init() == 1, 'missing footstep content is explicit failure'
        lib.audio_shutdown()
        (content / 'footstep.pcm').write_bytes((ROOT / 'content/audio/footstep.pcm').read_bytes())
        (content / 'explosion.pcm').unlink()
        assert lib.audio_init() == 1, 'missing explosion content is explicit failure'
        lib.audio_shutdown()
        (content / 'rifle.pcm').unlink()
        assert lib.audio_init() == 1, 'missing content is nonfatal'
        lib.audio_shutdown()
    finally:
        os.chdir(previous_cwd)
        if previous_device is None:
            os.environ.pop('RH_AUDIO_DEVICE', None)
        else:
            os.environ['RH_AUDIO_DEVICE'] = previous_device
    return {'legacy_groups': 16, 'spatial_blocks': spatial_blocks,
            'invalid_sources': len(rejected), 'invalid_listeners': 4,
            'recorded_waveform_frames': 800, 'profile_voices': 128,
            'profile_frames': 800, 'profile_blocks': 20,
            'mix_mean_ms': round(sum(mix_timings)/len(mix_timings), 6),
            'mix_p95_ms': round(sorted(mix_timings)[18], 6)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nasm', default='nasm')
    args = parser.parse_args()
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='red-horizon-audio-') as temp:
        work = pathlib.Path(temp)
        obj, shared = work / 'audio.o', work / 'audio.so'
        subprocess.run([args.nasm, '-f', 'elf64', '-g', '-F', 'dwarf', str(ROOT / 'src/audio/audio.asm'), '-o', str(obj)], check=True)
        subprocess.run(['cc', '-shared', '-o', str(shared), str(obj), '-lasound'], check=True)
        cases = verify(ctypes.CDLL(str(shared)), work)
    print(json.dumps({'suite': 'audio', 'checks': cases, 'passed': True, 'build_and_test_seconds': round(time.perf_counter()-start, 6)}))


if __name__ == '__main__':
    main()
