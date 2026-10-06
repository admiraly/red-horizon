#!/usr/bin/env python3
"""Independent parametric interval oracle for prepared actual NASM sweep primitive."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
def f(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def reference(box,start,end):
 if any(not math.isfinite(q) or abs(q)>16000 for q in (*box,*start,*end)) or any(box[i]>box[i+3] for i in range(3)):return -1,None
 intervals=[(0.,1.)]
 for i in range(3):
  delta=end[i]-start[i]
  if not delta:
   if not box[i]<=start[i]<=box[i+3]:return 0,None
  else:intervals.append(tuple(sorted(((box[i]-start[i])/delta,(box[i+3]-start[i])/delta))))
 low=max(q[0] for q in intervals);high=min(q[1] for q in intervals)
 return (1,low) if low<=high else (0,None)
with tempfile.TemporaryDirectory(prefix='rh-segment-box-') as name:
 td=pathlib.Path(name);source=(ROOT/'src/nav/segment_box.asm').read_text()
 def build(tag,text=source):
  asm=td/(tag+'.asm');asm.write_text(text);objs=[]
  for i,p in enumerate((asm,ROOT/'tests/probe_segment_box.asm')):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objs.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_segment_box.argtypes=[C.c_void_p,C.c_uint,C.c_void_p]+[C.c_float]*6;return lib,so
 lib,so=build('candidate');calls=hits=invalid=0;max_error=0.
 def observe(lib,box,start,end,cap=24,null=False):
  global calls,hits,invalid,max_error
  box,start,end=tuple(map(f,box)),tuple(map(f,start)),tuple(map(f,end));buf=(C.c_float*6)(*box);before=bytes(buf);regs=C.create_string_buffer(56)
  rc=lib.probe_segment_box(None if null else buf,cap,regs,*start,*end);expected,t=reference(box,start,end) if not null and cap>=24 else (-1,None)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert bytes(buf)==before
  assert rc==expected,(box,start,end,rc,expected)
  actual=struct.unpack('<f',regs.raw[48:52])[0]
  if rc==1:
   assert math.isfinite(actual) and 0<=actual<=1;error=abs(actual-t);max_error=max(max_error,error);assert error<6e-8,(actual,t);hits+=1
  else:assert struct.pack('<f',actual)==struct.pack('<f',start[0])
  calls+=1;invalid+=rc==-1
 box=(-1.,-2.,-3.,1.,2.,3.)
 cases=[((-4,0,0),(4,0,0)),((4,0,0),(-4,0,0)),((0,0,0),(0,0,0)),((4,0,0),(4,0,0)),((-4,2,3),(4,2,3)),((-4,2.001,3),(4,2.001,3)),((-4,0,0),(-1,0,0)),((-4,0,0),(-2,0,0)),((0,-4,0),(0,4,0)),((0,0,-4),(0,0,4)),((-4,-4,-4),(4,4,4))]
 for start,end in cases:observe(lib,box,start,end)
 for axis in range(3):
  start=[0.,0.,0.];end=[0.,0.,0.];start[axis]=-4;end[axis]=4;observe(lib,(0,0,0,0,0,0),start,end)
 # Extreme tiny deltas and signed zeros remain defined through double intermediates.
 for delta in (f(1e-45),f(-1e-45),0.,-0.):observe(lib,(-1,-1,-1,1,1,1),(0,0,0),(delta,0,0))
 rng=random.Random(109571)
 for _ in range(10000):
  center=[rng.uniform(-8000,8000) for _ in range(3)];extent=[rng.uniform(0,512) for _ in range(3)];b=tuple(center[i]-extent[i] for i in range(3))+tuple(center[i]+extent[i] for i in range(3));start=[center[i]+rng.uniform(-1200,1200) for i in range(3)];end=[center[i]+rng.uniform(-1200,1200) for i in range(3)];observe(lib,b,start,end)
 for i in range(12):
  for bad in (math.nan,math.inf,-math.inf,16000.01,-16000.01):
   data=list(box+(0.,0.,0.)+(1.,1.,1.));data[i]=bad;observe(lib,data[:6],data[6:9],data[9:])
 for i in range(3):
  bad=list(box);bad[i]=bad[i+3]+1;observe(lib,bad,(0,0,0),(1,1,1))
 for cap in (0,1,23):observe(lib,box,(0,0,0),(1,1,1),cap=cap)
 observe(lib,box,(0,0,0),(1,1,1),null=True)
 production=(calls,hits,invalid,max_error)
 # Assembly controls omit an axis or closed-boundary hit, or select last contact.
 faults=[]
 for tag,text,fixture in [('missing_z',source.replace(' cmp ecx,3\n jb .axis',' cmp ecx,2\n jb .axis'),(box,(-4,0,4),(4,0,4))),('grazing_miss',source.replace(' ja .clear',' jae .clear'),(box,(-4,0,0),(-1,0,0))),('last_contact',source.replace('cvtsd2ss xmm0,xmm6','cvtsd2ss xmm0,xmm7'),(box,(-4,0,0),(4,0,0)))]:
  assert text!=source;bad,_=build(tag,text)
  try:observe(bad,*fixture)
  except AssertionError:faults.append(tag)
  else:raise AssertionError('assembly negative escaped '+tag)
 print(json.dumps({'suite':'prepared-segment-box','passed':True,'calls':production[0],'hits':production[1],'invalid_preserved_cases':production[2],'maximum_first_t_error':production[3],'negative_controls':faults,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'scope':'Prepared read-only3D clip/ABI math only; no actual wreck spatial search, body/rifle/LOS/shell/render/wire integration'}))
