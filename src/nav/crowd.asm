; Immutable ground body snapshots and bounded conservative local steering.
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/combat.inc"
%include "schemas/terrain_body.inc"
%include "schemas/crowd.inc"
default rel
%define GRID_SIDE 1001
%define GRID_SIZE (GRID_SIDE*GRID_SIDE)
%define SNAP_SIZE 32
%define LIMIT 512
extern sim_players,sim_player_vehicle,sim_vehicles,vehicle_driver_generation,world_body_step,world_body_blocked
extern sim_entities,sim_count,sim_tick_count,terrain_body_move,world_body_path_clear,vehicle_entity_driver
section .rodata align=16
zero: dd 0.0
one: dd 1.0
maximum: dd 8000.0
cell_scale: dd 0.125
near_sq: dd 64.0
vehicle_near_sq: dd 256.0
epsilon: dd 0.000001
lookahead: dd 12.0
radii: dd BODY_INF_RADIUS,BODY_TANK_RADIUS,BODY_ARTY_RADIUS
steps: dd 0.12,0.5,0.2
driver_step: dd 0.6
hull_roundoff: dd 0.001
body_preview: dd 6.0
human_step: dd 0.3
local_min: dd -8000.0
local_max: dd 16000.0
; Forward, right/left30,60,90,135, and backwards. Goal-relative handedness
; reverses automatically for opposing directions; no side labels are read.
angles:
 dd 1.0,0.0
 dd 0.8660254,0.5
 dd 0.8660254,-0.5
 dd 0.5,0.8660254
 dd 0.5,-0.8660254
 dd 0.0,1.0
 dd 0.0,-1.0
 dd -0.7071068,0.7071068
 dd -0.7071068,-0.7071068
 dd -1.0,0.0
section .bss align=64
global crowd_enabled,crowd_metrics
crowd_enabled: resd 1
crowd_metrics: resq 8
heads: resd GRID_SIZE
occupied: resd ENTITY_CAPACITY
occupied_count: resd 1
snap_count: resd 1
snap_phase: resd 1
; x,z,radius,maxstep,kind,generation,next,reserved
snaps: resb SNAP_SIZE*(ENTITY_CAPACITY+PLAYER_CAPACITY)
section .text
global crowd_init,crowd_begin,crowd_move,crowd_step,crowd_hull_step,crowd_occupied,crowd_hash
crowd_init:
 mov dword [crowd_enabled],1
 mov dword [occupied_count],0
 mov dword [snap_count],0
 lea rdi,[heads]
 mov ecx,GRID_SIZE
 mov eax,-1
 rep stosd
 lea rdi,[snaps]
 mov ecx,SNAP_SIZE*(ENTITY_CAPACITY+PLAYER_CAPACITY)/8
 xor eax,eax
 rep stosq
 lea rdi,[crowd_metrics]
 mov ecx,8
 rep stosq
 ret
crowd_begin:
 mov eax,[sim_tick_count]
 and eax,1
 mov [snap_phase],eax
 push rbx
 push r12
 push r13
 lea rbx,[heads]
 lea rsi,[occupied]
 mov ecx,[occupied_count]
.clear:
 test ecx,ecx
 jz .cleared
 dec ecx
 mov eax,[rsi+rcx*4]
 mov dword [rbx+rax*4],-1
 jmp .clear
.cleared:
 mov dword [occupied_count],0
 lea rdi,[snaps]
 mov ecx,SNAP_SIZE*(ENTITY_CAPACITY+PLAYER_CAPACITY)/8
 xor eax,eax
 rep stosq
 mov eax,[sim_count]
 cmp eax,ENTITY_CAPACITY
 ja .empty
 mov [snap_count],eax
 mov r12d,eax
 lea r13,[sim_entities]
 lea rdi,[snaps]
 xor esi,esi
.actor:
 cmp esi,r12d
 jae .done
 cmp dword [r13+ENTITY_HP],0
 je .next
 mov edx,[r13+ENTITY_KIND]
 cmp edx,2
 ja .next
 mov ecx,[r13+ENTITY_GENERATION]
 test ecx,ecx
 jz .next
 movss xmm0,[r13+ENTITY_X]
 movss xmm1,[r13+ENTITY_Z]
 ucomiss xmm0,[zero]
 jp .next
 jb .next
 ucomiss xmm0,[maximum]
 ja .next
 ucomiss xmm1,[zero]
 jp .next
 jb .next
 ucomiss xmm1,[maximum]
 ja .next
 movss [rdi],xmm0
 movss [rdi+4],xmm1
 lea rax,[radii]
 movss xmm2,[rax+rdx*4]
 movss [rdi+8],xmm2
 lea rax,[steps]
 movss xmm2,[rax+rdx*4]
 cmp edx,1
 jne .ordinary_step
 ; Every tank can retain a 0.6m braking sweep after its driver exits.
 movss xmm2,[driver_step]
.ordinary_step:
 movss [rdi+12],xmm2
 mov [rdi+16],edx
 mov [rdi+20],ecx
 mulss xmm0,[cell_scale]
 mulss xmm1,[cell_scale]
 cvttss2si eax,xmm0
 cvttss2si edx,xmm1
 imul edx,GRID_SIDE
 add eax,edx
 mov edx,[rbx+rax*4]
 mov [rdi+24],edx
 cmp edx,-1
 jne .existing
 mov ecx,[occupied_count]
 lea rdx,[occupied]
 mov [rdx+rcx*4],eax
 inc dword [occupied_count]
.existing:
 mov [rbx+rax*4],esi
 inc qword [crowd_metrics]
.next:
 inc esi
 add r13,ENTITY_STRIDE
 add rdi,SNAP_SIZE
 jmp .actor
.empty: mov dword [snap_count],0
.done:
 xor r12d,r12d
.humans:
 mov edi,r12d
 call human_snapshot
 test eax,eax
 jz .human_not_counted
 inc qword [crowd_metrics]
.human_not_counted:
 inc r12d
 cmp r12d,PLAYER_CAPACITY
 jb .humans
 pop r13
 pop r12
 pop rbx
 ret
; Locals: ID0 kind4 step8 start12/16 goal20/24 unit28/32 endpoint36/40
; segment44/48 len252 radius56 overlap60 candidate64 visits68 cellX72/Z76
; grid scan80/84, neighborhood IDs128..2176. Stack remains 16-byte aligned.
crowd_move:
 xor eax,eax
 jmp crowd_common
crowd_step:
 mov eax,1
 jmp crowd_common
crowd_hull_step:
 mov eax,3
 jmp crowd_common
crowd_occupied:
 mov eax,2
crowd_common:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,2248
 mov [rsp+116],eax
 mov [rsp+120],esi
 mov [rsp],edi
 movss [rsp+8],xmm4
 movss [rsp+12],xmm0
 movss [rsp+16],xmm1
 movss [rsp+20],xmm2
 movss [rsp+24],xmm3
 cmp dword [rsp+116],2
 je .occupancy_source
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .unchanged
 cmp edi,ENTITY_CAPACITY
 jb .army_source
 cmp dword [rsp+116],1
 jne .unchanged
 sub edi,ENTITY_CAPACITY
 cmp edi,PLAYER_CAPACITY
 jae .unchanged
 call human_snapshot
 test eax,eax
 jz .unchanged
 mov r12d,[rsp]
 mov dword [rsp+4],0
 movss xmm4,[rsp+8]
 jmp .source_valid
.army_source:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .unchanged
 cmp edi,[sim_count]
 jae .unchanged
 mov r12d,edi
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .unchanged
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,2
 ja .unchanged
 cmp dword [rsp+116],3
 jne .source_role_ok
 test eax,eax
 jz .unchanged
 cmp dword [rsp+120],1
 ja .unchanged
.source_role_ok:
 mov [rsp+4],eax
 cmp dword [rbx+ENTITY_GENERATION],0
 je .unchanged
 cmp dword [rsp+116],3
 jne .old_driver_mode
 cmp dword [rsp+120],0
 je .source_valid
 jmp .driver_validation
.old_driver_mode:
 cmp dword [rsp+116],1
 jne .source_valid
.driver_validation:
 cmp eax,1
 jne .unchanged
 lea rdx,[vehicle_entity_driver]
 mov edi,[rdx+r12*4]
 cmp edi,PLAYER_CAPACITY
 jae .unchanged
 call boarding
 cmp eax,r12d
 jne .unchanged
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 movss xmm4,[rsp+8]
.source_valid:
 ; All supplied coordinates finite and map-valid. Maxstep finite and positive.
 xor ecx,ecx
.validate:
 movss xmm5,[rsp+12+rcx*4]
 cmp ecx,2
 jb .map_coordinate
 cmp dword [rsp+116],1
 jne .map_coordinate
 ucomiss xmm5,[local_min]
 jp .bad_input
 jb .bad_input
 ucomiss xmm5,[local_max]
 ja .bad_input
 jmp .coordinate_ok
.map_coordinate:
 ucomiss xmm5,[zero]
 jp .bad_input
 jb .bad_input
 ucomiss xmm5,[maximum]
 ja .bad_input
.coordinate_ok:
 inc ecx
 cmp ecx,4
 jb .validate
 ucomiss xmm4,[zero]
 jp .unchanged
 jbe .unchanged
 movd edx,xmm4
 and edx,0x7f800000
 cmp edx,0x7f800000
 je .unchanged
 cmp dword [rsp+116],3
 je .hull_step_cap
 cmp dword [rsp+116],1
 jne .ai_step_cap
 cmp r12d,ENTITY_CAPACITY
 jb .driver_step_cap
 minss xmm4,[human_step]
 jmp .step_clamped
.driver_step_cap:
 minss xmm4,[driver_step]
 jmp .step_clamped
.hull_step_cap:
 cmp dword [rsp+4],1
 je .driver_step_cap
.ai_step_cap:
 lea rcx,[steps]
 mov eax,[rsp+4]
 minss xmm4,[rcx+rax*4]
.step_clamped:
 movss [rsp+8],xmm4
 cmp dword [rsp+116],3
 je .require_snapshot
 cmp dword [crowd_enabled],0
 je .legacy
.require_snapshot:
 cmp r12d,ENTITY_CAPACITY
 jae .source_snapshot
 cmp r12d,[snap_count]
 jae .unchanged
.source_snapshot:
 lea r13,[snaps]
 mov eax,r12d
 shl eax,5
 add r13,rax
 mov eax,[r13+20]
 test eax,eax
 jz .unchanged
 cmp r12d,ENTITY_CAPACITY
 jae .source_human
 cmp eax,[rbx+ENTITY_GENERATION]
 jne .unchanged
 mov eax,[r13+16]
 cmp eax,[rbx+ENTITY_KIND]
 jne .unchanged
 jmp .source_position
.source_human:
 cmp eax,[rbx+PLAYER_GENERATION]
 jne .unchanged
.source_position:
 movss xmm5,[rsp+12]
 ucomiss xmm5,[r13]
 jne .unchanged
 movss xmm5,[rsp+16]
 ucomiss xmm5,[r13+4]
 jne .unchanged
 inc qword [crowd_metrics+8]
 movss xmm5,[r13+8]
 movss [rsp+56],xmm5
 movss xmm2,[rsp+20]
 subss xmm2,[rsp+12]
 movss xmm3,[rsp+24]
 subss xmm3,[rsp+16]
 movaps xmm5,xmm2
 mulss xmm5,xmm5
 movaps xmm6,xmm3
 mulss xmm6,xmm6
 addss xmm5,xmm6
 cmp dword [rsp+116],3
 jne .goal_nonzero_old
 ucomiss xmm5,[zero]
 jbe .unchanged
 jmp .goal_nonzero
.goal_nonzero_old:
 ucomiss xmm5,[epsilon]
 jbe .unchanged
.goal_nonzero:
 sqrtss xmm5,xmm5
 cmp dword [rsp+116],3
 jne .normalize_goal
 ; Exact float endpoint can round by up to two map-coordinate ULPs.
 movaps xmm6,xmm4
 addss xmm6,[hull_roundoff]
 ucomiss xmm5,xmm6
 ja .unchanged
 cmp dword [crowd_enabled],0
 je .hull_terrain
 jmp .query
.normalize_goal:
 movss [rsp+2176],xmm5
 ; Do not overshoot a nearby goal, even for rotated candidates.
 minss xmm4,xmm5
 movss [rsp+8],xmm4
 divss xmm2,xmm5
 divss xmm3,xmm5
 movss [rsp+28],xmm2
 movss [rsp+32],xmm3
.query:
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 mulss xmm0,[cell_scale]
 mulss xmm1,[cell_scale]
 cvttss2si eax,xmm0
 cvttss2si edx,xmm1
 mov [rsp+72],eax
 mov [rsp+76],edx
 mov dword [rsp+100],1
 movss xmm0,[near_sq]
 cmp dword [rsp+4],0
 je .query_span
 mov dword [rsp+100],2
 movss xmm0,[vehicle_near_sq]
.query_span:
 movss [rsp+96],xmm0
 mov eax,[rsp+100]
 neg eax
 mov [rsp+80],eax
 xor r14d,r14d
 mov dword [rsp+68],0
 mov dword [rsp+92],0
 mov dword [rsp+112],0
 mov dword [rsp+124],0
.human_query:
 inc dword [rsp+68]
 mov edi,[rsp+124]
 ; AI retains immutable matching human snapshots; controllers use live bodies.
 cmp dword [rsp+116],3
 jne .old_human_phase
 cmp dword [rsp+120],0
 je .immutable_human
 jmp .refresh_human
.old_human_phase:
 cmp dword [rsp+116],0
 jne .refresh_human
.immutable_human:
 mov eax,edi
 shl eax,5
 lea rbx,[snaps+ENTITY_CAPACITY*SNAP_SIZE]
 add rbx,rax
 lea rdx,[sim_players]
 mov eax,edi
 shl eax,6
 add rdx,rax
 mov eax,[rdx+PLAYER_GENERATION]
 cmp eax,[rbx+20]
 jne .refresh_human
 call human_valid
 jmp .human_ready
.refresh_human:
 call human_snapshot
.human_ready:
 test eax,eax
 jz .human_next
 mov ebp,[rsp+124]
 add ebp,ENTITY_CAPACITY
 cmp ebp,r12d
 je .human_next
 lea rbx,[snaps]
 mov eax,ebp
 shl eax,5
 add rbx,rax
 movss xmm0,[rbx]
 subss xmm0,[rsp+12]
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+16]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[rsp+96]
 ja .human_next
 ucomiss xmm0,[epsilon]
 ja .human_remember
 mov dword [rsp+92],1
 cmp dword [snap_phase],0
 jne .human_lower
 cmp r12d,ebp
 jb .human_yield
 jmp .human_remember
.human_lower:
 cmp r12d,ebp
 jbe .human_remember
.human_yield:
 mov dword [rsp+112],1
.human_remember:
 mov [rsp+128+r14*4],ebp
 inc r14d
.human_next:
 inc dword [rsp+124]
 cmp dword [rsp+124],PLAYER_CAPACITY
 jb .human_query
.cell_z:
 mov eax,[rsp+76]
 add eax,[rsp+80]
 cmp eax,GRID_SIDE
 jae .next_z
 imul eax,GRID_SIDE
 mov [rsp+88],eax
 mov eax,[rsp+100]
 neg eax
 mov [rsp+84],eax
.cell_x:
 mov eax,[rsp+72]
 add eax,[rsp+84]
 cmp eax,GRID_SIDE
 jae .next_x
 add eax,[rsp+88]
 lea rcx,[heads]
 mov ebp,[rcx+rax*4]
.chain:
 cmp ebp,-1
 je .next_x
 cmp ebp,[sim_count]
 jae .next_neighbor
 cmp ebp,r12d
 je .next_neighbor
 cmp dword [rsp+68],LIMIT
 jae .truncated
 inc dword [rsp+68]
 mov eax,ebp
 shl eax,5
 lea rbx,[snaps]
 add rbx,rax
 lea rcx,[sim_entities]
 add rcx,rax
 cmp dword [rcx+ENTITY_HP],0
 je .next_neighbor
 mov eax,[rbx+20]
 cmp eax,[rcx+ENTITY_GENERATION]
 jne .next_neighbor
 mov eax,[rbx+16]
 cmp eax,[rcx+ENTITY_KIND]
 jne .next_neighbor
 movss xmm0,[rbx]
 subss xmm0,[rsp+12]
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+16]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[rsp+96]
 ja .next_neighbor
 ucomiss xmm0,[epsilon]
 ja .no_coincident
 mov dword [rsp+92],1
 ; Exact coincidence has no separation vector. One physical-ID priority
 ; actor follows its actual intent; the other yields for this tick only.
 ; Alternating authoritative tick parity avoids permanently starving a
 ; moving actor whose coincident neighbor is an explicit held obstacle.
 cmp dword [snap_phase],0
 jne .lower_priority
 cmp r12d,ebp
 jb .coincident_yield
 jmp .no_coincident
.lower_priority:
 cmp r12d,ebp
 jbe .no_coincident
.coincident_yield:
 mov dword [rsp+112],1
.no_coincident:
 mov [rsp+128+r14*4],ebp
 inc r14d
.next_neighbor:
 mov eax,ebp
 shl eax,5
 lea rcx,[snaps]
 mov ebp,[rcx+rax+24]
 jmp .chain
.next_x:
 inc dword [rsp+84]
 mov eax,[rsp+100]
 cmp [rsp+84],eax
 jle .cell_x
.next_z:
 inc dword [rsp+80]
 mov eax,[rsp+100]
 cmp [rsp+80],eax
 jle .cell_z
 mov edi,[rsp+68]
 call .account
 cmp dword [rsp+116],2
 je .occupancy_check
 cmp dword [rsp+112],0
 je .desired_direction
 inc qword [crowd_metrics+32]
 jmp .unchanged
.desired_direction:
 xor r15d,r15d
.candidate:
 cmp dword [rsp+116],3
 je .hull_terrain
 cmp dword [rsp+116],1
 je .manual_candidate
 movss xmm2,[rsp+28]
 movss xmm3,[rsp+32]
 lea rax,[angles]
 movss xmm5,[rax+r15*8]
 movss xmm6,[rax+r15*8+4]
 ; Rotate normalized desired direction.
 movaps xmm7,xmm2
 mulss xmm2,xmm5
 mulss xmm7,xmm6
 movaps xmm8,xmm3
 mulss xmm3,xmm5
 mulss xmm8,xmm6
 subss xmm2,xmm8
 addss xmm3,xmm7
 movss [rsp+104],xmm2
 movss [rsp+108],xmm3
 test r15d,r15d
 jz .terrain_candidate
 ; A legal one-tick sidestep can lead straight into a wall beside a body.
 ; Prefer bounded directions with a clear twelve-meter static corridor.
 ; Source/body safety is still checked on the actual accepted short sweep.
 mulss xmm2,[lookahead]
 mulss xmm3,[lookahead]
 addss xmm2,[rsp+12]
 addss xmm3,[rsp+16]
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 mov edi,[rsp+4]
 call world_body_path_clear
 test eax,eax
 jz .reject
.terrain_candidate:
 movss xmm2,[rsp+104]
 movss xmm3,[rsp+108]
 mulss xmm2,[rsp+8]
 mulss xmm3,[rsp+8]
 addss xmm2,[rsp+12]
 addss xmm3,[rsp+16]
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 movss xmm4,[rsp+8]
 test r15d,r15d
 jnz .steering_goal
 ; Preserve terrain's long-corridor routing for the uncorrected direction.
 ; A one-step pseudo-goal can otherwise alternate against a wall forever.
 movss xmm2,[rsp+20]
 movss xmm3,[rsp+24]
.steering_goal:
 mov edi,[rsp+4]
 call terrain_body_move
 jmp .endpoint
.manual_candidate:
 movss xmm2,[rsp+28]
 mulss xmm2,[rsp+8]
 movss xmm3,[rsp+32]
 mulss xmm3,[rsp+8]
 cmp r15d,1
 jne .manual_z
 xorps xmm3,xmm3
.manual_z:
 cmp r15d,2
 jne .manual_goal
 xorps xmm2,xmm2
.manual_goal:
 addss xmm2,[rsp+12]
 addss xmm3,[rsp+16]
 movss xmm4,[rsp+8]
 ; Component slides preserve the original component magnitude.
 cmp r15d,0
 je .manual_cap
 movss xmm4,[rsp+28]
 cmp r15d,1
 je .manual_abs
 movss xmm4,[rsp+32]
.manual_abs:
 movd eax,xmm4
 and eax,0x7fffffff
 movd xmm4,eax
 mulss xmm4,[rsp+8]
.manual_cap:
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 mov edi,[rsp+4]
 call world_body_step
 jmp .endpoint
.hull_terrain:
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 movss xmm2,[rsp+20]
 movss xmm3,[rsp+24]
 mov edi,[rsp+4]
 call world_body_path_clear
 test eax,eax
 jz .hull_blocked
 movss xmm0,[rsp+20]
 movss xmm1,[rsp+24]
 cmp dword [crowd_enabled],0
 je .out
 jmp .endpoint
.hull_blocked:
 cmp dword [crowd_enabled],0
 je .unchanged
 jmp .reject
.endpoint:
 movss [rsp+36],xmm0
 movss [rsp+40],xmm1
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 mov edi,[rsp+4]
 call world_body_path_clear
 cmp eax,1
 jne .reject
 movss xmm0,[rsp+36]
 movss xmm1,[rsp+40]
 subss xmm0,[rsp+12]
 subss xmm1,[rsp+16]
 movss [rsp+44],xmm0
 movss [rsp+48],xmm1
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movss [rsp+52],xmm0
 cmp dword [rsp+116],3
 jne .segment_nonzero_old
 ucomiss xmm0,[zero]
 jbe .reject
 jmp .segment_nonzero
.segment_nonzero_old:
 ucomiss xmm0,[epsilon]
 jbe .reject
.segment_nonzero:
 ; Preview the resolved steering direction, never enlarge the returned step.
 ; Only AI tracked bodies use this guidance; exact hull/controller sweeps and
 ; genuine overlap recovery continue to use the actual short segment.
 cmp dword [rsp+116],0
 jne .preview_ready
 cmp dword [rsp+4],0
 je .preview_ready
 movss xmm2,[rsp+2176]
 minss xmm2,[body_preview]
 sqrtss xmm3,xmm0
 divss xmm2,xmm3
 movss xmm3,[rsp+44]
 movss xmm4,[rsp+48]
 mulss xmm3,xmm2
 mulss xmm4,xmm2
 movss [rsp+2180],xmm3
 movss [rsp+2184],xmm4
 mulss xmm3,xmm3
 mulss xmm4,xmm4
 addss xmm3,xmm4
 movss [rsp+2188],xmm3
.preview_ready:
 xor ebp,ebp
 mov dword [rsp+60],0
.check:
 cmp ebp,r14d
 jae .accept
 mov eax,[rsp+128+rbp*4]
 shl eax,5
 lea rbx,[snaps]
 add rbx,rax
 ; Initial squared center distance, radius sum, and nearest swept distance.
 movss xmm0,[rbx]
 subss xmm0,[rsp+12]
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+16]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 mulss xmm2,xmm2
 mulss xmm3,xmm3
 addss xmm2,xmm3
 movss xmm4,[rbx+8]
 addss xmm4,[rsp+56]
 movaps xmm5,xmm4
 mulss xmm5,xmm5
 ; Source sweeps remain authoritative. Preview only disjoint AI tracked
 ; bodies along the actual terrain-resolved candidate direction. No extra
 ; query records, radius, persistent preference or mutable heading is used.
 movss xmm8,[rsp+44]
 movss xmm9,[rsp+48]
 movss xmm10,[rsp+52]
 ucomiss xmm2,xmm5
 jb .projection
 cmp dword [rsp+116],0
 jne .projection
 cmp dword [rsp+4],0
 je .projection
 movss xmm8,[rsp+2180]
 movss xmm9,[rsp+2184]
 movss xmm10,[rsp+2188]
.projection:
 ; Projection onto chosen segment, clamped [0,1].
 movaps xmm6,xmm0
 mulss xmm6,xmm8
 movaps xmm7,xmm1
 mulss xmm7,xmm9
 addss xmm6,xmm7
 divss xmm6,xmm10
 maxss xmm6,[zero]
 minss xmm6,[one]
 movaps xmm7,xmm6
 mulss xmm6,xmm8
 mulss xmm7,xmm9
 subss xmm0,xmm6
 subss xmm1,xmm7
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm2,xmm5
 jb .overlap
 ; Conservative independent-motion clearance: target may advance its entire
 ; role maximum step toward any point on this segment in the same tick.
 addss xmm4,[rbx+12]
 mulss xmm4,xmm4
 ucomiss xmm0,xmm4
 jae .checked
 ; If already inside an anticipation margin, outward/tangent motion may
 ; escape safely rather than freeze. Its sweep must not decrease distance.
 ucomiss xmm2,xmm4
 jae .reject
 addss xmm0,[epsilon]
 ucomiss xmm0,xmm2
 jb .reject
 jmp .checked
.overlap:
 ; Existing overlaps cannot vanish instantly. Require a genuine outward
 ; radial component for noncoincident bodies: equal tangential displacement
 ; of two overlapping actors cannot masquerade as recovery.
 ucomiss xmm2,[epsilon]
 jbe .coincident_recovery
 movss xmm6,[rbx]
 subss xmm6,[rsp+12]
 mulss xmm6,[rsp+44]
 movss xmm7,[rbx+4]
 subss xmm7,[rsp+16]
 mulss xmm7,[rsp+48]
 addss xmm6,xmm7
 addss xmm6,[epsilon]
 ucomiss xmm6,[zero]
 jae .reject
.coincident_recovery:
 ; Never deepen along the sweep,
 ; and strictly increase separation at endpoint, with normal role step only.
 addss xmm0,[epsilon]
 ucomiss xmm0,xmm2
 jb .reject
 movss xmm0,[rbx]
 subss xmm0,[rsp+36]
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+40]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 addss xmm2,[epsilon]
 ucomiss xmm0,xmm2
 jbe .reject
 mov dword [rsp+60],1
.checked:
 inc ebp
 jmp .check
.reject:
 cmp dword [rsp+116],3
 je .hull_yield
 inc r15d
 mov eax,10
 cmp dword [rsp+116],1
 jne .candidate_count
 mov eax,3
.candidate_count:
 cmp r15d,eax
 jb .candidate
.hull_yield:
 inc qword [crowd_metrics+32]
 jmp .unchanged
.accept:
 test r15d,r15d
 jz .not_corrected
 inc qword [crowd_metrics+24]
.not_corrected:
 cmp dword [rsp+60],0
 je .result
 inc qword [crowd_metrics+40]
.result:
 movss xmm0,[rsp+36]
 movss xmm1,[rsp+40]
 jmp .out
.truncated:
 mov edi,[rsp+68]
 call .account
 inc qword [crowd_metrics+48]
 inc qword [crowd_metrics+32]
 cmp dword [rsp+116],2
 je .occupied
 jmp .unchanged
.account:
 ; Explicit inspected-record argument; CALL shifts the caller frame by8.
 mov eax,edi
 add [crowd_metrics+16],rax
 cmp rax,[crowd_metrics+56]
 jbe .account_done
 mov [crowd_metrics+56],rax
.account_done: ret
.bad_input:
 movss xmm0,[rbx+ENTITY_X]
 cmp r12d,ENTITY_CAPACITY
 jb .bad_army
 movss xmm1,[rbx+PLAYER_Z]
 jmp .bad_store
.bad_army:
 movss xmm1,[rbx+ENTITY_Z]
.bad_store:
 movss [rsp+12],xmm0
 movss [rsp+16],xmm1
 jmp .unchanged
.occupancy_source:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .occupied
 mov r12d,[rsp]
 mov eax,[rsp+120]
 cmp eax,2
 ja .occupied
 mov [rsp+4],eax
 mov edi,eax
 call world_body_blocked
 test eax,eax
 jnz .occupied
 cmp dword [crowd_enabled],0
 je .vacant
 lea rdx,[radii]
 mov eax,[rsp+4]
 movss xmm0,[rdx+rax*4]
 movss [rsp+56],xmm0
 inc qword [crowd_metrics+8]
 jmp .query
.occupancy_check:
 xor ebp,ebp
.occupancy_neighbor:
 cmp ebp,r14d
 jae .vacant
 mov eax,[rsp+128+rbp*4]
 shl eax,5
 lea rbx,[snaps]
 add rbx,rax
 movss xmm0,[rbx]
 subss xmm0,[rsp+12]
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+16]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movss xmm2,[rbx+8]
 addss xmm2,[rsp+56]
 mulss xmm2,xmm2
 ucomiss xmm0,xmm2
 jbe .occupied
 inc ebp
 jmp .occupancy_neighbor
.occupied:
 mov eax,1
 jmp .out
.vacant:
 xor eax,eax
 jmp .out
.legacy:
 mov edi,[rsp+4]
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 movss xmm2,[rsp+20]
 movss xmm3,[rsp+24]
 movss xmm4,[rsp+8]
 cmp dword [rsp+116],1
 jne .legacy_ai
 call world_body_step
 jmp .out
.legacy_ai:
 call terrain_body_move
 movss [rsp+36],xmm0
 movss [rsp+40],xmm1
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 mov edi,[rsp+4]
 call world_body_path_clear
 cmp eax,1
 jne .unchanged
 movss xmm0,[rsp+36]
 movss xmm1,[rsp+40]
 jmp .out
.unchanged:
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 maxss xmm0,[zero]
 minss xmm0,[maximum]
 maxss xmm1,[zero]
 minss xmm1,[maximum]
.out:
 add rsp,2248
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
; EDI slot -> EAX legitimate boarded hullID or -1. No authoritative writes.
boarding:
 cmp edi,PLAYER_CAPACITY
 jae .none
 lea rbx,[sim_players]
 mov eax,edi
 shl eax,6
 add rbx,rax
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .none
 cmp dword [rbx+PLAYER_HP],0
 je .none
 mov ecx,[rbx+PLAYER_GENERATION]
 test ecx,ecx
 jz .none
 lea rdx,[vehicle_driver_generation]
 cmp ecx,[rdx+rdi*4]
 jne .none
 lea rdx,[sim_player_vehicle]
 mov eax,[rdx+rdi*4]
 cmp eax,[sim_count]
 jae .none
 cmp eax,ENTITY_CAPACITY
 jae .none
 lea rdx,[sim_vehicles]
 mov ecx,edi
 shl ecx,5
 add rdx,rcx
 cmp dword [rdx+VEHICLE_ACTIVE],1
 jne .none
 cmp [rdx+VEHICLE_ENTITY],eax
 jne .none
 cmp [rdx+VEHICLE_DRIVER],edi
 jne .none
 lea r8,[vehicle_entity_driver]
 cmp [r8+rax*4],edi
 jne .none
 mov ecx,eax
 shl ecx,5
 lea r8,[sim_entities]
 add r8,rcx
 cmp dword [r8+ENTITY_HP],0
 je .none
 cmp dword [r8+ENTITY_SIDE],0
 jne .none
 cmp dword [r8+ENTITY_KIND],1
 jne .none
 mov ecx,[r8+ENTITY_GENERATION]
 test ecx,ecx
 jz .none
 cmp ecx,[rdx+VEHICLE_ENTITY_GENERATION]
 jne .none
 ret
.none:
 mov eax,-1
 ret
human_valid:
 push rdi
 call boarding
 pop rdi
 cmp eax,-1
 jne .invalid
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .invalid
 cmp dword [rbx+PLAYER_HP],0
 je .invalid
 cmp dword [rbx+PLAYER_GENERATION],0
 je .invalid
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 ucomiss xmm0,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 ucomiss xmm1,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[maximum]
 ja .invalid
 mov eax,1
 ret
.invalid:
 xor eax,eax
 ret
human_snapshot:
 push rdi
 call human_valid
 pop rdi
 mov ecx,edi
 shl ecx,5
 lea rdx,[snaps+ENTITY_CAPACITY*SNAP_SIZE]
 add rdx,rcx
 mov dword [rdx+20],0
 test eax,eax
 jz .done
 movss [rdx],xmm0
 movss [rdx+4],xmm1
 movss xmm2,[radii]
 movss [rdx+8],xmm2
 movss xmm2,[human_step]
 movss [rdx+12],xmm2
 mov dword [rdx+16],0
 mov ecx,[rbx+PLAYER_GENERATION]
 mov [rdx+20],ecx
.done:
 ret
crowd_hash:
 lea rsi,[crowd_enabled]
 mov ecx,4
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
