default rel
extern terrain_body_move, terrain_body_blocked, terrain_body_path_clear
section .text
global test_body_move,test_body_blocked,test_body_path
test_body_move:
 sub rsp,8
 call terrain_body_move
 add rsp,8
 movd eax,xmm0
 movd edx,xmm1
 shl rdx,32
 or rax,rdx
 ret
test_body_blocked: jmp terrain_body_blocked
test_body_path: jmp terrain_body_path_clear
section .note.GNU-stack noalloc noexec nowrite progbits
section .text
global test_body_hash,test_body_abi
extern terrain_body_hash
test_body_hash:
 mov rax,rdi
 mov r8,rsi
 jmp terrain_body_hash
test_body_abi:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov ebx,0x11223344
 mov ebp,0x22334455
 mov r12d,0x33445566
 mov r13d,0x44556677
 mov r14d,0x55667788
 mov r15d,0x66778899
 call terrain_body_move
 xor eax,eax
 cmp rbx,0x11223344
 jne .out
 cmp rbp,0x22334455
 jne .out
 cmp r12,0x33445566
 jne .out
 cmp r13,0x44556677
 jne .out
 cmp r14,0x55667788
 jne .out
 cmp r15,0x66778899
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
