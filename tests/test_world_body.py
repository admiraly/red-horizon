#!/usr/bin/env python3
"""Prepared ground-body composition ABI with independent assembled sources."""
import ctypes as C,hashlib,itertools,json,os,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
STUB='''default rel
section .data
global cover_status,cover_calls,context_seen,endpoints_seen,role_seen,stack_bad
global sim_wrecks,sim_wreck_count,wreck_query_revision
cover_status: dd 1,0
cover_calls: dd 0,0
context_seen: times 5 dq 0
endpoints_seen: times 5 dd 0
role_seen: dd 0
stack_bad: dd 0
sim_wreck_count: dd 8
wreck_query_revision: dq 79
sim_wrecks: times 65536 db 0
section .text
global terrain_body_path_clear,terrain_body_step,wreck_body_query_context
terrain_body_step:
 movaps xmm0,xmm2
 movaps xmm1,xmm3
 ret
terrain_body_path_clear:
 mov [role_seen],edi
 inc dword [cover_calls]
 mov rax,rsp
 and eax,15
 cmp eax,8
 je .aligned
 inc dword [stack_bad]
.aligned:
 pcmpeqd xmm0,xmm0
 movaps xmm1,xmm0
 movaps xmm2,xmm0
 movaps xmm3,xmm0
 movaps xmm4,xmm0
 mov rdi,-1
 mov rsi,-1
 mov rdx,-1
 mov rcx,-1
 mov r8,-1
 mov eax,[cover_status]
 ret
wreck_body_query_context:
 inc dword [cover_calls+4]
 mov [context_seen],rdx
 mov [context_seen+8],rcx
 mov [context_seen+16],r8
 mov [context_seen+24],rsi
 mov [context_seen+32],rdi
 movss [endpoints_seen],xmm0
 movss [endpoints_seen+4],xmm1
 movss [endpoints_seen+8],xmm2
 movss [endpoints_seen+12],xmm3
 movss [endpoints_seen+16],xmm4
 mov rax,rsp
 and eax,15
 cmp eax,8
 je .aligned
 inc dword [stack_bad]
.aligned:
 mov eax,[cover_status+4]
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
with tempfile.TemporaryDirectory(prefix='rh-world-body-') as folder:
 td=pathlib.Path(folder);stub=td/'sources.asm';stub.write_text(STUB)
 source=(ROOT/'src/nav/world_body.asm').read_text()
 def build(tag,text=source):
  asm=td/(tag+'.asm');asm.write_text(text);objects=[]
  for i,p in enumerate((asm,stub,ROOT/'tests/probe_world_body.asm')):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True)
  lib=C.CDLL(str(so));lib.probe_world_body_path_clear_context.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint64,C.c_void_p]+[C.c_float]*4
  lib.world_body_blocked_context.argtypes=[C.c_uint,C.c_void_p,C.c_uint,C.c_uint64]+[C.c_float]*2
  return lib
 lib=build('candidate');records=C.create_string_buffer(b'Z'*65536);calls=0
 def run(which,role,status):
  global calls
  statuses=(C.c_int*2).in_dll(which,'cover_status');seen=(C.c_uint64*5).in_dll(which,'context_seen');counts=(C.c_uint*2).in_dll(which,'cover_calls');regs=C.create_string_buffer(56)
  for i,s in enumerate(status):statuses[i]=s;counts[i]=0
  C.c_uint.in_dll(which,'stack_bad').value=0
  before=records.raw;actual=which.probe_world_body_path_clear_context(role,records,512,0xfedcba9876543210,regs,1000,1001,1100,1101)
  assert actual==int(status[0]==1 and status[1]==0),(status,actual)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert records.raw==before
  assert list(counts)==[1,int(status[0]==1)]
  assert C.c_uint.in_dll(which,'stack_bad').value==0
  assert C.c_uint.in_dll(which,'role_seen').value==role
  if status[0]==1:
   assert list(seen)[:4]==[C.addressof(records),512,0xfedcba9876543210,24]
   assert seen[4]%16==0
   endpoints=(C.c_float*5).in_dll(which,'endpoints_seen')
   assert list(endpoints)==[1000,1001,1100,1101,C.c_float((.551,3.551,4.491)[role]).value]
  blocked=which.world_body_blocked_context(role,records,512,79,1000,1001)
  assert blocked==1-actual
  if status[0]==1:assert list((C.c_float*5).in_dll(which,'endpoints_seen'))[:4]==[1000,1001,1000,1001]
  calls+=1
 for role in range(3):
  for statuses in itertools.product((-2,-1,0,1),(-2,-1,0,1)):run(lib,role,statuses)
 negative=[]
 for name,text,role,fixture in [
  ('source_alias',source.replace(' mov rdx,[rsp+24]',' lea rdx,[sim_wrecks]'),0,(1,0)),
  ('radius_flattened',source.replace(' mov eax,[rsp+48]',' xor eax,eax'),2,(1,0)),
  ('source_fault_clear',source.replace(' setz al',' setle al'),0,(1,-2)),
  ('occupation_inverted',source.replace(' xor eax,1',' nop'),0,(1,0))]:
  bad=build(name,text)
  try:run(bad,role,fixture)
  except AssertionError:negative.append(name)
  else:raise AssertionError('negative escaped '+name)
 print(json.dumps({'suite':'prepared-world-body-contract','passed':True,'cases':48,'negative_controls':negative,'readonly_ABI':True,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'scope':'Assembled composition/source/role/radius/alignment contracts only; no gameplay movement/nav/remote prediction acceptance.'}))
