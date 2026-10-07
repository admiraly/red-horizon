default rel
extern air_gun_solution_ready
section .text
global probe_air_gun_solution_ready
; EDI source, RSI register observer. Keep the production predicate's EAX.
probe_air_gun_solution_ready:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp+8],rsi
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 call air_gun_solution_ready
 mov [rsp],eax
 mov rsi,[rsp+8]
 mov [rsi],rbx
 mov [rsi+8],rbp
 mov [rsi+16],r12
 mov [rsi+24],r13
 mov [rsi+32],r14
 mov [rsi+40],r15
 mov rax,rsp
 and eax,15
 mov [rsi+48],rax
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
