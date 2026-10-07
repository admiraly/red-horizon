; Successful finite rifle gate calls this bounded cosmetic event publisher.
%include "schemas/entity.inc"
%include "schemas/combat.inc"
default rel
extern sim_count,sim_entities,sim_entity_height,combat_event
section .rodata
zero: dd 0.0
maximum: dd 8000.0
min_y: dd -2000.0
max_y: dd 2000.0
radius: dd 0.25
section .text
global infantry_rifle_event
; EDI actor, EAX0 published/-1 invalid. No stock/body/authority writes.
infantry_rifle_event:
 push rbx
 push r12
 sub rsp,8
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 cmp edi,[sim_count]
 jae .bad
 mov r12d,edi
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_KIND],0
 jne .bad
 cmp dword [rbx+ENTITY_HP],0
 je .bad
 cmp dword [rbx+ENTITY_SIDE],1
 ja .bad
 cmp dword [rbx+ENTITY_GENERATION],0
 je .bad
 movss xmm0,[rbx+ENTITY_X]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 movss xmm0,[rbx+ENTITY_Z]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 mov edi,r12d
 call sim_entity_height
 ucomiss xmm0,[min_y]
 jp .bad
 jb .bad
 ucomiss xmm0,[max_y]
 ja .bad
 movaps xmm1,xmm0
 movss xmm0,[rbx+ENTITY_X]
 movss xmm2,[rbx+ENTITY_Z]
 movss xmm3,[radius]
 mov edi,EVENT_INFANTRY_RIFLE
 mov esi,[rbx+ENTITY_SIDE]
 call combat_event
 xor eax,eax
 jmp .done
.bad: mov eax,-1
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
