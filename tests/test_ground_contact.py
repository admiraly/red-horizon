#!/usr/bin/env python3
"""Development-only independent contact floor, exact renderer frame and ABI proof."""
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
with tempfile.TemporaryDirectory(prefix='rh-contact-') as name:
 td=pathlib.Path(name);source=(ROOT/'src/nav/ground_contact.asm').read_text()
 def build(tag,extra=None,bad_height=False):
  sources=['src/nav/terrain.asm','src/nav/terrain_relief.asm','src/nav/ground_contact.asm','tests/probe_ground_contact.asm'];objs=[]
  for i,s in enumerate(sources):
   src=ROOT/s
   if extra and s=='src/nav/ground_contact.asm':src=td/(tag+'.asm');src.write_text(extra)
   if bad_height and s=='src/nav/terrain.asm':
    src=td/'bad-height.asm';src.write_text('section .rodata\nh: dd 0x7fc00000\nsection .text\nglobal terrain_height\nterrain_height: movss xmm0,[rel h]\n ret\nsection .note.GNU-stack noalloc noexec nowrite progbits\n')
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(src),'-o',str(obj)],check=True);objs.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,*['-Wl,--wrap='+n for n in ('sinf','cosf','terrain_height')],'-lm','-o',str(so)],check=True)
  lib=C.CDLL(str(so));lib.probe_ground_contact.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p]+[C.c_float]*5;lib.probe_ground_contact.restype=C.c_int
  lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
  return lib,so
 lib,so=build('contact');count=0;maximum=[0.,0.]
 def contact(lib,kind,x,z,y,p,b,invalid=False,cap=64):
  global count
  x,z,y,p,b=map(f,(x,z,y,p,b));out=C.create_string_buffer(b'\xa5'*96,96);regs=(C.c_uint64*6)()
  calls=C.c_uint64.in_dll(lib,'contact_probe_height_calls');before=calls.value
  ret=lib.probe_ground_contact(out,kind,cap,regs,x,z,y,p,b)
  assert tuple(regs)==tuple(0x123401+i for i in range(6)),'nonvolatile/stack failure'
  assert C.c_uint64.in_dll(lib,'contact_probe_alignment_errors').value==0,'unaligned call'
  if invalid:
   assert ret==-1 and out.raw==b'\xa5'*96 and calls.value==before,'invalid queried terrain or wrote output'
   return
  assert ret==0 and calls.value-before==5
  assert out.raw[64:]==b'\xa5'*32 and struct.unpack_from('<I',out.raw,12)[0]==1
  vals=struct.unpack('<16f',out.raw[:64]);assert vals[1:3]==(p,b)
  assert all(out.raw[i:i+4]==bytes(4) for i in (28,44,60))
  frame=basis(y,p,b);axes=[vals[4:7],vals[8:11],vals[12:15]]
  for j,a in enumerate(axes):
   assert max(abs(a[i]-frame[i][j]) for i in range(3))<3e-7,'wrong rotation'
   for k,d in enumerate(axes):assert abs(sum(a[i]*d[i] for i in range(3))-(j==k))<5e-7
  cross=[axes[0][1]*axes[1][2]-axes[0][2]*axes[1][1],axes[0][2]*axes[1][0]-axes[0][0]*axes[1][2],axes[0][0]*axes[1][1]-axes[0][1]*axes[1][0]]
  assert max(abs(a-b) for a,b in zip(cross,axes[2]))<5e-7
  w,l,off=(1.75,2.55,-.45) if kind==1 else (2.4,3.43,-.01)
  actual_floor=[lib.terrain_height(x,z)];independent_floor=[analytic(x,z)]
  for r,t in ((w,l),(w,-l),(-w,l),(-w,-l)):
   r,t=f(r),f(f(t)+f(off))
   dx=[f(f(r*axes[0][i])+f(t*axes[2][i])) for i in range(3)]
   xx,zz=f(dx[0]+x),f(dx[2]+z);h=lib.terrain_height(xx,zz)
   assert abs(h-analytic(xx,zz))<2.5e-5,'terrain observer mismatch'
   actual_floor.append(h-dx[1])
   q=[r*frame[i][0]+t*frame[i][2] for i in range(3)]
   independent_floor.append(analytic(x+q[0],z+q[2])-q[1])
  err=abs(vals[0]-max(actual_floor));inderr=abs(vals[0]-max(independent_floor))
  maximum[0]=max(maximum[0],err);maximum[1]=max(maximum[1],inderr)
  assert err<2e-5,'rotated local Y omitted/contact floor incorrect'
  assert inderr<.0007,'independent projected-contact disagreement'
  assert all(vals[0]>=h-2e-5 for h in actual_floor)
  count+=1
 points=[(4000,4000),(1000,1000),(3200,3900),(4800,3900),(5400,5200),(5480,5200),(5620,5200),(5820,5200),(5479,4999),(5480,5000),(5620,5400),(5720,5200)]
 rng=random.Random(772971);points.extend((rng.uniform(10,7990),rng.uniform(10,7990)) for _ in range(400));points.extend((rng.uniform(5385,5835),rng.uniform(4785,5615)) for _ in range(400))
 for kind in (1,2):
  for x,z in points:
   for y,p,b in ((0,0,0),(.7,.3,-.2),(-1.9,-.4,.35),(math.pi,math.pi/2,-math.pi/2)):contact(lib,kind,x,z,y,p,b)
 for kind in (1,2):
  for x,z in points[12:412]:contact(lib,kind,x,z,rng.uniform(-math.pi,math.pi),rng.uniform(-math.pi/2,math.pi/2),rng.uniform(-math.pi/2,math.pi/2))
 invalid=[]
 for kind in (0,3,0xffffffff):invalid.append((kind,64,4000,4000,0,0,0))
 for cap in (0,1,63):invalid.append((1,cap,4000,4000,0,0,0))
 for axis,limit in enumerate((8000,8000,math.pi,math.pi/2,math.pi/2)):
  for bad in (math.nan,math.inf,-math.inf,limit+.01,-limit-.01):
   a=[4000,4000,0,0,0];a[axis]=bad;invalid.append((1,64,*a))
 for kind in (1,2):
  for x,z in ((0,0),(8000,8000),(.1,4000),(7999.9,4000),(4000,.1),(4000,7999.9)):
   for y,p,b in ((0,0,0),(.7,.3,-.2),(-1.9,-.4,.35)):invalid.append((kind,64,x,z,y,p,b))
 for kind,cap,x,z,y,p,b in invalid:contact(lib,kind,x,z,y,p,b,True,cap)
 regs=(C.c_uint64*6)();prior=C.c_uint64.in_dll(lib,'contact_probe_height_calls').value
 assert lib.probe_ground_contact(None,1,64,regs,4000,4000,0,0,0)==-1
 assert C.c_uint64.in_dll(lib,'contact_probe_height_calls').value==prior
 badheight,_=build('badheight',bad_height=True);out=C.create_string_buffer(b'\xa5'*96,96)
 assert badheight.probe_ground_contact(out,1,64,regs,4000,4000,0,.3,.2)==-1 and out.raw==b'\xa5'*96,'nonfinite terrain published'
 assert tuple(regs)==tuple(0x123401+i for i in range(6))
 assert C.c_uint64.in_dll(badheight,'contact_probe_alignment_errors').value==0
 production_count=count;production_max=maximum[:]
 mutations={'upright_only':source.replace(' ; Frame =',' mov dword [rsp+100],0\n mov dword [rsp+104],0x3f800000\n mov dword [rsp+108],0\n mov dword [rsp+112],0x3f800000\n ; Frame ='),'omitted_local_y':source.replace('subss xmm0,[rsp+64+rbx*4]','nop'),'wrong_rotation':source.replace('movss [rsp+148],xmm0','xorps xmm0,xmm0\n subss xmm0,[rsp+108]\n movss [rsp+148],xmm0')};faults=[]
 for tag,text in mutations.items():
  assert text!=source;bad,_=build(tag,text)
  try:contact(bad,2,5480,5000,.7,.3,-.2)
  except AssertionError:faults.append(tag)
  else:raise AssertionError('fault escaped '+tag)
 print(json.dumps({'ground_contact_samples':production_count,'invalid_zero_query_preserved':len(invalid)+1,'nonfinite_height_preserved':1,'max_cpu_floor_error':production_max[0],'max_independent_matrix_floor_error':production_max[1],'negative_controls':faults,'alignment_errors':C.c_uint64.in_dll(lib,'contact_probe_alignment_errors').value,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'isolated five-point intermediate-pose contact; no renderer integration, entire mesh clearance or physical suspension acceptance'},sort_keys=True))
