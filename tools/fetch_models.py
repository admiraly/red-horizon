#!/usr/bin/env python3
"""Optional development-only download of pinned model sources for rebaking."""
import argparse
import hashlib
import io
import json
import pathlib
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=pathlib.Path, default=ROOT / '.tools/asset-sources')
    args = parser.parse_args()
    sources = json.loads((ROOT / 'content/model-sources.json').read_text())['sources']
    args.destination.mkdir(parents=True, exist_ok=True)
    for source in sources:
        name = source['filename']
        assert pathlib.Path(name).name == name, 'source filename must be a basename'
        path = args.destination / name
        digest = source['sha256']
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            print('Verified cached source:', name)
            continue
        # Public Drive may serve a scan-warning page on the first request.
        # Never accept that page, changed sources, or partial data as a model.
        for attempt in range(3):
            request = urllib.request.Request(source['download_url'], headers={'User-Agent': 'RED-HORIZON-offline-asset-tool/1'})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(64 * 1024 * 1024 + 1)
            if 'archive_member' in source:
                if len(data) > 64 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != source['archive_sha256']:
                    continue
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    member = archive.getinfo(source['archive_member'])
                    assert member.file_size <= 64 * 1024 * 1024, 'expanded model source too large'
                    data = archive.read(member)
            if len(data) <= 64 * 1024 * 1024 and hashlib.sha256(data).hexdigest() == digest:
                temporary = path.with_suffix(path.suffix + '.download')
                temporary.write_bytes(data)
                temporary.replace(path)
                print('Downloaded verified source:', name)
                break
        else:
            raise RuntimeError(f'{name}: source hash differs from the reviewed asset; cached file preserved')


if __name__ == '__main__':
    main()
