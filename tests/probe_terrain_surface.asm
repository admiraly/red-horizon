; Development-only C ABI wrapper around the actual stateless NASM sampler.
default rel
extern terrain_surface,terrain_height
section .text
global test_surface,test_height
test_surface:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rdi
 mov ebx,0x12345
 mov ebp,0x23456
 mov r12d,0x34567
 mov r13d,0x45678
 mov r14d,0x56789
 mov r15d,0x6789a
 movss xmm0,[rdi]
 movss xmm1,[rdi+4]
 call terrain_surface
 mov rdi,[rsp]
 movss [rdi+8],xmm0
 movss [rdi+12],xmm1
 movss [rdi+16],xmm2
 cmp rbx,0x12345
 jne .abi_fail
 cmp rbp,0x23456
 jne .abi_fail
 cmp r12,0x34567
 jne .abi_fail
 cmp r13,0x45678
 jne .abi_fail
 cmp r14,0x56789
 jne .abi_fail
 cmp r15,0x6789a
 jne .abi_fail
 jmp .out
.abi_fail:
 mov eax,-2
.out:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
test_height:
 push rdi
 movss xmm0,[rdi]
 movss xmm1,[rdi+4]
 call terrain_height
 pop rdi
 movss [rdi+8],xmm0
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
