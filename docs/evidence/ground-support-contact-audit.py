#!/usr/bin/env python3
"""Development-only measurement of upright source hulls against actual CPU terrain."""
from pathlib import Path
import ctypes as C,hashlib,json,math,struct,sys
root=Path(__file__).resolve().parents[2];library=Path(sys.argv[1]).resolve();world=C.CDLL(str(library))
world.sim_init.argtypes=[C.c_uint,C.c_uint];world.sim_init(8192,42)
world.sim_checksum.restype=C.c_uint64
world.terrain_height.argtypes=[C.c_float,C.c_float];world.terrain_height.restype=C.c_float
before=world.sim_checksum();path=root/'content/models/battle.rham';data=path.read_bytes()
magic,version,size,meshes,clips,vectors,mo,co,vo=struct.unpack_from('<4s8I',data);assert magic==b'RHAM'
rows=[]
for i in range(meshes):
    role,lod,vertices,frames,base,first,count,flags=struct.unpack_from('<8I',data,mo+i*64)
    if role not in (1,2) or lod!=0:continue
    scale=struct.unpack_from('<f',data,mo+i*64+32)[0]
    points=[tuple(v*scale for v in struct.unpack_from('<3f',data,vo+base*16+j*48)) for j in range(vertices)]
    for label,x,z,yaw in (('shallow_control',1000.,1000.,0.),('gentle_forward',5750.,5200.,math.pi/2),('gentle_cross',5750.,5200.,0.),('plateau',5550.,5200.,math.pi/2)):
        h=world.terrain_height(x,z);sy=math.sin(yaw);cy=math.cos(yaw);gaps=[]
        for px,py,pz in points:
            wx=x+cy*px+sy*pz;wz=z-sy*px+cy*pz
            gaps.append(h+py-world.terrain_height(wx,wz))
        rows.append({'role':role,'fixture':label,'center_xz':[x,z],'heading':yaw,'vertices':vertices,'minimum_source_vertex_ground_gap':min(gaps),'penetrating_vertices':sum(g<-.027 for g in gaps),'interpretation':'Computed from audited current upright mesh shader placement and actual CPU height; not GPU capture or future supported-hull acceptance'})
after=world.sim_checksum();assert before==after,'readonly terrain query mutated authority'
print(json.dumps({'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'model_sha256':hashlib.sha256(data).hexdigest(),'authority_before_after':f'{before:016x}','rows':rows,'scope':'Actual immutable world height, frame0 sourced geometry and renderer placement equation; cosmetic support gap, no contact physics or sampled-GPU proof'},indent=2))
