#!/usr/bin/env python3
"""Prepared exact solid contacts; independent intervals and real authored table."""
import ctypes as C,hashlib,json,math,os,pathlib,random,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
def f(v):return C.c_float(v).value
def clip(box,start,end):
 lo,hi=0.,1.
 for i in range(3):
  d=end[i]-start[i]
  if not d:
   if not box[i]<=start[i]<=box[i+3]:return None
  else:
   a,b=sorted(((box[i]-start[i])/d,(box[i+3]-start[i])/d));lo=max(lo,a);hi=min(hi,b)
   if lo>hi:return None
 return f(lo)
with tempfile.TemporaryDirectory(prefix='rh-terrain-solid-') as name:
 td=pathlib.Path(name);source=(ROOT/'src/nav/terrain_solid_query.asm').read_text();calls=0;maxerr=0.
 def build(tag,text=source,mutable=False):
  asm=td/(tag+'.asm');asm.write_text(text);paths=[asm,ROOT/'src/nav/segment_box.asm',ROOT/'tests/probe_terrain_solid_query.asm']
  if mutable:
   terrain=(ROOT/'src/nav/terrain.asm').read_text();table=terrain.split('terrain_obstacles:\n',1)[1].split('center:',1)[0]
   data=td/(tag+'-table.asm');data.write_text('default rel\nsection .data\nglobal terrain_obstacle_count,terrain_obstacles\nterrain_obstacle_count: dd 5\nterrain_obstacles:\n'+table+'\nsection .note.GNU-stack noalloc noexec nowrite progbits\n');paths.append(data)
  else:paths.extend((ROOT/'src/nav/terrain.asm',ROOT/'src/nav/terrain_relief.asm'))
  objs=[]
  for i,path in enumerate(paths):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(path),'-o',str(obj)],check=True);objs.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_terrain_solid_query.argtypes=[C.c_void_p,C.c_uint,C.c_void_p]+[C.c_float]*6;return lib,so
 lib,so=build('production');raw=(C.c_byte*160).in_dll(lib,'terrain_obstacles');initial=bytes(raw);records=[struct.unpack('<6f2I',initial[i*32:(i+1)*32])for i in range(5)]
 boxes=[(r[0],r[4],r[1],r[2],f(r[4]+r[5]),r[3])for r in records]
 def query(which,start,end,expected=None,cap=16,null=False):
  global calls,maxerr
  start,end=tuple(map(f,start)),tuple(map(f,end));out=C.create_string_buffer(b'Z'*16,16);regs=C.create_string_buffer(56)
  rows=(C.c_byte*160).in_dll(which,'terrain_obstacles');before=bytes(rows);rc=which.probe_terrain_solid_query(None if null else out,cap,regs,*start,*end)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert bytes(rows)==before
  valid=all(math.isfinite(v) and abs(v)<=16000 for v in (*start,*end)) and cap>=16 and not null
  options=[(t,i)for i,b in enumerate(boxes) if (t:=clip(b,start,end)) is not None] if valid else []
  wanted=min(options) if options else None
  if expected is None:expected=(1 if wanted else 0) if valid else -1
  assert rc==expected,(rc,expected,start,end)
  if rc==1:
   t,slot,flags,reserved=struct.unpack('<f3I',out.raw);assert slot==wanted[1] and flags==records[slot][6] and reserved==0;maxerr=max(maxerr,abs(t-wanted[0]));assert abs(t-wanted[0])<6e-8
  else:assert out.raw==b'Z'*16
  calls+=1;return rc
 for i,b in enumerate(boxes):
  x=(b[0]+b[3])/2;y=(b[1]+b[4])/2;z=(b[2]+b[5])/2
  for start,end in [((b[0]-100,y,z),(b[3]+100,y,z)),((b[3]+100,y,z),(b[0]-100,y,z)),((x,y,z),(x,y,z)),((b[0]-1,y,z),(b[0],y,z)),((b[0]-1,b[4],b[5]),(b[3]+1,b[4],b[5]))]:query(lib,start,end)
 rng=random.Random(172629)
 for _ in range(3000):
  b=rng.choice(boxes);center=[(b[j]+b[j+3])/2 for j in range(3)];start=[center[j]+rng.uniform(-300,300)for j in range(3)];end=[center[j]+rng.uniform(-300,300)for j in range(3)];query(lib,start,end)
 for j in range(6):
  for bad in (math.nan,math.inf,-math.inf,16000.01,-16000.01):
   pts=[4000,30,1000,4000,30,2000];pts[j]=bad;query(lib,pts[:3],pts[3:])
 for cap in (0,1,15):query(lib,(0,0,0),(1,1,1),cap=cap)
 query(lib,(0,0,0),(1,1,1),null=True)
 assert bytes(raw)==initial
 mutable,_=build('malformed',mutable=True);data=(C.c_byte*160).in_dll(mutable,'terrain_obstacles');count=C.c_uint.in_dll(mutable,'terrain_obstacle_count');assert bytes(data)==initial
 bad_sources=0
 # A malformed final row must reject the whole query despite an earlier hit.
 for offset,value in [(4*32,math.nan),(4*32+8,0.),(4*32+20,-1.)]:
  C.memmove(C.addressof(data),initial,160);C.memmove(C.addressof(data)+offset,struct.pack('<f',value),4);query(mutable,(3900,30,1300),(4100,30,1300),-2);bad_sources+=1
 for offset,value in [(4*32+24,2),(4*32+28,1)]:
  C.memmove(C.addressof(data),initial,160);C.memmove(C.addressof(data)+offset,struct.pack('<I',value),4);query(mutable,(3900,30,1300),(4100,30,1300),-2);bad_sources+=1
 C.memmove(C.addressof(data),initial,160);count.value=6;query(mutable,(0,0,0),(1,1,1),-2);count.value=0;query(mutable,(3900,30,1300),(4100,30,1300),0)
 production_calls=calls;negatives=[]
 for tag,text,fixture in [('first_slot',source.replace(' ucomiss xmm0,[rsp+48]\n jae .next',' jmp .next'),((6000,30,1750),(3800,30,1255))),('last_entry',source.replace(' movss [rsp+48],xmm0',' movss xmm0,[rsp+12]\n movss [rsp+48],xmm0'),((3900,30,1300),(4100,30,1300))),('missing_height',source.replace(' addss xmm0,[rbx+20]',' nop'),((3900,30,1300),(4100,30,1300)))]:
  bad,_=build(tag,text)
  try:query(bad,*fixture)
  except AssertionError:negatives.append(tag)
  else:raise AssertionError('assembled fault escaped '+tag)
 print(json.dumps({'suite':'terrain-solid-first-contact','passed':True,'calls':production_calls,'random_paths':3000,'authored_obstacles':5,'malformed_atomic_sources':bad_sources+1,'nearest_first_t_error':maxerr,'negative_controls':negatives,'ABI_source_preserved':True,'query_source_sha256':hashlib.sha256((ROOT/'src/nav/terrain_solid_query.asm').read_bytes()).hexdigest(),'terrain_source_sha256':hashlib.sha256((ROOT/'src/nav/terrain.asm').read_bytes()).hexdigest(),'scope':'Prepared exact point/AABB contacts for current five authored solids. No analytic ground, actor/wreck arbitration, runtime hooks, physical bodies or scale acceptance.'}))
