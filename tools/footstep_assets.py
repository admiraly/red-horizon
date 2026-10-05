#!/usr/bin/env python3
"""Offline hash-pinned conversion; never downloads or fabricates audio."""
import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
asset=next(a for a in json.loads((root/'content/asset-manifest.json').read_text())['assets'] if a['id']=='footstep-recorded')
source=root/asset['source_file'];output=root/asset['destination']
assert hashlib.sha256(source.read_bytes()).hexdigest()==asset['original_sha256']
subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ac','1','-ar','48000','-af','volume=0.6,afade=t=in:st=0:d=0.005,afade=t=out:st=0.144:d=0.01','-f','s16le',str(output)],check=True)
assert hashlib.sha256(output.read_bytes()).hexdigest()==asset['derived_sha256']
print(json.dumps({'suite':'footstep-assets','passed':True,'source_sha256':asset['original_sha256'],'derived_sha256':asset['derived_sha256'],'samples':len(output.read_bytes())//2}))
