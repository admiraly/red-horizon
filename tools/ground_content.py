#!/usr/bin/env python3
"""Development-only compatibility fingerprint for canonical roads/handling."""
import argparse, hashlib, json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
definitions = dict(re.findall(r'^%define ([A-Z_]+) ([A-Za-z0-9_.]+)$',
    (ROOT/'schemas/ground_surfaces.inc').read_text()+'\n'+(ROOT/'schemas/terrain_body.inc').read_text(), re.M))
keys = ('GROUND_SURFACE_VERSION', 'GROUND_TANK_OFFROAD', 'GROUND_ARTILLERY_OFFROAD', 'GROUND_TANK_RADIUS', 'GROUND_ARTILLERY_RADIUS')
def resolve(name, seen=()):
    assert name not in seen, 'Circular surface policy definition'
    value = definitions[name]
    return resolve(value, (*seen, name)) if value in definitions else value
policy = {name: resolve(name) for name in keys}
assert all(0 < float(policy[name]) <= 1 for name in keys[1:3]), 'Invalid surface multiplier'
assert all(0 <= float(policy[name]) <= 8000 for name in keys[3:]), 'Invalid body radius'
asset_fingerprint = hashlib.sha256((ROOT/'content/asset-manifest.json').read_bytes()).hexdigest()[:8]
payload = {'previous_content': asset_fingerprint, 'terrain_surface_abi': 1,
           'roads': json.loads((ROOT/'content/terrain/roads.json').read_text()),
           'tracked_policy': policy}
digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
fingerprint = digest[:8]
if args.check:
    actual = re.search(r'^%define NET_CONTENT 0x([0-9a-f]{8})$', (ROOT/'src/net/protocol.inc').read_text(), re.M)
    assert actual and actual.group(1) == fingerprint, f'Ground content compatibility mismatch: expected 0x{fingerprint}'
print(json.dumps({'ground_content': '0x'+fingerprint, 'canonical_sha256': digest, 'checked': args.check}))
