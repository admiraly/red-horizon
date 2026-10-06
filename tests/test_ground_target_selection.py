#!/usr/bin/env python3
"""Independent sparse nearest-visible oracle over actual public world ticks."""
import ctypes as C,json,math,random,collections,pathlib,hashlib,sys
paths=[pathlib.Path(p).resolve() for p in sys.argv[1:]];assert 1<=len(paths)<=2
libs=[C.CDLL(str(p)) for p in paths]
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
arrays=[(Entity*32768).in_dll(l,'sim_entities') for l in libs]
for l in libs:
 l.sim_checksum.restype=C.c_uint64;l.terrain_height.argtypes=[C.c_float]*2;l.terrain_height.restype=C.c_float;l.world_los.argtypes=[C.c_float]*6;l.world_los.restype=C.c_uint
rng=random.Random(52913);cases=[]
for side in (0,1):
 for case in range(40):
  source=12+96*side;ids=list(range(96*(1-side),96*(1-side)+80))
  sx,sz=(1251,2000) if case==0 else (3970,1300) if case==1 else (rng.uniform(1200,6500),rng.uniform(1600,6400))
  points=[(sx+rng.uniform(-600,600),sz+rng.uniform(-600,600)) for _ in ids]
  points=[(x,z) if math.hypot(x-sx,z-sz)>30 else (sx+50,z) for x,z in points]
  if case==0:points=[(951,2000),(1551,2000)]+[(sx+600,sz+i*3) for i in range(78)]
  if case==1:points=[(4030,1300),(3700,1300)]+[(sx+600,sz+i*3) for i in range(78)]
  for li,l in enumerate(libs):
   assert l.sim_init(192,42)==0
   e=arrays[li]
   for a in e[:192]:a.hp=0
   e[source].x,e[source].z,e[source].hp,e[source].front=sx,sz,400,0
   # Deliberately invalid/stale initial target hints must not change selection.
   e[source].target=ids[0] if case in (0,1) else 191 if case%2 else -1
   ammo=(C.c_uint*32768).in_dll(l,'sim_shell_ammo')
   for i,(x,z) in zip(ids,points):e[i].x,e[i].z,e[i].hp,e[i].kind,e[i].front=x,z,100,0,0
   for s in range(2):
    for f in range(3):assert l.sim_order(s,f,1)==0
   l.sim_tick()
  if len(libs)==2:
   assert libs[0].sim_checksum()==libs[1].sim_checksum(),(side,case)
   assert bytes(arrays[0])==bytes(arrays[1])
  e=arrays[0];sx,sz=e[source].x,e[source].z
  # Oracle is exhaustive when no relevant cell exceeds the24-ID reservoir.
  counts=collections.Counter((int(a.x*.004),int(a.z*.004)) for a in e[:192] if a.hp)
  eligible=[]
  for i in ids:
   if not e[i].hp:continue
   x,z=e[i].x,e[i].z;d=(x-sx)**2+(z-sz)**2
   if d>450**2:continue
   assert counts[(int(x*.004),int(z*.004))]<=24
   y0=libs[0].terrain_height(sx,sz)+2;y1=libs[0].terrain_height(x,z)+2
   before=libs[0].sim_checksum();visible=libs[0].world_los(sx,y0,sz,x,y1,z);assert libs[0].sim_checksum()==before
   if visible:eligible.append((d,i))
  if case==0:assert e[source].target==ids[1]
  elif case==1:assert e[source].target==ids[1]
  elif eligible:assert abs(next(d for d,i in eligible if i==e[source].target)-min(d for d,i in eligible))<.01
  else:assert e[source].target==-1
  # Two real consecutive ticks exercise reuse of an actual acquired target.
  for l in libs:l.sim_tick()
  if len(libs)==2:assert libs[0].sim_checksum()==libs[1].sim_checksum() and bytes(arrays[0])==bytes(arrays[1])
  cases.append({'side':side,'case':case,'target':e[source].target,'visible_candidates':len(eligible)})
report={'passed':True,'seed':52913,'cases':cases,'libraries_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'limits':['Initial sparse fixtures and stale hints only; two actual world ticks and unchanged complete authority.','Independent exhaustive distance/visibility oracle in unsaturated relevant cells; physical LOS uses production geometry queries.','Equal-distance tie case preserves original reservoir rank; hidden closest target selects farther visible target.']}
print(json.dumps({'suite':'ground-target-selection',**report}))
