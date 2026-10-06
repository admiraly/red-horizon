default rel
extern sim_shell_contact
section .text
global probe_shell_contact
; EDI side,RSI observation64, XMM0..5 endpoints.
probe_shell_contact:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rsi
 mov [rsp+8],rsp
 mov ebx,0x123401
 mov ebp,0x123402
 mov r12d,0x123403
 mov r13d,0x123404
 mov r14d,0x123405
 mov r15d,0x123406
 call sim_shell_contact wrt ..plt
 mov rdx,[rsp]
 mov [rdx],rbx
 mov [rdx+8],rbp
 mov [rdx+16],r12
 mov [rdx+24],r13
 mov [rdx+32],r14
 mov [rdx+40],r15
 movss [rdx+48],xmm0
 movss [rdx+52],xmm1
 movss [rdx+56],xmm2
 movss [rdx+60],xmm3
 cmp rsp,[rsp+8]
 je .done
 mov eax,-99
.done:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
