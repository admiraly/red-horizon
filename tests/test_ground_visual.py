#!/usr/bin/env python3
"""Independent dynamic presentation/contact proof. Python is development only."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM',str(ROOT/'.tools/nasm/nasm'))
def f(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def unpack(s):return struct.unpack('<6f2If3I',s.raw[:48])
def basis(y,p,b):
 cy,sy,cp,sp,cb,sb=math.cos(y),math.sin(y),math.cos(p),math.sin(p),math.cos(b),math.sin(b)
 return ((cy*cb-sy*sp*sb,-cy*sb-sy*sp*cb,sy*cp),(cp*sb,cp*cb,sp),(-sy*cb-cy*sp*sb,sy*sb-cy*sp*cb,cy*cp))
with tempfile.TemporaryDirectory(prefix='rh-visual-') as name:
 td=pathlib.Path(name);source=(ROOT/'src/render/ground_visual.asm').read_text()
 def build(tag,text=source):
  path=td/(tag+'.asm');path.write_text(text);objects=[]
  for i,p in enumerate((path,ROOT/'src/render/suspension.asm',ROOT/'src/nav/ground_support.asm',ROOT/'src/nav/ground_contact.asm',ROOT/'src/nav/terrain.asm',ROOT/'src/nav/terrain_relief.asm',ROOT/'tests/probe_ground_visual.asm')):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic','-Wl,--wrap=expf',*objects,'-lm','-o',str(so)],check=True)
  lib=C.CDLL(str(so));lib.probe_ground_visual.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_void_p]+[C.c_float]*4;lib.probe_ground_visual.restype=C.c_int
  lib.ground_support.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*3;lib.ground_support.restype=C.c_int
  lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
  return lib,so
 lib,so=build('visual');calls=0;max_error=0.;minimum_gap=1e9;lags=0;floor_corrections=0
 def call(lib,s,role,x,z,h,dt,frame,gen=7,ok=True):
  global calls
  out=C.create_string_buffer(b'\xa5'*80,80);regs=(C.c_uint64*6)();before=s.raw
  r=lib.probe_ground_visual(s,out,gen,role,frame,regs,x,z,h,dt);assert r==(0 if ok else -1),(r,role,x,z,h,dt,frame)
  assert tuple(regs)==tuple(0x123401+i for i in range(6))
  assert C.c_uint64.in_dll(lib,'visual_alignment_errors').value==0
  assert out.raw[64:]==b'\xa5'*16 and s.raw[64:]==before[64:],'overrun'
  if not ok:assert out.raw==b'\xa5'*80 and struct.unpack_from('<I',s.raw,36)[0]==0;return
  calls+=1;return struct.unpack('<16f',out.raw[:64])
 def new():return C.create_string_buffer(bytes(64)+b'\x5a'*16,80)
 def target(lib,role,x,z,h):
  t=(C.c_float*16)();assert lib.ground_support(t,role,64,x,z,h)==0;return tuple(t[:3])
 def verify_contact(lib,role,x,z,h,pose):
  global minimum_gap
  m=basis(f(h),pose[1],pose[2]);w,l,off=(1.75,2.55,-.45) if role==1 else (2.40,3.43,-.01)
  gaps=[pose[0]-lib.terrain_height(f(x),f(z))]
  for a,b in ((w,l),(w,-l),(-w,l),(-w,-l)):
   b=f(b+f(off));a=f(a);dx=m[0][0]*a+m[0][2]*b;dy=m[1][0]*a+m[1][2]*b;dz=m[2][0]*a+m[2][2]*b
   gaps.append(pose[0]+dy-lib.terrain_height(f(f(x)+dx),f(f(z)+dz)))
  minimum_gap=min(minimum_gap,*gaps);assert min(gaps)>-0.0004,('penetration',min(gaps),role,x,z,h,pose[:3])
  for j,off in enumerate((4,8,12)):
   assert max(abs(pose[off+i]-m[i][j]) for i in range(3))<4e-7,'frame not current smoothed angles'
 # Natural-size displacements over relief edge/crest, both directions and roles.
 for role in (1,2):
  for start,direction in ((5615,1),(5625,-1),(5815,1),(5485,-1)):
   s=new()
   for frame in range(1,241):
    x=f(start+direction*.08*frame);z=f(5200+.02*frame);h=f(direction*math.pi/2+.1*math.sin(frame*.01));dt=f(1/60)
    previous=unpack(s);pose=call(lib,s,role,x,z,h,dt,frame);actual=unpack(s);t=target(lib,role,x,z,h)
    if frame>1:
     expected=[];vel=[]
     for p,v,targ,w in zip(previous[:3],previous[3:6],t,(20,16,18)):
      q=p-targ;k=v+w*q;e=math.exp(-w*dt);expected.append(targ+(q+k*dt)*e);vel.append((v-w*k*dt)*e)
     for i in (1,2):
      error=abs(actual[i]-expected[i]);max_error=max(max_error,error);assert error<2e-6
      assert abs(actual[i+3]-vel[i])<3e-5
     assert actual[0]>=expected[0]-5e-5
     if actual[0]>expected[0]+5e-5:floor_corrections+=1;assert actual[3]>=0
     if max(abs(actual[i]-t[i]) for i in (1,2))>.0001:lags+=1
    assert pose[:3]==actual[:3] and actual[6:8]==(7,role)
    verify_contact(lib,role,x,z,h,pose)
 assert lags>500 and floor_corrections>100,(lags,floor_corrections)
 # Idempotent same-frame draw, role/generation reuse, camera gaps and teleport.
 s=new();p=call(lib,s,1,5750,5200,1.2,1/60,10);before=s.raw
 assert call(lib,s,1,5750,5200,1.2,1/60,10)==p and s.raw==before,'double draw advanced spring'
 for frame,gen,role,x,dt in ((11,8,1,5750,1/60),(12,8,2,5750,1/60),(15,8,2,5620,1/60),(16,8,2,5620,.2),(17,8,2,5650,1/60)):
  pose=call(lib,s,role,x,5200,.7,dt,frame,gen);t=target(lib,role,x,5200,.7)
  assert abs(pose[1]-t[1])<1e-7 and abs(pose[2]-t[2])<1e-7 and unpack(s)[3:6]==(0,0,0) and unpack(s)[8]==0,'lifecycle did not reset'
  verify_contact(lib,role,x,5200,.7,pose)
 # Invalid dt/identity/offmap and poisoned live cache produce no output and reset.
 for kwargs in ((1,0,0,0,1/60,18,8),(1,5750,5200,0,math.nan,18,8),(1,5750,5200,0,-.01,18,8),(1,5750,5200,0,1/60,0,8),(1,5750,5200,0,1/60,18,0),(3,5750,5200,0,1/60,18,8)):
  call(lib,s,*kwargs[:6],gen=kwargs[6],ok=False)
 s=new();call(lib,s,1,5750,5200,0,1/60,1);struct.pack_into('<f',s,12,math.nan);call(lib,s,1,5750,5200,0,1/60,2,ok=False)
 # Causal faults must be caught by behavioral proof, not source presence.
 accepted_minimum_gap=minimum_gap;accepted_calls=calls
 faults=[]
 for tag,text in (('no_floor',source.replace(' jae .height_done',' jmp .height_done')),('always_reset',source.replace(' cmp eax,1',' mov eax,2\n cmp eax,1')),('double_step',source.replace(' mov dword [rsp+140],0 ; validate live cache without advancing spring',' nop'))):
  bad,_=build(tag,text);caught=False
  try:
   q=new();last=None
   for frame in range(1,150):
    x=f(5618+.05*frame);out=call(bad,q,1,x,5200,math.pi/2,1/60,frame);verify_contact(bad,1,x,5200,math.pi/2,out)
    if tag=='always_reset' and frame>5:assert abs(out[1]-target(bad,1,x,5200,math.pi/2)[1])>1e-5
    if tag=='double_step' and frame==80:
     before=q.raw;call(bad,q,1,x,5200,math.pi/2,1/60,frame);assert before==q.raw
  except AssertionError:caught=True
  assert caught,('negative survived',tag);faults.append(tag)
 print(json.dumps({'suite':'ground-visual','passed':True,'calls':accepted_calls,'dynamic_angle_lag_samples':lags,'contact_corrections':floor_corrections,'minimum_independent_corner_gap':accepted_minimum_gap,'maximum_damping_angle_error':max_error,'causal_negatives':faults,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'actual NASM derived spring/contact composition; five sample contact points, no physical hull or natural gameplay acceptance'}))
