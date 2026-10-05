; Authoritative fixed-tick FPS players. SysV AMD64; static storage only.
%include "schemas/player.inc"
%include "schemas/entity.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,sim_sites,sim_fire
extern terrain_height,terrain_blocked,terrain_move,terrain_los,sinf,cosf
extern vehicle_detach,vehicle_tick_player
section .bss align=64
global sim_players,player_deaths,player_respawns
sim_players: resb PLAYER_CAPACITY*PLAYER_STRIDE
intents: resb PLAYER_CAPACITY*32
player_deaths: resd 1
player_respawns: resd 1
; Single authoritative thread scratch; never used by callbacks.
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
zero: dd 0.0
one: dd 1.0
minus_one: dd -1.0
world_max: dd 8000.0
yaw_max: dd 10000.0
yaw_min: dd -10000.0
pitch_max: dd 1.3
pitch_min: dd -1.3
eye: dd 1.8
target_eye: dd 1.0
air_altitude: dd 90.0
walk_step: dd 0.166666667
sprint_step: dd 0.3
fire_range: dd 450.0
cone: dd 0.998
suppressed_cone: dd 0.9995
threat_range2: dd 25600.0
friend_range2: dd 62500.0
nearfield_x: dd 3780.0
spawn_offsets: dd 0.0,0.0,-80.0,0.0,0.0,80.0,0.0,-80.0,-150.0,0.0,-150.0,80.0,-150.0,-80.0,-250.0,0.0
section .text
global player_init,player_join,player_leave,player_input,player_tick,player_hash
player_init:
 lea rdi,[sim_players]
 xor eax,eax
 mov ecx,(PLAYER_CAPACITY*PLAYER_STRIDE+PLAYER_CAPACITY*32+8)/4
 rep stosd
 ret
player_join:
 cmp edi,PLAYER_CAPACITY
 jae .bad
 cmp esi,3
 jae .bad
 push rbx
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
 call spawn_player
 test eax,eax
 jz .joined
 mov dword [rbx+PLAYER_HP],0
 mov dword [rbx+PLAYER_RESPAWN],30
.joined:
 xor eax,eax
 pop rbx
 ret
.failed:
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
 call vehicle_detach
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
 test esi,~31
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
 jnz .next
 cmp dword [rbx+PLAYER_HP],0
 jne .alive
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
 mov dword [rbx+PLAYER_AMMO],30
.intent:
 mov eax,r12d
 shl eax,5
 lea r13,[intents]
 add r13,rax
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 addss xmm2,[r13]
 addss xmm3,[r13+4]
 movss xmm4,[walk_step]
 test dword [r13+16],INPUT_SPRINT
 jz .move
 movss xmm4,[sprint_step]
.move:
 xor edi,edi
 call terrain_move
 movss [rbx+PLAYER_X],xmm0
 movss [rbx+PLAYER_Z],xmm1
 call terrain_height
 addss xmm0,[eye]
 movss [rbx+PLAYER_Y],xmm0
 cmp dword [rbx+PLAYER_RELOAD],0
 jne .enemy
 test dword [r13+16],INPUT_RELOAD
 jz .fire
 cmp dword [rbx+PLAYER_AMMO],30
 je .fire
 mov dword [rbx+PLAYER_RELOAD],60
 jmp .enemy
.fire:
 test dword [r13+16],INPUT_FIRE
 jz .enemy
 cmp dword [rbx+PLAYER_AMMO],0
 je .enemy
 cmp dword [rbx+PLAYER_COOLDOWN],0
 jne .enemy
 dec dword [rbx+PLAYER_AMMO]
 inc dword [rbx+PLAYER_SHOTS]
 mov dword [rbx+PLAYER_COOLDOWN],4
 call fire_player
.enemy:
 mov eax,[sim_tick_count]
 add eax,r12d
 test eax,15
 jnz .next
 call enemy_attack
.next:
 add rbx,PLAYER_STRIDE
 inc r12d
 cmp r12d,PLAYER_CAPACITY
 jb .loop
 pop r13
 pop r12
 pop rbx
 ret
; Choose nearby squad deployment only while that front has a connected site,
; otherwise a connected owned site. Candidate clearance uses actual LOS.
spawn_player:
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
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
 addss xmm0,[rax+r12*8]
 movss [candidate_x],xmm0
 mov eax,[rbx+PLAYER_FRONT]
 shl eax,7
 lea rdx,[sim_sites]
 movss xmm1,[rdx+rax+4]
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
 movss xmm0,[r15]
 movss [candidate_x],xmm0
 movss xmm0,[r15+4]
 movss [candidate_z],xmm0
 call safe_candidate
 test eax,eax
 jz .publish
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
; 0safe,-1unsafe. Checks solid occupancy plus observed enemy threat within160m.
safe_candidate:
 push r12
 push r13
 push r14
 movss xmm0,[candidate_x]
 movss xmm1,[candidate_z]
 xor edi,edi
 call terrain_blocked
 test eax,eax
 jnz .bad
 movss xmm0,[candidate_x]
 movss xmm1,[candidate_z]
 call terrain_height
 addss xmm0,[eye]
 movss [candidate_y],xmm0
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
 comiss xmm0,[threat_range2]
 ja .next
 movss xmm0,[r14+ENTITY_X]
 movss xmm1,[r14+ENTITY_Z]
 call terrain_height
 addss xmm0,[target_eye]
 cmp dword [r14+ENTITY_KIND],3
 jne .height
 addss xmm0,[air_altitude]
.height:
 movss xmm4,xmm0
 movss xmm0,[candidate_x]
 movss xmm1,[candidate_y]
 movss xmm2,[candidate_z]
 movss xmm3,[r14+ENTITY_X]
 movss xmm5,[r14+ENTITY_Z]
 call terrain_los
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
 movss xmm0,[r14+ENTITY_X]
 movss xmm1,[r14+ENTITY_Z]
 call terrain_height
 addss xmm0,[target_eye]
 cmp dword [r14+ENTITY_KIND],3
 jne .ground
 addss xmm0,[air_altitude]
.ground:
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
 call terrain_los
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
enemy_attack:
 push r12
 push r13
 push r14
 lea r14,[sim_entities]
 xor r12d,r12d
.scan:
 cmp r12d,[sim_count]
 jae .return
 cmp dword [r14+ENTITY_HP],0
 je .next
 cmp dword [r14+ENTITY_SIDE],1
 jne .next
 movss xmm0,[r14+ENTITY_X]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[r14+ENTITY_Z]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[threat_range2]
 ja .next
 movss xmm0,[r14+ENTITY_X]
 movss xmm1,[r14+ENTITY_Z]
 call terrain_height
 addss xmm0,[target_eye]
 cmp dword [r14+ENTITY_KIND],3
 jne .height
 addss xmm0,[air_altitude]
.height:
 movss xmm1,xmm0
 movss xmm0,[r14+ENTITY_X]
 movss xmm2,[r14+ENTITY_Z]
 movss xmm3,[rbx+PLAYER_X]
 movss xmm4,[rbx+PLAYER_Y]
 movss xmm5,[rbx+PLAYER_Z]
 call terrain_los
 test eax,eax
 jz .next
 add dword [rbx+PLAYER_SUPPRESSION],25
 cmp dword [rbx+PLAYER_SUPPRESSION],100
 jbe .damage
 mov dword [rbx+PLAYER_SUPPRESSION],100
.damage:
 cmp dword [rbx+PLAYER_HP],10
 jbe .dead
 sub dword [rbx+PLAYER_HP],10
 jmp .return
.dead:
 mov dword [rbx+PLAYER_HP],0
 mov dword [rbx+PLAYER_RESPAWN],30
 mov dword [rbx+PLAYER_RELOAD],0
 inc dword [player_deaths]
 mov rdi,rbx
 lea rdx,[sim_players]
 sub rdi,rdx
 shr edi,6
 call vehicle_detach
 jmp .return
.next:
 add r14,ENTITY_STRIDE
 inc r12d
 jmp .scan
.return:
 pop r14
 pop r13
 pop r12
 ret
player_hash:
 lea rsi,[sim_players]
 mov ecx,PLAYER_CAPACITY*PLAYER_STRIDE+PLAYER_CAPACITY*32+8
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
