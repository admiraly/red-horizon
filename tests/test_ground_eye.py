#!/usr/bin/env python3
"""Independent unsmoothed gameplay-eye prerequisites; development only."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
def f(v):return struct.unpack('<f',struct.pack('<f',v))[0]
field=json.loads((ROOT/'content/terrain/relief.json').read_text())['fields'][0]
def factor(p,b):
 if p<=b[0] or p>=b[3]:return 0.
 if p<b[1]:return (p-b[0])/(b[1]-b[0])
 if p>b[2]:return (b[3]-p)/(b[3]-b[2])
 return 1.
def height(x,z):return 12+(x-4000)**2*1e-6+(z-4000)**2*5e-7+max(0,1-abs(x-4000)/800)*18+field['height']*factor(x,field['x'])*factor(z,field['z'])
def mm(a,b):return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def frame(y,p,b):
 cy,sy,cp,sp,cb,sb=math.cos(y),math.sin(y),math.cos(p),math.sin(p),math.cos(b),math.sin(b)
 return mm(mm([[cy,0,sy],[0,1,0],[-sy,0,cy]],[[1,0,0],[0,cp,sp],[0,-sp,cp]]),[[cb,-sb,0],[sb,cb,0],[0,0,1]])
def reference(lib,kind,x,z,y):
 w,l,off=(1.75,2.55,-.45) if kind==1 else (2.4,3.43,-.01)
 cy,sy=f(math.cos(y)),f(math.sin(y));points=[]
 for r,t in ((w,l),(w,-l),(-w,l),(-w,-l)):
  r,t=f(r),f(f(t)+f(off));points.append((f(f(f(r*cy)+f(t*sy))+x),f(f(f(t*cy)-f(r*sy))+z)))
 h=[lib.terrain_height(*q) for q in points]
 for q,a in zip(points,h):assert abs(a-height(*q))<2.5e-5
 rs=(h[0]+h[1]-h[2]-h[3])/(4*f(w));fs=(h[0]+h[2]-h[1]-h[3])/(4*f(l))
 p,b=math.atan2(fs,1),math.atan2(rs,math.sqrt(1+fs*fs));basis=frame(y,p,b)
 base=max([lib.terrain_height(x,z)]+[a-r*f(w)*rs-(f(off)+t*f(l))*fs for a,(r,t) in zip(h,((1,1),(1,-1),(-1,1),(-1,-1)))])
 # Independently project tilted contacts and query actual authoritative height.
 for r,t in ((w,l),(w,-l),(-w,l),(-w,-l)):
  r,t=f(r),f(f(t)+f(off));local=[r*basis[i][0]+t*basis[i][2] for i in range(3)]
  base=max(base,lib.terrain_height(f(x+local[0]),f(z+local[2]))-local[1])
 return (x+3*basis[0][1],base+3*basis[1][1],z+3*basis[2][1])
with tempfile.TemporaryDirectory(prefix='rh-eye-') as name:
 td=pathlib.Path(name);source=(ROOT/'src/nav/ground_eye.asm').read_text()
 def build(tag,text=source,stub=None):
  files=['src/nav/terrain.asm','src/nav/terrain_relief.asm','src/nav/ground_support.asm','src/nav/ground_contact.asm','src/nav/ground_eye.asm','tests/probe_ground_eye.asm'];objs=[]
  if stub:files=[s for s in files if s not in ('src/nav/ground_support.asm','src/nav/ground_contact.asm')]
  for i,s in enumerate(files):
   src=ROOT/s
   if s=='src/nav/ground_eye.asm':src=td/(tag+'.asm');src.write_text(text)
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(src),'-o',str(obj)],check=True);objs.append(str(obj))
  if stub:
   src=td/(tag+'-stub.asm');src.write_text(stub);obj=td/(tag+'-stub.o');subprocess.run([NASM,'-f','elf64',str(src),'-o',str(obj)],check=True);objs.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,*['-Wl,--wrap='+n for n in ('sinf','cosf','terrain_height','ground_support','ground_contact')],'-lm','-o',str(so)],check=True)
  lib=C.CDLL(str(so));lib.probe_ground_eye.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p]+[C.c_float]*3;lib.probe_ground_eye.restype=C.c_int
  lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
  lib.ground_support.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*3
  lib.ground_contact.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*5
  return lib,so
 lib,so=build('eye');count=0;maximum=[0.,0.,0.];maximum_contact_raise=0.;maximum_contact_case=None
 def observe(lib,kind,x,z,y,invalid=False,cap=12):
  global count,maximum_contact_raise,maximum_contact_case
  x,z,y=map(f,(x,z,y));out=C.create_string_buffer(b'\xa5'*32,32);regs=(C.c_uint64*6)();tc=C.c_uint64.in_dll(lib,'eye_probe_height_calls');before=tc.value
  result=lib.probe_ground_eye(out,kind,cap,regs,x,z,y)
  assert tuple(regs)==tuple(0x123401+i for i in range(6))
  assert C.c_uint64.in_dll(lib,'eye_probe_alignment_errors').value==0
  if invalid:assert result==-1 and out.raw==b'\xa5'*32 and tc.value==before;return
  assert result==0 and tc.value-before==10
  assert out.raw[12:]==b'\xa5'*20
  actual=struct.unpack('<3f',out.raw[:12]);assert all(math.isfinite(a) for a in actual) and 0<=actual[0]<=8000 and 0<=actual[2]<=8000 and -2000<=actual[1]<=2000
  expected=reference(lib,kind,x,z,y)
  for i,(a,b) in enumerate(zip(actual,expected)):
   maximum[i]=max(maximum[i],abs(a-b));assert abs(a-b)<.001,(kind,x,z,y,i,a,b)
  # Strict composition with actual helpers is separate from mathematical proof.
  support=C.create_string_buffer(64);contact=C.create_string_buffer(64);assert lib.ground_support(support,kind,64,x,z,y)==0
  sv=struct.unpack('<16f',support.raw);assert lib.ground_contact(contact,kind,64,x,z,y,sv[1],sv[2])==0;cv=struct.unpack('<16f',contact.raw)
  if cv[0]-sv[0]>maximum_contact_raise:maximum_contact_raise=cv[0]-sv[0];maximum_contact_case=(kind,x,z,y)
  exact=(f(x+f(3*sv[8])),f(max(sv[0],cv[0])+f(3*sv[9])),f(z+f(3*sv[10])))
  assert actual==exact,'eye is not corrected base plus UP column'
  count+=1
 points=[(4000,4000),(3200,3900),(4800,3900),(5400,5200),(5480,5200),(5620,5200),(5820,5200),(5479,4999),(5480,5000),(5620,5400),(5720,5200)]
 rng=random.Random(487721);points.extend((rng.uniform(10,7990),rng.uniform(10,7990)) for _ in range(400));points.extend((rng.uniform(5385,5835),rng.uniform(4785,5615)) for _ in range(400))
 for kind in (1,2):
  for x,z in points:
   for y in (0,.7,-1.9,math.pi):observe(lib,kind,x,z,y)
 invalid=[]
 for kind in (0,3,0xffffffff):invalid.append((kind,12,4000,4000,0))
 for cap in (0,1,11):invalid.append((1,cap,4000,4000,0))
 for i,limit in enumerate((8000,8000,math.pi)):
  for bad in (math.nan,math.inf,-math.inf,limit+.01,-limit-.01):
   a=[4000,4000,0];a[i]=bad;invalid.append((1,12,*a))
 for kind in (1,2):
  for x,z in ((0,0),(8000,8000),(.1,4000),(7999.9,4000),(4000,.1),(4000,7999.9)):
   for y in (0,.7,-1.9):invalid.append((kind,12,x,z,y))
 for kind,cap,x,z,y in invalid:observe(lib,kind,x,z,y,True,cap)
 regs=(C.c_uint64*6)();before=C.c_uint64.in_dll(lib,'eye_probe_height_calls').value
 assert lib.probe_ground_eye(None,1,12,regs,4000,4000,0)==-1 and C.c_uint64.in_dll(lib,'eye_probe_height_calls').value==before
 production_count=count;production_max=maximum[:];production_raise=maximum_contact_raise;production_contact_case=maximum_contact_case
 assert production_raise>.001,'contact negative needs a lift above mathematical observer tolerance'
 # Hostile dependency fixture only: exercise final finite/map/Y gate in isolation.
 stub_template='''section .text
global ground_support,ground_contact
ground_support:
 xor eax,eax
 mov ecx,16
 mov r9,rdi
 rep stosd
 mov dword [r9],BASE
 mov dword [r9+32],UPX
 mov dword [r9+36],UPY
 mov dword [r9+40],UPZ
 xor eax,eax
 ret
ground_contact:
 mov dword [rdi],BASE
 xor eax,eax
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
 final_bad=0
 for base,up in ((2010,(0,1,0)),(0,(math.nan,1,0)),(0,(-2000,1,0)),(0,(0,1,2000))):
  stub=stub_template
  for key,v in dict(BASE=base,UPX=up[0],UPY=up[1],UPZ=up[2]).items():stub=stub.replace(key,hex(struct.unpack('<I',struct.pack('<f',v))[0]))
  bad,_=build('result-'+str(final_bad),stub=stub);out=C.create_string_buffer(b'\xa5'*32,32)
  assert bad.probe_ground_eye(out,1,12,regs,4000,4000,0)==-1 and out.raw==b'\xa5'*32
  assert tuple(regs)==tuple(0x123401+i for i in range(6));final_bad+=1
 mutations={'upright_eye':source.replace('movss xmm0,[rsp+SUPPORT_UP]','xorps xmm0,xmm0').replace('movss xmm1,[rsp+SUPPORT_UP+4]','movss xmm1,[anchor]\n divss xmm1,[anchor]').replace('movss xmm2,[rsp+SUPPORT_UP+8]','xorps xmm2,xmm2'),'wrong_axis':source.replace('SUPPORT_UP','SUPPORT_FORWARD'),'omitted_contact_floor':source.replace('maxss xmm2,[rsp+64+SUPPORT_Y]','nop')};faults=[]
 for tag,text in mutations.items():
  assert text!=source;bad,_=build(tag,text)
  try:observe(bad,*production_contact_case) if tag=='omitted_contact_floor' else observe(bad,2,5479,4999,.7)
  except AssertionError:faults.append(tag)
  else:raise AssertionError('fault escaped '+tag)
 # Separate dependency composition fixture exercises contact>support even when
 # canonical observations do not produce a substantial contact lift.
 stub=stub_template.replace('mov dword [rdi],BASE','mov dword [rdi],CONTACT_BASE')
 for key,v in dict(CONTACT_BASE=120,BASE=100,UPX=0,UPY=1,UPZ=0).items():stub=stub.replace(key,hex(struct.unpack('<I',struct.pack('<f',v))[0]))
 composition,_=build('composition',stub=stub);out=C.create_string_buffer(12)
 assert composition.probe_ground_eye(out,1,12,regs,4000,4000,0)==0 and struct.unpack('<3f',out.raw)==(4000,123,4000)
 mutation=source.replace('maxss xmm2,[rsp+64+SUPPORT_Y]','nop');bad,_=build('missing-contact',mutation,stub)
 assert bad.probe_ground_eye(out,1,12,regs,4000,4000,0)==0 and struct.unpack('<3f',out.raw)!=(4000,123,4000)
 # Dependency composition is additionally checked, but is not authored-terrain evidence.
 print(json.dumps({'ground_eye_cases':production_count,'invalid_zero_query_preserved':len(invalid)+1,'hostile_result_gate_cases':final_bad,'maximum_independent_xyz_error':production_max,'maximum_rotated_floor_raise':production_raise,'maximum_rotated_floor_raise_case':production_contact_case,'negative_controls':faults,'alignment_errors':C.c_uint64.in_dll(lib,'eye_probe_alignment_errors').value,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'prepared stateless legacy eye; no driver/camera integration or physical socket acceptance'},sort_keys=True))
