%include "schemas/entity.inc"
default rel
extern crowd_move,crowd_hash
section .bss align=64
global sim_entities,sim_count
sim_entities: resb ENTITY_CAPACITY*ENTITY_STRIDE
sim_count: resd 1
global vehicle_entity_driver
vehicle_entity_driver: resd ENTITY_CAPACITY
section .text
; C wrapper (ID, float[5] input/output). ABI checked around actual call.
global test_move,test_hash
test_move:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rsi
 mov ebx,0x12345
 mov ebp,0x23456
 mov r12d,0x34567
 mov r13d,0x45678
 mov r14d,0x56789
 mov r15d,0x6789a
 movss xmm0,[rsi]
 movss xmm1,[rsi+4]
 movss xmm2,[rsi+8]
 movss xmm3,[rsi+12]
 movss xmm4,[rsi+16]
 call crowd_move
 mov rsi,[rsp]
 movss [rsi],xmm0
 movss [rsi+4],xmm1
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
 inc eax
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
 jmp crowd_hash
section .note.GNU-stack noalloc noexec nowrite progbits
section .text
global test_tick
test_tick:
 push rbx
 push r12
 sub rsp,8
 xor r12d,r12d
.loop:
 cmp r12d,[sim_count]
 jae .done
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 movss xmm0,[rbx]
 movss xmm1,[rbx+4]
 movaps xmm2,xmm0
 addss xmm2,[test_ahead]
 movaps xmm3,xmm1
 movss xmm4,[test_step]
 mov edi,r12d
 call crowd_move
 movss [rbx],xmm0
 movss [rbx+4],xmm1
 inc r12d
 jmp .loop
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
section .rodata
test_ahead: dd 40.0
test_step: dd 0.12
