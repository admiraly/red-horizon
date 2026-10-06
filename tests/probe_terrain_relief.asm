default rel
extern terrain_relief
section .text
global test_terrain_relief
; Development probe: XMM0/1 coordinates, RDI 16-byte output record.
; Store actual height/dX/dZ/status; return1 only when SysV preserved registers match.
test_terrain_relief:
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
 call terrain_relief
 mov rdi,[rsp]
 movss [rdi],xmm0
 movss [rdi+4],xmm1
 movss [rdi+8],xmm2
 mov [rdi+12],eax
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
section .note.GNU-stack noalloc noexec nowrite progbits
