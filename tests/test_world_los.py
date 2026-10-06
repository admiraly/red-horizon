#!/usr/bin/env python3
"""Prepared readonly/fail-closed LOS source composition, assembled contracts."""
import ctypes as C,hashlib,itertools,json,os,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
STUB='''default rel
section .data
global cover_status,cover_calls,context_seen,sim_wrecks,sim_wreck_count,wreck_query_revision
cover_status: times 3 dd 0
cover_calls: times 3 dd 0
context_seen: times 3 dq 0
sim_wreck_count: dd 8
wreck_query_revision: dq 79
sim_wrecks: times 65536 db 0
section .text
global terrain_ground_query,terrain_solid_query,wreck_query_context
terrain_ground_query:
 inc dword [cover_calls]
 mov eax,[cover_status]
 ret
terrain_solid_query:
 inc dword [cover_calls+4]
 mov eax,[cover_status+4]
 ret
wreck_query_context:
 inc dword [cover_calls+8]
 mov [context_seen],rdx
 mov [context_seen+8],rcx
 mov [context_seen+16],r8
 mov eax,[cover_status+8]
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
with tempfile.TemporaryDirectory(prefix='rh-world-los-') as folder:
 td=pathlib.Path(folder);stub=td/'sources.asm';stub.write_text(STUB);source=(ROOT/'src/nav/world_los.asm').read_text()
 def build(tag,text=source):
  asm=td/(tag+'.asm');asm.write_text(text);objects=[]
  for i,p in enumerate((asm,stub,ROOT/'tests/probe_world_los.asm')):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_world_los_context.argtypes=[C.c_void_p,C.c_uint,C.c_uint64,C.c_void_p]+[C.c_float]*6;return lib
 lib=build('candidate');records=C.create_string_buffer(b'Z'*65536);calls=0
 def run(which,status):
  global calls
  statuses=(C.c_int*3).in_dll(which,'cover_status');seen=(C.c_uint64*3).in_dll(which,'context_seen');counts=(C.c_uint*3).in_dll(which,'cover_calls');regs=C.create_string_buffer(56)
  for i,s in enumerate(status):statuses[i]=s;counts[i]=seen[i]=0
  before=records.raw;actual=which.probe_world_los_context(records,512,0xfedcba9876543210,regs,1000,40,1000,1100,50,1200)
  assert actual==int(all(s==0 for s in status)),(status,actual)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert records.raw==before
  expected=[1,int(status[0]==0),int(status[0]==0 and status[1]==0)];assert list(counts)==expected
  if expected[2]:assert list(seen)==[C.addressof(records),512,0xfedcba9876543210],list(seen)
  calls+=1
 for statuses in itertools.product((-2,-1,0,1),repeat=3):run(lib,statuses)
 negative=[]
 for name,text,fixture in [('ground_fault_clear',source.replace(' jnz .blocked',' jg .blocked',1),(-2,0,0)),('source_alias',source.replace(' mov rdx,[rsp+64]',' lea rdx,[sim_wrecks]'),(0,0,0))]:
  bad=build(name,text)
  try:run(bad,fixture)
  except AssertionError:negative.append(name)
  else:raise AssertionError('negative escaped '+name)
 print(json.dumps({'suite':'prepared-world-los-contract','passed':True,'cases':64,'negative_controls':negative,'readonly_ABI':True,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'scope':'Assembled cover-contract stubs/source forwarding only, no real geometry/gameplay/remote prediction acceptance.'}))
