default rel
extern air_rollout_clear
section .text
global probe_air_rollout_clear
; EDI own ID, ESI base, RDX seven u64 register/stack observations.
probe_air_rollout_clear:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rdx
 mov [rsp+8],rsp
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 call air_rollout_clear
 mov rcx,[rsp]
 mov [rcx],rbx
 mov [rcx+8],rbp
 mov [rcx+16],r12
 mov [rcx+24],r13
 mov [rcx+32],r14
 mov [rcx+40],r15
 mov rdx,rsp
 sub rdx,[rsp+8]
 mov [rcx+48],rdx
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
