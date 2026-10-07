; Return to an interior own-side recovery area on critical damage/empty stores.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_recovery.inc"
default rel
extern sim_entities,sim_aircraft,sim_count
section .rodata
home: dd AIR_RECOVERY_HOME_X
world_edge: dd 8000.0
front_spacing: dd AIR_RECOVERY_FRONT_SPACING
section .text
global air_recovery_goal
; EDI owned physical aircraft ID. EAX1/XMM0X/XMM1Z goal; EAX0 preservesXMM0/1.
; Read-only: current own condition, never another body or private target cache.
air_recovery_goal:
 cmp edi,[sim_count]
 jae .none
 cmp edi,ENTITY_CAPACITY
 jae .none
 mov eax,edi
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 cmp dword [r8+ENTITY_HP],0
 je .none
 cmp dword [r8+ENTITY_KIND],3
 jne .none
 cmp dword [r8+ENTITY_SIDE],1
 ja .none
 cmp dword [r8+ENTITY_FRONT],2
 ja .none
 mov eax,edi
 shl eax,6
 lea r9,[sim_aircraft]
 add r9,rax
 mov eax,[r8+ENTITY_GENERATION]
 test eax,eax
 jz .none
 cmp eax,[r9+AIR_GENERATION]
 jne .none
 test dword [r9+AIR_FLAGS],AIR_ACTIVE
 jz .none
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 ja .none
 cmp dword [r8+ENTITY_HP],AIR_RECOVERY_CRITICAL_HP
 jbe .goal
 cmp dword [r9+AIR_AMMO],0
 jne .none
.goal:
 movss xmm0,[home]
 cmp dword [r8+ENTITY_SIDE],0
 je .front
 movss xmm0,[world_edge]
 subss xmm0,[home]
.front:
 mov eax,[r8+ENTITY_FRONT]
 inc eax
 cvtsi2ss xmm1,eax
 mulss xmm1,[front_spacing]
 mov eax,1
 ret
.none:
 xor eax,eax
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
