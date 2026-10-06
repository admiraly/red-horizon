#!/usr/bin/env python3
"""Actual dynamic navigation FIFO, reuse, saturation and ABI contracts."""
import ctypes as C,json,hashlib,os,pathlib,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1];library=pathlib.Path(sys.argv[1]).resolve()
asm='''default rel
extern wreck_nav_goal,wreck_nav_hash
section .text
global test_goal,test_hash
test_goal:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rsi
 mov [rsp+8],rsp
 mov ebx,11
 mov ebp,12
 mov r12d,13
 mov r13d,14
 mov r14d,15
 mov r15d,16
 movss xmm0,[rsi]
 movss xmm1,[rsi+4]
 call wreck_nav_goal
 mov rsi,[rsp]
 movss [rsi],xmm0
 movss [rsi+4],xmm1
 xor eax,eax
 cmp [rsp+8],rsp
 jne .out
 cmp ebx,11
 jne .out
 cmp ebp,12
 jne .out
 cmp r12d,13
 jne .out
 cmp r13d,14
 jne .out
 cmp r14d,15
 jne .out
 cmp r15d,16
 jne .out
 mov eax,1
.out:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
test_hash:
 mov rax,rdi
 mov r8,rsi
 jmp wreck_nav_hash
section .note.GNU-stack noalloc noexec nowrite progbits
'''
with tempfile.TemporaryDirectory(prefix='rh-wreck-nav-') as td:
 td=pathlib.Path(td);(td/'probe.asm').write_text(asm)
 subprocess.run([os.environ['RED_HORIZON_NASM'],'-f','elf64',str(td/'probe.asm'),'-o',str(td/'probe.o')],check=True)
 objects=[str(root/'build'/(str(p.relative_to(root)).replace('/','_')+'.o')) for folder in ('sim','nav','ai','game') for p in (root/'src'/folder).glob('*.asm')]
 subprocess.run(['cc','-shared','-Wl,-Bsymbolic',str(td/'probe.o'),*objects,'-lm','-o',str(td/'probe.so')],check=True)
 lib=C.CDLL(str(td/'probe.so'))
 class E(C.Structure):
  _fields_=[('x',C.c_float),('z',C.c_float)]+[(n,C.c_uint) for n in ('hp','side','kind','front')]+[('target',C.c_int),('gen',C.c_uint)]
 e=(E*32768).in_dll(lib,'sim_entities');count=C.c_uint.in_dll(lib,'sim_count');m=(C.c_uint*8).in_dll(lib,'wreck_nav_metrics');w=(C.c_byte*65536).in_dll(lib,'sim_wrecks')
 lib.test_goal.argtypes=[C.c_uint,C.POINTER(C.c_float)];lib.test_goal.restype=C.c_uint
 lib.test_hash.argtypes=[C.c_uint64,C.c_uint64];lib.test_hash.restype=C.c_uint64
 def digest():return lib.test_hash(14695981039346656037,1099511628211)
 assert lib.sim_init(2048,42)==0
 for i in range(2048):e[i]=E(3480,2000,100,0,0,0,-1,i+1)
 e[2047]=E(3500,2000,1,0,1,1,-1,2048);lib.ground_init();lib.sim_air_damage(2047,1)
 saved=bytes(w);calls=0
 def goal(i,x=3520,z=2000):
  global calls
  data=(C.c_float*2)(x,z);assert lib.test_goal(i,data)==1,'SysV preservation';calls+=1
  assert bytes(w)==saved,'navigation wrote casualty records'
  return tuple(data)
 for i in range(512):assert goal(i)==(3520,2000)
 assert m[0]==512 and m[2]==0
 for i in range(512,1024):goal(i)
 assert m[0]==512 and m[2]==512
 # Update pending generation/role/goal without a second queue identity.
 e[0].gen+=2000;e[0].kind=1;goal(0,3521)
 assert m[0]==512
 for step in range(64):
  old=m[0];lib.wreck_nav_tick();assert m[6]==8 and m[0]==old-8
 assert m[0]==0 and m[1]==512 and m[7]==8
 assert goal(511)!=(3520,2000),'last FIFO request did not receive a usable path'
 # Invalid requests must leave the complete commitment and queue hash untouched.
 lib.wreck_nav_init();before=digest();e[0].gen=0;goal(0);assert digest()==before,'zero generation changed route state'
 e[0].gen=1;count.value=32769;goal(0);assert digest()==before,'invalid count changed route state'
 count.value=2048
 for i,x,z in ((32768,3520,2000),(0,float('nan'),2000),(0,float('inf'),2000),(0,-1,2000),(0,3520,8001)):
  goal(i,x,z);assert digest()==before,'invalid ID/goal changed route state'
 e[0].hp=0;goal(0);assert digest()==before
 e[0].hp=100;e[0].kind=3;goal(0);assert digest()==before
 print(json.dumps({'suite':'wreck-nav-fifo-contract','passed':True,'requests':calls,'saturated_admissions':512,'safe_overflows':512,'drain_ticks':64,'build_cap':8,'pending_reuse_coalesced':True,'complete_state_invalid_preservation':True,'readonly_wrecks':True,'GPR_stack_preserved':True,'module_sha256':hashlib.sha256((root/'src/nav/wreck_nav.asm').read_bytes()).hexdigest(),'probe_sha256':hashlib.sha256((td/'probe.so').read_bytes()).hexdigest(),'limits':['Actual module scheduler and proposals; no army-motion, performance or network acceptance.','Development-only dense initial requests and genuine casualty.']}))
