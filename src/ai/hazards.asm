; Bounded camera-independent observation of actual incoming explosives.
%include "schemas/entity.inc"
%include "schemas/combat.inc"
%include "schemas/hazard.inc"
default rel
extern sim_count,sim_entities,sim_tick_count,sim_projectiles
extern vehicle_entity_driver,terrain_height,world_los,hazard_choose_goal
section .data
global hazard_enabled
hazard_enabled: dd 1
section .bss align=64
global hazards,hazard_states,hazard_metrics
hazards: resb HAZARD_CAPACITY*HAZARD_STRIDE
hazard_states: resb ENTITY_CAPACITY*HAZARD_STATE_STRIDE
hazard_metrics: resq 8
tile_counts: resd HAZARD_TILE_COUNT
tile_items: resd HAZARD_TILE_COUNT*HAZARD_TILE_CAPACITY
section .rodata
zero: dd 0.0
one: dd 1.0
halfgravity: dd 0.00545
maximum: dd 8000.0
cellscale: dd 0.004
margin: dd 20.0
maxradius: dd 50.0
range2: dd 90000.0
eye: dd 2.0
section .text
global hazard_init,hazard_tick,hazard_query,hazard_entity_goal,hazard_hash
hazard_init:
 lea rdi,[hazards]
 xor eax,eax
 mov ecx,(HAZARD_CAPACITY*HAZARD_STRIDE+ENTITY_CAPACITY*HAZARD_STATE_STRIDE+64+HAZARD_TILE_COUNT*4+HAZARD_TILE_COUNT*HAZARD_TILE_CAPACITY*4)/4
 rep stosd
 mov dword [hazard_enabled],1
 ret
; Rebuild derived predictions and tile lists. No opponent/entity reads here.
hazard_tick:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,104
 lea rdi,[hazards]
 xor eax,eax
 mov ecx,HAZARD_CAPACITY*HAZARD_STRIDE/4
 rep stosd
 lea rdi,[tile_counts]
 mov ecx,HAZARD_TILE_COUNT
 rep stosd
 mov qword [hazard_metrics+56],0
 cmp dword [hazard_enabled],1
 jne .clear_all
 mov dword [rsp+64],0
.predict:
 mov r12d,[rsp+64]
 add r12d,[sim_tick_count]
 and r12d,HAZARD_CAPACITY-1
 mov eax,r12d
 shl eax,6
 lea rbx,[sim_projectiles]
 add rbx,rax
 lea rbp,[hazards]
 add rbp,rax
 cmp dword [rbx+PROJECTILE_ACTIVE],1
 jne .next_prediction
 mov eax,[rbx+PROJECTILE_KIND]
 sub eax,2
 cmp eax,1
 ja .next_prediction
 cmp dword [rbx+PROJECTILE_SIDE],1
 ja .next_prediction
 cmp dword [rbx+PROJECTILE_GENERATION],0
 je .next_prediction
 cmp dword [rbx+PROJECTILE_TTL],0
 je .next_prediction
 ; Reject non-finite positions, velocities and radius before float arithmetic.
 xor ecx,ecx
.finite:
 mov eax,[rbx+rcx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .next_prediction
 inc ecx
 cmp ecx,6
 jb .finite
 mov eax,[rbx+PROJECTILE_RADIUS]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .next_prediction
 movss xmm0,[rbx+PROJECTILE_RADIUS]
 comiss xmm0,[zero]
 jbe .next_prediction
 comiss xmm0,[maxradius]
 ja .next_prediction
 mov r13d,[rbx+PROJECTILE_TTL]
 cmp r13d,120
 jbe .ttl_ready
 mov r13d,120
.ttl_ready:
 xor r14d,r14d
.sample:
 add r14d,4
 cmp r14d,r13d
 jbe .sample_ready
 mov r14d,r13d
.sample_ready:
 call .trajectory
 test eax,eax
 jz .next_prediction
 comiss xmm2,xmm0
 jbe .refine
 cmp r14d,r13d
 jb .sample
 jmp .next_prediction
.refine:
 mov r15d,r14d
 sub r14d,4
 jns .refine_loop
 xor r14d,r14d
.refine_loop:
 inc r14d
 call .trajectory
 test eax,eax
 jz .next_prediction
 comiss xmm2,xmm0
 jbe .store
 cmp r14d,r15d
 jb .refine_loop
 jmp .next_prediction
.store:
 mov eax,[rsp]
 mov [rbp+HAZARD_IMPACT_X],eax
 mov eax,[rsp+4]
 mov [rbp+HAZARD_IMPACT_Z],eax
 mov eax,[rbx+PROJECTILE_RADIUS]
 mov [rbp+HAZARD_RADIUS],eax
 mov eax,[rbx+PROJECTILE_SIDE]
 mov [rbp+HAZARD_SIDE],eax
 mov eax,[rbx+PROJECTILE_X]
 mov [rbp+HAZARD_X],eax
 mov eax,[rbx+PROJECTILE_Y]
 mov [rbp+HAZARD_Y],eax
 mov eax,[rbx+PROJECTILE_Z]
 mov [rbp+HAZARD_Z],eax
 mov [rbp+HAZARD_PROJECTILE],r12d
 mov eax,[rbx+PROJECTILE_GENERATION]
 mov [rbp+HAZARD_PROJECTILE_GENERATION],eax
 mov eax,[rbx+PROJECTILE_KIND]
 mov [rbp+HAZARD_KIND],eax
 cvtsi2ss xmm0,r14d
 movss [rbp+HAZARD_ETA],xmm0
 mov dword [rbp+HAZARD_ACTIVE],1
 inc qword [hazard_metrics]
 ; Radius <=50 plus20m margin: at most four250m tiles (nine upper bound).
 movss xmm4,[rbp+HAZARD_RADIUS]
 addss xmm4,[margin]
 movss xmm0,[rbp]
 subss xmm0,xmm4
 call .tilecoord
 mov [rsp+16],eax
 movss xmm0,[rbp]
 addss xmm0,xmm4
 call .tilecoord
 mov [rsp+20],eax
 movss xmm0,[rbp+4]
 subss xmm0,xmm4
 call .tilecoord
 mov [rsp+24],eax
 movss xmm0,[rbp+4]
 addss xmm0,xmm4
 call .tilecoord
 mov [rsp+28],eax
 mov r14d,[rsp+24]
.tile_z:
 mov r15d,[rsp+16]
.tile_x:
 mov eax,r14d
 shl eax,5
 add eax,r15d
 lea rdx,[tile_counts]
 mov ecx,[rdx+rax*4]
 cmp ecx,8
 jb .append
 inc qword [hazard_metrics+8]
 ; Rotating deterministic replacement prevents fixed low-index monopoly.
 mov ecx,r12d
 add ecx,[sim_tick_count]
 and ecx,7
 jmp .insert
.append:
 inc dword [rdx+rax*4]
.insert:
 shl eax,3
 add eax,ecx
 lea rdx,[tile_items]
 mov [rdx+rax*4],r12d
 inc r15d
 cmp r15d,[rsp+20]
 jbe .tile_x
 inc r14d
 cmp r14d,[rsp+28]
 jbe .tile_z
.next_prediction:
 inc dword [rsp+64]
 cmp dword [rsp+64],HAZARD_CAPACITY
 jb .predict
 ; Persistent goal commitments, with stable eight-phase perception budget.
 cmp dword [sim_count],0
 je .done
 mov eax,[sim_tick_count]
 shr eax,3
 shl eax,7
 xor edx,edx
 div dword [sim_count]
 mov r12d,edx
 mov dword [rsp+68],0
 mov dword [rsp+32],1024
.entity:
 mov eax,[rsp+68]
 cmp eax,[sim_count]
 jae .done
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 lea rbp,[hazard_states]
 add rbp,rax
 cmp dword [rbx+ENTITY_HP],0
 je .clear_state
 cmp dword [rbx+ENTITY_KIND],3
 jae .clear_state
 lea rax,[vehicle_entity_driver]
 cmp dword [rax+r12*4],-1
 jne .clear_state
 mov eax,[rbx+ENTITY_GENERATION]
 cmp eax,[rbp]
 jne .clear_state
 mov eax,[sim_tick_count]
 sub eax,[rbp+HAZARD_STATE_UNTIL]
 js .committed
 mov eax,r12d
 add eax,[sim_tick_count]
 and eax,7
 jnz .next_entity
 cmp dword [rsp+32],8
 jb .skip
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 call terrain_height
 addss xmm0,[eye]
 movaps xmm1,xmm0
 movss xmm0,[rbx+ENTITY_X]
 movss xmm2,[rbx+ENTITY_Z]
 mov edi,[rbx+ENTITY_SIDE]
 call hazard_query
 sub [rsp+32],edx
 add [hazard_metrics+40],rdx
 cmp eax,-1
 je .next_entity
 mov [rsp+36],eax
 movss [rsp+40],xmm0
 movss [rsp+44],xmm1
 mov edi,r12d
 call hazard_choose_goal
 test eax,eax
 jnz .next_entity
 movss [rbp+HAZARD_STATE_GOAL_X],xmm0
 movss [rbp+HAZARD_STATE_GOAL_Z],xmm1
 mov eax,[rbx+ENTITY_GENERATION]
 mov [rbp],eax
 mov eax,[sim_tick_count]
 add eax,40
 mov [rbp+HAZARD_STATE_UNTIL],eax
 mov eax,[rsp+40]
 mov [rbp+HAZARD_STATE_CENTER_X],eax
 mov eax,[rsp+44]
 mov [rbp+HAZARD_STATE_CENTER_Z],eax
 mov eax,[rsp+36]
 mov [rbp+HAZARD_STATE_PROJECTILE],eax
 shl eax,6
 lea rcx,[hazards]
 mov eax,[rcx+rax+HAZARD_PROJECTILE_GENERATION]
 mov [rbp+HAZARD_STATE_PROJECTILE_GENERATION],eax
 inc qword [hazard_metrics+16]
 cmp edx,2
 je .shelter
 inc qword [hazard_metrics+24]
 jmp .committed
.shelter:
 inc qword [hazard_metrics+32]
.committed:
 inc qword [hazard_metrics+56]
 jmp .next_entity
.skip:
 inc qword [hazard_metrics+48]
 jmp .next_entity
.clear_state:
 mov eax,[rbx+ENTITY_GENERATION]
 mov [rbp],eax
 mov qword [rbp+4],0
 mov qword [rbp+12],0
 mov qword [rbp+20],0
 mov dword [rbp+28],0
.next_entity:
 inc dword [rsp+68]
 inc r12d
 cmp r12d,[sim_count]
 jb .entity
 xor r12d,r12d
 jmp .entity
.clear_all:
 lea rdi,[hazard_states]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*HAZARD_STATE_STRIDE/4
 rep stosd
.done:
 add rsp,104
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
; Internal sample helper retains trajectoryY across terrain_height call.
.trajectory:
 cvtsi2ss xmm3,r14d
 movss xmm0,[rbx+PROJECTILE_VX]
 mulss xmm0,xmm3
 addss xmm0,[rbx+PROJECTILE_X]
 movss [rsp+8],xmm0
 movss xmm1,[rbx+PROJECTILE_VZ]
 mulss xmm1,xmm3
 addss xmm1,[rbx+PROJECTILE_Z]
 movss [rsp+12],xmm1
 movss xmm2,[rbx+PROJECTILE_VY]
 mulss xmm2,xmm3
 addss xmm2,[rbx+PROJECTILE_Y]
 movaps xmm4,xmm3
 subss xmm4,[one]
 mulss xmm4,xmm3
 mulss xmm4,[halfgravity]
 subss xmm2,xmm4
 movss [rsp+16],xmm2
 movd eax,xmm2
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .outside
 comiss xmm0,[zero]
 jb .outside
 comiss xmm0,[maximum]
 ja .outside
 comiss xmm1,[zero]
 jb .outside
 comiss xmm1,[maximum]
 ja .outside
 sub rsp,8
 call terrain_height
 add rsp,8
 movss xmm2,[rsp+16]
 mov eax,1
 ret
.outside:
 xor eax,eax
 ret
.tilecoord:
 mulss xmm0,[cellscale]
 cvttss2si eax,xmm0
 cmp eax,0
 jge .tilepositive
 xor eax,eax
.tilepositive:
 cmp eax,31
 jle .tile_return
 mov eax,31
.tile_return: ret
; Read-only local visibility query. Camera and players are never consulted.
hazard_query:
 push rbx
 push rbp
 push r12
 push r13
 sub rsp,72
 mov [rsp],edi
 movss [rsp+4],xmm0
 movss [rsp+8],xmm1
 movss [rsp+12],xmm2
 mov dword [rsp+16],0
 cmp dword [hazard_enabled],1
 jne .miss
 cmp edi,1
 ja .miss
 xor ecx,ecx
.qfinite:
 mov eax,[rsp+4+rcx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .miss
 inc ecx
 cmp ecx,3
 jb .qfinite
 comiss xmm0,[zero]
 jb .miss
 comiss xmm0,[maximum]
 ja .miss
 comiss xmm2,[zero]
 jb .miss
 comiss xmm2,[maximum]
 ja .miss
 mulss xmm0,[cellscale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .qx
 mov eax,31
.qx:
 mulss xmm2,[cellscale]
 cvttss2si ecx,xmm2
 cmp ecx,31
 jbe .qz
 mov ecx,31
.qz:
 shl ecx,5
 add eax,ecx
 lea rcx,[tile_counts]
 mov r13d,[rcx+rax*4]
 cmp r13d,8
 ja .miss
 shl eax,5
 lea rbp,[tile_items]
 add rbp,rax
 xor r12d,r12d
.candidate:
 cmp r12d,r13d
 jae .miss
 mov eax,[rbp+r12*4]
 cmp eax,HAZARD_CAPACITY
 jae .qnext
 mov [rsp+20],eax
 shl eax,6
 lea rbx,[hazards]
 add rbx,rax
 cmp dword [rbx+HAZARD_ACTIVE],1
 jne .qnext
 mov eax,[rbx+HAZARD_SIDE]
 cmp eax,[rsp]
 je .qnext
 mov ecx,[rbx+HAZARD_PROJECTILE]
 cmp ecx,HAZARD_CAPACITY
 jae .qnext
 shl ecx,6
 lea rdx,[sim_projectiles]
 add rdx,rcx
 cmp dword [rdx+PROJECTILE_ACTIVE],1
 jne .qnext
 cmp dword [rdx+PROJECTILE_TTL],0
 je .qnext
 mov eax,[rdx+PROJECTILE_GENERATION]
 cmp eax,[rbx+HAZARD_PROJECTILE_GENERATION]
 jne .qnext
 mov eax,[rdx+PROJECTILE_SIDE]
 cmp eax,[rbx+HAZARD_SIDE]
 jne .qnext
 mov eax,[rdx+PROJECTILE_KIND]
 cmp eax,[rbx+HAZARD_KIND]
 jne .qnext
 xor ecx,ecx
.current_finite:
 mov eax,[rdx+rcx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .qnext
 inc ecx
 cmp ecx,6
 jb .current_finite
 mov eax,[rdx+PROJECTILE_RADIUS]
 cmp eax,[rbx+HAZARD_RADIUS]
 jne .qnext
 ; Danger proximity concerns estimated impact, perception current projectile.
 movss xmm0,[rbx+HAZARD_IMPACT_X]
 subss xmm0,[rsp+4]
 mulss xmm0,xmm0
 movss xmm1,[rbx+HAZARD_IMPACT_Z]
 subss xmm1,[rsp+12]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movss xmm1,[rbx+HAZARD_RADIUS]
 addss xmm1,[margin]
 mulss xmm1,xmm1
 comiss xmm0,xmm1
 ja .qnext
 movss xmm3,[rdx+PROJECTILE_X]
 movss xmm4,[rdx+PROJECTILE_Y]
 movss xmm5,[rdx+PROJECTILE_Z]
 movaps xmm0,xmm3
 subss xmm0,[rsp+4]
 mulss xmm0,xmm0
 movaps xmm1,xmm4
 subss xmm1,[rsp+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movaps xmm1,xmm5
 subss xmm1,[rsp+12]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[range2]
 ja .qnext
 movss xmm0,[rsp+4]
 movss xmm1,[rsp+8]
 movss xmm2,[rsp+12]
 inc dword [rsp+16]
 call world_los
 test eax,eax
 jz .qnext
 mov eax,[rsp+20]
 movss xmm0,[rbx+HAZARD_IMPACT_X]
 movss xmm1,[rbx+HAZARD_IMPACT_Z]
 movss xmm2,[rbx+HAZARD_RADIUS]
 movss xmm3,[rbx+HAZARD_ETA]
 jmp .qreturn
.qnext:
 inc r12d
 jmp .candidate
.miss:
 mov eax,-1
.qreturn:
 mov edx,[rsp+16]
 add rsp,72
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
hazard_entity_goal:
 xor eax,eax
 cmp dword [hazard_enabled],1
 jne .return
 cmp edi,[sim_count]
 jae .return
 mov ecx,edi
 shl ecx,5
 lea rdx,[sim_entities]
 add rdx,rcx
 cmp dword [rdx+ENTITY_HP],0
 je .return
 cmp dword [rdx+ENTITY_KIND],3
 jae .return
 lea rsi,[vehicle_entity_driver]
 cmp dword [rsi+rdi*4],-1
 jne .return
 lea rsi,[hazard_states]
 add rsi,rcx
 mov ecx,[rdx+ENTITY_GENERATION]
 cmp ecx,[rsi+HAZARD_STATE_GENERATION]
 jne .return
 mov ecx,[sim_tick_count]
 sub ecx,[rsi+HAZARD_STATE_UNTIL]
 jns .return
 movss xmm0,[rsi+HAZARD_STATE_GOAL_X]
 movss xmm1,[rsi+HAZARD_STATE_GOAL_Z]
 mov eax,1
.return: ret
; Existing FNV stream ABI RAX accumulator,R8 multiplier. Derived caches and
; diagnostics excluded. Entire initialized live-world sidecar range included.
hazard_hash:
 lea rsi,[hazard_enabled]
 mov ecx,4
.enabled_hash:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .enabled_hash
 lea rsi,[hazard_states]
 mov ecx,[sim_count]
 shl ecx,5
 test ecx,ecx
 jz .hash_done
.state_hash:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .state_hash
.hash_done: ret
section .note.GNU-stack noalloc noexec nowrite progbits
