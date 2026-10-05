#!/usr/bin/env python3
"""Validate distributed asset hashes and generate explicit credits."""
import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((root/'content/asset-manifest.json').read_text())
lines=['# Audio credits','']
for a in manifest['assets']:
    p=root/a['destination']
    assert p.is_file(),p
    assert hashlib.sha256(p.read_bytes()).hexdigest()==a['derived_sha256'],p
    assert a['license'] in ('CC0-1.0','CC-BY-3.0','CC-BY-4.0')
    for key in ('source_url','author','original_sha256','processing','required_attribution'): assert key in a
    lines += [a['required_attribution'],f"Source: {a['source_url']}",f"Licence: {a['license_url']}",'']
(root/'content/CREDITS.md').write_text('\n'.join(lines))
print(f'Validated {len(manifest["assets"])} asset(s)')
