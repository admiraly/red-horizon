#!/usr/bin/env python3
"""Continuous ground-contact oracle via independent Decimal profile evaluation."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
from decimal import Decimal as D,localcontext
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
def f(v):return C.c_float(v).value
XS,ZS,RS,RH,BASE,CENTER,SKIN=map(lambda v:D(f(v)),(1e-6,5e-7,.00125,18,12,4000,.002))
FIELD=tuple(map(D,(5400,5480,5620,5820,4800,5000,5400,5600,64)))
def factor(q,row):
 a,b,c,d=row
 return D(0) if q<=a or q>=d else (q-a)/(b-a) if q<b else D(1) if q<=c else (d-q)/(d-c)
def height(x,z):return BASE+XS*(x-CENTER)**2+ZS*(z-CENTER)**2+RH*max(D(0),1-abs(x-CENTER)*RS)+FIELD[8]*factor(x,FIELD[:4])*factor(z,FIELD[4:8])
def reference(start,end):
 if any(not math.isfinite(v) or abs(v)>16000 for v in (*start,*end)) or any(not 0<=v<=8000 for v in (start[0],start[2],end[0],end[2])):return -1,None
 with localcontext() as ctx:
  ctx.prec=80;s=tuple(map(D,start));e=tuple(map(D,end));delta=tuple(e[i]-s[i] for i in range(3));cuts={D(0),D(1)}
  for axis,points in [(0,(CENTER-1/RS,CENTER,CENTER+1/RS,*FIELD[:4])),(2,FIELD[4:8])]:
   if delta[axis]:
    for point in points:
     t=(point-s[axis])/delta[axis]
     if 0<t<1:cuts.add(t)
  def gap(t):return s[1]+delta[1]*t-height(s[0]+delta[0]*t,s[2]+delta[2]*t)-SKIN
  ordered=sorted(cuts)
  for lo,hi in zip(ordered,ordered[1:]):
   c=gap(lo)
   if c<=0:return 1,float(lo)
   gh,gm=gap(hi),gap((lo+hi)/2);a=2*(gh+c-2*gm);b=gh-c-a
   if abs(a)<D('1e-60'):
    roots=[-c/b] if b<0 else []
   else:
    disc=b*b-4*a*c
    roots=[] if disc<0 else sorted(((-b-disc.sqrt())/(2*a),(-b+disc.sqrt())/(2*a)))
   for u in roots:
    if 0<=u<=1:return 1,float(lo+(hi-lo)*u)
 return 0,None
with tempfile.TemporaryDirectory(prefix='rh-ground-query-') as name:
 td=pathlib.Path(name);source=(ROOT/'src/nav/terrain_ground_query.asm').read_text()
 def build(tag,text=source,mutable=False):
  asm=td/(tag+'.asm');asm.write_text(text);relief=ROOT/'src/nav/terrain_relief.asm'
  if mutable:
   relief=td/(tag+'-relief.asm');relief.write_text((ROOT/'src/nav/terrain_relief.asm').read_text().replace('section .rodata','section .data'))
  objs=[]
  for i,p in enumerate((asm,relief,ROOT/'tests/probe_terrain_ground_query.asm')):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objs.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_terrain_ground_query.argtypes=[C.c_void_p,C.c_uint,C.c_void_p]+[C.c_float]*6;return lib,so
 lib,so=build('candidate');calls=hits=0;maxerr=0.;records=(C.c_byte*40).in_dll(lib,'terrain_relief_fields');initial=bytes(records)
 def query(which,start,end,expected=None,cap=16,null=False):
  global calls,hits,maxerr
  start,end=tuple(map(f,start)),tuple(map(f,end));out=C.create_string_buffer(b'Z'*16,16);regs=C.create_string_buffer(56);rows=(C.c_byte*40).in_dll(which,'terrain_relief_fields');before=bytes(rows)
  rc=which.probe_terrain_ground_query(None if null else out,cap,regs,*start,*end);assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert bytes(rows)==before
  wanted,t=reference(start,end) if cap>=16 and not null else (-1,None)
  if expected is not None:wanted=expected
  assert rc==wanted,(start,end,rc,wanted,t)
  if rc==1:
   actual,*zeros=struct.unpack('<f3I',out.raw);assert zeros==[0,0,0] and 0<=actual<=1;error=abs(actual-t);maxerr=max(maxerr,error);assert error<8e-8,(start,end,actual,t,error);hits+=1
  else:assert out.raw==b'Z'*16
  calls+=1;return rc,t
 cases=[((0,60,5000),(8000,60,5000)),((8000,60,5000),(0,60,5000)),((4000,100,4000),(4000,0,4000)),((0,200,0),(8000,200,8000)),((5600,40,5200),(5600,40,5200)),((5600,200,5200),(5600,200,5200)),((5300,30,4800),(5900,30,5600)),((3200,20,1000),(4800,20,1000))]
 for start,end in cases:query(lib,start,end)
 rng=random.Random(140528)
 for _ in range(1500):
  start=(rng.uniform(0,8000),rng.uniform(0,150),rng.uniform(0,8000));end=(rng.uniform(0,8000),rng.uniform(0,150),rng.uniform(0,8000));query(lib,start,end)
 for _ in range(300):
  x=rng.uniform(5300,5900);z=rng.uniform(4700,5700);y=float(height(D(f(x)),D(f(z))))+rng.uniform(-2,2)
  query(lib,(x,y,z),(x+rng.uniform(-30,30),y+rng.uniform(-2,2),z+rng.uniform(-30,30)))
 for i in range(6):
  for bad in (math.nan,math.inf,-math.inf,16000.01,-16000.01):
   points=[1000,30,1000,1100,30,1100];points[i]=bad;query(lib,points[:3],points[3:])
 for axis in (0,2):
  start=[1000,30,1000];start[axis]=-.001;query(lib,start,(1100,30,1100));start[axis]=8000.001;query(lib,start,(1100,30,1100))
 for cap in (0,1,15):query(lib,(1000,30,1000),(1100,30,1100),cap=cap)
 query(lib,(1000,30,1000),(1100,30,1100),null=True)
 mutable,_=build('invalid-source',mutable=True);rows=(C.c_byte*40).in_dll(mutable,'terrain_relief_fields');count=C.c_uint.in_dll(mutable,'terrain_relief_count');bad_sources=0
 for offset,value in ((0,math.nan),(4,5400.),(12,5600.),(32,-1.),(32,2001.)):
  C.memmove(C.addressof(rows),initial,40);C.memmove(C.addressof(rows)+offset,struct.pack('<f',value),4);query(mutable,(1000,30,1000),(1100,30,1100),-2);bad_sources+=1
 C.memmove(C.addressof(rows),initial,40);C.memmove(C.addressof(rows)+36,struct.pack('<I',2),4);query(mutable,(1000,30,1000),(1100,30,1100),-2);bad_sources+=1
 count.value=2;query(mutable,(1000,30,1000),(1100,30,1100),-2);bad_sources+=1
 production=(calls,hits,maxerr);negative=[]
 for tag,text,fixture in [('no_relief',source.replace(' addsd xmm8,xmm0',' nop'),cases[0]),('no_ridge_cuts',source.replace(' call .append_x',' nop',3),cases[-1]),('last_root',source.replace(' minsd xmm0,xmm1',' maxsd xmm0,xmm1'),((5400,25,5400),(5480,25,5600)))]:
  bad,_=build(tag,text)
  try:query(bad,*fixture)
  except AssertionError:negative.append(tag)
  else:raise AssertionError('negative escaped '+tag)
 print(json.dumps({'suite':'terrain-ground-continuous-contact','passed':True,'calls':production[0],'hits':production[1],'random_global_paths':1500,'near_surface_paths':300,'max_first_t_error':production[2],'decimal_precision':80,'malformed_sources':bad_sources,'negative_controls':negative,'ABI_source_preserved':True,'skin_m':f(.002),'source_sha256':hashlib.sha256((ROOT/'src/nav/terrain_ground_query.asm').read_bytes()).hexdigest(),'scope':'Continuous current base/ridge/one-relief-field point contact, no actor/wreck arbitration or runtime hooks yet.'}))
