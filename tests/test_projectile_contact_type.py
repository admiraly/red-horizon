#!/usr/bin/env python3
"""Actual air-gun launch/tick with scripted contacts exercises damage routing."""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
STUB='''default rel
section .data
global sim_entities,sim_count,sim_tick_count,sim_aircraft,contact_result,contact_status,damage_calls,damage_id,damage_amount
sim_entities: times 8*32 db 0
sim_count: dd 8
sim_tick_count: dd 1
sim_aircraft: times 8*64 db 0
contact_result: dd 0.5,4,3,79,0,0
contact_status: dd 1
damage_calls: dd 0
damage_id: dd 0
damage_amount: dd 0
height: dd 100.0
section .text
global world_contact_query,sim_air_damage,sim_blast,sim_entity_height,terrain_height
world_contact_query:
 mov eax,[contact_status]
 cmp eax,1
 jne .out
 movdqu xmm0,[contact_result]
 movdqu [rdi],xmm0
 mov rdx,[contact_result+16]
 mov [rdi+16],rdx
.out: ret
sim_air_damage:
 inc dword [damage_calls]
 mov [damage_id],edi
 mov [damage_amount],esi
 ret
sim_blast: ret
sim_entity_height:
terrain_height:
 movss xmm0,[height]
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
with tempfile.TemporaryDirectory(prefix='rh-projectile-type-') as folder:
 td=pathlib.Path(folder);stub=td/'sources.asm';stub.write_text(STUB);source=(ROOT/'src/sim/projectiles.asm').read_text()
 def build(tag,text=source):
  asm=td/(tag+'.asm');asm.write_text(text);objects=[]
  for i,p in enumerate((asm,stub)):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(p),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True);return C.CDLL(str(so))
 def run(lib,kind,generation,status=1):
  lib.projectile_init();entities=(C.c_byte*256).in_dll(lib,'sim_entities');air=(C.c_byte*512).in_dll(lib,'sim_aircraft');C.memset(C.addressof(entities),0,256);C.memset(C.addressof(air),0,512)
  for index,side,gen in ((0,0,42),(3,1,79)):C.memmove(C.addressof(entities)+index*32,struct.pack('<ff4IiI',1000+index*20,1000,1000,side,3,0,-1,gen),32)
  # Declared initial fighter sidecar; production launch owns the projectile.
  record=struct.pack('<5f6I3f2I',100,0,0,0,2,1,0,3,0,1,42,2,0,0,0,1);C.memmove(C.addressof(air),record,64)
  out=(C.c_byte*24).in_dll(lib,'contact_result');C.memmove(C.addressof(out),struct.pack('<f5I',.5,kind,3,generation,0,0),24);C.c_int.in_dll(lib,'contact_status').value=status;C.c_uint.in_dll(lib,'damage_calls').value=0
  assert lib.projectile_air_launch(0,4)==0
  before=bytes(entities);lib.projectile_tick();assert bytes(entities)==before
  damage=C.c_uint.in_dll(lib,'damage_calls').value
  assert damage==int(status==1 and kind==4 and generation==79),(kind,generation,status,damage)
  assert C.c_uint.in_dll(lib,'sim_projectile_count').value==int(status==0)
  if damage:assert C.c_uint.in_dll(lib,'damage_id').value==3 and C.c_uint.in_dll(lib,'damage_amount').value==24
 lib=build('candidate');cases=0
 for kind in (1,2,3,4):
  for generation in (42,79):run(lib,kind,generation);cases+=1
 for status in (-2,-1,0):run(lib,4,79,status);cases+=1
 negative=[]
 for name,text,fixture in [('cover_alias',source.replace(' cmp dword [rsp+60],WORLD_CONTACT_ACTOR\n jne .expire',' cmp dword [rsp+60],WORLD_CONTACT_ACTOR\n nop'),(3,79)),('retired_generation',source.replace(' cmp [rdx+rax+ENTITY_GENERATION],ecx\n jne .expire',' cmp [rdx+rax+ENTITY_GENERATION],ecx\n nop'),(4,42))]:
  bad=build(name,text)
  try:run(bad,*fixture)
  except AssertionError:negative.append(name)
  else:raise AssertionError('negative escaped '+name)
 print(json.dumps({'suite':'projectile-contact-damage-type','passed':True,'cases':cases,'negative_controls':negative,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'scope':'Actual public air-gun launch and projectile tick with assembled scripted contact source/damage observer. Cover/recycled-identity routing, not natural dogfight or production collision acceptance.'}))
