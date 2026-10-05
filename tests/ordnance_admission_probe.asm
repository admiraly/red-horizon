; Development-only controlled spawn kernel; does not prove production trajectories.
%include "schemas/entity.inc"
default rel
extern ordnance_flush,ordnance_hash
section .bss align=64
global sim_entities,sim_count,sim_tick_count,vehicle_entity_driver
sim_entities: resb ENTITY_CAPACITY*ENTITY_STRIDE
sim_count: resd 1
sim_tick_count: resd 1
vehicle_entity_driver: resd ENTITY_CAPACITY
global sim_shell_ammo,sim_shell_cooldown,sim_projectile_count
sim_shell_ammo: resd ENTITY_CAPACITY
sim_shell_cooldown: resd ENTITY_CAPACITY
sim_projectile_count: resd 1
global test_calls,test_sources,test_fail,test_dropped
test_calls: resd 1
test_sources: resd ENTITY_CAPACITY
test_fail: resd 1
test_dropped: resd 1
section .text
global projectile_spawn,test_hash,test_flush_abi
projectile_spawn:
 mov eax,[test_calls]
 lea rcx,[test_sources]
 mov [rcx+rax*4],edi
 inc dword [test_calls]
 cmp dword [sim_projectile_count],416
 jae .capacity
 cmp dword [test_fail],0
 jne .bad
 inc dword [sim_projectile_count]
 lea rcx,[sim_shell_ammo]
 dec dword [rcx+rdi*4]
 lea rcx,[sim_shell_cooldown]
 mov dword [rcx+rdi*4],30
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
 jmp ordnance_hash
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
 call ordnance_flush
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
