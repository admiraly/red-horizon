default rel
extern air_gun_intercept
section .text
global probe_air_gun_intercept
; RDI outXYZtime16, RSI preserved-register observer56, XMM0..5 inputs.
probe_air_gun_intercept:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 mov [rsp+8],rdi
 mov [rsp+16],rsi
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 call air_gun_intercept
 mov [rsp],eax
 test eax,eax
 jnz .registers
 mov rdi,[rsp+8]
 movss [rdi],xmm0
 movss [rdi+4],xmm1
 movss [rdi+8],xmm2
 movss [rdi+12],xmm3
.registers:
 mov rsi,[rsp+16]
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
 add rsp,40
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
