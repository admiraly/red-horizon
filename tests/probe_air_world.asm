default rel
extern air_world_sweep
section .text
global probe_air_world_sweep
; RDI output16, ESI capacity, EDX unused, RCX register observation pointer56.
probe_air_world_sweep:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rcx
 mov [rsp+8],rsp
 mov ebx,0x123401
 mov ebp,0x123402
 mov r12d,0x123403
 mov r13d,0x123404
 mov r14d,0x123405
 mov r15d,0x123406
 call air_world_sweep
 mov rdx,[rsp]
 mov [rdx],rbx
 mov [rdx+8],rbp
 mov [rdx+16],r12
 mov [rdx+24],r13
 mov [rdx+32],r14
 mov [rdx+40],r15
 movss [rdx+48],xmm0
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
