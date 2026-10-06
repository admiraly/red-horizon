; Stateless effective resupply destination; never credits, moves or rewrites plans.
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/company_control.inc"
%include "schemas/company_assault.inc"
%include "schemas/depot_ammunition.inc"
%include "schemas/infantry_supply_route.inc"
default rel
extern sim_entities,sim_sites,depot_ammunition,company_controls,ai_fronts,company_plans
extern infantry_weapon_rounds,company_for_player
section .rodata
zero: dd 0.0
maximum: dd 8000.0
radius2: dd INFANTRY_SUPPLY_ROUTE_RADIUS_SQ
section .text
global infantry_supply_goal
; EDI moving actor ->EAX physical site0..11,XMM0/1XZ, or-1 no detour.
; Caller retains primary goal and resolves hazard/hold/retreat precedence.
; Valid human command must be advance; autonomous withdrawal cannot be diverted.
; Living/gen-matching valid low stock; source eligibility is current authority.
infantry_supply_goal:
 push rbx
 push r12
 push r13
 sub rsp,16
 mov r12d,edi
 call infantry_weapon_rounds
 cmp eax,INFANTRY_SUPPLY_ROUTE_LOW
 ja .none
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 mov eax,[rbx+ENTITY_SIDE]
 imul eax,3
 add eax,[rbx+ENTITY_FRONT]
 mov r13d,eax
 shl eax,8
 mov edx,r12d
 shr edx,7
 add eax,edx
 mov [rsp],eax
 shl eax,5
 lea rdx,[company_controls]
 add rdx,rax
 mov edi,[rdx]
 cmp edi,COMPANY_CONTROL_PLAYERS
 jae .autonomous
 call company_for_player
 cmp eax,[rsp]
 jne .autonomous
 mov ecx,[rdx+PLAYER_FRONT]
 cmp ecx,[rbx+ENTITY_FRONT]
 jne .autonomous
 mov eax,[rsp]
 shl eax,5
 lea rdx,[company_controls]
 add rdx,rax
 cmp dword [rdx+12],1
 jne .autonomous
 cmp dword [rdx+8],0
 jne .none
 jmp .position
.autonomous:
 mov eax,r13d
 shl eax,6
 lea rdx,[ai_fronts]
 add rdx,rax
 cmp dword [rdx+24],0
 jne .position ; explicit front advance caller already rejects hold/retreat
 cmp dword [rdx+16],2
 je .none
 mov eax,[rsp]
 shl eax,7
 lea rdx,[company_plans]
 cmp dword [rdx+rax],COMPANY_WITHDRAW
 je .none
.position:
 movss xmm2,[rbx]
 ucomiss xmm2,[zero]
 jp .none
 jb .none
 ucomiss xmm2,[maximum]
 ja .none
 movss xmm3,[rbx+4]
 ucomiss xmm3,[zero]
 jp .none
 jb .none
 ucomiss xmm3,[maximum]
 ja .none
 lea rdx,[sim_sites]
 lea rsi,[depot_ammunition]
 xor ecx,ecx
 movss xmm4,[radius2]
 mov r8d,-1
.scan:
 mov eax,[rbx+ENTITY_SIDE]
 cmp [rdx+8],eax
 jne .next
 cmp dword [rdx+16],1
 jne .next
 cmp dword [rdx+20],1
 jne .next
 cmp dword [rdx+24],0
 je .next
 test dword [rdx+28],4
 jnz .next
 cmp dword [rsi+8],DEPOT_AMMUNITION_INITIAL
 jne .next
 cmp dword [rsi+12],0
 jne .next
 cmp dword [rsi],0
 je .next
 cmp dword [rsi],DEPOT_AMMUNITION_INITIAL
 ja .next
 cmp dword [rsi+4],DEPOT_AMMUNITION_INITIAL
 ja .next
 mov eax,[rsi]
 add eax,[rsi+4]
 cmp eax,DEPOT_AMMUNITION_INITIAL
 jne .next
 movss xmm5,[rdx]
 ucomiss xmm5,[zero]
 jp .next
 jb .next
 ucomiss xmm5,[maximum]
 ja .next
 movss xmm6,[rdx+4]
 ucomiss xmm6,[zero]
 jp .next
 jb .next
 ucomiss xmm6,[maximum]
 ja .next
 subss xmm5,xmm2
 subss xmm6,xmm3
 mulss xmm5,xmm5
 mulss xmm6,xmm6
 addss xmm5,xmm6
 ucomiss xmm5,xmm4
 ja .next
 ; Stable physical-ID tie, no faction order weighting.
 jne .chosen
 cmp r8d,-1
 jne .next
.chosen:
 mov r8d,ecx
 movss xmm4,xmm5
 mov r9,rdx
.next:
 inc ecx
 add rdx,32
 add rsi,DEPOT_AMMUNITION_STRIDE
 cmp ecx,DEPOT_AMMUNITION_SITES
 jb .scan
 cmp r8d,-1
 je .none
 movss xmm0,[r9]
 movss xmm1,[r9+4]
 mov eax,r8d
 jmp .done
.none:
 mov eax,-1
.done:
 add rsp,16
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
