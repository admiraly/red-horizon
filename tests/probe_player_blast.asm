default rel
extern player_apply_damage,player_blast,player_motion_reset
section .text
global probe_player_blast
; EDI entry0..2,ESI slot/side,EDX damage,ECX source side,R8 observations.
; XMM0..3 blast floats remain untouched before the real helper call.
probe_player_blast:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 mov [rsp],edi
 mov [rsp+4],esi
 mov [rsp+8],edx
 mov [rsp+12],ecx
 mov [rsp+16],r8
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 mov edi,esi
 mov esi,edx
 cmp dword [rsp],0
 je .damage
 cmp dword [rsp],1
 je .blast
 call player_motion_reset wrt ..plt
 jmp .observe
.damage:
 mov edx,[rsp+12]
 call player_apply_damage wrt ..plt
 jmp .observe
.blast:
 call player_blast wrt ..plt
.observe:
 mov [rsp+24],eax
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
