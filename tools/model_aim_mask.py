#!/usr/bin/env python3
"""Offline reference-space upper-body weights; preserve all geometry/material data."""
import argparse,hashlib,json,pathlib,struct

def apply(blob):
 data=bytearray(blob);head=struct.unpack_from('<12I',data);mo,co,vo=head[6:9];reports=[]
 assert head[0:2]==(0x4d414852,1)and head[2]==len(data)
 for m in range(head[3]):
  role,lod,vertices,frames,base,first,count=struct.unpack_from('<7I',data,mo+m*64)
  if role!=0:continue
  aim=next(struct.unpack_from('<I',data,co+c*16)[0]for c in range(first,first+count)if struct.unpack_from('<I',data,co+c*16+12)[0]==3)
  weights=[]
  for v in range(vertices):
   y=struct.unpack_from('<f',data,vo+base*16+(aim*vertices+v)*48+4)[0]
   # Static authored firing-reference mask, not animated-frame height slicing.
   t=max(0.,min(1.,(y-.8)/.25));weights.append(t*t*(3-2*t))
  for frame in range(frames):
   for v,w in enumerate(weights):struct.pack_into('<f',data,vo+base*16+(frame*vertices+v)*48+28,w)
  assert any(w==0 for w in weights)and any(w==1 for w in weights)
  reports.append({'role':role,'lod':lod,'reference_frame':aim,'vertices':vertices,'lower_vertices':sum(w==0 for w in weights),'upper_vertices':sum(w==1 for w in weights),'blend_vertices':sum(0<w<1 for w in weights)})
 return bytes(data),reports
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pack',type=pathlib.Path);p.add_argument('report',type=pathlib.Path);a=p.parse_args();old=a.pack.read_bytes();new,weights=apply(old);report=json.loads(a.report.read_text());report['aim_mask']={'version':1,'method':'Static authored firing-reference height mask in unused normal.w; no original skin weights/IK','source_pack_sha256':hashlib.sha256(old).hexdigest(),'meshes':weights};report['sha256']=hashlib.sha256(new).hexdigest();a.pack.write_bytes(new);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['aim_mask']))
