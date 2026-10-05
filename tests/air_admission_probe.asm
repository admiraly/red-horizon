; Development-only controlled spawn kernel; does not prove production trajectories.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
default rel
extern air_admission_flush,air_admission_hash
section .bss align=64
global sim_entities,sim_count,sim_tick_count,sim_aircraft
sim_entities: resb ENTITY_CAPACITY*ENTITY_STRIDE
sim_count: resd 1
sim_tick_count: resd 1
sim_aircraft: resb ENTITY_CAPACITY*AIR_STRIDE
global sim_projectile_count
sim_projectile_count: resd 1
global test_calls,test_sources,test_fail,test_dropped,test_bad_abi,test_roles
test_calls: resd 1
test_sources: resd ENTITY_CAPACITY
test_fail: resd 1
test_dropped: resd 1
test_bad_abi: resd 1
test_roles: resd ENTITY_CAPACITY
section .text
global projectile_air_launch,test_hash,test_flush_abi
projectile_air_launch:
 mov rax,rsp
 and eax,15
 cmp eax,8
 je .aligned
 inc dword [test_bad_abi]
.aligned:
 mov eax,[test_calls]
 lea rcx,[test_sources]
 mov [rcx+rax*4],edi
 lea rcx,[test_roles]
 mov [rcx+rax*4],esi
 inc dword [test_calls]
 cmp dword [sim_projectile_count],480
 jae .capacity
 cmp dword [test_fail],0
 jne .bad
 inc dword [sim_projectile_count]
 ; Production may clobber all ordinary caller-saved registers.
 mov r8,-1
 mov r9,-1
 mov r10,-1
 mov r11,-1
 xor eax,eax
 ret
.capacity: inc dword [test_dropped]
.bad: mov eax,-1
 ret
test_hash:
 mov rax,rdi
 mov r8,rsi
 jmp air_admission_hash
test_flush_abi:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov ebx,0x12345
 mov ebp,0x23456
 mov r12d,0x34567
 mov r13d,0x45678
 mov r14d,0x56789
 mov r15d,0x6789a
 call air_admission_flush
 xor eax,eax
 cmp rbx,0x12345
 jne .out
 cmp rbp,0x23456
 jne .out
 cmp r12,0x34567
 jne .out
 cmp r13,0x45678
 jne .out
 cmp r14,0x56789
 jne .out
 cmp r15,0x6789a
 jne .out
 mov eax,1
.out:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
