#!/usr/bin/env python3
"""Offline validation of the distributed baked model/animation pack."""
import array
import json
import math
import pathlib
import struct
import sys


def validate(path):
    data = pathlib.Path(path).read_bytes()
    assert 48 <= len(data) <= 64 * 1024 * 1024, 'model pack size'
    magic, version, size, meshes, clips, vectors, mo, co, vo = struct.unpack_from('<4s8I', data)
    assert magic == b'RHAM' and version == 1 and size == len(data), 'model header'
    assert 1 <= meshes <= 32 and 1 <= clips <= 128, 'model counts'
    assert mo >= 48 and mo + meshes * 64 <= co, 'mesh table'
    assert co + clips * 16 <= vo and vo + vectors * 16 == size, 'vertex table'
    floats = array.array('f', data[vo:])
    if sys.byteorder != 'little':
        floats.byteswap()
    assert all(math.isfinite(value) for value in floats), 'nonfinite baked vertex'
    seen = set()
    evidence = []
    for index in range(meshes):
        role, lod, vertices, frames, base, first, count, flags = struct.unpack_from('<8I', data, mo + index * 64)
        scale, radius, width, height, depth = struct.unpack_from('<5f', data, mo + index * 64 + 32)
        assert role <= 7 and lod <= 1 and (role, lod) not in seen, 'duplicate/unknown role'
        seen.add((role, lod))
        assert 3 <= vertices <= 30000 and vertices % 3 == 0 and 1 <= frames <= 128, 'mesh geometry'
        assert base + vertices * frames * 3 <= vectors, 'mesh vertex range'
        assert 1 <= count and first + count <= clips, 'mesh clips'
        assert all(math.isfinite(v) and v > 0 for v in (scale, radius, width, height, depth)), 'mesh bounds'
        semantics = set()
        changing = set()
        for ci in range(first, first + count):
            start, length, fps, semantic = struct.unpack_from('<IIfI', data, co + ci * 16)
            assert length >= 1 and start + length <= frames, 'clip frame range'
            assert math.isfinite(fps) and 1 <= fps <= 120 and semantic <= 3, 'clip metadata'
            semantics.add(semantic)
            stride = vertices * 48
            if length > 1:
                a = vo + base * 16 + start * stride
                frame = data[a:a + stride]
                if any(data[a + j * stride:a + (j + 1) * stride] != frame for j in range(1, length)):
                    changing.add(semantic)
        if role == 0:
            assert {0, 1, 2} <= semantics and {1, 2} <= changing, 'infantry must have authored locomotion'
        evidence.append({'role': role, 'lod': lod, 'triangles': vertices // 3, 'frames': frames,
                         'clip_semantics': sorted(semantics), 'changing_clips': sorted(changing)})
    assert seen == {(role, lod) for role in range(8) for lod in range(2)}, 'missing rendered category/LOD'
    return {'bytes': size, 'meshes': meshes, 'clips': clips, 'geometry': evidence}


if __name__ == '__main__':
    print(json.dumps(validate(sys.argv[1])))
