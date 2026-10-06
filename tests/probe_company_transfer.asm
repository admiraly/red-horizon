default rel
extern company_transfer
section .text
global probe_company_transfer
; Four integer API arguments; R8 output registers.
probe_company_transfer:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp+8],r8
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 call company_transfer
 mov [rsp],eax
 mov rdx,[rsp+8]
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
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
