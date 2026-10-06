#!/usr/bin/env python3
"""Actual server packet-builder selection, ownership, bounds and causal controls."""
import ctypes as C,hashlib,json,os,pathlib,struct,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
NASM=os.environ.get('RED_HORIZON_NASM','/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm')
server=(ROOT/'src/net/coop_server.asm').read_text()
routine=server[server.index('send_projectiles:'):server.index('; Global source-independent fair wreck stream')]
prefix='''%include "schemas/player.inc"
%include "schemas/entity.inc"
%include "schemas/combat.inc"
%include "schemas/projectile_remote.inc"
%include "src/net/protocol.inc"
default rel
section .data
global sim_count,sim_players,sim_player_vehicle,sim_vehicles,vehicle_driver_generation,vehicle_entity_driver,sim_entities,sim_projectiles,projectile_cursors,output,captured_len,stack_bad
sim_count: dd 8192
interest2: dd 810000.0
section .bss
sim_players: resb 256
sim_player_vehicle: resd 4
sim_vehicles: resb 128
vehicle_driver_generation: resd 4
vehicle_entity_driver: resd 32768
sim_entities: resb 1048576
sim_projectiles: resb 32768
projectile_cursors: resd 4
output: resb 1200
captured_len: resd 1
stack_bad: resd 1
section .text
global send_projectiles
header:
 mov eax,esp
 and eax,15
 cmp eax,8
 je .aligned
 inc dword [stack_bad]
.aligned:
 mov dword [output],NET_MAGIC
 mov dword [output+4],NET_VERSION
 mov dword [output+8],NET_SCHEMA
 mov dword [output+12],NET_CONTENT
 mov [output+16],edi
 mov [output+20],esi
 mov [output+32],edx
 ret
send_packet:
 mov [captured_len],esi
 mov eax,esp
 and eax,15
 cmp eax,8
 je .aligned
 inc dword [stack_bad]
.aligned:
 xor eax,eax
 ret
'''
with tempfile.TemporaryDirectory(prefix='rh-projectile-priority-') as folder:
 td=pathlib.Path(folder)
 def build(tag,code=routine):
  p=td/(tag+'.asm');p.write_text(prefix+code+'\nsection .note.GNU-stack noalloc noexec nowrite progbits\n');objects=[]
  for i,path in enumerate((p,ROOT/'tests/probe_projectile_priority.asm')):
   obj=td/f'{tag}-{i}.o';subprocess.run([NASM,'-f','elf64','-I',str(ROOT)+'/',str(path),'-o',str(obj)],check=True);objects.append(str(obj))
  so=td/(tag+'.so');subprocess.run(['cc','-shared','-Wl,-Bsymbolic',*objects,'-o',str(so)],check=True)
  lib=C.CDLL(str(so));lib.probe_send_projectiles.argtypes=[C.c_uint,C.c_void_p,C.c_void_p];return lib
 def arena(lib,name,size):return (C.c_ubyte*size).in_dll(lib,name)
 def reset(lib):
  sizes={'sim_players':256,'sim_player_vehicle':16,'sim_vehicles':128,'vehicle_driver_generation':16,'vehicle_entity_driver':131072,'sim_entities':1048576,'sim_projectiles':32768,'projectile_cursors':16,'output':1200}
  for n,size in sizes.items():C.memset(C.addressof(arena(lib,n,size)),0,size)
  C.c_uint.in_dll(lib,'stack_bad').value=0;C.c_uint.in_dll(lib,'captured_len').value=0
  def put(name,offset,data):C.memmove(C.addressof(arena(lib,name,sizes[name]))+offset,data,len(data))
  put('sim_players',0,struct.pack('<5f11I',1000,15,2000,0,0,100,30,0,0,0,0,1,0,0,0,9))
  put('sim_player_vehicle',0,struct.pack('<i',12));put('sim_vehicles',0,struct.pack('<8I',12,42,0,1,64,0,1,0));put('vehicle_driver_generation',0,struct.pack('<I',9));put('vehicle_entity_driver',48,struct.pack('<I',0));put('sim_entities',384,struct.pack('<2f6I',1000,2000,400,0,1,0,0xffffffff,42))
  for i in range(512):put('sim_projectiles',64*i,struct.pack('<6f4If5I',1000,15,2000,0,0,10,100,0,1,80,18,20,1,0,42,0))
  for i,ttl in zip(range(400,406),(40,60,50,80,70,90)):
   put('sim_projectiles',64*i+24,struct.pack('<I',ttl));put('sim_projectiles',64*i+44,struct.pack('<I',12));put('sim_projectiles',64*i+52,struct.pack('<I',1))
  # A newer-looking retired identity must never enter owned priority.
  put('sim_projectiles',500*64+24,struct.pack('<I',220));put('sim_projectiles',500*64+44,struct.pack('<I',12));put('sim_projectiles',500*64+52,struct.pack('<II',1,99))
  return put,sizes
 def send(lib):
  sizes={'sim_players':256,'sim_player_vehicle':16,'sim_vehicles':128,'vehicle_driver_generation':16,'vehicle_entity_driver':131072,'sim_entities':1048576,'sim_projectiles':32768}
  before={n:bytes(arena(lib,n,size)) for n,size in sizes.items()};regs=C.create_string_buffer(56)
  lib.probe_send_projectiles(0,None,regs)
  assert struct.unpack('<6Q',regs.raw[:48])==tuple(0x123401+i for i in range(6))
  assert C.c_uint.in_dll(lib,'stack_bad').value==0
  assert before=={n:bytes(arena(lib,n,size)) for n,size in sizes.items()}
  packet=bytes(arena(lib,'output',1200));size=C.c_uint.in_dll(lib,'captured_len').value
  assert 44<=size<=1200;count=struct.unpack_from('<I',packet,40)[0];assert count<=18 and size==44+64*count
  assert struct.unpack_from('<I',packet,32)[0]==size-40
  rows=[struct.unpack_from('<I15I',packet,44+64*i) for i in range(count)];ids=[r[0] for r in rows];assert len(ids)==len(set(ids))
  for row in rows:assert struct.pack('<15I',*row[1:])==before['sim_projectiles'][row[0]*64:row[0]*64+60]
  return ids
 def positive(lib):
  put,_=reset(lib);assert send(lib)==[405,403,404,401]+list(range(14))
  assert send(lib)==[405,403,404,401]+list(range(14,28))
  put('projectile_cursors',0,struct.pack('<I',400));ids=send(lib);assert ids[:4]==[405,403,404,401] and len(ids)==18
  return ids
 lib=build('candidate');positive(lib);cases=3
 # Every independent ownership identity guard disables priority; fair stream remains.
 for name,offset,value in [('sim_players',44,0),('sim_players',20,0),('sim_players',60,0),('sim_player_vehicle',0,8192),('sim_vehicles',12,0),('sim_vehicles',0,13),('sim_vehicles',8,1),('vehicle_driver_generation',0,10),('vehicle_entity_driver',48,1),('sim_entities',396,1),('sim_entities',400,2),('sim_entities',392,0),('sim_entities',412,43)]:
  put,_=reset(lib);put(name,offset,struct.pack('<I',value));assert send(lib)==list(range(18)),(name,offset,value);cases+=1
 put,_=reset(lib);put('sim_projectiles',405*64,struct.pack('<f',3000));assert send(lib)[:4]==[403,404,401,402];cases+=1
 put,_=reset(lib);put('sim_projectiles',405*64+24,struct.pack('<I',80));assert send(lib)[:2]==[403,405];cases+=1
 negative=[]
 mutations=[('priority_omitted',routine.replace('.priority:\n','.priority:\n jmp .fair_begin\n',1)),('freshest_omitted',routine.replace(' jbe .priority_next',' nop',1)),('source_generation_omitted',routine.replace(' cmp [rsi+PROJECTILE_SOURCE_GENERATION],eax\n jne .priority_next',' nop\n nop',1)),('dedup_omitted',routine.replace(' cmp [rdx+rax],r10d\n je .skip',' nop\n nop',1))]
 for name,code in mutations:
  bad=build(name,code)
  try:positive(bad)
  except AssertionError:negative.append(name)
  else:raise AssertionError('negative escaped '+name)
 print(json.dumps({'suite':'owned-projectile-priority','passed':True,'cases':cases,'maximum_owned_priority':4,'minimum_fair_capacity':14,'MTU_maximum':1196,'negative_controls':negative,'preserved_authority_and_ABI':True,'source_sha256':hashlib.sha256(routine.encode()).hexdigest(),'scope':'Actual extracted server packet builder with controlled core records. Real UDP/GUI and extended network verification remain separate.'}))
