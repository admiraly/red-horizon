#!/usr/bin/env python3
"""Actual RHAM pack parsing plus unsafe/truncated/non-finite rejection fixtures."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
lib=C.CDLL(str(Path(sys.argv[1]).resolve()));source=Path(sys.argv[2]).read_bytes()
header=struct.unpack_from('<12I',source);assert header[0]==0x4d414852
mesh,clip,vertices=header[6:9];original=os.getcwd();rejections=0
with tempfile.TemporaryDirectory() as folder:
    os.chdir(folder);path=Path('content/models/battle.rham');path.parent.mkdir(parents=True)
    try:
        path.write_bytes(source);assert lib.mesh_asset_load()==0,'actual authored pack rejected'
        cases=[(0,0),(4,2),(8,len(source)-1),(12,33),(16,129),(20,0),(24,0),(28,mesh),(32,clip),(mesh+8,4),(mesh+12,0),(mesh+16,0xffffffff),(mesh+20,0xffffffff),(mesh+24,0),(mesh+32,0x7fc00000),(mesh+40,0),(clip+4,0xffffffff),(clip+8,0x7f800000),(clip+12,4),(vertices,0x7f800000)]
        fighter=next(mesh+i*64 for i in range(header[3]) if struct.unpack_from('<2I',source,mesh+i*64)==(8,0))
        cases += [(fighter,9)] # valid lookup slot, but required fighter mesh absent
        for offset,value in cases:
            damaged=bytearray(source);struct.pack_into('<I',damaged,offset,value);path.write_bytes(damaged)
            assert lib.mesh_asset_load()==-1,('malformed pack accepted',offset,value);rejections+=1
        for damaged in (source[:47],source[:-16],source+b'X'):
            path.write_bytes(damaged);assert lib.mesh_asset_load()==-1;rejections+=1
        path.write_bytes(source);assert lib.mesh_asset_load()==0,'loader did not recover after rejection'
    finally:os.chdir(original)
print(json.dumps({'suite':'mesh-assets','passed':True,'actual_bytes':len(source),'actual_meshes':header[3],'malformed_rejected':rejections}))
