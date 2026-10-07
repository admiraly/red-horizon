default rel
extern sun_shadows_matrix,sun_shadows_apply,sun_shadows_filter
section .text
global probe_sun_shadows_matrix,probe_sun_shadows_apply
; Development ABI observers: update(RDI observations48,XMM0..2 camera),
; apply(EDI program,RSI observations48). Original return preserved.
probe_sun_shadows_matrix:
 mov rsi,rdi
 lea rax,[sun_shadows_matrix]
 jmp probe_common
probe_sun_shadows_apply:
 lea rax,[sun_shadows_apply]
probe_common:
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
 call rax
 mov rdx,[rsp]
 mov [rdx],rbx
 mov [rdx+8],rbp
 mov [rdx+16],r12
 mov [rdx+24],r13
 mov [rdx+32],r14
 mov [rdx+40],r15
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
global probe_sun_shadows_filter
probe_sun_shadows_filter:
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
 call sun_shadows_filter wrt ..plt
 mov rdx,[rsp]
 mov [rdx],rbx
 mov [rdx+8],rbp
 mov [rdx+16],r12
 mov [rdx+24],r13
 mov [rdx+32],r14
 mov [rdx+40],r15
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
