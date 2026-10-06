#!/usr/bin/env python3
"""Independent transformed-corner, spatial first-contact and lifecycle observer."""
import ctypes as C,hashlib,itertools,json,math,os,pathlib,random,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
class Wreck(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
def f(x):return C.c_float(x).value
def bounds(w):
 # Rotate each corner in three explicit stages, independent of runtime matrix.
 ext=(1.895,1.30455,3.) if w.kind==1 else (2.528,1.59185,3.5)
 cy=1.31645 if w.kind==1 else 1.60815
 corners=[]
 for a,b,c in itertools.product((-1,1),repeat=3):
  x,y,z=a*ext[0],cy+b*ext[1],c*ext[2]
  sb,cb=math.sin(w.bank),math.cos(w.bank);x,y=cb*x-sb*y,sb*x+cb*y
  sp,cp=math.sin(w.pitch),math.cos(w.pitch);y,z=cp*y+sp*z,-sp*y+cp*z
  sh,ch=math.sin(w.heading),math.cos(w.heading);x,z=ch*x+sh*z,-sh*x+ch*z
  corners.append((x+w.x,y+w.y,z+w.z))
 return tuple(min(c[i] for c in corners)-.002 for i in range(3))+tuple(max(c[i] for c in corners)+.002 for i in range(3))
def clip(b,s,e):
 enter,leave=0.,1.
 for axis in range(3):
  d=e[axis]-s[axis]
  if not d:
   if not b[axis]<=s[axis]<=b[axis+3]:return None
  else:
   a,z=sorted(((b[axis]-s[axis])/d,(b[axis+3]-s[axis])/d));enter=max(enter,a);leave=min(leave,z)
   if enter>leave:return None
 return enter
with tempfile.TemporaryDirectory(prefix='rh-wreck-query-') as name:
 td=pathlib.Path(name);objs=[]
 sources=('src/sim/wrecks.asm','src/nav/wreck_query.asm','src/nav/segment_box.asm','src/nav/terrain.asm','src/nav/terrain_relief.asm','src/nav/ground_support.asm','src/nav/ground_contact.asm','tests/probe_wrecks.asm','tests/probe_wreck_query.asm')
 for i,src in enumerate(sources):
  obj=td/f'{i}.o';subprocess.run([NASM,'-f','elf64','-D','WRECK_STANDALONE=1','-I',str(ROOT)+'/',str(ROOT/src),'-o',str(obj)],check=True);objs.append(str(obj))
 def link(tag,objects):
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,*['-Wl,--wrap='+s for s in ('ground_support','ground_contact','terrain_height','sinf','cosf','atan2f')],'-lm','-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_wreck_query.argtypes=[C.c_void_p,C.c_uint,C.c_void_p]+[C.c_float]*6;return lib,so
 lib,so=link('candidate',objs)
 def state(lib):
  return ((Wreck*1024).in_dll(lib,'sim_wrecks'),C.c_uint.in_dll(lib,'sim_wreck_count'),C.c_uint64.in_dll(lib,'wreck_query_revision'))
 W,count,rev=state(lib);cache=(C.c_float*(1024*6)).in_dll(lib,'wreck_query_bounds');candidates=C.c_uint.in_dll(lib,'wreck_query_candidates');lib.wreck_init();calls=0;maxerr=0.;maxshort=0
 def authority():return C.string_at(C.addressof(W),1024*64+32768*4+12)
 def query(s,e,cap=24,null=False,which=lib):
  global calls
  out=C.create_string_buffer(b'Z'*24,24);regs=C.create_string_buffer(56);old=authority() if which is lib else None
  rc=which.probe_wreck_query(None if null else out,cap,regs,*map(f,(*s,*e)))
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6))
  if which is lib:assert authority()==old
  assert C.c_uint64.in_dll(which,'wreck_probe_alignment_errors').value==0
  if rc!=1:assert out.raw==b'Z'*24
  calls+=1
  return rc,struct.unpack('<f5I',out.raw) if rc==1 else None
 def fixture(records):
  lib.wreck_init()
  for i,w in enumerate(records):W[i]=w
  count.value=len(records);rev.value+=1
 def record(x=1000,y=30,z=1000,heading=0,pitch=0,bank=0,kind=1,entity=12,seq=1):return Wreck(x,y,z,heading,pitch,bank,kind,entity%2,entity,1,0,1800,seq,1,0,0)
 # Verify every actual high/low frame0 vertex against the outward local policy.
 pack=(ROOT/'content/models/battle.rham').read_bytes();header=struct.unpack_from('<12I',pack);mesh_vertices=0
 local={1:((-1.895,.0119,-3.),(1.895,2.621,3.)),2:((-2.528,.0163,-3.5),(2.528,3.200,3.5))}
 for mesh in range(header[3]):
  d=struct.unpack_from('<8I5f3I',pack,header[6]+mesh*64);role,lod,vertices,frames,base=d[:5]
  if role not in local:continue
  low,high=local[role]
  for vertex in range(vertices):
   xyz=struct.unpack_from('<3f',pack,header[8]+base*16+vertex*48)
   assert all(low[axis]<=xyz[axis]<=high[axis] for axis in range(3)),(role,lod,xyz)
   mesh_vertices+=1
 assert mesh_vertices>1000
 rng=random.Random(942005)
 records=[record(x=min(8000,(i%32)*250+rng.uniform(0,250)),z=min(8000,(i//32)*250+rng.uniform(0,250)),y=rng.uniform(-100,100),heading=rng.uniform(-math.pi,math.pi),pitch=rng.uniform(-.8,.8),bank=rng.uniform(-.8,.8),kind=1+i%2,entity=i,seq=i+1) for i in range(1024)]
 fixture(records);assert query((0,0,0),(8000,0,8000))[0] in (0,1);diagonal_candidates=candidates.value;assert diagonal_candidates<128
 expected=[bounds(w) for w in W]
 for i,b in enumerate(expected):
  actual=tuple(cache[i*6+j] for j in range(6));assert max(abs(a-z) for a,z in zip(actual,b))<.0016,(i,actual,b)
 # Compare independent all-record nearest contacts against spatial runtime.
 for _ in range(2000):
  i=rng.randrange(1024);w=W[i];s=(f(w.x-12),f(w.y+1),f(w.z));e=(f(w.x+12),f(w.y+1),f(w.z))
  if rng.random()<.25:s,e=(s[0],f(w.y+12),s[2]),(e[0],f(w.y+12),e[2])
  hits=[(t,w.entity,w.generation,w.sequence,j) for j,(w,b) in enumerate(zip(W,expected)) if (t:=clip(b,s,e)) is not None]
  rc,out=query(s,e);maxshort=max(maxshort,candidates.value)
  assert rc==bool(hits),(i,rc,hits)
  if hits:
   t,entity,generation,sequence,slot=min(hits);assert out[1:5]==(slot,entity,generation,sequence)
   err=abs(out[0]-t);maxerr=max(maxerr,err);assert err<.0001,(out,t)
 assert maxshort<=9
 # Long, reverse, nearly horizontal, boundary and outside-map segments use
 # the same independent exhaustive corner/slab oracle, with no spatial pruning.
 long_paths=[((0,0,0),(8000,0,8000)),((8000,0,0),(0,0,8000)),
  ((-16000,0,-16000),(16000,0,16000)),((8000,0,8000),(0,0,0)),
  ((0,0,62.5),(8000,0,62.5001)),((8000,0,62.5001),(0,0,62.5))]
 for _ in range(250):
  w=W[rng.randrange(1024)];scale=rng.uniform(100,7500);angle=rng.uniform(-math.pi,math.pi)
  dx,dz=math.cos(angle)*scale,math.sin(angle)*scale
  long_paths.append(((f(w.x-dx),f(w.y+1),f(w.z-dz)),(f(w.x+dx),f(w.y+1),f(w.z+dz))))
 for s,e in long_paths:
  hits=[(t,w.entity,w.generation,w.sequence,j) for j,(w,b) in enumerate(zip(W,expected)) if (t:=clip(b,s,e)) is not None]
  rc,out=query(s,e);assert rc==bool(hits),(s,e,rc,hits)
  if hits:
   t,entity,generation,sequence,slot=min(hits);assert out[1:5]==(slot,entity,generation,sequence),(s,e,out,min(hits))
   err=abs(out[0]-t);maxerr=max(maxerr,err);assert err<.0001,(s,e,out,t)
 # Coincident records require identity tie independent of order/side labels.
 for flip in (0,1):
  records=[record(entity=i,seq=2048-i) for i in range(1024)];records.reverse()
  for w in records:w.side^=flip
  fixture(records);rc,out=query((990,31,1000),(1010,31,1000));assert rc==1 and out[2]==0 and candidates.value==1024
 # Invalid query must reject before cache refresh, preserving caller output.
 for index in range(6):
  for bad in (math.nan,math.inf,-math.inf,16000.01,-16000.01):
   args=[1000.,31.,1000.,1010.,31.,1000.];args[index]=bad;assert query(args[:3],args[3:])[0]==-1
 for cap in (0,23):assert query((0,0,0),(0,0,0),cap=cap)[0]==-1
 assert query((0,0,0),(0,0,0),null=True)[0]==-1
 # Invalid active cache source must fail closed, even outside queried region.
 for field,bad in (('x',math.nan),('y',math.inf),('z',-1),('heading',math.nan),('pitch',17),('bank',math.inf),('kind',0),('side',2),('entity',32768),('generation',0),('sequence',0),('flags',5),('reserved0',1)):
  w=record();setattr(w,field,bad);fixture([w]);assert query((0,0,0),(1,1,1))[0]==-2,field
 fixture([record()]);count.value=2;assert query((0,0,0),(1,1,1))[0]==-2
 # Center-bucket neighbor: visible corner crosses250m cell edge.
 fixture([record(x=249,z=1000)]);assert query((251,31,990),(251,31,1010))[0]==0 # tank halfwidth1.895
 fixture([record(x=249,z=1000,kind=2)]);assert query((251,31,990),(251,31,1010))[0]==1
 # Exact actual registry API invalidation: death, duplicate, expiry, reset,
 # same-clock same-ID reuse and full-ring replacement; no private lifetime changes.
 E=(Entity*32768).in_dll(lib,'sim_entities');C.c_uint.in_dll(lib,'sim_count').value=32768;tick=C.c_uint.in_dll(lib,'sim_tick_count');regs=(C.c_uint64*6)()
 def add(i,x=1000):E[i]=Entity(x,1000,0,0,1,0,-1,1);assert lib.probe_wreck_register(i,regs)==0
 lib.wreck_init();tick.value=0;assert query((990,1,1000),(1010,1,1000))[0]==0
 add(0);assert query((990,W[0].y+1,1000),(1010,W[0].y+1,1000))[0]==1
 oldrev=rev.value;assert lib.probe_wreck_register(0,regs)==1 and rev.value==oldrev
 tick.value=1799;lib.wreck_tick();assert query((990,W[0].y+1,1000),(1010,W[0].y+1,1000))[0]==1
 tick.value=1800;lib.wreck_tick();assert query((990,W[0].y+1,1000),(1010,W[0].y+1,1000))[0]==0
 # Reset followed by re-registration before first query: same sequence/count/tick.
 lib.wreck_init();tick.value=0;add(0,2000);assert query((990,W[0].y+1,1000),(1010,W[0].y+1,1000))[0]==0
 for i in range(1,1025):add(i,3000)
 assert count.value==1024;assert query((1990,W[0].y+1,1000),(2010,W[0].y+1,1000))[0]==0
 assert query((2990,W[0].y+1,1000),(3010,W[0].y+1,1000))[0]==1
 # Assembly negative controls exercise padding, nearest choice and invalidation.
 negatives=[];qsource=(ROOT/'src/nav/wreck_query.asm').read_text();rsource=(ROOT/'src/sim/wrecks.asm').read_text()
 for tag,source,index in [('no_padding',qsource.replace('padding: dd 6.0','padding: dd 0.0'),1),('far_contact',qsource.replace(' jb .select\n ja .next_record',' ja .select\n jb .next_record',1),1),('stale_cache',rsource.replace(' inc qword [wreck_query_revision]',' nop'),0)]:
  asm=td/(tag+'.asm');asm.write_text(source);obj=td/(tag+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True);objects=list(objs);objects[index]=str(obj);bad,_=link(tag,objects);bw,bc,br=state(bad);bad.wreck_init()
  if tag=='no_padding':
   bw[0]=record(x=249,kind=2);bc.value=1;br.value+=1;assert query((251,31,990),(251,31,1010),which=bad)[0]==0
  elif tag=='far_contact':
   bw[0]=record(x=1000);bw[1]=record(x=1020,entity=13,seq=2);bc.value=2;br.value+=1;rc,out=query((990,31,1000),(1040,31,1000),which=bad);assert rc==1 and out[2]==13
  else:
   assert query((990,1,1000),(1010,1,1000),which=bad)[0]==0
   be=(Entity*32768).in_dll(bad,'sim_entities');C.c_uint.in_dll(bad,'sim_count').value=32768;be[0]=Entity(1000,1000,0,0,1,0,-1,1);assert bad.probe_wreck_register(0,regs)==0
   assert query((990,bw[0].y+1,1000),(1010,bw[0].y+1,1000),which=bad)[0]==0
  negatives.append(tag)
 print(json.dumps({'suite':'wreck-spatial-query','passed':True,'query_calls':calls,'actual_frame0_vertices':mesh_vertices,'asset_sha256':hashlib.sha256(pack).hexdigest(),'transformed_bounds':1024,'random_nearest_paths':2000,'maximum_first_t_error':maxerr,'maximum_short_candidates':maxshort,'coincident_candidates':1024,'full_map_diagonal_candidates':diagonal_candidates,'exhaustive_long_paths':len(long_paths),'invalid_callers':33,'malformed_registry_cases':14,'lifecycle_invalidation':True,'negative_controls':negatives,'source_sha256':hashlib.sha256(qsource.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Derived conservative AABB query only; no gameplay/body/LOS/rifle/shell/render/UDP acceptance'}))
