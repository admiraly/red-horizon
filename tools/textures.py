#!/usr/bin/env python3
"""Offline validation of pinned source-derived terrain layers (standard library)."""
import hashlib,json,pathlib,struct

def validate(root):
    root=pathlib.Path(root)
    data=(root/'content/textures/terrain.rhtx').read_bytes()
    assert len(data)==4194336
    assert struct.unpack_from('<4s7I',data)==(b'RHTX',1,len(data),512,512,4,32,1)
    report=json.loads((root/'content/textures/bake-report.json').read_text())
    sources=json.loads((root/'content/texture-sources.json').read_text())['sources']
    entries=json.loads((root/'content/asset-manifest.json').read_text())['assets']
    digest=hashlib.sha256(data).hexdigest()
    assert report['sha256']==digest and report['bytes']==len(data)
    assert sorted(s['layer'] for s in sources)==list(range(4))
    for source in sources:
        layer=source['layer']; pixels=data[32+layer*1048576:32+(layer+1)*1048576]
        baked=next(b for b in report['layers'] if b['layer']==layer)
        asset=next(a for a in entries if a.get('texture_layer')==layer)
        assert baked['original_sha256']==asset['original_sha256']==source['sha256']
        assert baked['filename']==asset['source_file']==source['filename']
        assert baked['layer_sha256']==hashlib.sha256(pixels).hexdigest()
        assert asset['derived_sha256']==digest and asset['author']==source['author']
        assert asset['source_url']==source['source_url'] and asset['license']==source['license']=='CC0-1.0'
        assert set(pixels[3::4])=={255}
        assert all(len(set(pixels[channel::4]))>16 for channel in range(3))
    return {'suite':'baked-terrain-assets','passed':True,'bytes':len(data),'layers':4,'sha256':digest}

if __name__=='__main__':
    print(json.dumps(validate(pathlib.Path(__file__).resolve().parents[1])))
