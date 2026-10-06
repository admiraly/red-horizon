#!/usr/bin/env python3
"""Typed arbitration tested with assembled, observable source contracts."""
import ctypes as C,hashlib,json,os,pathlib,random,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
STUB='''default rel
section .data
global contact_rows,contact_calls,sim_entities,sim_count
contact_rows: times 24 dd 0
contact_calls: times 4 dd 0
sim_count: dd 8
sim_entities: times 8*32 db 0
section .text
global terrain_ground_query,terrain_solid_query,wreck_query,sim_shell_contact
%macro cover 2
%1:
 inc dword [contact_calls+%2*4]
 mov eax,[contact_rows+%2*24]
 cmp eax,1
 jne %%out
 movdqu xmm0,[contact_rows+%2*24+4]
 movdqu [rdi],xmm0
 mov eax,[contact_rows+%2*24+20]
 mov [rdi+16],eax
 mov dword [rdi+20],0
 mov eax,1
%%out: ret
%endmacro
cover terrain_ground_query,0
cover terrain_solid_query,1
cover wreck_query,2
sim_shell_contact:
 inc dword [contact_calls+12]
 mov eax,[contact_rows+72]
 movss xmm3,[contact_rows+76]
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
with tempfile.TemporaryDirectory(prefix='rh-world-contact-') as folder:
 td=pathlib.Path(folder);stub=td/'sources.asm';stub.write_text(STUB);source=(ROOT/'src/sim/world_contact.asm').read_text()
 def build(tag,text=source):
  asm=td/(tag+'.asm');asm.write_text(text);objects=[]
  for i,p in enumerate((asm,stub,ROOT/'tests/probe_world_contact.asm')):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_world_contact_query.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p]+[C.c_float]*6;return lib
 lib=build('candidate');calls=0
 def run(which,rows,cap=24,side=0,coords=(1000,40,1000,1020,40,1000),null=False):
  global calls
  data=(C.c_byte*96).in_dll(which,'contact_rows');counts=(C.c_uint*4).in_dll(which,'contact_calls');entities=(C.c_byte*256).in_dll(which,'sim_entities');count=C.c_uint.in_dll(which,'sim_count');count.value=8
  C.memset(C.addressof(entities),0,256);C.memmove(C.addressof(entities)+3*32+8,struct.pack('<I',100),4);C.memmove(C.addressof(entities)+3*32+28,struct.pack('<I',79),4)
  for i,row in enumerate(rows):C.memmove(C.addressof(data)+i*24,struct.pack('<if4I',*row),24)
  for i in range(4):counts[i]=0
  before=bytes(data)+bytes(entities);out=C.create_string_buffer(b'Z'*24,24);regs=C.create_string_buffer(56)
  actual=which.probe_world_contact_query(None if null else out,cap,side,regs,*coords)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert bytes(data)+bytes(entities)==before
  invalid=null or cap<24 or side>1 or any(not -16000<=q<=16000 for q in coords) or any(not 0<=coords[i]<=8000 for i in (0,2,3,5))
  candidates=[]
  for i,(rc,t,ident,gen,seq,res) in enumerate(rows):
   if i<3 and rc==1:
    ident,gen,seq=(0,0,0) if i==0 else (ident,0,0) if i==1 else (gen,seq,res)
    candidates.append((C.c_float(t).value,i+1,ident,gen,seq,0))
   if i==3 and rc>=0:candidates.append((C.c_float(t).value,4,rc,79,0,0))
  malformed=any(row[0]<0 for row in rows[:3]) or rows[3][0] not in (-1,3)
  expected=-1 if invalid else -2 if malformed else 1 if candidates else 0
  assert actual==expected,(actual,expected,rows)
  if actual==1:assert struct.unpack('<f5I',out.raw)==min(candidates), (struct.unpack('<f5I',out.raw),min(candidates))
  else:assert out.raw==b'Z'*24
  if invalid:assert list(counts)==[0]*4
  elif not malformed:assert list(counts)==[1]*4
  calls+=1
 empty=[(0,.9,0,0,0,0)]*3+[(-1,.9,0,0,0,0)]
 for kind in range(4):
  rows=list(empty);rows[kind]=(1 if kind<3 else 3,.4,2,11,12,13);run(lib,rows)
 rng=random.Random(27041)
 for _ in range(2000):
  rows=[(rng.randrange(2),rng.choice((.0,.125,.5,.875,1.,rng.random())),2,11,12,13) for i in range(3)]+[(rng.choice((-1,3)),rng.random(),0,0,0,0)];run(lib,rows)
 tie=[(1,.5,2,11,12,13)]*3+[(3,.5,0,0,0,0)];run(lib,tie)
 for i in range(3):
  rows=list(tie);rows[i]=(-2,.5,2,11,12,13);run(lib,rows)
 for cap in (0,1,23):run(lib,tie,cap=cap)
 run(lib,tie,null=True);run(lib,tie,side=2)
 for idx in range(6):
  for bad in (float('nan'),float('inf'),16001):
   coords=[1000,40,1000,1020,40,1000];coords[idx]=bad;run(lib,tie,coords=coords)
 production=calls;negative=[]
 for name,text,rows in [('later_hit',source.replace(' jae .keep',' jbe .keep'),[(1,.1,0,0,0,0),(1,.8,2,0,0,0),empty[2],empty[3]]),('actor_wreck_alias',source.replace('mov r13d,WORLD_CONTACT_WRECK','mov r13d,WORLD_CONTACT_ACTOR'),[empty[0],empty[1],(1,.5,2,11,12,13),empty[3]])]:
  bad=build(name,text)
  try:run(bad,rows)
  except AssertionError:negative.append(name)
  else:raise AssertionError('negative escaped '+name)
 print(json.dumps({'suite':'typed-world-contact-arbitration','passed':True,'calls':production,'random_source_orders':2000,'negative_controls':negative,'source_readonly_ABI':True,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'scope':'Actual NASM arbitration with assembled observable source-contract stubs; not production geometry or projectile hook acceptance.'}))
