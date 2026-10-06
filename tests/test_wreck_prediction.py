#!/usr/bin/env python3
"""Extract the actual client foot preview; link it to production collision."""
import ctypes as C,hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1];library=pathlib.Path(sys.argv[1]).resolve()
source=(root/'src/platform/linux/client.asm').read_text();body=source.split('player_pointer:\n',1)[1].split('.noprediction:\n',1)[0]
if '--negative-authority' in sys.argv:
 body=body.replace('lea rsi,[net_wrecks]','lea rsi,[sim_wrecks]').replace('mov edx,[net_wreck_count]','mov edx,[sim_wreck_count]').replace('mov rcx,[net_wreck_query_revision]','mov rcx,[wreck_query_revision]')
asm='''%include "schemas/player.inc"
default rel
extern sim_players,sim_player_vehicle,terrain_height,world_body_step_context,net_wrecks,net_wreck_count,net_wreck_query_revision,sim_wrecks,sim_wreck_count,wreck_query_revision
section .bss align=64
global local_player,network_mode,net_connected,visual_target,wish_x,wish_z,intent_buttons
local_player: resd 1
network_mode: resd 1
net_connected: resd 1
visual_target: resd 3
wish_x: resd 1
wish_z: resd 1
intent_buttons: resd 1
section .data
global last_net_time
last_net_time: dq 0.99
net_predict_timeout: dq 0.2
now: dq 1.0
crouch_prediction: dd 0.1
walk_prediction: dd 0.16666667
sprint_prediction: dd 0.3
section .text
glfwGetTime:
 movsd xmm0,[now]
 ret
global sync_player
player_pointer:
'''+body+'''.noprediction:
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
'''
with tempfile.TemporaryDirectory(prefix='rh-wreck-predict-') as td:
 td=pathlib.Path(td);(td/'probe.asm').write_text(asm)
 nasm=os.environ.get('RED_HORIZON_NASM') or shutil.which('nasm') or str(root/'.tools/nasm/nasm')
 subprocess.run([nasm,'-f','elf64','-I',str(root)+'/',str(td/'probe.asm'),'-o',str(td/'probe.o')],check=True)
 objects=[str(root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o')) for folder in ('sim','nav','ai','game') for p in (root/'src'/folder).glob('*.asm')]
 subprocess.run(['cc','-shared','-Wl,-Bsymbolic',str(td/'probe.o'),*objects,'-lm','-o',str(td/'probe.so')],check=True)
 lib=C.CDLL(str(td/'probe.so'))
 class E(C.Structure):
  _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
 e=(E*32768).in_dll(lib,'sim_entities');alive=(C.c_uint*2).in_dll(lib,'sim_alive')
 p=(C.c_float*64).in_dll(lib,'sim_players');pi=(C.c_uint*64).in_dll(lib,'sim_players')
 v=(C.c_int*4).in_dll(lib,'sim_player_vehicle');remote=(C.c_byte*65536).in_dll(lib,'net_wrecks');authority=(C.c_byte*65536).in_dll(lib,'sim_wrecks')
 count=C.c_uint.in_dll(lib,'net_wreck_count');rev=C.c_uint64.in_dll(lib,'net_wreck_query_revision');target=(C.c_float*3).in_dll(lib,'visual_target')
 lib.sim_checksum.restype=C.c_uint64;cases=[]
 def init():
  assert lib.sim_init(32,42)==0
  C.c_uint.in_dll(lib,'network_mode').value=1;C.c_uint.in_dll(lib,'net_connected').value=1
  C.c_double.in_dll(lib,'last_net_time').value=.99
  p[0],p[1],p[2]=3495.84,47.,2000.;pi[5]=100;v[0]=-1
  C.c_float.in_dll(lib,'wish_x').value=1.;C.c_float.in_dll(lib,'wish_z').value=0.;rev.value+=1
 def preview(label,blocked):
  before=lib.sim_checksum();old=bytes(authority);src=bytes(remote);lib.sync_player()
  assert target[1]==47.;assert lib.sim_checksum()==before and bytes(authority)==old and bytes(remote)==src
  assert (target[0]==p[0])==blocked,(label,list(target),p[0]);assert target[2]==p[2]
  cases.append({'name':label,'target':list(target)})
 init()
 for x in e[:32]:x.hp=0
 e[12]=E(3500,2000,1,0,1,0,-1,42);alive[0]=1;alive[1]=0
 lib.ground_init();lib.sim_air_damage(12,1);captured=bytes(authority);C.memset(remote,0,65536)
 count.value=0;preview('authority_wreck_remote_empty',False)
 C.memmove(remote,captured,65536);count.value=1;rev.value+=1;preview('admitted_remote_wreck_blocks',True)
 init();C.memmove(remote,captured,65536);count.value=1;preview('remote_wreck_authority_empty',True)
 C.c_uint.from_buffer(remote,52).value &= ~1;count.value=0;rev.value+=1;preview('remote_retirement_allows',False)
 C.memmove(remote,captured,65536);count.value=1;rev.value+=1;C.c_double.in_dll(lib,'last_net_time').value=0.;preview('stale_packet_no_preview',True)
 C.c_double.in_dll(lib,'last_net_time').value=.99;v[0]=12;preview('boarded_no_foot_preview',True)
 v[0]=-1;C.c_uint.in_dll(lib,'net_connected').value=0;preview('disconnected_no_preview',True)
 print(json.dumps({'suite':'actual-client-wreck-foot-preview','passed':True,'cases':cases,'readonly_authority_and_sources':True,'client_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'probe_binary_sha256':hashlib.sha256((td/'probe.so').read_bytes()).hexdigest(),'limits':['Extracted actual preview prefix with development clock stub; no full GUI or network packet admission evidence.','The remote cache fair delivery delay remains; empty cache admits motion.','No camera smoothing, HUD hazard or vehicle prediction acceptance.']}))
