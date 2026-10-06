#!/usr/bin/env python3
"""Read actual distributed vehicle vertices for the next support-frame contract."""
from pathlib import Path
import hashlib,json,math,struct
root=Path(__file__).resolve().parents[2];path=root/'content/models/battle.rham';data=path.read_bytes()
magic,version,size,meshes,clips,vectors,mo,co,vo=struct.unpack_from('<4s8I',data)
assert magic==b'RHAM' and version==1 and size==len(data)
rows=[]
for i in range(meshes):
    role,lod,vertices,frames,base,first,count,flags=struct.unpack_from('<8I',data,mo+i*64)
    if role not in (1,2):continue
    scale,radius,width,height,depth=struct.unpack_from('<5f',data,mo+i*64+32)
    points=[tuple(v*scale for v in struct.unpack_from('<3f',data,vo+base*16+j*48)) for j in range(vertices*frames)]
    low=[min(p[a] for p in points) for a in range(3)];high=[max(p[a] for p in points) for a in range(3)]
    # This bottom band only measures source geometry; it does not identify wheels
    # semantically or declare a support collider from a cannon-inclusive bound.
    bottom=[p for p in points if p[1]<=low[1]+(high[1]-low[1])*.1]
    rows.append({'role':role,'lod':lod,'frames':frames,'vertices_per_frame':vertices,'source_scale':scale,'scaled_xyz_min':low,'scaled_xyz_max':high,'scaled_planar_radius':max(math.hypot(p[0],p[2]) for p in points),'bottom_tenth_xyz_min':[min(p[a] for p in bottom) for a in range(3)],'bottom_tenth_xyz_max':[max(p[a] for p in bottom) for a in range(3)],'physical_nominal_circle_radius':(3.55 if role==1 else 4.49)})
print(json.dumps({'model_sha256':hashlib.sha256(data).hexdigest(),'scope':'Actual baked source vertices at renderer scale, all clip frames and both LODs; no terrain pose or physical collider acceptance','bounds':rows},indent=2))
