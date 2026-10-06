; Persistent observed, finite-support ground assault coordination.
%include "schemas/entity.inc"
%include "schemas/company_assault.inc"
%include "schemas/combat.inc"
default rel
extern company_control_init,company_control_hash
extern sim_entities,sim_count,sim_tick_count,ai_fronts,sim_shell_ammo,sim_projectiles
section .bss align=64
global company_plans
company_plans: resb COMPANY_SLOTS*COMPANY_STRIDE
section .rodata
zero: dd 0.0
one: dd 1.0
maximum: dd 8000.0
near2: dd COMPANY_NEAR_SQ
stage_distance: dd COMPANY_STAGE_DISTANCE
arty_back: dd COMPANY_ARTY_BACK
armour_forward: dd COMPANY_ARMOUR_FORWARD
ready2: dd COMPANY_READY_SQ
withdraw_distance: dd COMPANY_WITHDRAW_DISTANCE
lanes: dd COMPANY_INF_LANE,COMPANY_ARMOUR_LANE,COMPANY_ARTY_LANE
inf_spacing: dd COMPANY_INF_SPACING
row_spacing: dd COMPANY_INF_ROW,COMPANY_HULL_ROW,COMPANY_HULL_ROW
section .text
global company_init,company_tick,company_goal,company_hash
company_init:
 lea rdi,[company_plans]
 xor eax,eax
 mov ecx,COMPANY_SLOTS*COMPANY_STRIDE/8
 rep stosq
 jmp company_control_init
; EDI actor; EAX key or-1. Validated own actor fields only.
key:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 cmp edi,[sim_count]
 jae .bad
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .bad
 cmp dword [rdx+ENTITY_GENERATION],0
 je .bad
 cmp dword [rdx+ENTITY_KIND],2
 ja .bad
 mov eax,[rdx+ENTITY_SIDE]
 cmp eax,1
 ja .bad
 imul eax,3
 mov ecx,[rdx+ENTITY_FRONT]
 cmp ecx,2
 ja .bad
 add eax,ecx
 shl eax,8
 mov ecx,edi
 shr ecx,7
 add eax,ecx
 ret
.bad:
 mov eax,-1
 ret
; R13 plan, RBX actor, R12 ID ->XMM0/1 role staging goal.
role_goal:
 movss xmm0,[r13+48]
 movss xmm1,[r13+52]
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,1
 jne .arty
 movss xmm2,[armour_forward]
 jmp .longitudinal
.arty:
 xorps xmm2,xmm2
 cmp eax,2
 jne .longitudinal
 subss xmm2,[arty_back]
.longitudinal:
 movss xmm3,[r13+64]
 mulss xmm3,xmm2
 addss xmm0,xmm3
 mulss xmm2,[r13+68]
 addss xmm1,xmm2
 ; Distinct ranks avoid asking many bodies to occupy one shared point.
 mov ecx,r12d
 and ecx,127
 shr ecx,4
 cvtsi2ss xmm2,ecx
 lea rcx,[row_spacing]
 mulss xmm2,[rcx+rax*4]
 movss xmm3,[r13+64]
 mulss xmm3,xmm2
 subss xmm0,xmm3
 mulss xmm2,[r13+68]
 subss xmm1,xmm2
 lea rcx,[lanes]
 movss xmm2,[rcx+rax*4]
 mov ecx,r12d
 cmp eax,0
 jne .heavy_lane
 test ecx,16
 jmp .lane_sign
.heavy_lane:
 test ecx,1
.lane_sign:
 jnz .rank_lateral
 xorps xmm3,xmm3
 subss xmm3,xmm2
 movaps xmm2,xmm3
.rank_lateral:
 test eax,eax
 jnz .lateral
 mov ecx,r12d
 and ecx,15
 sub ecx,7
 cvtsi2ss xmm3,ecx
 mulss xmm3,[inf_spacing]
 addss xmm2,xmm3
.lateral:
 movss xmm3,[r13+68]
 mulss xmm3,xmm2
 subss xmm0,xmm3
 mulss xmm2,[r13+64]
 addss xmm1,xmm2
 maxss xmm0,[zero]
 minss xmm0,[maximum]
 maxss xmm1,[zero]
 minss xmm1,[maximum]
 ret
company_goal:
 push rbx
 push r12
 push r13
 sub rsp,16
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 mov r12d,edi
 call key
 cmp eax,-1
 je .original
 mov rbx,rdx
 mov ecx,eax
 shr ecx,8
 shl ecx,6
 lea rdx,[ai_fronts]
 cmp dword [rdx+rcx+24],0
 jne .original
 shl eax,7
 lea r13,[company_plans]
 add r13,rax
 mov eax,[r13]
 cmp eax,COMPANY_WITHDRAW
 je .withdrawing
 test r12d,15
 jz .original ; designated scouts still reconnoitre, but also obey withdrawal
 cmp eax,COMPANY_STAGE
 je .staging
 cmp eax,COMPANY_PREP
 je .staging
 cmp eax,COMPANY_ADVANCE
 je .advance
 jmp .original
.withdrawing:
 movss xmm0,[r13+48]
 movss xmm1,[r13+52]
 movss xmm2,[r13+64]
 mulss xmm2,[withdraw_distance]
 subss xmm0,xmm2
 movss xmm2,[r13+68]
 mulss xmm2,[withdraw_distance]
 subss xmm1,xmm2
 maxss xmm0,[zero]
 minss xmm0,[maximum]
 maxss xmm1,[zero]
 minss xmm1,[maximum]
 jmp .out
.staging:
 call role_goal
 jmp .out
.advance:
 movss xmm0,[r13+56]
 movss xmm1,[r13+60]
 jmp .out
.original:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
.out:
 xor eax,eax
 add rsp,16
 pop r13
 pop r12
 pop rbx
 ret
company_tick:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .invalid_count
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 ; Per-update observations are derived from own living actors.
 lea r13,[company_plans]
 mov ecx,COMPANY_SLOTS
.clear:
 mov qword [r13+20],0
 mov qword [r13+28],0
 mov qword [r13+36],0
 mov dword [r13+44],0
 mov qword [r13+88],0
 add r13,COMPANY_STRIDE
 loop .clear
 xor r12d,r12d
.gather:
 cmp r12d,[sim_count]
 jae .projectiles
 mov edi,r12d
 call key
 cmp eax,-1
 je .next_actor
 mov rbx,rdx
 shl eax,7
 lea r13,[company_plans]
 add r13,rax
 movss xmm0,[rbx]
 ucomiss xmm0,[zero]
 jp .next_actor
 jb .next_actor
 ucomiss xmm0,[maximum]
 ja .next_actor
 movss xmm1,[rbx+4]
 ucomiss xmm1,[zero]
 jp .next_actor
 jb .next_actor
 ucomiss xmm1,[maximum]
 ja .next_actor
 inc dword [r13+20]
 addss xmm0,[r13+40]
 movss [r13+40],xmm0
 addss xmm1,[r13+44]
 movss [r13+44],xmm1
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,2
 jne .nonscout
 inc dword [r13+32]
 lea rdx,[sim_shell_ammo]
 mov eax,[rdx+r12*4]
 add [r13+88],eax
 jmp .readiness
.nonscout:
 test r12d,15
 jz .next_actor
 lea rdx,[r13+24]
 inc dword [rdx+rax*4]
.readiness:
 cmp dword [r13],COMPANY_STAGE
 jb .next_actor
 call role_goal
 subss xmm0,[rbx]
 subss xmm1,[rbx+4]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[ready2]
 ja .next_actor
 cmp dword [rbx+ENTITY_KIND],2
 je .arty_ready
 inc dword [r13+36]
 jmp .next_actor
.arty_ready:
 inc dword [r13+92]
.next_actor:
 inc r12d
 jmp .gather
.projectiles:
 ; Observe actual finite-store artillery projectiles, never cosmetic events.
 xor r14d,r14d
 lea r15,[sim_projectiles]
.shot:
 test dword [r15+PROJECTILE_ACTIVE],1
 jz .next_shot
 cmp dword [r15+PROJECTILE_KIND],2
 jne .next_shot
 mov edi,[r15+PROJECTILE_SOURCE]
 mov [rsp],edi
 call key
 cmp eax,-1
 je .next_shot
 cmp dword [rdx+ENTITY_KIND],2
 jne .next_shot
 mov ecx,[rdx+ENTITY_GENERATION]
 cmp [r15+PROJECTILE_SOURCE_GENERATION],ecx
 jne .next_shot
 mov ecx,[rdx+ENTITY_SIDE]
 cmp [r15+PROJECTILE_SIDE],ecx
 jne .next_shot
 mov ecx,[r15+PROJECTILE_TTL]
 test ecx,ecx
 jz .next_shot
 cmp ecx,240
 ja .next_shot
 shl eax,7
 lea r13,[company_plans]
 add r13,rax
 cmp dword [r13],COMPANY_STAGE
 jb .next_shot
 cmp dword [r13],COMPANY_PREP
 ja .next_shot
 mov eax,240
 sub eax,ecx
 mov ecx,[sim_tick_count]
 sub ecx,eax
 cmp ecx,[r13+80]
 jb .next_shot
 mov [r13+72],ecx
.next_shot:
 add r15,PROJECTILE_STRIDE
 inc r14d
 cmp r14d,PROJECTILE_CAPACITY
 jb .shot
 xor r12d,r12d
 lea r13,[company_plans]
.evaluate:
 mov eax,r12d
 shr eax,8
 shl eax,6
 lea rbp,[ai_fronts]
 add rbp,rax
 cmp dword [rbp+24],0
 jne .cancel
 mov eax,[rbp+20]
 cmp eax,[r13+4]
 jne .new_objective
 cmp dword [r13],COMPANY_IDLE
 je .start
 jmp .existing
.new_objective:
 mov [r13+4],eax
 mov dword [r13],COMPANY_IDLE
 mov dword [r13+72],0
.start:
 cmp dword [r13+20],COMPANY_MIN_GROUND
 jb .next_plan
 cmp dword [r13+24],0
 je .next_plan
 cmp dword [r13+28],0
 je .next_plan
 cmp dword [r13+32],0
 je .next_plan
 cmp dword [r13+88],0
 je .next_plan
 cmp dword [rbp+52],0
 je .next_plan
 cmp dword [rbp+16],2
 je .next_plan
 cvtsi2ss xmm2,[r13+20]
 movss xmm0,[r13+40]
 divss xmm0,xmm2
 movss xmm1,[r13+44]
 divss xmm1,xmm2
 movss xmm3,[rbp+44]
 subss xmm3,xmm0
 movss xmm4,[rbp+48]
 subss xmm4,xmm1
 movaps xmm5,xmm3
 mulss xmm5,xmm5
 movaps xmm6,xmm4
 mulss xmm6,xmm6
 addss xmm5,xmm6
 ucomiss xmm5,[near2]
 ja .next_plan
 ucomiss xmm5,[one]
 jb .next_plan
 sqrtss xmm5,xmm5
 divss xmm3,xmm5
 divss xmm4,xmm5
 movss [r13+64],xmm3
 movss [r13+68],xmm4
 movss xmm0,[rbp+44]
 movss xmm1,[rbp+48]
 movss [r13+56],xmm0
 movss [r13+60],xmm1
 mulss xmm3,[stage_distance]
 mulss xmm4,[stage_distance]
 subss xmm0,xmm3
 subss xmm1,xmm4
 maxss xmm0,[zero]
 minss xmm0,[maximum]
 maxss xmm1,[zero]
 minss xmm1,[maximum]
 movss [r13+48],xmm0
 movss [r13+52],xmm1
 mov eax,[r13+20]
 mov [r13+16],eax
 inc dword [r13+8]
 mov dword [r13+72],0
 mov eax,[sim_tick_count]
 mov [r13+80],eax
 mov eax,COMPANY_STAGE
 mov edx,1
 jmp .phase
.existing:
 cmp dword [r13],COMPANY_WITHDRAW
 je .next_plan
 cmp dword [rbp+16],2
 je .loss
 mov eax,[r13+20]
 imul eax,100
 mov ecx,[r13+16]
 imul ecx,100-COMPANY_LOSS_PERCENT
 cmp eax,ecx
 jb .loss
 mov ecx,[sim_tick_count]
 sub ecx,[r13+12]
 cmp dword [r13],COMPANY_STAGE
 je .stage
 cmp dword [r13],COMPANY_PREP
 jne .next_plan
 cmp dword [r13+72],0
 jne .advance
 cmp dword [r13+88],0
 je .empty
 cmp ecx,COMPANY_PREP_TIMEOUT
 jae .support_timeout
 jmp .next_plan
.stage:
 mov eax,[r13+24]
 add eax,[r13+28]
 imul eax,2
 mov edx,[r13+36]
 imul edx,3
 cmp edx,eax
 jb .stage_deadline
 cmp dword [r13+92],0
 je .stage_deadline
 mov eax,COMPANY_PREP
 mov edx,2
 jmp .phase
.stage_deadline:
 cmp ecx,COMPANY_STAGE_TIMEOUT
 jb .next_plan
 mov edx,6
 jmp .withdraw
.advance:
 mov eax,COMPANY_ADVANCE
 mov edx,3
 jmp .phase
.loss:
 mov edx,4
 jmp .withdraw
.empty:
 mov edx,7
 jmp .withdraw
.support_timeout:
 mov edx,5
.withdraw:
 mov eax,COMPANY_WITHDRAW
.phase:
 mov [r13],eax
 mov [r13+76],edx
 mov eax,[sim_tick_count]
 mov [r13+12],eax
 jmp .next_plan
.cancel:
 mov dword [r13],COMPANY_IDLE
 mov dword [r13+72],0
.next_plan:
 add r13,COMPANY_STRIDE
 inc r12d
 cmp r12d,COMPANY_SLOTS
 jb .evaluate
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
.invalid_count:
 ret
company_hash:
 lea rsi,[company_plans]
 mov ecx,COMPANY_SLOTS*COMPANY_STRIDE
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .loop
 jmp company_control_hash
section .note.GNU-stack noalloc noexec nowrite progbits
