#!/usr/bin/env python3
"""Independent high-precision first-entry oracle for actual NASM sphere sweep."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
from decimal import Decimal as D,localcontext
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
def f(v):return C.c_float(v).value
def reference(sphere,start,end):
 if any(not math.isfinite(v) or abs(v)>16000 for v in (*sphere[:3],*start,*end)) or not f(.001)<=sphere[3]<=4096:return -1,None
 with localcontext() as ctx:
  ctx.prec=80;m=[D(start[i])-D(sphere[i]) for i in range(3)];d=[D(end[i])-D(start[i]) for i in range(3)];r=D(sphere[3]);a=sum(x*x for x in d);b=sum(x*y for x,y in zip(m,d));c=sum(x*x for x in m)-r*r
  if c<=0:return 1,0.
  if not a or b>=0:return 0,None
  discriminant=b*b-a*c
  if discriminant<0:return 0,None
  t=(-b-discriminant.sqrt())/a
  return (1,float(t)) if 0<=t<=1 else (0,None)
with tempfile.TemporaryDirectory(prefix='rh-segment-sphere-') as name:
 td=pathlib.Path(name);source=(ROOT/'src/nav/segment_sphere.asm').read_text()
 def build(tag,text=source):
  asm=td/(tag+'.asm');asm.write_text(text);objs=[]
  for i,p in enumerate((asm,ROOT/'tests/probe_segment_sphere.asm')):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objs.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_segment_sphere.argtypes=[C.c_void_p,C.c_uint,C.c_void_p]+[C.c_float]*6;return lib,so
 lib,so=build('candidate');calls=hits=invalid=0;max_error=0.
 def observe(which,sphere,start,end,cap=16,null=False):
  global calls,hits,invalid,max_error
  sphere,start,end=tuple(map(f,sphere)),tuple(map(f,start)),tuple(map(f,end));buf=(C.c_float*4)(*sphere);before=bytes(buf);regs=C.create_string_buffer(56)
  rc=which.probe_segment_sphere(None if null else buf,cap,regs,*start,*end);expected,t=reference(sphere,start,end) if not null and cap>=16 else (-1,None)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert bytes(buf)==before;assert rc==expected,(sphere,start,end,rc,expected)
  actual=struct.unpack('<f',regs.raw[48:52])[0]
  if rc==1:
   assert math.isfinite(actual) and 0<=actual<=1;error=abs(actual-t);max_error=max(max_error,error);assert error<6e-8,(actual,t);hits+=1
  else:assert struct.pack('<f',actual)==struct.pack('<f',start[0])
  calls+=1;invalid+=rc==-1
 sphere=(0,0,0,4)
 cases=[((-10,0,0),(10,0,0)),((10,0,0),(-10,0,0)),((0,0,0),(0,0,0)),((5,0,0),(5,0,0)),((-10,4,0),(10,4,0)),((-10,4.0001,0),(10,4.0001,0)),((-10,0,0),(-4,0,0)),((-10,0,0),(-5,0,0)),((4,0,0),(10,0,0)),((5,0,0),(10,0,0)),((0,0,5),(1,0,5))]
 for start,end in cases:observe(lib,sphere,start,end)
 for radius in (.001,.551,3.551,4.,4.491,4096):
  observe(lib,(0,0,0,radius),(-16000,0,0),(16000,0,0))
  observe(lib,(0,0,0,radius),(0,0,0),(f(1e-45),0,0))
  observe(lib,(0,0,0,radius),(16000,0,0),(16000,-0.,f(1e-45)))
 rng=random.Random(78111)
 for _ in range(5000):
  center=[rng.uniform(-8000,8000) for _ in range(3)];radius=rng.uniform(.01,512);start=[center[i]+rng.uniform(-1200,1200) for i in range(3)];end=[center[i]+rng.uniform(-1200,1200) for i in range(3)];observe(lib,(*center,radius),start,end)
 for i in range(9):
  for bad in (math.nan,math.inf,-math.inf,16000.01,-16000.01):
   data=list(sphere+(0,0,0)+(1,1,1));index=i if i<3 else i+1;data[index]=bad;observe(lib,data[:4],data[4:7],data[7:])
 for bad in (math.nan,math.inf,-math.inf,-1,-0.,0,.0009,4096.01):observe(lib,(0,0,0,bad),(0,0,0),(1,1,1))
 for cap in (0,1,15):observe(lib,sphere,(0,0,0),(1,1,1),cap=cap)
 observe(lib,sphere,(0,0,0),(1,1,1),null=True)
 production=(calls,hits,invalid,max_error);faults=[]
 fixtures=[('last_entry',source.replace(' subsd xmm13,xmm12',' addsd xmm13,xmm12'),(sphere,(-10,0,0),(10,0,0))),('tangent_miss',source.replace(' ucomisd xmm8,xmm12\n ja .clear',' ucomisd xmm8,xmm12\n jae .clear'),(sphere,(-10,4,0),(10,4,0))),('missing_z',source.replace(' cmp ecx,3',' cmp ecx,2'),(sphere,(0,0,5),(1,0,5)))]
 for tag,text,fixture in fixtures:
  bad,_=build(tag,text)
  try:observe(bad,*fixture)
  except AssertionError:faults.append(tag)
  else:raise AssertionError('assembled fault escaped '+tag)
 print(json.dumps({'suite':'segment-sphere-first-entry','passed':True,'calls':production[0],'hits':production[1],'invalid':production[2],'max_first_t_error':production[3],'decimal_precision':80,'random_paths':5000,'negative_controls':faults,'ABI_source_preserved':True,'source_sha256':hashlib.sha256((ROOT/'src/nav/segment_sphere.asm').read_bytes()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Geometry primitive only; no actor policy, broadphase, damage or world cover acceptance.'}))
