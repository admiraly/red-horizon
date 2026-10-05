#!/usr/bin/env python3
"""Development-only black-box verification of the assembly PCM mixer/ALSA pump."""
import argparse
import ctypes
import json
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
    # Synthetic test data, not a claim of recorded sound quality.
    content = work / 'content/audio'
    content.mkdir(parents=True)
    (content / 'rifle.pcm').write_bytes(struct.pack('<1000h', *([200] * 1000)))
    previous_cwd = pathlib.Path.cwd()
    previous_device = os.environ.get('RH_AUDIO_DEVICE')
    try:
        os.chdir(work)
        os.environ['RH_AUDIO_DEVICE'] = 'null'
        assert lib.audio_init() == 0, 'ALSA null backend unavailable'
        lib.audio_shot()
        for _ in range(3):
            lib.audio_update()
        assert lib.audio_active() == 0, 'null pump consumes sample'
        lib.audio_shutdown()
        lib.audio_update()
        os.environ['RH_AUDIO_DEVICE'] = 'red_horizon_missing_device'
        assert lib.audio_init() == 2, 'unavailable device is nonfatal'
        lib.audio_update()
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
    return 16


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
