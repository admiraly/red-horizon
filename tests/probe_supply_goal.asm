default rel
extern infantry_supply_goal
section .text
global probe_supply_goal
; EDI actor, RSI 8-byte goal output, RCX 7-qword ABI observations.
probe_supply_goal:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 mov [rsp],edi
 mov [rsp+4],edx
 mov [rsp+8],rsi
 mov [rsp+16],rcx
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 mov edi,[rsp]
 mov rsi,[rsp+8]
 mov edx,[rsp+4]
 call infantry_supply_goal wrt ..plt
 mov [rsp+24],eax
 cmp eax,-1
 je .no_goal
 mov rsi,[rsp+8]
 movss [rsi],xmm0
 movss [rsi+4],xmm1
.no_goal:
 mov rcx,[rsp+16]
 mov [rcx],rbx
 mov [rcx+8],rbp
 mov [rcx+16],r12
 mov [rcx+24],r13
 mov [rcx+32],r14
 mov [rcx+40],r15
 mov rax,rsp
 and eax,15
 mov [rcx+48],rax
 mov eax,[rsp+24]
 add rsp,40
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
