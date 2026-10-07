#!/usr/bin/env python3
"""Offline mask invariants: geometry/material preservation and static leg weights."""
import hashlib,json,pathlib,struct,sys
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tools'))
from model_aim_mask import apply
blob=(root/'content/models/battle.rham').read_bytes();new,rows=apply(blob)
assert new==blob,'reviewed pack differs from reproducible offline mask'
h=struct.unpack_from('<12I',blob);mo,co,vo=h[6:9];lower=upper=0
# Reset only the declared unused normal.w lanes and reapply. Everything else
# must remain exactly byte-identical; constant vertex weights across all clips.
zeroed=bytearray(blob)
for m in range(h[3]):
 role,lod,n,frames,base,first,count=struct.unpack_from('<7I',blob,mo+m*64)
 if role!=0:continue
 shoot=next(struct.unpack_from('<I',blob,co+c*16)[0]for c in range(first,first+count)if struct.unpack_from('<I',blob,co+c*16+12)[0]==3)
 for v in range(n):
  ref=vo+base*16+(shoot*n+v)*48;y=struct.unpack_from('<f',blob,ref+4)[0]
  weight=struct.unpack_from('<f',blob,ref+28)[0]
  assert 0<=weight<=1
  if y<=.8:assert weight==0;lower+=1
  if y>=1.05:assert weight==1;upper+=1
  for frame in range(frames):
   offset=vo+base*16+(frame*n+v)*48+28
   assert struct.unpack_from('<f',blob,offset)[0]==weight
   struct.pack_into('<I',zeroed,offset,0)
rebuilt,_=apply(zeroed);assert rebuilt==blob and lower and upper
print(json.dumps({'suite':'model-aim-static-mask','passed':True,'lower_vertices_unrotated':lower,'upper_vertices':upper,'all_geometry_normals_xyz_materials_unchanged':True,'weights_static_across_all_frames':True,'pack_sha256':hashlib.sha256(blob).hexdigest(),'method':'Authored shoot-reference height weights; no original bone weights or IK.'}))
