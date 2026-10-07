default rel
extern air_observation_capture,air_observation_goal
section .text
global probe_air_observation
; EDI own,ESI target,EDX mode0 capture/1 recall,RCX float7,R8 ABI7.
probe_air_observation:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 mov [rsp],rcx
 mov [rsp+8],r8
 mov [rsp+16],edx
 mov [rsp+24],rsp
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 cmp dword [rsp+16],0
 jne .goal
 call air_observation_capture
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 xorps xmm2,xmm2
 xorps xmm3,xmm3
 xorps xmm4,xmm4
 xorps xmm5,xmm5
 xorps xmm6,xmm6
 jmp .save
.goal:
 call air_observation_goal
.save:
 mov r9d,eax
 mov rdx,[rsp]
 movss [rdx],xmm0
 movss [rdx+4],xmm1
 movss [rdx+8],xmm2
 movss [rdx+12],xmm3
 movss [rdx+16],xmm4
 movss [rdx+20],xmm5
 movss [rdx+24],xmm6
 mov rcx,[rsp+8]
 mov [rcx],rbx
 mov [rcx+8],rbp
 mov [rcx+16],r12
 mov [rcx+24],r13
 mov [rcx+32],r14
 mov [rcx+40],r15
 mov rax,rsp
 sub rax,[rsp+24]
 mov [rcx+48],rax
 mov eax,r9d
 add rsp,40
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
