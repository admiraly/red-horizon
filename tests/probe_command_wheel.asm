default rel
extern command_terrain_point
section .text
global probe_command_terrain_point
probe_command_terrain_point:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 mov [rsp+8],rsi
 mov [rsp+16],rdx
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 call command_terrain_point
 mov [rsp],eax
 cmp eax,0
 jne .regs
 mov rsi,[rsp+8]
 movss [rsi],xmm0
 movss [rsi+4],xmm1
.regs:
 mov rdx,[rsp+16]
 mov [rdx],rbx
 mov [rdx+8],rbp
 mov [rdx+16],r12
 mov [rdx+24],r13
 mov [rdx+32],r14
 mov [rdx+40],r15
 mov rax,rsp
 and eax,15
 mov [rdx+48],rax
 mov eax,[rsp]
 add rsp,40
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
