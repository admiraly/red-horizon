; Authoritative fixed-tick FPS players. SysV AMD64; static storage only.
%include "schemas/player.inc"
%include "schemas/player_ammunition.inc"
%include "schemas/infantry_weapon.inc"
%include "schemas/entity.inc"
default rel
extern player_ammunition_init,player_ammunition_equip,player_ammunition_reserve,player_ammunition_reload_finish,player_ammunition_fire,player_ammunition_resupply,player_ammunition_hash
extern company_assign,company_release,company_control_init,company_redeploy
extern sim_entities,sim_count,sim_tick_count,sim_sites,sim_fire
extern deployment_blast_clear
extern sim_entity_height
extern terrain_height,world_body_blocked,world_los,sinf,cosf
extern vehicle_detach,vehicle_tick_player
extern crowd_begin,crowd_step,crowd_occupied
section .bss align=64
global sim_players,player_deaths,player_respawns
sim_players: resb PLAYER_CAPACITY*PLAYER_STRIDE
intents: resb PLAYER_CAPACITY*32
; Private authoritative motion sidecar: foot Y, vertical step, generation,
; jump latch, grounded, initialized, last eye, reserved. Public player ABI stays64.
global player_motion
player_motion: resb PLAYER_CAPACITY*32
player_deaths: resd 1
player_respawns: resd 1
; Single authoritative thread scratch; never used by callbacks.
; Authored birth configuration; reset on every world init, never a camera override.
deployment_enabled: resd 1
deployment_anchor: resd 2
candidate_x: resd 1
candidate_z: resd 1
candidate_y: resd 1
ray_dx: resd 1
ray_dy: resd 1
ray_dz: resd 1
target_y: resd 1
direction_x: resd 1
direction_y: resd 1
direction_z: resd 1
best_distance: resd 1
section .rodata
align 16
abs_mask: dd 0x7fffffff,0x7fffffff,0x7fffffff,0x7fffffff
zero: dd 0.0
one: dd 1.0
minus_one: dd -1.0
world_max: dd 8000.0
yaw_max: dd 10000.0
yaw_min: dd -10000.0
pitch_max: dd 1.3
pitch_min: dd -1.3
eye: dd 1.8
crouch_eye: dd 1.1
crouch_step: dd 0.083333333
jump_step: dd 0.2
gravity_step: dd 0.010888889
fall_limit: dd -1.666666667
height_min: dd -1000.0
height_max: dd 1000.0
pose_tolerance: dd 0.05
target_eye: dd 1.0
air_altitude: dd 90.0
walk_step: dd 0.166666667
sprint_step: dd 0.3
fire_range: dd 450.0
cone: dd 0.998
suppressed_cone: dd 0.9995
threat_range2: dd 25600.0
infantry_threat_range2: dd INFANTRY_HUMAN_RANGE_SQ
friend_range2: dd 62500.0
nearfield_x: dd 3780.0
spawn_offsets: dd 0.0,0.0,-80.0,0.0,0.0,80.0,0.0,-80.0,-150.0,0.0,-150.0,80.0,-150.0,-80.0,-250.0,0.0
section .text
global player_init,player_join,player_leave,player_input,player_tick,player_hash
player_init:
 mov dword [deployment_enabled],0
 mov qword [deployment_anchor],0
 lea rdi,[sim_players]
 xor eax,eax
 mov ecx,(PLAYER_CAPACITY*PLAYER_STRIDE+PLAYER_CAPACITY*64+8)/4
 rep stosd
 push rax
 call player_ammunition_init
 pop rax
 jmp company_control_init
player_join:
 cmp edi,PLAYER_CAPACITY
 jae .bad
 cmp esi,3
 jae .bad
 push rbx
 sub rsp,16
 mov [rsp],edi
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 cmp dword [rbx+PLAYER_CONNECTED],0
 jne .failed
 mov r8d,[rbx+PLAYER_GENERATION]
 inc r8d
 mov r9d,esi
 mov r10d,edi
 mov rdi,rbx
 xor eax,eax
 mov ecx,16
 rep stosd
 mov [rbx+PLAYER_GENERATION],r8d
 mov [rbx+PLAYER_FRONT],r9d
 mov dword [rbx+PLAYER_CONNECTED],1
 mov eax,r10d
 shl eax,5
 lea rdi,[intents]
 add rdi,rax
 xor eax,eax
 mov ecx,8
 rep stosd
 mov edi,r10d
 call motion_clear
 call spawn_player
 test eax,eax
 jz .joined
 mov dword [rbx+PLAYER_HP],0
 mov dword [rbx+PLAYER_RESPAWN],30
.joined:
 mov edi,[rsp]
 call player_ammunition_equip
 mov edi,[rsp]
 mov esi,[rbx+PLAYER_FRONT]
 call company_assign
 xor eax,eax
 add rsp,16
 pop rbx
 ret
.failed:
 add rsp,16
 pop rbx
.bad:
 mov eax,-1
 ret
player_leave:
 cmp edi,PLAYER_CAPACITY
 jae .bad
 mov eax,edi
 shl eax,6
 lea rdx,[sim_players]
 add rdx,rax
 cmp dword [rdx+PLAYER_CONNECTED],0
 je .bad
 mov dword [rdx+PLAYER_CONNECTED],0
 mov dword [rdx+PLAYER_HP],0
 push rdi
 call company_release
 pop rdi
 push rdi
 call vehicle_detach
 pop rdi
 push rdi
 call motion_clear
 pop rdi
 mov eax,edi
 shl eax,5
 lea rdi,[intents]
 add rdi,rax
 xor eax,eax
 mov ecx,8
 rep stosd
 ret
.bad: mov eax,-1
 ret
player_input:
 cmp edi,PLAYER_CAPACITY
 jae .bad
 test esi,~127
 jnz .bad
 ucomiss xmm0,[minus_one]
 jp .bad
 jb .bad
 ucomiss xmm0,[one]
 ja .bad
 ucomiss xmm1,[minus_one]
 jp .bad
 jb .bad
 ucomiss xmm1,[one]
 ja .bad
 ucomiss xmm2,[yaw_min]
 jp .bad
 jb .bad
 ucomiss xmm2,[yaw_max]
 ja .bad
 ucomiss xmm3,[pitch_min]
 jp .bad
 jb .bad
 ucomiss xmm3,[pitch_max]
 ja .bad
 mov eax,edi
 shl eax,6
 lea rdx,[sim_players]
 cmp dword [rdx+rax+PLAYER_CONNECTED],1
 jne .bad
 movss [rdx+rax+PLAYER_YAW],xmm2
 movss [rdx+rax+PLAYER_PITCH],xmm3
 mov eax,edi
 shl eax,5
 lea rdx,[intents]
 movss [rdx+rax],xmm0
 movss [rdx+rax+4],xmm1
 mov [rdx+rax+16],esi
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
player_tick:
 push rbx
 push r12
 push r13
 ; Army-only ticks need no second snapshot. Living controllers use final-army
 ; positions; deployment refreshes separately when a dead player respawns.
 lea rax,[sim_players]
 mov ecx,PLAYER_CAPACITY
.body_scan:
 cmp dword [rax+PLAYER_CONNECTED],1
 jne .body_next
 cmp dword [rax+PLAYER_HP],0
 jne .body_refresh
.body_next:
 add rax,PLAYER_STRIDE
 loop .body_scan
 jmp .body_ready
.body_refresh:
 call crowd_begin
.body_ready:
 xor r12d,r12d
 lea rbx,[sim_players]
.loop:
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .next
 ; The helper consumes action edges even while dead, handles boarded movement
 ; and cannon fire, and returns1 to suppress infantry logic for this tick.
 mov eax,r12d
 shl eax,5
 lea r13,[intents]
 add r13,rax
 movss xmm0,[r13]
 movss xmm1,[r13+4]
 mov esi,[r13+16]
 mov edi,r12d
 call vehicle_tick_player
 test eax,eax
 jz .infantry
 call motion_consume
 jmp .next
.infantry:
 cmp dword [rbx+PLAYER_HP],0
 jne .alive
 call motion_consume
 cmp dword [rbx+PLAYER_RESPAWN],0
 je .redeploy
 dec dword [rbx+PLAYER_RESPAWN]
 jnz .next
.redeploy:
 call spawn_player
 test eax,eax
 jz .respawned
 mov dword [rbx+PLAYER_RESPAWN],30
 jmp .next
.respawned:
 inc dword [player_respawns]
 inc dword [rbx+PLAYER_GENERATION]
 mov edi,r12d
 call player_ammunition_equip
 mov edi,r12d
 call company_redeploy
 jmp .next
.alive:
 cmp dword [rbx+PLAYER_SUPPRESSION],0
 je .cooldown
 dec dword [rbx+PLAYER_SUPPRESSION]
.cooldown:
 cmp dword [rbx+PLAYER_COOLDOWN],0
 je .reload
 dec dword [rbx+PLAYER_COOLDOWN]
.reload:
 cmp dword [rbx+PLAYER_RELOAD],0
 je .intent
 dec dword [rbx+PLAYER_RELOAD]
 jnz .intent
 mov edi,r12d
 call player_ammunition_reload_finish
.intent:
 mov eax,r12d
 shl eax,5
 lea r13,[intents]
 add r13,rax
 call motion_validate
 test eax,eax
 jnz .next
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 addss xmm2,[r13]
 addss xmm3,[r13+4]
 movss xmm4,[walk_step]
 test dword [r13+16],INPUT_CROUCH
 jz .sprint
 movss xmm4,[crouch_step]
 jmp .move
.sprint:
 test dword [r13+16],INPUT_SPRINT
 jz .move
 movss xmm4,[sprint_step]
.move:
 mov edi,r12d
 add edi,ENTITY_CAPACITY
 call crowd_step
 movss [rbx+PLAYER_X],xmm0
 movss [rbx+PLAYER_Z],xmm1
 call motion_vertical
 mov eax,[sim_tick_count]
 xor edx,edx
 mov ecx,PLAYER_AMMUNITION_SUPPLY_PERIOD
 div ecx
 cmp edx,r12d
 jne .supply_done
 mov edi,r12d
 call player_ammunition_resupply
.supply_done:
 cmp dword [rbx+PLAYER_RELOAD],0
 jne .enemy
 test dword [r13+16],INPUT_RELOAD
 jz .fire
 cmp dword [rbx+PLAYER_AMMO],30
 je .fire
 mov edi,r12d
 call player_ammunition_reserve
 cmp eax,0
 jle .fire
 mov dword [rbx+PLAYER_RELOAD],PLAYER_AMMUNITION_RELOAD_TICKS
 jmp .enemy
.fire:
 test dword [r13+16],INPUT_FIRE
 jz .enemy
 cmp dword [rbx+PLAYER_AMMO],0
 je .enemy
 cmp dword [rbx+PLAYER_COOLDOWN],0
 jne .enemy
 mov edi,r12d
 call player_ammunition_fire
 cmp eax,1
 jne .enemy
 inc dword [rbx+PLAYER_SHOTS]
 mov dword [rbx+PLAYER_COOLDOWN],4
 call fire_player
.enemy:
.next:
 add rbx,PLAYER_STRIDE
 inc r12d
 cmp r12d,PLAYER_CAPACITY
 jb .loop
 pop r13
 pop r12
 pop rbx
 ret
global player_motion_reset
; Bounded death helper for shared player damage; no body/weapon birth.
player_motion_reset:
 cmp edi,PLAYER_CAPACITY
 jae .bad
 sub rsp,8
 call motion_clear
 add rsp,8
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
 ; EDI bounded player slot. Clear private state on join/leave/death.
motion_clear:
 mov eax,edi
 shl eax,5
 lea rdx,[player_motion]
 add rdx,rax
 pxor xmm0,xmm0
 movups [rdx],xmm0
 movups [rdx+16],xmm0
 ret
; Tick owns RBX player, R12 slot, R13 intent. Consume held jump while dead or
; boarded so respawn/disembark requires release before a fresh jump edge.
motion_consume:
 sub rsp,8
 mov edi,r12d
 call motion_clear
 mov eax,[r13+16]
 and eax,INPUT_JUMP
 mov [rdx+12],eax
 mov eax,[rbx+PLAYER_GENERATION]
 mov [rdx+8],eax
 add rsp,8
 ret
; Refuse poisoned authoritative positions before any terrain query. No client
; can supply these through player_input; this is a defensive invariant boundary.
motion_validate:
 movss xmm0,[rbx+PLAYER_X]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[world_max]
 ja .bad
 movss xmm0,[rbx+PLAYER_Z]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[world_max]
 ja .bad
 movss xmm0,[rbx+PLAYER_Y]
 ucomiss xmm0,[height_min]
 jp .bad
 jb .bad
 ucomiss xmm0,[height_max]
 ja .bad
 xor eax,eax
 ret
.bad:
 mov dword [rbx+PLAYER_HP],0
 mov dword [rbx+PLAYER_RESPAWN],30
 sub rsp,8
 call motion_consume
 ; Keep replicated records finite during the recovery delay, too.
 pxor xmm0,xmm0
 pxor xmm1,xmm1
 movss [rbx+PLAYER_X],xmm0
 movss [rbx+PLAYER_Z],xmm1
 call terrain_height
 addss xmm0,[eye]
 movss [rbx+PLAYER_Y],xmm0
 add rsp,8
 mov eax,-1
 ret
; Update actual world-space foot height, not a camera-relative offset: while in
; flight falling terrain cannot carry the player down. Terrain remains swept in
; XZ, so this grounded jump cannot cross solids or masquerade as vaulting.
motion_vertical:
 sub rsp,24
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 call terrain_height
 movss [rsp],xmm0
 mov eax,r12d
 shl eax,5
 lea rdx,[player_motion]
 add rdx,rax
 mov eax,[rbx+PLAYER_GENERATION]
 cmp [rdx+8],eax
 jne .reset
 cmp dword [rdx+20],1
 jne .reset
 cmp dword [rdx+16],1
 ja .reset
 movss xmm1,[rdx+4]
 ucomiss xmm1,[fall_limit]
 jp .reset
 jb .reset
 ucomiss xmm1,[jump_step]
 ja .reset
 movss xmm1,[rdx]
 ucomiss xmm1,[height_min]
 jp .reset
 jb .reset
 ucomiss xmm1,[height_max]
 ja .reset
 ; An externally restored pose / direct vehicle exit cannot resurrect old flight.
 addss xmm1,[rdx+24]
 subss xmm1,[rbx+PLAYER_Y]
 andps xmm1,[abs_mask]
 ucomiss xmm1,[pose_tolerance]
 ja .reset
 jmp .ready
.reset:
 movss [rdx],xmm0
 mov dword [rdx+4],0
 mov [rdx+8],eax
 mov dword [rdx+16],1
 mov dword [rdx+20],1
.ready:
 mov ecx,[r13+16]
 and ecx,INPUT_JUMP
 mov eax,[rdx+12]
 mov [rdx+12],ecx
 test ecx,ecx
 jz .integrate
 test eax,eax
 jnz .integrate
 cmp dword [rdx+16],1
 jne .integrate
 ; Crouched players must stand to jump; the edge is still consumed.
 test dword [r13+16],INPUT_CROUCH
 jnz .integrate
 movss xmm1,[jump_step]
 movss [rdx+4],xmm1
 mov dword [rdx+16],0
.integrate:
 cmp dword [rdx+16],1
 je .ground
 movss xmm1,[rdx]
 addss xmm1,[rdx+4]
 movss xmm2,[rdx+4]
 subss xmm2,[gravity_step]
 maxss xmm2,[fall_limit]
 movss [rdx+4],xmm2
 ucomiss xmm1,[rsp]
 jbe .ground
 movss [rdx],xmm1
 jmp .eye
.ground:
 movss xmm1,[rsp]
 movss [rdx],xmm1
 mov dword [rdx+4],0
 mov dword [rdx+16],1
.eye:
 movss xmm0,[eye]
 test dword [r13+16],INPUT_CROUCH
 jz .publish
 movss xmm0,[crouch_eye]
.publish:
 movss [rdx+24],xmm0
 addss xmm0,[rdx]
 movss [rbx+PLAYER_Y],xmm0
 add rsp,24
 ret
; Trusted one-time scenario birth configuration. XMM0=x, XMM1=z.
; World initialization clears this; all joins still use the full safety policy.
global player_deployment_set
player_deployment_set:
 movss [deployment_anchor],xmm0
 movss [deployment_anchor+4],xmm1
 mov dword [deployment_enabled],1
 ret
; Choose nearby squad deployment only while that front has a connected site,
; otherwise a connected owned site. Candidate clearance uses actual LOS.
spawn_player:
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 ; Joins/redeployment use current generation-safe bodies, independent of camera.
 call crowd_begin
 mov eax,[rbx+PLAYER_FRONT]
 shl eax,7
 lea rdx,[sim_sites]
 add rdx,rax
 cmp dword [rdx+32+8],0
 jne .sites
 cmp dword [rdx+32+20],1
 jne .sites
 cmp dword [rdx+32+24],0
 je .sites
 movss xmm0,[rdx+4]
 movss [candidate_z],xmm0
 xor r12d,r12d
.offset:
 lea rax,[spawn_offsets]
 movss xmm0,[nearfield_x]
 cmp dword [deployment_enabled],0
 je .legacy_x
 movss xmm0,[deployment_anchor]
.legacy_x:
 addss xmm0,[rax+r12*8]
 movss [candidate_x],xmm0
 mov eax,[rbx+PLAYER_FRONT]
 shl eax,7
 lea rdx,[sim_sites]
 movss xmm1,[rdx+rax+4]
 cmp dword [deployment_enabled],0
 je .legacy_z
 movss xmm1,[deployment_anchor+4]
.legacy_z:
 lea rax,[spawn_offsets]
 addss xmm1,[rax+r12*8+4]
 movss [candidate_z],xmm1
 ; Require a living allied formation near the proposed near-field deployment.
 lea r14,[sim_entities]
 xor r13d,r13d
.friend:
 cmp r13d,[sim_count]
 jae .next_offset
 cmp dword [r14+ENTITY_HP],0
 je .friend_next
 cmp dword [r14+ENTITY_SIDE],0
 jne .friend_next
 cmp dword [deployment_enabled],0
 je .friend_ground_ready
 cmp dword [r14+ENTITY_KIND],3
 je .friend_next
.friend_ground_ready:
 mov eax,[rbx+PLAYER_FRONT]
 cmp [r14+ENTITY_FRONT],eax
 jne .friend_next
 movss xmm0,[r14+ENTITY_X]
 subss xmm0,[candidate_x]
 mulss xmm0,xmm0
 movss xmm1,[r14+ENTITY_Z]
 subss xmm1,[candidate_z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[friend_range2]
 ja .friend_next
 call safe_candidate
 test eax,eax
 jz .publish
 jmp .next_offset
.friend_next:
 add r14,ENTITY_STRIDE
 inc r13d
 jmp .friend
.next_offset:
 inc r12d
 cmp r12d,8
 jb .offset
.sites:
 xor r12d,r12d
 lea r15,[sim_sites]
.site:
 cmp dword [r15+8],0
 jne .site_next
 cmp dword [r15+20],1
 jne .site_next
 cmp dword [r15+24],0
 je .site_next
 ; Site models occupy their centres. Test the existing exterior deployment
 ; offsets with the full physical/threat policy, never the building centre.
 mov r13d,1
.site_offset:
 lea rax,[spawn_offsets]
 movss xmm0,[r15]
 addss xmm0,[rax+r13*8]
 movss [candidate_x],xmm0
 movss xmm0,[r15+4]
 addss xmm0,[rax+r13*8+4]
 movss [candidate_z],xmm0
 call safe_candidate
 test eax,eax
 jz .publish
 inc r13d
 cmp r13d,8
 jb .site_offset
.site_next:
 add r15,32
 inc r12d
 cmp r12d,12
 jb .site
 mov eax,-1
 jmp .return
.publish:
 movss xmm0,[candidate_x]
 movss [rbx+PLAYER_X],xmm0
 movss xmm0,[candidate_z]
 movss [rbx+PLAYER_Z],xmm0
 movss xmm0,[candidate_y]
 movss [rbx+PLAYER_Y],xmm0
 mov dword [rbx+PLAYER_HP],100
 mov dword [rbx+PLAYER_AMMO],30
 mov dword [rbx+PLAYER_RELOAD],0
 mov dword [rbx+PLAYER_COOLDOWN],0
 mov dword [rbx+PLAYER_RESPAWN],0
 mov dword [rbx+PLAYER_SUPPRESSION],0
 xor eax,eax
.return:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 ret
; 0safe,-1unsafe. Checks body/solid occupancy plus observed enemy threat within160m.
safe_candidate:
 push r12
 push r13
 push r14
 mov rdi,rbx
 lea rax,[sim_players]
 sub rdi,rax
 shr edi,6
 add edi,ENTITY_CAPACITY
 xor esi,esi
 movss xmm0,[candidate_x]
 movss xmm1,[candidate_z]
 call crowd_occupied
 test eax,eax
 jnz .bad
 movss xmm0,[candidate_x]
 movss xmm1,[candidate_z]
 xor edi,edi
 call world_body_blocked
 test eax,eax
 jnz .bad
 movss xmm0,[candidate_x]
 movss xmm1,[candidate_z]
 call terrain_height
 addss xmm0,[eye]
 movss [candidate_y],xmm0
 movaps xmm1,xmm0
 movss xmm0,[candidate_x]
 movss xmm2,[candidate_z]
 call deployment_blast_clear
 test eax,eax
 jnz .bad
 lea r14,[sim_entities]
 xor r12d,r12d
.enemy:
 cmp r12d,[sim_count]
 jae .safe
 cmp dword [r14+ENTITY_HP],0
 je .next
 cmp dword [r14+ENTITY_SIDE],1
 jne .next
 movss xmm0,[r14+ENTITY_X]
 subss xmm0,[candidate_x]
 mulss xmm0,xmm0
 movss xmm1,[r14+ENTITY_Z]
 subss xmm1,[candidate_z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 cmp dword [r14+ENTITY_KIND],0
 jne .other_threat_range
 comiss xmm0,[infantry_threat_range2]
 jmp .threat_distance_ready
.other_threat_range:
 comiss xmm0,[threat_range2]
.threat_distance_ready:
 ja .next
 mov edi,r12d
 call sim_entity_height
 movss xmm4,xmm0
 movss xmm0,[candidate_x]
 movss xmm1,[candidate_y]
 movss xmm2,[candidate_z]
 movss xmm3,[r14+ENTITY_X]
 movss xmm5,[r14+ENTITY_Z]
 call world_los
 test eax,eax
 jnz .bad
.next:
 add r14,ENTITY_STRIDE
 inc r12d
 jmp .enemy
.safe:
 xor eax,eax
 jmp .return
.bad: mov eax,-1
.return:
 pop r14
 pop r13
 pop r12
 ret
fire_player:
 push r12
 push r13
 push r14
 movss xmm0,[rbx+PLAYER_YAW]
 call sinf wrt ..plt
 movss [direction_x],xmm0
 movss xmm0,[rbx+PLAYER_YAW]
 call cosf wrt ..plt
 movss [direction_z],xmm0
 movss xmm0,[rbx+PLAYER_PITCH]
 call sinf wrt ..plt
 movss [direction_y],xmm0
 movss xmm0,[rbx+PLAYER_PITCH]
 call cosf wrt ..plt
 movss xmm1,[direction_x]
 mulss xmm1,xmm0
 movss [direction_x],xmm1
 mulss xmm0,[direction_z]
 movss [direction_z],xmm0
 movss xmm0,[fire_range]
 movss [best_distance],xmm0
 mov r13d,-1
 lea r14,[sim_entities]
 xor r12d,r12d
.scan:
 cmp r12d,[sim_count]
 jae .hit
 cmp dword [r14+ENTITY_HP],0
 je .next
 cmp dword [r14+ENTITY_SIDE],1
 jne .next
 mov edi,r12d
 call sim_entity_height
 movss [target_y],xmm0
 subss xmm0,[rbx+PLAYER_Y]
 movss [ray_dy],xmm0
 movss xmm1,[r14+ENTITY_X]
 subss xmm1,[rbx+PLAYER_X]
 movss [ray_dx],xmm1
 movss xmm2,[r14+ENTITY_Z]
 subss xmm2,[rbx+PLAYER_Z]
 movss [ray_dz],xmm2
 mulss xmm0,xmm0
 movaps xmm3,xmm1
 mulss xmm3,xmm3
 addss xmm0,xmm3
 movaps xmm3,xmm2
 mulss xmm3,xmm3
 addss xmm0,xmm3
 sqrtss xmm0,xmm0
 comiss xmm0,[one]
 jb .next
 comiss xmm0,[best_distance]
 jae .next
 movss xmm3,[ray_dx]
 mulss xmm3,[direction_x]
 movss xmm4,[ray_dy]
 mulss xmm4,[direction_y]
 addss xmm3,xmm4
 movss xmm4,[ray_dz]
 mulss xmm4,[direction_z]
 addss xmm3,xmm4
 divss xmm3,xmm0
 comiss xmm3,[cone]
 jb .next
 cmp dword [rbx+PLAYER_SUPPRESSION],50
 jb .los
 comiss xmm3,[suppressed_cone]
 jb .next
.los:
 ; Save distance because terrain query owns all volatile SSE registers.
 movss [ray_dx],xmm0
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Y]
 movss xmm2,[rbx+PLAYER_Z]
 movss xmm3,[r14+ENTITY_X]
 movss xmm4,[target_y]
 movss xmm5,[r14+ENTITY_Z]
 call world_los
 test eax,eax
 jz .next
 movss xmm0,[ray_dx]
 movss [best_distance],xmm0
 mov r13d,r12d
.next:
 add r14,ENTITY_STRIDE
 inc r12d
 jmp .scan
.hit:
 cmp r13d,-1
 je .return
 mov edi,r13d
 mov esi,34
 call sim_fire
 test eax,eax
 jnz .return
 inc dword [rbx+PLAYER_HITS]
.return:
 pop r14
 pop r13
 pop r12
 ret
player_hash:
 lea rsi,[sim_players]
 mov ecx,PLAYER_CAPACITY*PLAYER_STRIDE+PLAYER_CAPACITY*64+8
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 cmp dword [deployment_enabled],0
 je .ammunition
 lea rsi,[deployment_enabled]
 mov ecx,12
.deployment:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .deployment
.ammunition:
 jmp player_ammunition_hash
section .note.GNU-stack noalloc noexec nowrite progbits
