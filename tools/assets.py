#!/usr/bin/env python3
"""Validate distributed asset hashes and generate explicit credits."""
import hashlib,json,pathlib
from models import validate
root=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((root/'content/asset-manifest.json').read_text())
lines=['# Asset credits','']
notices=['# Third-party notices','',
    'NASM 2.16.03 is a development dependency under the BSD 2-clause licence (see upstream archive LICENSE). GCC, glibc, GLFW and OpenGL are system/toolchain dependencies, not vendored project runtime code.',
    'Asset licences are separate from the pending project code licence. The following notices are generated from content/asset-manifest.json. Raw model sources are not distributed; the game contains the baked derivative. Pack-specific model grant evidence and downloaded licences are in content/licenses/.','']
for a in manifest['assets']:
    p=root/a['destination']
    assert p.is_file(),p
    assert hashlib.sha256(p.read_bytes()).hexdigest()==a['derived_sha256'],p
    assert a['license'] in ('CC0-1.0','CC-BY-3.0','CC-BY-4.0')
    for key in ('source_url','author','original_sha256','processing','required_attribution'): assert key in a
    if a.get('format')=='RHAM v1':
        assert len(a['original_sha256'])==64
    lines += [a['required_attribution'],f"Source: {a['source_url']}",f"Licence: {a['license_url']}",'']
    notices += [a['required_attribution'],f"Source: {a['source_url']}",f"Licence: {a['license_url']}",'']
(root/'content/CREDITS.md').write_text('\n'.join(lines))
(root/'THIRD_PARTY.md').write_text('\n'.join(notices))
if (root/'content/model-sources.json').exists():
    sources=json.loads((root/'content/model-sources.json').read_text())['sources']
    for source in sources:
        entries=[a for a in manifest['assets'] if a.get('source_file')==source['filename']]
        assert entries and all(a['original_sha256']==source['sha256'] for a in entries),source['filename']
    report=json.loads((root/'content/models/bake-report.json').read_text())
    assert report['sha256']==hashlib.sha256((root/'content/models/battle.rham').read_bytes()).hexdigest()
    for mesh in report['meshes']:
        source=next(s for s in sources if s['filename']==mesh['file'])
        assert mesh['source_sha256']==source['sha256'] and mesh['role']==source['role']
    print(json.dumps({'suite':'baked-model-assets','passed':True,**validate(root/'content/models/battle.rham')}))
print(f'Validated {len(manifest["assets"])} asset(s)')
