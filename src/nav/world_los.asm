%include "schemas/world_los.inc"
default rel
extern terrain_ground_query,terrain_solid_query,wreck_query_context
extern sim_wrecks,sim_wreck_count,wreck_query_revision
section .text
global world_los,world_los_context
world_los:
 lea rdi,[sim_wrecks]
 mov esi,[sim_wreck_count]
 mov rdx,[wreck_query_revision]
 jmp world_los_context
world_los_context:
 sub rsp,104
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 mov [rsp+64],rdi
 mov [rsp+72],esi
 mov [rsp+80],rdx
 lea rdi,[rsp+32]
 mov esi,24
 call terrain_ground_query
 test eax,eax
 jnz .blocked
%macro endpoints 0
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
%endmacro
 endpoints
 lea rdi,[rsp+32]
 mov esi,24
 call terrain_solid_query
 test eax,eax
 jnz .blocked
 endpoints
 lea rdi,[rsp+32]
 mov esi,24
 mov rdx,[rsp+64]
 mov ecx,[rsp+72]
 mov r8,[rsp+80]
 call wreck_query_context
 test eax,eax
 setz al
 movzx eax,al
 jmp .out
.blocked:
 xor eax,eax
.out:
 add rsp,104
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
