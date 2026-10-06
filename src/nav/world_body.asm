%include "schemas/world_body.inc"
%include "schemas/terrain_body.inc"
default rel
extern terrain_body_path_clear,terrain_body_step,wreck_body_query_context
extern sim_wrecks,sim_wreck_count,wreck_query_revision
section .rodata
radii: dd BODY_INF_SWEEP_RADIUS,BODY_TANK_SWEEP_RADIUS,BODY_ARTY_SWEEP_RADIUS
section .text
global world_body_path_clear,world_body_path_clear_context
global world_body_blocked,world_body_blocked_context
global world_body_step,world_body_step_context
world_body_step:
 lea rsi,[sim_wrecks]
 mov edx,[sim_wreck_count]
 mov rcx,[wreck_query_revision]
world_body_step_context:
 cmp edi,2
 ja .invalid
 sub rsp,104
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 mov [rsp+24],rsi
 mov [rsp+32],edx
 mov [rsp+40],rcx
 mov [rsp+48],edi
 call terrain_body_step
 movss [rsp+8],xmm0
 movss [rsp+12],xmm1
 ; Recheck every actual returned fragment, including component slides.
 call .check
 cmp eax,1
 je .accept
 movss xmm0,[rsp+8]
 movss xmm1,[rsp+4]
 call .check
 cmp eax,1
 je .accept
 movss xmm0,[rsp]
 movss xmm1,[rsp+12]
 call .check
 cmp eax,1
 je .accept
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 jmp .out
.accept:
 movss xmm0,[rsp+64]
 movss xmm1,[rsp+68]
.out:
 add rsp,104
.invalid:
 ret
.check:
 ; Internal CALL adds8; save this fragment independently of the candidate.
 movss [rsp+72],xmm0
 movss [rsp+76],xmm1
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 movss xmm0,[rsp+8]
 movss xmm1,[rsp+12]
 mov edi,[rsp+56]
 mov rsi,[rsp+32]
 mov edx,[rsp+40]
 mov rcx,[rsp+48]
 sub rsp,8
 call world_body_path_clear_context
 add rsp,8
 ret
world_body_blocked:
 lea rsi,[sim_wrecks]
 mov edx,[sim_wreck_count]
 mov rcx,[wreck_query_revision]
world_body_blocked_context:
 sub rsp,8
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 call world_body_path_clear_context
 xor eax,1
 add rsp,8
 ret
world_body_path_clear:
 lea rsi,[sim_wrecks]
 mov edx,[sim_wreck_count]
 mov rcx,[wreck_query_revision]
world_body_path_clear_context:
 cmp edi,2
 ja .invalid
 sub rsp,104
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 mov [rsp+24],rsi
 mov [rsp+32],edx
 mov [rsp+40],rcx
 mov [rsp+48],edi
 call terrain_body_path_clear
 cmp eax,1
 jne .blocked
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 mov eax,[rsp+48]
 lea rdx,[radii]
 movss xmm4,[rdx+rax*4]
 lea rdi,[rsp+64]
 mov esi,24
 mov rdx,[rsp+24]
 mov ecx,[rsp+32]
 mov r8,[rsp+40]
 call wreck_body_query_context
 test eax,eax
 setz al
 movzx eax,al
 jmp .out
.blocked:
 xor eax,eax
.out:
 add rsp,104
 ret
.invalid:
 xor eax,eax
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
