#!/usr/bin/env python3
"""Offline deterministic conversion of licensed log-drum explosion surrogate."""
import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
source=root/'content/audio/sources/muffled-distant-explosion.wav'
output=root/'content/audio/explosion.pcm'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-t','4','-ac','1','-ar','48000','-af','volume=0.8,afade=t=out:st=3.5:d=0.5','-f','s16le',str(output)],check=True)
manifest=json.loads((root/'content/asset-manifest.json').read_text())
asset=next(a for a in manifest['assets'] if a['id']=='explosion-surrogate')
assert hashlib.sha256(source.read_bytes()).hexdigest()==asset['original_sha256']
assert hashlib.sha256(output.read_bytes()).hexdigest()==asset['derived_sha256']
print(json.dumps({'suite':'audio-assets','passed':True,'source_sha256':asset['original_sha256'],'derived_sha256':asset['derived_sha256']}))

# Reproducible recorded aircraft loop from the stored compact field excerpt.
import array
asset=next(a for a in manifest['assets'] if a['id']=='aircraft-engine-recorded')
source=root/asset['source_file'];assert hashlib.sha256(source.read_bytes()).hexdigest()==asset['excerpt_sha256']
x=array.array('h');x.frombytes(source.read_bytes());assert len(x)==100800
k=4800
wave=list(x[k:-k])+[round(x[-k+i]*(1-i/(k-1))+x[i]*i/(k-1)) for i in range(k)]
result=array.array('h',[max(-32768,min(32767,v*4)) for v in wave]);assert len(result)==96000
output=root/asset['destination'];output.write_bytes(result.tobytes());assert hashlib.sha256(output.read_bytes()).hexdigest()==asset['derived_sha256']
print(json.dumps({'suite':'aircraft-audio-assets','passed':True,'original_sha256':asset['original_sha256'],'excerpt_sha256':asset['excerpt_sha256'],'derived_sha256':asset['derived_sha256'],'loop_frames':len(result),'seam_delta':abs(result[0]-result[-1])}))
