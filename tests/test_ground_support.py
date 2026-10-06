#!/usr/bin/env python3
"""Development-only independent support plane, exact renderer frame and ABI proof."""
import ctypes as C, hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM', '/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
def f(v):return struct.unpack('<f',struct.pack('<f',v))[0]
field=json.loads((ROOT/'content/terrain/relief.json').read_text())['fields'][0]
def factor(p,b):
 if p<=b[0] or p>=b[3]:return 0.
 if p<b[1]:return (p-b[0])/(b[1]-b[0])
 if p>b[2]:return (b[3]-p)/(b[3]-b[2])
 return 1.
def analytic(x,z):return 12+(x-4000)**2*1e-6+(z-4000)**2*5e-7+max(0,1-abs(x-4000)/800)*18+field['height']*factor(x,field['x'])*factor(z,field['z'])
def mm(a,b):return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def basis(y,p,b):
 cy,sy,cp,sp,cb,sb=math.cos(y),math.sin(y),math.cos(p),math.sin(p),math.cos(b),math.sin(b)
 return mm(mm([[cy,0,sy],[0,1,0],[-sy,0,cy]],[[1,0,0],[0,cp,sp],[0,-sp,cp]]),[[cb,-sb,0],[sb,cb,0],[0,0,1]])
def geometry(kind,x,z,y):
 w,l,off=(1.75,2.55,-.45) if kind==1 else (2.40,3.43,-.01)
 # The public ABI takes binary32 world coordinates and platform float trig.
 # Retain their actual sample locations, then fit independently in double.
 sy,cy=f(math.sin(y)),f(math.cos(y));points=[]
 for r,t in ((w,l),(w,-l),(-w,l),(-w,-l)):
  r,t=f(r),f(f(t)+f(off))
  points.append((f(f(f(r*cy)+f(t*sy))+x),f(f(f(t*cy)-f(r*sy))+z)))
 return w,l,off,points
with tempfile.TemporaryDirectory(prefix='rh-support-') as name:
 td=pathlib.Path(name)
 def build(tag,extra=None,world=False,flat=False):
  srcs=[str(p.relative_to(ROOT)) for folder in ('sim','nav','ai','game') for p in sorted((ROOT/'src'/folder).glob('*.asm'))] if world else ['src/nav/terrain.asm','src/nav/terrain_relief.asm','src/nav/ground_support.asm','tests/probe_ground_support.asm']
  objs=[]
  for i,s in enumerate(srcs):
   source=ROOT/s
   if extra and s=='src/nav/ground_support.asm':source=td/(tag+'.asm');source.write_text(extra)
   if flat and s=='src/nav/terrain.asm':
    source=td/'flat-height.asm';source.write_text('default rel\nsection .rodata\nh: dd 12.0\nsection .text\nglobal terrain_height\nterrain_height: movss xmm0,[h]\n ret\nsection .note.GNU-stack noalloc noexec nowrite progbits\n')
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(source),'-o',str(obj)],check=True);objs.append(str(obj))
  so=td/(tag+'.so');wrap=[] if world else ['-Wl,--wrap='+n for n in ('sinf','cosf','atan2f','terrain_height')];subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,*wrap,'-lm','-o',str(so)],check=True)
  lib=C.CDLL(str(so));lib.ground_support.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*3;lib.ground_support.restype=C.c_int
  lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
  if not world:lib.probe_ground_support.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p]+[C.c_float]*3
  return lib,so
 lib,so=build('support');maxerr=[0.,0.,0.];count=0
 def observe(lib,kind,x,z,y,probe=False):
  global count
  x,z,y=map(f,(x,z,y));out=C.create_string_buffer(b'\xa5'*96,96);regs=(C.c_uint64*6)()
  calls=C.c_uint64.in_dll(lib,'support_probe_height_calls');before_calls=calls.value
  result=lib.probe_ground_support(out,kind,64,regs,x,z,y) if probe else lib.ground_support(out,kind,64,x,z,y)
  assert calls.value-before_calls==5,'not exactly four corners plus center'
  assert C.c_uint64.in_dll(lib,'support_probe_alignment_errors').value==0,'unaligned external call'
  assert result==0,(kind,x,z,y,result)
  if probe:assert tuple(regs)==tuple(0x123401+i for i in range(6)),tuple(regs)
  assert out.raw[64:]==b'\xa5'*32,'output overrun'
  values=struct.unpack('<16f',out.raw[:64]);assert struct.unpack_from('<I',out.raw,12)[0]==1
  assert all(math.isfinite(v) for i,v in enumerate(values) if i!=3)
  assert all(out.raw[i:i+4]==bytes(4) for i in (28,44,60))
  w,l,off,points=geometry(kind,x,z,y);heights=[lib.terrain_height(*p) for p in points]
  for p,h in zip(points,heights):assert abs(h-analytic(*p))<2.5e-5,(p,h,analytic(*p))
  rs=(heights[0]+heights[1]-heights[2]-heights[3])/(4*f(w));fs=(heights[0]+heights[2]-heights[1]-heights[3])/(4*f(l))
  height=max([h-r*f(w)*rs-(f(off)+t*f(l))*fs for h,(r,t) in zip(heights,((1,1),(1,-1),(-1,1),(-1,-1)))]+[lib.terrain_height(x,z)])
  pitch,bank=math.atan2(fs,1),math.atan2(rs,math.sqrt(1+fs*fs))
  for i,(actual,want) in enumerate(zip(values[:3],(height,pitch,bank))):
   maxerr[i]=max(maxerr[i],abs(actual-want));assert abs(actual-want)<(3e-5 if i==0 else 8e-6),(kind,x,z,y,i,actual,want)
  frame=basis(y,values[1],values[2]);axes=[values[4:7],values[8:11],values[12:15]]
  for j,a in enumerate(axes):
   assert max(abs(a[i]-frame[i][j]) for i in range(3))<3e-7,'wrong rotation order/sign'
   for k,b in enumerate(axes):assert abs(sum(a[i]*b[i] for i in range(3))-(j==k))<5e-7
  cross=[axes[0][1]*axes[1][2]-axes[0][2]*axes[1][1],axes[0][2]*axes[1][0]-axes[0][0]*axes[1][2],axes[0][0]*axes[1][1]-axes[0][1]*axes[1][0]]
  assert max(abs(a-b) for a,b in zip(cross,axes[2]))<5e-7,'left-handed frame'
  for h,(r,t) in zip(heights,((1,1),(1,-1),(-1,1),(-1,-1))):assert values[0]+r*f(w)*rs+(f(off)+t*f(l))*fs>=h-3e-5,'unsupported corner'
  assert values[0]>=lib.terrain_height(x,z)-3e-5
  count+=1
  return values
 points=[(1000,1000),(4000,4000),(3200,3900),(4800,3900),(5400,5200),(5480,5200),(5620,5200),(5820,5200),(5720,5200),(5479,4999),(5550,4800),(5550,5000),(5550,5400),(5550,5600)]
 rng=random.Random(248293)
 points += [(rng.uniform(10,7990),rng.uniform(10,7990)) for _ in range(600)]
 points += [(rng.uniform(5385,5835),rng.uniform(4785,5615)) for _ in range(600)]
 for kind in (1,2):
  for x,z in points:
   for yaw in (0,.7,-1.9,math.pi):observe(lib,kind,x,z,yaw,True)
 invalid=[]
 for kind in (0,3,0xffffffff):invalid.append((kind,64,4000,4000,0))
 for cap in (0,1,63):invalid.append((1,cap,4000,4000,0))
 for bad in (math.nan,math.inf,-math.inf,-1,8001):
  invalid.extend(((1,64,bad,4000,0),(2,64,4000,bad,0)))
 for bad in (math.nan,math.inf,-math.inf,-3.15,3.15):invalid.append((1,64,4000,4000,bad))
 for kind in (1,2):
  for xy in ((0,0),(8000,8000),(.1,4000),(7999.9,4000),(4000,.1),(4000,7999.9)):
   for yaw in (0,.7,-1.9):invalid.append((kind,64,*xy,yaw))
 for kind,cap,x,z,y in invalid:
  out=C.create_string_buffer(b'\xa5'*96,96);regs=(C.c_uint64*6)();before_calls=C.c_uint64.in_dll(lib,'support_probe_height_calls').value;assert lib.probe_ground_support(out,kind,cap,regs,x,z,y)==-1
  assert C.c_uint64.in_dll(lib,'support_probe_height_calls').value==before_calls,'invalid input queried terrain'
  assert out.raw==b'\xa5'*96 and tuple(regs)==tuple(0x123401+i for i in range(6))
 assert lib.ground_support(None,1,64,4000,4000,0)==-1
 production_count=count;production_errors=maxerr[:]
 flat,_=build('flat',flat=True)
 for kind in (1,2):
  for yaw in (0,.7,-1.9,math.pi):
   out=C.create_string_buffer(64);assert flat.ground_support(out,kind,64,4000,4000,yaw)==0
   vals=struct.unpack('<16f',out.raw);assert vals[:3]==(12.,0.,0.)
   frame=basis(f(yaw),0,0)
   for j in range(3):assert max(abs(vals[4+4*j+i]-frame[i][j]) for i in range(3))<3e-7
 # Distinguish three actual assembled implementation faults, not Python flags.
 source=(ROOT/'src/nav/ground_support.asm').read_text();faults=[]
 mutations={'flat_pitch':source.replace('movss xmm0,[rsp+84]\n movss xmm1,[one]\n call atan2f','xorps xmm0,xmm0\n movss xmm1,[one]\n call atan2f'), 'wrong_forward':source.replace('movss [rsp+180],xmm0','xorps xmm0,xmm0\n subss xmm0,[rsp+100]\n movss [rsp+180],xmm0'),'center_only':source.replace('maxss xmm0,[rsp+116]','movss xmm0,[rsp+116]')}
 for tag,mutation in mutations.items():
  assert mutation!=source
  bad,_=build(tag,mutation)
  try:
   for x,z in ((5479,4999),(5480,5000),(5400,5200),(4000,4000),(5620,5400)):observe(bad,2,x,z,.7)
  except AssertionError:faults.append(tag)
  else:raise AssertionError('negative implementation accepted: '+tag)
 world,wso=build('world',world=True);world.sim_checksum.restype=C.c_uint64;assert world.sim_init(8192,42)==0
 for _ in range(8):world.sim_tick()
 before=world.sim_checksum()
 for kind in (1,2):
  for x,z in points[:100]:world.ground_support(C.create_string_buffer(64),kind,64,x,z,.7)
 for kind,cap,x,z,y in invalid:world.ground_support(C.create_string_buffer(64),kind,cap,x,z,y)
 after=world.sim_checksum();assert before==after,'read-only query changed world authority'
 report={'ground_support_samples':production_count,'flat_stub_samples':8,'invalid_preserved':len(invalid)+1,'max_cpu_fit_error':production_errors,'negative_controls':faults,'stack_alignment_errors':C.c_uint64.in_dll(lib,'support_probe_alignment_errors').value,'world_entities':8192,'world_readonly_checksum':f'{before:016x}','source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'world_library_sha256':hashlib.sha256(wso.read_bytes()).hexdigest(),'scope':'stateless five-height support and exact mesh rotation; no runtime caller, suspension, oriented collision, entire mesh clearance or rendered acceptance'}
 print(json.dumps(report,sort_keys=True))
