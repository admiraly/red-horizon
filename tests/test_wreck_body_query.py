#!/usr/bin/env python3
"""Prepared planar inflated wreck query and continuous no-deepening observer."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
class W(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
def f(v):return C.c_float(v).value
def clip(box,start,end):
 lo,hi=0.,1.
 for i in range(2):
  d=end[i]-start[i]
  if not d:
   if not box[i]<=start[i]<=box[i+2]:return None
  else:
   a,b=sorted(((box[i]-start[i])/d,(box[i+2]-start[i])/d));lo=max(lo,a);hi=min(hi,b)
   if lo>hi:return None
 return lo
def escape(box,start,end):
 if not (box[0]<=start[0]<=box[2] and box[1]<=start[1]<=box[3]) or start==end:return False
 depths=(start[0]-box[0],box[2]-start[0],start[1]-box[1],box[3]-start[1]);slopes=(end[0]-start[0],start[0]-end[0],end[1]-start[1],start[1]-end[1]);minimum=min(depths)
 allow=any(d==minimum and slope<=0 for d,slope in zip(depths,slopes))
 if allow:
  # Independent continuous consequence sampled densely, in addition to derivative.
  for t in (j/100 for j in range(101)):
   x=start[0]+(end[0]-start[0])*t;z=start[1]+(end[1]-start[1])*t
   assert min(x-box[0],box[2]-x,z-box[1],box[3]-z)<=minimum+1e-10
 return allow
with tempfile.TemporaryDirectory(prefix='rh-wreck-body-') as name:
 td=pathlib.Path(name);objs=[]
 for i,src in enumerate(('src/sim/wrecks.asm','src/nav/wreck_query.asm','src/nav/segment_box.asm','src/nav/terrain.asm','src/nav/terrain_relief.asm','src/nav/ground_support.asm','src/nav/ground_contact.asm','tests/probe_wrecks.asm','tests/probe_wreck_body.asm')):
  obj=td/f'{i}.o';subprocess.run([NASM,'-f','elf64','-D','WRECK_STANDALONE=1','-I',str(ROOT)+'/',str(ROOT/src),'-o',str(obj)],check=True);objs.append(str(obj))
 def link(tag,objects):
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,*['-Wl,--wrap='+s for s in ('ground_support','ground_contact','terrain_height','sinf','cosf','atan2f')],'-lm','-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_wreck_body_query.argtypes=[C.c_void_p,C.c_uint,C.c_void_p]+[C.c_float]*5;return lib,so
 lib,so=link('candidate',objs);wrecks=(W*1024).in_dll(lib,'sim_wrecks');count=C.c_uint.in_dll(lib,'sim_wreck_count');rev=C.c_uint64.in_dll(lib,'wreck_query_revision');bounds=(C.c_float*(1024*6)).in_dll(lib,'wreck_query_bounds');regs=C.create_string_buffer(56);calls=escaped=hits=0;maxerr=0.;rng=random.Random(100529)
 def fixture(rows):
  lib.wreck_init()
  for i,w in enumerate(rows):wrecks[i]=w
  count.value=len(rows);rev.value+=1
 def record(x=1000,z=1000,heading=0,kind=1,entity=12):return W(x,100,z,heading,.12,-.17,kind,entity%2,entity,1,0,1800,entity+1,1,0,0)
 def arena():return C.string_at(C.addressof(wrecks),196620)
 def query(start,end,radius,expect=None,which=lib):
  global calls
  out=C.create_string_buffer(b'Z'*24,24);old=arena();rc=which.probe_wreck_body_query(out,24,regs,*start,*end,radius);assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert arena()==old
  assert C.c_uint64.in_dll(which,'wreck_probe_alignment_errors').value==0
  if expect is not None:assert rc==expect,(start,end,radius,rc,expect)
  if rc!=1:assert out.raw==b'Z'*24
  calls+=1;return rc,struct.unpack('<f5I',out.raw) if rc==1 else None
 fixture([record()]);query((990,1000),(1010,1000),0)
 # Explicit nearest-face escape, inward, parallel slide, zero occupied and cross-center.
 b=tuple(bounds[:6]);box=(f(b[0]-.551),f(b[2]-.551),f(b[3]+.551),f(b[5]+.551))
 cases=[((box[0]+.1,1000),(box[0]-.1,1000),0),((box[0]+.1,1000),(box[2]+2,1000),1),((box[0]+.1,1000),(box[0]+.1,1001),0),((1000,1000),(1000,1000),1),((box[0],1000),(box[0]-1,1000),0),((box[0],1000),(box[0]+1,1000),1)]
 for start,end,expected in cases:query(tuple(map(f,start)),tuple(map(f,end)),f(.551),expected)
 # Radii are original sweep envelopes, not weakened to simplify contacts.
 rows=[record(x=(i%32)*250+125,z=(i//32)*250+125,heading=rng.uniform(-math.pi,math.pi),kind=1+i%2,entity=i) for i in range(512)];fixture(rows);query((0,0),(8000,8000),0)
 for _ in range(2500):
  index=rng.randrange(512);w=wrecks[index];radius=f(rng.choice((0,.551,3.551,4.491)));start=(f(w.x+rng.uniform(-7,7)),f(w.z+rng.uniform(-7,7)));end=(f(start[0]+rng.uniform(-10,10)),f(start[1]+rng.uniform(-10,10)))
  expected=[]
  for j in range(512):
   b=bounds[j*6:j*6+6];box=(f(b[0]-radius),f(b[2]-radius),f(b[3]+radius),f(b[5]+radius))
   if escape(box,start,end):escaped+=1;continue
   t=clip(box,start,end)
   if t is not None:expected.append((f(t),wrecks[j].entity,wrecks[j].generation,wrecks[j].sequence,j))
  rc,out=query(start,end,radius);assert rc==bool(expected),(index,rc,expected)
  if expected:
   wanted=min(expected);assert out[1:5]==(wanted[4],wanted[1],wanted[2],wanted[3]);error=abs(out[0]-wanted[0]);maxerr=max(maxerr,error);assert error<6e-8;hits+=1
 for bad in (math.nan,math.inf,-math.inf,-.001,4.492,100):query((1000,1000),(1001,1000),bad,-1)
 # Real assembled faults: omit inflation; permit cross-center deeper escape;
 # incorrectly let zero-motion occupied placement pass.
 source=(ROOT/'src/nav/wreck_query.asm').read_text();negatives=[];production_calls=calls
 for tag,text in [('no_inflation',source.replace(' movss xmm0,[rsp+76]\n movss xmm1,[rdi]',' xorps xmm0,xmm0\n movss xmm1,[rdi]')),('any_escape',source.replace(' ucomiss xmm2,xmm6\n jne .right',' jmp .allow\n ucomiss xmm2,xmm6\n jne .right')),('zero_clear',source.replace(' ucomiss xmm1,[zero]\n je .block',' ucomiss xmm1,[zero]\n je .allow',1))]:
  asm=td/(tag+'.asm');asm.write_text(text);obj=td/(tag+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True);objects=list(objs);objects[1]=str(obj);bad,_=link(tag,objects);bw=(W*1024).in_dll(bad,'sim_wrecks');bad.wreck_init();bw[0]=record();C.c_uint.in_dll(bad,'sim_wreck_count').value=1;C.c_uint64.in_dll(bad,'wreck_query_revision').value+=1
  query((990,1000),(1010,1000),0,which=bad);bb=(C.c_float*6144).in_dll(bad,'wreck_query_bounds');lo,hi=bb[0],bb[3]
  if tag=='no_inflation':assert query((lo-1,990),(lo-1,1010),3.551,which=bad)[0]==0
  elif tag=='any_escape':assert query((f(lo+.1),1000),(f(hi+2),1000),0,which=bad)[0]==0
  else:assert query((1000,1000),(1000,1000),0,which=bad)[0]==0
  negatives.append(tag)
 print(json.dumps({'suite':'prepared-wreck-body-query','passed':True,'calls':production_calls,'random_paths':2500,'roles_radii':[0,.551,3.551,4.491],'continuous_no_deepening_samples_per_allowed_overlap':101,'allowed_overlap_cases':escaped,'hits':hits,'maximum_first_t_error':maxerr,'negative_controls':negatives,'ABI_authority_and_alignment':True,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Isolated conservative planar inflated-AABB/escape query only; no actor movement/nav/controller/remote-cover hooks or vertical capsule/mesh collision acceptance'}))
