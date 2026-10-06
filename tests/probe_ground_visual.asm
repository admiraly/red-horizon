default rel
extern ground_visual,__real_expf
section .text
global probe_ground_visual
; Suspension ABI plus R9 six-qword register observation record.
probe_ground_visual:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],r9
 mov [rsp+8],rsp
 mov ebx,0x123401
 mov ebp,0x123402
 mov r12d,0x123403
 mov r13d,0x123404
 mov r14d,0x123405
 mov r15d,0x123406
 call ground_visual
 mov r9,[rsp]
 mov [r9],rbx
 mov [r9+8],rbp
 mov [r9+16],r12
 mov [r9+24],r13
 mov [r9+32],r14
 mov [r9+40],r15
 cmp rsp,[rsp+8]
 je .ok
 mov eax,-99
.ok:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
global __wrap_expf
__wrap_expf:
 inc qword [visual_exp_calls]
 mov rax,rsp
 and eax,15
 cmp eax,8
 je .aligned
 inc qword [visual_alignment_errors]
.aligned:
 jmp __real_expf wrt ..plt
section .bss align=8
global visual_exp_calls,visual_alignment_errors
visual_exp_calls: resq 1
visual_alignment_errors: resq 1
section .note.GNU-stack noalloc noexec nowrite progbits
