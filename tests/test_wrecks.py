#!/usr/bin/env python3
"""Actual NASM bounded death-registry lifecycle/ABI; development only."""
import ctypes as C,hashlib,json,math,os,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
class Entity(C.Structure):
 _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('generation',C.c_uint)]
class Motion(C.Structure):
 _fields_=[(n,C.c_float) for n in ('heading','speed','turn','vx','vz')]+[(n,C.c_uint) for n in ('generation','kind','flags')]
class Wreck(C.Structure):
 _fields_=[(n,C.c_float) for n in ('x','y','z','heading','pitch','bank')]+[(n,C.c_uint) for n in ('kind','side','entity','generation','birth','expiry','sequence','flags','reserved0','reserved1')]
assert C.sizeof(Wreck)==64
with tempfile.TemporaryDirectory(prefix='rh-wreck-') as name:
 td=pathlib.Path(name);objs=[]
 for i,src in enumerate(('src/sim/wrecks.asm','src/nav/terrain.asm','src/nav/terrain_relief.asm','src/nav/ground_support.asm','src/nav/ground_contact.asm','tests/probe_wrecks.asm')):
  obj=td/f'{i}.o';subprocess.run([NASM,'-f','elf64','-D','WRECK_STANDALONE=1','-I',str(ROOT)+'/',str(ROOT/src),'-o',str(obj)],check=True);objs.append(str(obj))
 so=td/'wreck.so';subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objs,*['-Wl,--wrap='+s for s in ('ground_support','ground_contact','terrain_height','sinf','cosf','atan2f')],'-lm','-o',str(so)],check=True)
 lib=C.CDLL(str(so));E=(Entity*32768).in_dll(lib,'sim_entities');M=(Motion*32768).in_dll(lib,'sim_ground_motion');W=(Wreck*1024).in_dll(lib,'sim_wrecks');count=C.c_uint.in_dll(lib,'sim_wreck_count');seq=C.c_uint.in_dll(lib,'sim_wreck_sequence');tick=C.c_uint.in_dll(lib,'sim_tick_count');C.c_uint.in_dll(lib,'sim_count').value=32768
 lib.probe_wreck_register.argtypes=[C.c_uint,C.c_void_p];lib.ground_support.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*3;lib.ground_contact.argtypes=[C.c_void_p,C.c_uint,C.c_uint]+[C.c_float]*5;lib.terrain_height.argtypes=[C.c_float]*2;lib.terrain_height.restype=C.c_float
 regs=(C.c_uint64*6)();calls=0
 def add(i):
  global calls
  rc=lib.probe_wreck_register(i,regs);calls+=1
  assert tuple(regs)==tuple(0x123401+j for j in range(6))
  assert C.c_uint64.in_dll(lib,'wreck_probe_alignment_errors').value==0
  return rc
 def birth(i,kind=1,heading=.7,gen=1,xy=(5481.,4999.),side=0):
  E[i]=Entity(*xy,0,side,kind,0,-1,gen);M[i]=Motion(heading,0,0,0,0,gen,kind,1)
 def state():return C.string_at(C.addressof(W),1024*64+32768*4+12)
 # Complete 32k physical-ID capacity, FIFO retirement and per-source dedup.
 lib.wreck_init();tick.value=42
 for i in range(32768):
  birth(i,1+i%2,side=i%2);assert add(i)==0
  assert count.value==min(i+1,1024) and seq.value==i+1
 assert sorted((w.entity,w.sequence) for w in W)==[(i,i+1) for i in range(31744,32768)]
 before=state()
 for i in range(32768):assert add(i)==1
 assert state()==before
 # Lifetime boundaries and modular clock wrapping; tombstone identity survives.
 tick.value=42+1799;lib.wreck_tick();assert count.value==1024
 tick.value=42+1800;lib.wreck_tick();assert count.value==0 and all(not w.flags&1 for w in W)
 expired=state();lib.wreck_tick();assert state()==expired
 for i in range(32768):assert add(i)==1
 assert state()==expired
 lib.wreck_init();tick.value=0xfffffff0;birth(9);assert add(9)==0;birth_bytes=bytes(W[0]);assert W[0].expiry==(tick.value+1800)&0xffffffff
 tick.value=(0xfffffff0+1799)&0xffffffff;lib.wreck_tick();assert count.value==1 and bytes(W[0])==birth_bytes
 tick.value=(0xfffffff0+1800)&0xffffffff;lib.wreck_tick();assert count.value==0
 # Source recycling creates independent immutable history, not a new pose for old death.
 lib.wreck_init();tick.value=17;birth(12,gen=3);assert add(12)==0;old=bytes(W[0]);birth(12,gen=4,xy=(5720,5250));assert add(12)==0 and bytes(W[0])==old and count.value==2
 # Support composition, immutability, missing/invalid motion fallback.
 pose_cases=0
 for kind in (1,2):
  for xy in ((3500,2000),(5481,4999),(5620,5200),(5820,5200)):
   for heading in (0,.7,-1.9,math.pi):
    lib.wreck_init();birth(12,kind,heading,xy=xy);before_entities=bytes(E[12]);before_motion=bytes(M[12]);assert add(12)==0
    assert bytes(E[12])==before_entities and bytes(M[12])==before_motion
    support=C.create_string_buffer(64);contact=C.create_string_buffer(64);assert lib.ground_support(support,kind,64,*xy,C.c_float(heading).value)==0;sv=struct.unpack('<16f',support.raw);assert lib.ground_contact(contact,kind,64,*xy,C.c_float(heading).value,sv[1],sv[2])==0;cv=struct.unpack('<16f',contact.raw)
    assert (W[0].x,W[0].y,W[0].z,W[0].heading,W[0].pitch,W[0].bank)==(xy[0],max(sv[0],cv[0]),xy[1],C.c_float(heading).value,sv[1],sv[2]);assert W[0].flags==1
    saved=bytes(W[0]);E[12].x+=100;M[12].heading=0;assert add(12)==1 and bytes(W[0])==saved;pose_cases+=1
 fallback_cases=0
 for mutation in ('generation','kind','inactive','nan_heading','map_edge'):
  lib.wreck_init();birth(12)
  if mutation=='generation':M[12].generation+=1
  elif mutation=='kind':M[12].kind=2
  elif mutation=='inactive':M[12].flags=0
  elif mutation=='nan_heading':M[12].heading=math.nan
  else:E[12].x=0
  assert add(12)==0 and W[0].flags==3 and W[0].heading==W[0].pitch==W[0].bank==0
  assert W[0].y==lib.terrain_height(E[12].x,E[12].z);fallback_cases+=1
 # Invalid public calls preserve the entire registry and accept no dedup history.
 invalid_cases=0
 for mutation in ('living','infantry','air','bad_kind','side','zero_gen','nan_x','inf_z','negative_x','outside_z'):
  lib.wreck_init();birth(12)
  if mutation=='living':E[12].hp=1
  elif mutation in ('infantry','air','bad_kind'):E[12].kind={'infantry':0,'air':3,'bad_kind':0xffffffff}[mutation]
  elif mutation=='side':E[12].side=2
  elif mutation=='zero_gen':E[12].generation=0
  elif mutation=='nan_x':E[12].x=math.nan
  elif mutation=='inf_z':E[12].z=math.inf
  elif mutation=='negative_x':E[12].x=-.01
  else:E[12].z=8000.01
  before=state();assert add(12)==-1 and state()==before
  birth(12);assert add(12)==0;invalid_cases+=1
 for i in (32768,0xffffffff):
  before=state();assert add(i)==-1 and state()==before;invalid_cases+=1
 # Exact authoritative FNV over the documented persistent arena.
 lib.probe_wreck_hash.restype=C.c_uint64
 def check_hash():
  raw=C.string_at(C.addressof(W),1024*64+32768*4+12);value=14695981039346656037
  for b in raw:value=((value^b)*1099511628211)&0xffffffffffffffff
  assert value==lib.probe_wreck_hash()
 lib.wreck_init();check_hash();birth(12);assert add(12)==0;check_hash();tick.value+=1800;lib.wreck_tick();check_hash()
 # Sequence wrap keeps nonzero identity.
 lib.wreck_init();seq.value=0xffffffff;birth(12);assert add(12)==0 and W[0].sequence==1
 # Source-ID/side-label mirrors preserve retirement, pose and timing.
 histories=[]
 for flip in (0,1):
  lib.wreck_init();tick.value=90
  for i in range(2048):birth(i,side=(i%2)^flip);assert add(i)==0
  histories.append([(w.x,w.y,w.z,w.heading,w.pitch,w.bank,w.kind,w.entity,w.generation,w.birth,w.expiry,w.sequence,w.flags) for w in W])
 assert histories[0]==histories[1]
 # Actual assembly negative controls, with production helpers and ABI adapter.
 source=(ROOT/'src/sim/wrecks.asm').read_text();negatives=[]
 mutations={'missing_dedup':source.replace(' je .duplicate',' nop',1),'late_expiry':source.replace(' jb .next',' jbe .next',1),'lost_pitch':source.replace(' mov eax,[rsp+SUPPORT_PITCH]',' xor eax,eax',1)}
 for tag,text in mutations.items():
  assert text!=source;asm=td/(tag+'.asm');asm.write_text(text);obj=td/(tag+'.o');subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(asm),'-o',str(obj)],check=True)
  dest=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',str(obj),*objs[1:],*['-Wl,--wrap='+s for s in ('ground_support','ground_contact','terrain_height','sinf','cosf','atan2f')],'-lm','-o',str(dest)],check=True)
  bad=C.CDLL(str(dest));be=(Entity*32768).in_dll(bad,'sim_entities');bm=(Motion*32768).in_dll(bad,'sim_ground_motion');bw=(Wreck*1024).in_dll(bad,'sim_wrecks');bc=C.c_uint.in_dll(bad,'sim_wreck_count');bt=C.c_uint.in_dll(bad,'sim_tick_count');C.c_uint.in_dll(bad,'sim_count').value=32;bad.wreck_init();be[12]=Entity(5481,4999,0,0,1,0,-1,1);bm[12]=Motion(.7,0,0,0,0,1,1,1)
  assert bad.probe_wreck_register(12,regs)==0
  if tag=='missing_dedup':assert bad.probe_wreck_register(12,regs)==0 and bc.value==2
  elif tag=='late_expiry':bt.value=1800;bad.wreck_tick();assert bc.value==1
  else:
   support=C.create_string_buffer(64);assert lib.ground_support(support,1,64,5481,4999,C.c_float(.7).value)==0
   correct=struct.unpack('<16f',support.raw)[1];assert abs(correct)>.01 and bw[0].pitch==0
  negatives.append(tag)
 print(json.dumps({'suite':'wreck-lifecycle','passed':True,'register_calls':calls,'negative_controls':negatives,'physical_ids':32768,'capacity':1024,'pose_composition_cases':pose_cases,'fallback_cases':fallback_cases,'invalid_preserved_cases':invalid_cases,'wrap_expiry':True,'retired_source_duplicate_rejection':True,'label_mirror':True,'aligned_helpers_and_preserved_registers':True,'library_sha256':hashlib.sha256(so.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'src/sim/wrecks.asm').read_bytes()).hexdigest(),'scope':'Registry/pose/lifetime prerequisites only; no collision, renderer or wire acceptance'}))
