; Bounded visible-human arbitration against an already visible army target.
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/infantry_weapon.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,sim_players,sim_player_vehicle
extern sim_entity_height,world_los,infantry_weapon_shot,player_apply_damage,infantry_aim_mark
section .rodata
zero: dd 0.0
maximum: dd 8000.0
min_y: dd -2000.0
max_y: dd 2000.0
range_sq: dd INFANTRY_HUMAN_RANGE_SQ
one: dd 1.0
section .text
global infantry_human_fire
; EDI infantry ID,ESI already acquired visible army ID or-1. Actor's8tick phase.
; 1 human selected (including unavailable finite weapon),0 retain army/no human,
; -1 invalid. No target memory, birth, pose or stock renewal. At most4 extra LOS.
infantry_human_fire:
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,32
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 cmp edi,[sim_count]
 jae .bad
 mov r12d,edi
 mov r13d,esi
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_KIND],0
 jne .none
 cmp dword [rbx+ENTITY_HP],0
 je .none
 cmp dword [rbx+ENTITY_SIDE],1
 jne .none
 cmp dword [rbx+ENTITY_FRONT],2
 ja .bad
 cmp dword [rbx+ENTITY_GENERATION],0
 je .bad
 mov eax,[sim_tick_count]
 add eax,r12d
 test eax,7
 jnz .none
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 call position
 test eax,eax
 jnz .bad
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 mov edi,r12d
 call sim_entity_height
 ucomiss xmm0,[min_y]
 jp .bad
 jb .bad
 ucomiss xmm0,[max_y]
 ja .bad
 movss [rsp+8],xmm0
 movss xmm0,[range_sq]
 addss xmm0,[one]
 movss [rsp+12],xmm0
 cmp r13d,-1
 je .scan_start
 cmp r13d,[sim_count]
 jae .bad
 mov eax,r13d
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .bad
 cmp dword [rdx+ENTITY_SIDE],0
 jne .bad
 cmp dword [rdx+ENTITY_KIND],2
 ja .bad
 cmp dword [rdx+ENTITY_GENERATION],0
 je .bad
 movss xmm0,[rdx+ENTITY_X]
 movss xmm1,[rdx+ENTITY_Z]
 call position
 test eax,eax
 jnz .bad
 subss xmm0,[rsp]
 subss xmm1,[rsp+4]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 minss xmm0,[rsp+12]
 movss [rsp+12],xmm0
.scan_start:
 mov r14d,-1
 xor r13d,r13d
 mov r15d,[sim_tick_count]
 shr r15d,3
 add r15d,r12d
 and r15d,3
.scan:
 mov eax,r15d
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .next
 cmp dword [rbx+PLAYER_HP],0
 je .next
 cmp dword [rbx+PLAYER_HP],100
 ja .next
 cmp dword [rbx+PLAYER_FRONT],2
 ja .next
 cmp dword [rbx+PLAYER_GENERATION],0
 je .next
 lea rdx,[sim_player_vehicle]
 cmp dword [rdx+r15*4],-1
 jne .next
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 call position
 test eax,eax
 jnz .next
 movss xmm2,[rbx+PLAYER_Y]
 ucomiss xmm2,[min_y]
 jp .next
 jb .next
 ucomiss xmm2,[max_y]
 ja .next
 subss xmm0,[rsp]
 subss xmm1,[rsp+4]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[range_sq]
 ja .next
 comiss xmm0,[rsp+12]
 jae .next ; army wins exact army/human tie, rotated humans break human ties
 movss [rsp+16],xmm0
 movss xmm0,[rsp]
 movss xmm1,[rsp+8]
 movss xmm2,[rsp+4]
 movss xmm3,[rbx+PLAYER_X]
 movss xmm4,[rbx+PLAYER_Y]
 movss xmm5,[rbx+PLAYER_Z]
 call world_los
 test eax,eax
 jz .next
 movss xmm0,[rsp+16]
 movss [rsp+12],xmm0
 mov r14d,r15d
.next:
 inc r15d
 and r15d,3
 inc r13d
 cmp r13d,PLAYER_CAPACITY
 jb .scan
 cmp r14d,-1
 je .none
 mov edi,r12d
 mov esi,r14d
 mov edx,1
 call infantry_aim_mark
 mov edi,r12d
 call infantry_weapon_shot
 test eax,eax
 jnz .selected
 mov edi,r14d
 mov esi,INFANTRY_HUMAN_DAMAGE
 mov edx,1
 call player_apply_damage
.selected:
 mov eax,1
 jmp .return
.none:
 xor eax,eax
 jmp .return
.bad:
 mov eax,-1
.return:
 add rsp,32
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
; Read-only finite XZ helper, preserves XMM0/1 and all source pointers.
position:
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 ucomiss xmm1,[zero]
 jp .bad
 jb .bad
 ucomiss xmm1,[maximum]
 ja .bad
 xor eax,eax
 ret
.bad:mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
