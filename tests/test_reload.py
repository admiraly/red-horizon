#!/usr/bin/env python3
"""Development-only builder and black-box tests for the NASM reload proof."""
import argparse
import json
import pathlib
import subprocess
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]


def build(nasm, output):
    output.mkdir(parents=True, exist_ok=True)
    common = [nasm, '-f', 'elf64', '-g', '-F', 'dwarf', '-I', str(ROOT / 'src/reload') + '/']
    subprocess.run(common + [str(ROOT / 'src/reload/host.asm'), '-o', str(output / 'host.o')], check=True)
    subprocess.run(['cc', '-o', str(output / 'reload-proof'), str(output / 'host.o'), '-ldl'], check=True)
    for name, flags in [('v1', ['-DMULTIPLIER=1']), ('v2', ['-DMULTIPLIER=2']), ('bad', ['-DINCOMPATIBLE=1'])]:
        subprocess.run(common + flags + [str(ROOT / 'src/reload/module.asm'), '-o', str(output / (name + '.o'))], check=True)
        subprocess.run(['cc', '-shared', '-nostdlib', '-o', str(output / (name + '.so')), str(output / (name + '.o'))], check=True)
    return output / 'reload-proof'


def run_case(exe, output, valid=b'5\n', invalid=b'0\n', compatible='v2.so', bad='bad.so'):
    (output / 'valid.params').write_bytes(valid)
    (output / 'invalid.params').write_bytes(invalid)
    result = subprocess.run([str(exe), str(output / 'v1.so'), str(output / compatible),
                             str(output / bad), str(output / 'missing.so'),
                             str(output / 'valid.params'), str(output / 'invalid.params')],
                            check=True, capture_output=True, text=True)
    return [json.loads(line) for line in result.stdout.splitlines()]


def verify(exe, output):
    rows = run_case(exe, output)
    assert [r['event'] for r in rows] == ['initial', 'compatible', 'incompatible', 'missing', 'parameter', 'invalid_parameter']
    assert [r['status'] for r in rows] == [1, 1, -1, 0, 1, 0], rows
    assert [r['ticks'] for r in rows] == [1, 2, 3, 4, 5, 6], rows
    assert [r['value'] for r in rows] == [1, 3, 5, 7, 17, 27], rows
    assert [r['step'] for r in rows] == [1, 1, 1, 1, 5, 5], rows
    rejected = [b'', b'0', b'101', b'-1', b'2junk', b'3\n4', b'\n', b' ' + b'5', b'9'*100, b'5\x00', b'5\n\n']
    for content in rejected:
        rows = run_case(exe, output, invalid=content)
        assert rows[-1]['status'] == 0 and rows[-1]['step'] == 5 and rows[-1]['value'] == 27, (content, rows)
    for content, number in [(b'1', 1), (b'100\n', 100), (b'0005', 5)]:
        rows = run_case(exe, output, valid=content)
        assert rows[-2]['status'] == 1 and rows[-1]['value'] == 7 + number*4, (content, rows)
    # Missing or symbol-less module retains the initial implementation.
    rows = run_case(exe, output, compatible='missing.so')
    assert rows[1]['status'] == 0 and [r['value'] for r in rows] == [1, 2, 3, 4, 9, 14], rows
    # A valid shared object with no table exercises dlsym failure.
    subprocess.run(['cc', '-shared', '-nostdlib', '-o', str(output / 'no_symbol.so'), str(output / 'host.o')], check=True)
    rows = run_case(exe, output, bad='no_symbol.so')
    assert rows[2]['status'] == 0 and rows[-1]['value'] == 27, rows
    initial_failed = subprocess.run([str(exe)] + [str(output / 'missing.so')]*6, capture_output=True, text=True)
    assert initial_failed.returncode == 1
    assert json.loads(initial_failed.stdout)['ticks'] == 0
    assert subprocess.run([str(exe)], capture_output=True).returncode == 2
    return 19


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nasm', default='nasm')
    parser.add_argument('--build-dir', type=pathlib.Path)
    args = parser.parse_args()
    start = time.perf_counter()
    if args.build_dir:
        output = args.build_dir.resolve()
        exe = build(args.nasm, output)
        cases = verify(exe, output)
    else:
        with tempfile.TemporaryDirectory(prefix='red-horizon-reload-') as temp:
            output = pathlib.Path(temp)
            exe = build(args.nasm, output)
            cases = verify(exe, output)
    print(json.dumps({'suite': 'reload', 'cases': cases, 'passed': True, 'build_and_test_seconds': round(time.perf_counter()-start, 6)}))


if __name__ == '__main__':
    main()
