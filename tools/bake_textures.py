#!/usr/bin/env python3
"""Offline pinned photo texture conversion; Pillow is never a game dependency."""
import argparse
import hashlib
import json
import pathlib
import struct
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    from PIL import Image
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=pathlib.Path, default=ROOT / '.tools/texture-sources')
    parser.add_argument('--fetch', action='store_true', help='Download missing original files with SHA256 verification')
    args = parser.parse_args()
    config = json.loads((ROOT / 'content/texture-sources.json').read_text())
    sources = sorted(config['sources'], key=lambda s: s['layer'])
    assert [s['layer'] for s in sources] == list(range(4))
    args.sources.mkdir(parents=True, exist_ok=True)
    payload = bytearray()
    reports = []
    for source in sources:
        name = source['filename']
        assert pathlib.Path(name).name == name
        path = args.sources / name
        if not path.exists() and args.fetch:
            request = urllib.request.Request(source['download_url'], headers={'User-Agent': 'RED-HORIZON-offline-texture-tool/1'})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(16 * 1024 * 1024 + 1)
            assert len(data) <= 16 * 1024 * 1024 and hashlib.sha256(data).hexdigest() == source['sha256'], name
            temporary = path.with_suffix('.download')
            temporary.write_bytes(data)
            temporary.replace(path)
        original = path.read_bytes()
        assert hashlib.sha256(original).hexdigest() == source['sha256'], name
        with Image.open(path) as image:
            assert image.size == (1024, 1024), (name, image.size)
            image = image.convert('RGBA').resize((512, 512), Image.Resampling.LANCZOS)
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            raw = image.tobytes()
        payload.extend(raw)
        reports.append({'filename': name, 'layer': source['layer'], 'original_sha256': source['sha256'],
                        'layer_sha256': hashlib.sha256(raw).hexdigest()})
    blob = struct.pack('<4s7I', b'RHTX', 1, 32 + len(payload), 512, 512, 4, 32, 1) + payload
    destination = ROOT / 'content/textures/terrain.rhtx'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)
    report = {'format': 'RHTX v1', 'width': 512, 'height': 512, 'layers': reports,
              'encoding': 'bottom-up RGBA8, original sRGB source color, opaque alpha',
              'processing': 'Pillow RGBA conversion; 1024 to512 Lanczos resize; vertical flip; no procedural replacement or recoloring',
              'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
    (destination.parent / 'bake-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
