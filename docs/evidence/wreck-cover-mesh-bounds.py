#!/usr/bin/env python3
"""Development-only exact existing pack bounds for prospective wreck cover."""
from pathlib import Path
import hashlib,json,math,struct
root=Path(__file__).resolve().parents[2];p=root/'content/models/battle.rham';data=p.read_bytes();header=struct.unpack_from('<12I',data);assert header[0]==0x4d414852 and header[1]==1 and header[2]==len(data)
rows=[]
for i in range(header[3]):
 desc=struct.unpack_from('<8I5f3I',data,header[6]+64*i);role,lod,vertices,frames,base=desc[:5]
 if role not in (1,2):continue
 def bounds(frame_indices):
  lo=[math.inf]*3;hi=[-math.inf]*3
  for frame in frame_indices:
   for vertex in range(vertices):
    pos=struct.unpack_from('<3f',data,header[8]+base*16+(frame*vertices+vertex)*48)
    for axis,v in enumerate(pos):lo[axis]=min(lo[axis],v);hi[axis]=max(hi[axis],v)
  return {'minimum':lo,'maximum':hi}
 rows.append({'role':role,'lod':lod,'vertices':vertices,'frames':frames,'frame0':bounds([0]),'all_frames':bounds(range(frames))})
roles=[]
for role in (1,2):
 r=[q for q in rows if q['role']==role];lo=[min(q['frame0']['minimum'][axis] for q in r) for axis in range(3)];hi=[max(q['frame0']['maximum'][axis] for q in r) for axis in range(3)];radius=max(math.sqrt(sum(v*v for v in corner)) for corner in ((x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])))
 high=next(q for q in r if q['lod']==0);low=next(q for q in r if q['lod']==1)
 roles.append({'role':role,'frame0_union':{'minimum':lo,'maximum':hi},'rotation_invariant_conservative_radius_from_entity_origin':radius,'high_minus_low_maximum_y':high['frame0']['maximum'][1]-low['frame0']['maximum'][1]})
print(json.dumps({'pack':str(p),'sha256':hashlib.sha256(data).hexdigest(),'meshes':rows,'prospective_static_wreck_bounds':roles,'scope':'Measurements of actual existing sourced geometry only. No cover shape/art/runtime change. Whole3D boxes are conservative; low LOD height differs substantially and needs matched visible cover treatment before physical/rendered acceptance. Geometry extents do not establish cockpit/muzzle sockets.'},indent=2))
