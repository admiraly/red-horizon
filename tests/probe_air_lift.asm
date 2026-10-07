default rel
extern air_lift_step
section .text
global probe_air_lift
; EDI role,XMM0 desired VY,XMM1 speed,XMM2 old VY,RSI out,RDX ABI.
probe_air_lift:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rsi
 mov [rsp+8],rdx
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 mov [rsp+16],rsp
 call air_lift_step
 mov r8d,eax
 mov rdx,[rsp]
 movss [rdx],xmm0
 movss [rdx+4],xmm1
 movss [rdx+8],xmm2
 mov rcx,[rsp+8]
 mov [rcx],rbx
 mov [rcx+8],rbp
 mov [rcx+16],r12
 mov [rcx+24],r13
 mov [rcx+32],r14
 mov [rcx+40],r15
 mov rax,rsp
 sub rax,[rsp+16]
 mov [rcx+48],rax
 mov eax,r8d
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
