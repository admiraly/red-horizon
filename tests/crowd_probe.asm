%include "schemas/entity.inc"
default rel
extern crowd_move,crowd_step,crowd_hull_step,crowd_occupied,crowd_hash
section .bss align=64
global sim_entities,sim_count,sim_tick_count
sim_entities: resb ENTITY_CAPACITY*ENTITY_STRIDE
sim_count: resd 1
sim_tick_count: resd 1
global vehicle_entity_driver
vehicle_entity_driver: resd ENTITY_CAPACITY
global sim_players,sim_player_vehicle,sim_vehicles
sim_players: resb 4*64
sim_player_vehicle: resd 4
sim_vehicles: resb 4*32
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
global test_step
test_step:
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
 call crowd_step
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
global test_hull_step
test_hull_step:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rdx
 mov ebx,0x12345
 mov ebp,0x23456
 mov r12d,0x34567
 mov r13d,0x45678
 mov r14d,0x56789
 mov r15d,0x6789a
 movss xmm0,[rdx]
 movss xmm1,[rdx+4]
 movss xmm2,[rdx+8]
 movss xmm3,[rdx+12]
 movss xmm4,[rdx+16]
 call crowd_hull_step
 mov rdx,[rsp]
 movss [rdx],xmm0
 movss [rdx+4],xmm1
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
 movss xmm4,[test_ai_step]
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
test_ai_step: dd 0.12

section .text
global test_occupied
test_occupied:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 movss xmm0,[rdx]
 movss xmm1,[rdx+4]
 mov ebx,0x12345
 mov ebp,0x23456
 mov r12d,0x34567
 mov r13d,0x45678
 mov r14d,0x56789
 mov r15d,0x6789a
 call crowd_occupied
 mov r10d,eax
 mov eax,2
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
 mov eax,r10d
.out:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
