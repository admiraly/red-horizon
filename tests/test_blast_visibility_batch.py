#!/usr/bin/env python3
"""Production blast routine with an observable cover/casualty source contract."""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm');world=(ROOT/'src/sim/world.asm').read_text();body=world[world.index('sim_blast:\n'):world.index('sim_shell_contact:')]
STUB='''default rel
section .data
global sim_entities,cell_counts,cell_samples,casualties,death_ids,cover_calls
sim_entities: times 32*32 db 0
cell_counts: times 1024 dd 0
cell_samples: times 1024*24 dd 0
casualties: dd 0
death_ids: times 32 dd 0
cover_calls: dd 0
height: dd 10.0
section .text
global terrain_los,sim_entity_height,sim_air_damage
terrain_los:
 inc dword [cover_calls]
 mov eax,1
 cmp dword [casualties],0
 je .out
 xor eax,eax
.out: ret
sim_entity_height:
 movss xmm0,[height]
 ret
sim_air_damage:
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 cmp dword [rdx+rax+8],0
 je .out
 mov dword [rdx+rax+8],0
 mov eax,[casualties]
 lea rdx,[death_ids]
 mov [rdx+rax*4],edi
 inc dword [casualties]
.out: ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
with tempfile.TemporaryDirectory(prefix='rh-blast-batch-') as folder:
 td=pathlib.Path(folder);stub=td/'sources.asm';stub.write_text(STUB);probe=td/'probe.asm';probe.write_text((ROOT/'tests/probe_terrain_ground_query.asm').read_text().replace('terrain_ground_query','sim_blast'))
 def build(tag,text=body):
  asm=td/(tag+'.asm');asm.write_text('%include "schemas/entity.inc"\ndefault rel\nextern sim_entities,cell_counts,cell_samples,terrain_los,sim_entity_height,sim_air_damage\nsection .rodata\ncell_scale: dd 0.004\nmaximum: dd 8000.0\nsection .text\nglobal sim_blast\n'+text+'\nsection .note.GNU-stack noalloc noexec nowrite progbits\n');objects=[]
  for i,p in enumerate((asm,stub,probe)):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True);lib=C.CDLL(str(so));lib.probe_sim_blast.argtypes=[C.c_uint,C.c_uint,C.c_void_p]+[C.c_float]*4;return lib
 def run(lib,ids,side=0):
  records=(C.c_byte*1024).in_dll(lib,'sim_entities');cells=(C.c_uint*1024).in_dll(lib,'cell_counts');samples=(C.c_uint*(1024*24)).in_dll(lib,'cell_samples');deaths=(C.c_uint*32).in_dll(lib,'death_ids');C.memset(C.addressof(records),0,1024);C.memset(C.addressof(cells),0,4096)
  C.c_uint.in_dll(lib,'casualties').value=0;C.c_uint.in_dll(lib,'cover_calls').value=0
  for n,i in enumerate(ids):C.memmove(C.addressof(records)+i*32,struct.pack('<ff4IiI',1000+n,1000,1,1-side,1,0,-1,42),32);samples[132*24+n]=i
  cells[132]=len(ids);regs=C.create_string_buffer(56);rc=lib.probe_sim_blast(side,40,regs,1000,1000,36,10)
  assert tuple(struct.unpack('<6Q',regs.raw[:48]))==tuple(0x123401+i for i in range(6));assert rc==len(ids) and C.c_uint.in_dll(lib,'casualties').value==len(ids),(rc,list(deaths[:len(ids)]));assert list(deaths[:len(ids)])==list(ids);assert C.c_uint.in_dll(lib,'cover_calls').value==len(ids)
 lib=build('candidate')
 for ids in ((0,24),(24,0),(0,12,24),(24,12,0)):
  for side in (0,1):run(lib,ids,side)
 # Causal immediate-casualty variant changes visibility before the next candidate.
 bad=build('immediate',body.replace(' mov [rsp+104+rbp*4],eax\n inc ebp',' mov [rsp+104+rbp*4],eax\n mov edi,eax\n mov esi,r13d\n call sim_air_damage\n inc ebp'))
 try:run(bad,(0,24))
 except AssertionError:negative=True
 else:raise AssertionError('immediate casualty escaped')
 print(json.dumps({'suite':'prepared-blast-visibility-batch','passed':True,'cases':8,'negative_immediate_casualty':negative,'SysV':True,'source_sha256':hashlib.sha256(body.encode()).hexdigest(),'scope':'Actual production blast routine with assembled mutable visibility/casualty contract stubs. Establishes collect-before-apply ordering, not real wreck shielding or gameplay hook acceptance.'}))
