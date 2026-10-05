; Continuous fixed-step aircraft. All perception is range/LOS limited.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,sim_waypoints,terrain_height,terrain_los
extern sinf,cosf,atan2f,projectile_air_launch
section .bss align=64
global sim_aircraft
sim_aircraft: resb ENTITY_CAPACITY*AIR_STRIDE
; Private fixed state: remaining maneuver and refractory ticks, indexed by stable ID.
air_defense: resd ENTITY_CAPACITY*2
air_counts: resd 1024
air_samples: resd 1024*8
section .rodata
zero: dd 0.0
one: dd 1.0
eye: dd 2.0
fallback: dd 92.0
altitude: dd 110.0,140.0
speeds: dd 5.0,7.0
turns: dd 0.025,0.04
pi: dd 3.14159265
tau: dd 6.2831853
negative: dd -1.0
climb: dd 0.5
minus_climb: dd -0.5
bank_scale: dd 18.0
pitch_scale: dd 0.15
half: dd 0.5
scale: dd 0.004
margin: dd 650.0
edge: dd 7350.0
centre: dd 4000.0
homes: dd 1000.0,7000.0
range2: dd 562500.0
bomber_range2: dd 1440000.0
cone: dd 0.985
bomb_cross: dd 28.0
release_margin: dd 18.0
grav: dd 0.0109
two: dd 2.0
lead_ticks: dd 8.0
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global air_init,air_tick,air_combat_tick,air_hash,sim_entity_height,air_hit
sim_entity_height:
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_KIND],3
 jne .ground
 mov eax,edi
 shl eax,6
 lea rcx,[sim_aircraft]
 add rcx,rax
 mov eax,[rdx+ENTITY_GENERATION]
 cmp [rcx+AIR_GENERATION],eax
 jne .fallback
 test dword [rcx+AIR_FLAGS],AIR_ACTIVE
 jz .fallback
 movss xmm0,[rcx+AIR_Y]
 ret
.fallback:
 movss xmm0,[rdx+ENTITY_X]
 movss xmm1,[rdx+ENTITY_Z]
 sub rsp,8
 call terrain_height
 add rsp,8
 addss xmm0,[fallback]
 ret
.ground:
 movss xmm0,[rdx+ENTITY_X]
 movss xmm1,[rdx+ENTITY_Z]
 sub rsp,8
 call terrain_height
 add rsp,8
 addss xmm0,[eye]
 ret
air_init:
 lea rdi,[sim_aircraft]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*AIR_STRIDE/4
 rep stosd
 lea rdi,[air_defense]
 mov ecx,ENTITY_CAPACITY*2
 rep stosd
 ret
; Genuine surviving damage hook: EDI stable actor index, no shooter information.
; Repeated hits cannot extend the commitment or reset its recovery window.
air_hit:
 cmp edi,[sim_count]
 jae .done
 cmp edi,ENTITY_CAPACITY
 jae .done
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .done
 cmp dword [rdx+ENTITY_KIND],3
 jne .done
 mov eax,edi
 shl eax,6
 lea rcx,[sim_aircraft]
 add rcx,rax
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[rcx+AIR_GENERATION]
 jne .done
 test dword [rcx+AIR_FLAGS],AIR_ACTIVE
 jz .done
 lea rdx,[air_defense]
 cmp dword [rdx+rdi*8+4],0
 jne .done
 mov eax,48
 mov esi,150
 cmp dword [rcx+AIR_ROLE],AIR_FIGHTER
 je .commit
 mov eax,90
 mov esi,210
.commit:
 mov [rdx+rdi*8],eax
 mov [rdx+rdi*8+4],esi
 mov dword [rcx+AIR_TARGET],-1
 mov dword [rcx+AIR_PASS_TICKS],0
 mov dword [rcx+AIR_MODE],AIR_EGRESS
.done:
 ret
; Each aircraft keeps flying even under formation hold. Turn rate is bounded.
air_tick:
 push rbx
 push rbp
 push r12
 sub rsp,64
 xor r12d,r12d
 lea rbx,[sim_entities]
 lea rbp,[sim_aircraft]
.loop:
 cmp dword [rbx+ENTITY_HP],0
 je .next
 cmp dword [rbx+ENTITY_KIND],3
 jne .next
 mov eax,[rbx+ENTITY_GENERATION]
 cmp [rbp+AIR_GENERATION],eax
 jne .init
 test dword [rbp+AIR_FLAGS],AIR_ACTIVE
 jnz .ready
.init:
 lea rcx,[air_defense]
 mov qword [rcx+r12*8],0
 mov [rbp+AIR_GENERATION],eax
 mov dword [rbp+AIR_FLAGS],AIR_ACTIVE
 mov eax,r12d
 shr eax,4
 and eax,1
 mov [rbp+AIR_ROLE],eax
 lea rcx,[speeds]
 movss xmm0,[rcx+rax*4]
 movss [rbp+AIR_SPEED],xmm0
 mov dword [rbp+AIR_AMMO],8
 test eax,eax
 jz .ammo
 mov dword [rbp+AIR_AMMO],180
.ammo:
 mov dword [rbp+AIR_TARGET],-1
 mov dword [rbp+AIR_MODE],AIR_PATROL
 movss xmm0,[pi]
 mulss xmm0,[half]
 cmp dword [rbx+ENTITY_SIDE],0
 je .heading
 mulss xmm0,[negative]
.heading:
 movss [rbp+AIR_HEADING],xmm0
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 call terrain_height
 mov eax,[rbp+AIR_ROLE]
 lea rcx,[altitude]
 addss xmm0,[rcx+rax*4]
 movss [rbp+AIR_Y],xmm0
.ready:
 lea rcx,[air_defense]
 cmp dword [rcx+r12*8+4],0
 je .cooldown
 dec dword [rcx+r12*8+4]
.cooldown:
 cmp dword [rbp+AIR_COOLDOWN],0
 je .goal
 dec dword [rbp+AIR_COOLDOWN]
.goal:
 lea rcx,[air_defense]
 cmp dword [rcx+r12*8],0
 jne .defense_goal
 mov eax,[rbx+ENTITY_SIDE]
 imul eax,3
 add eax,[rbx+ENTITY_FRONT]
 lea rcx,[sim_waypoints]
 movss xmm0,[rcx+rax*8]
 movss xmm1,[rcx+rax*8+4]
 cmp dword [rbp+AIR_AMMO],0
 jne .egress_goal
 mov eax,[rbx+ENTITY_SIDE]
 lea rcx,[homes]
 movss xmm0,[rcx+rax*4]
.egress_goal:
 cmp dword [rbp+AIR_PASS_TICKS],0
 jne .egress
 cmp dword [rbp+AIR_AMMO],0
 je .target
 mov dword [rbp+AIR_MODE],AIR_PATROL
 jmp .target
.defense_goal:
 mov dword [rbp+AIR_MODE],AIR_EGRESS
 mov dword [rbp+AIR_TARGET],-1
 movss xmm0,[rbx+ENTITY_X]
 addss xmm0,[rbp+AIR_VX]
 movss xmm1,[rbx+ENTITY_Z]
 addss xmm1,[rbp+AIR_VZ]
 jmp .boundary
.egress:
 dec dword [rbp+AIR_PASS_TICKS]
 ; Egress follows current forward vector rather than reversing above the victim.
 movss xmm0,[rbx+ENTITY_X]
 addss xmm0,[rbp+AIR_VX]
 movss xmm1,[rbx+ENTITY_Z]
 addss xmm1,[rbp+AIR_VZ]
 jmp .boundary
.target:
 mov eax,[rbp+AIR_TARGET]
 cmp eax,[sim_count]
 jae .boundary
 shl eax,5
 lea rcx,[sim_entities]
 add rcx,rax
 movss xmm0,[rcx+ENTITY_X]
 movss xmm1,[rcx+ENTITY_Z]
 cmp dword [rbp+AIR_ROLE],AIR_FIGHTER
 jne .boundary
 mov eax,[rbp+AIR_TARGET]
 shl eax,6
 lea rcx,[sim_aircraft]
 movss xmm2,[rcx+rax+AIR_VX]
 mulss xmm2,[lead_ticks]
 addss xmm0,xmm2
 movss xmm2,[rcx+rax+AIR_VZ]
 mulss xmm2,[lead_ticks]
 addss xmm1,xmm2
.boundary:
 mov dword [rsp+48],0
 movss xmm2,[rbx+ENTITY_X]
 comiss xmm2,[margin]
 jb .centre
 comiss xmm2,[edge]
 ja .centre
 movss xmm2,[rbx+ENTITY_Z]
 comiss xmm2,[margin]
 jb .centre
 comiss xmm2,[edge]
 jbe .steer
.centre:
 mov dword [rsp+48],1
 movss xmm0,[centre]
 movaps xmm1,xmm0
.steer:
 subss xmm0,[rbx+ENTITY_X]
 subss xmm1,[rbx+ENTITY_Z]
 call atan2f wrt ..plt
 subss xmm0,[rbp+AIR_HEADING]
 comiss xmm0,[pi]
 jbe .low_angle
 subss xmm0,[tau]
.low_angle:
 movss xmm1,[pi]
 mulss xmm1,[negative]
 comiss xmm0,xmm1
 jae .bounded
 addss xmm0,[tau]
.bounded:
 ; Boundary steering always wins over the damage-driven break.
 cmp dword [rsp+48],0
 jne .turn_limit
 lea rcx,[air_defense]
 mov eax,[rcx+r12*8]
 test eax,eax
 jz .turn_limit
 movss xmm0,[one]
 test r12d,1
 jz .defense_direction
 mulss xmm0,[negative]
.defense_direction:
 cmp dword [rbp+AIR_ROLE],AIR_FIGHTER
 jne .bomber_break
 cmp eax,24
 ja .turn_limit
 ; Reverse the bank halfway through a short fighter jink.
 mulss xmm0,[negative]
 jmp .turn_limit
.bomber_break:
 cmp eax,45
 ja .turn_limit
 xorps xmm0,xmm0 ; sustain the new egress heading after the initial break
.turn_limit:
 mov eax,[rbp+AIR_ROLE]
 lea rcx,[turns]
 movss xmm1,[rcx+rax*4]
 minss xmm0,xmm1
 mulss xmm1,[negative]
 maxss xmm0,xmm1
 movaps xmm1,xmm0
 mulss xmm1,[bank_scale]
 movss [rbp+AIR_BANK],xmm1
 addss xmm0,[rbp+AIR_HEADING]
 comiss xmm0,[pi]
 jbe .wrap_low
 subss xmm0,[tau]
.wrap_low:
 movss xmm1,[pi]
 mulss xmm1,[negative]
 comiss xmm0,xmm1
 jae .angle
 addss xmm0,[tau]
.angle:
 movss [rbp+AIR_HEADING],xmm0
 call sinf wrt ..plt
 mulss xmm0,[rbp+AIR_SPEED]
 movss [rbp+AIR_VX],xmm0
 movss xmm0,[rbp+AIR_HEADING]
 call cosf wrt ..plt
 mulss xmm0,[rbp+AIR_SPEED]
 movss [rbp+AIR_VZ],xmm0
 movss xmm0,[rbx+ENTITY_X]
 addss xmm0,[rbp+AIR_VX]
 movss [rbx+ENTITY_X],xmm0
 movss xmm1,[rbx+ENTITY_Z]
 addss xmm1,[rbp+AIR_VZ]
 movss [rbx+ENTITY_Z],xmm1
 call terrain_height
 mov eax,[rbp+AIR_ROLE]
 lea rcx,[altitude]
 addss xmm0,[rcx+rax*4]
 ; Fighters climb toward physically acquired opposing aircraft.
 cmp eax,AIR_FIGHTER
 jne .height
 mov edi,[rbp+AIR_TARGET]
 cmp edi,[sim_count]
 jae .height
 call sim_entity_height
.height:
 lea rcx,[air_defense]
 cmp dword [rcx+r12*8],0
 je .height_delta
 ; Physical climb at the existing half-metre/tick vertical limit.
 movss xmm0,[rbp+AIR_Y]
 addss xmm0,[climb]
 dec dword [rcx+r12*8]
 jnz .height_delta
 mov dword [rbp+AIR_MODE],AIR_PATROL
 cmp dword [rbp+AIR_AMMO],0
 jne .height_delta
 mov dword [rbp+AIR_MODE],AIR_RETURN
.height_delta:
 subss xmm0,[rbp+AIR_Y]
 minss xmm0,[climb]
 maxss xmm0,[minus_climb]
 movss [rbp+AIR_VY],xmm0
 addss xmm0,[rbp+AIR_Y]
 movss [rbp+AIR_Y],xmm0
 movss xmm0,[rbp+AIR_VY]
 mulss xmm0,[pitch_scale]
 movss [rbp+AIR_PITCH],xmm0
.next:
 add rbx,ENTITY_STRIDE
 add rbp,AIR_STRIDE
 inc r12d
 cmp r12d,[sim_count]
 jb .loop
 add rsp,64
 pop r12
 pop rbp
 pop rbx
 ret
; Build a separate bounded air index so dense infantry never hide every fighter.
air_combat_tick:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,104
 lea rdi,[air_counts]
 xor eax,eax
 mov ecx,1024
 rep stosd
 xor r12d,r12d
.index:
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .index_next
 cmp dword [rbx+ENTITY_KIND],3
 jne .index_next
 call .cell
 lea rcx,[air_counts]
 mov edx,[rcx+rax*4]
 inc dword [rcx+rax*4]
 and edx,7
 shl eax,3
 add eax,edx
 lea rcx,[air_samples]
 mov [rcx+rax*4],r12d
.index_next:
 inc r12d
 cmp r12d,[sim_count]
 jb .index
 xor r12d,r12d
.loop:
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 mov eax,r12d
 shl eax,6
 lea rbp,[sim_aircraft]
 add rbp,rax
 cmp dword [rbx+ENTITY_HP],0
 je .next
 cmp dword [rbx+ENTITY_KIND],3
 jne .next
 lea rcx,[air_defense]
 cmp dword [rcx+r12*8],0
 je .combat_ready
 mov dword [rbp+AIR_TARGET],-1
 mov dword [rbp+AIR_MODE],AIR_EGRESS
 jmp .next
.combat_ready:
 mov eax,[rbp+AIR_TARGET]
 mov [rsp+36],eax
 mov dword [rbp+AIR_TARGET],-1
 cmp dword [rbp+AIR_ROLE],AIR_FIGHTER
 je .fighter
 ; Keep a pass only while its previously observed victim remains in real LOS.
 mov r13d,[rsp+36]
 cmp r13d,[sim_count]
 jb .ground_candidate
.acquire_ground:
 mov r13d,[rbx+ENTITY_TARGET]
 cmp r13d,[sim_count]
 jae .next
.ground_candidate:
 mov eax,r13d
 shl eax,5
 lea r14,[sim_entities]
 add r14,rax
 cmp dword [r14+ENTITY_HP],0
 je .next
 cmp dword [r14+ENTITY_KIND],3
 je .next
 mov eax,[r14+ENTITY_SIDE]
 cmp eax,[rbx+ENTITY_SIDE]
 je .next
 movss xmm0,[r14+ENTITY_X]
 subss xmm0,[rbx+ENTITY_X]
 mulss xmm0,xmm0
 movss xmm1,[r14+ENTITY_Z]
 subss xmm1,[rbx+ENTITY_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[bomber_range2]
 ja .next
 mov edi,r13d
 call sim_entity_height
 movaps xmm4,xmm0
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbp+AIR_Y]
 movss xmm2,[rbx+ENTITY_Z]
 movss xmm3,[r14+ENTITY_X]
 movss xmm5,[r14+ENTITY_Z]
 call terrain_los
 test eax,eax
 jz .next
 jmp .observed
.fighter:
 call .cell
 mov edx,eax
 and edx,31
 mov [rsp],edx
 shr eax,5
 mov [rsp+4],eax
 movss xmm0,[range2]
 movss [rsp+8],xmm0
 mov r13d,-1
 mov r14d,-1
.z:
 mov eax,[rsp+4]
 add eax,r14d
 cmp eax,31
 ja .zn
 shl eax,5
 mov [rsp+12],eax
 mov r15d,-1
.x:
 mov eax,[rsp]
 add eax,r15d
 cmp eax,31
 ja .xn
 add eax,[rsp+12]
 lea rcx,[air_counts]
 mov ecx,[rcx+rax*4]
 test ecx,ecx
 jz .xn
 cmp ecx,8
 jbe .cnt
 mov ecx,8
.cnt:
 mov [rsp+16],ecx
 shl eax,3
 mov [rsp+20],eax
.scan:
 mov eax,[rsp+20]
 lea rcx,[air_samples]
 mov edi,[rcx+rax*4]
 mov [rsp+24],edi
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 mov eax,[rdx+ENTITY_SIDE]
 cmp eax,[rbx+ENTITY_SIDE]
 je .sn
 movss xmm0,[rdx+ENTITY_X]
 subss xmm0,[rbx+ENTITY_X]
 mulss xmm0,xmm0
 movss xmm1,[rdx+ENTITY_Z]
 subss xmm1,[rbx+ENTITY_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movss [rsp+28],xmm0
 call sim_entity_height
 movss [rsp+40],xmm0
 subss xmm0,[rbp+AIR_Y]
 mulss xmm0,xmm0
 addss xmm0,[rsp+28]
 comiss xmm0,[range2]
 ja .sn
 mov edi,[rsp+24]
 mov eax,edi
 shl eax,6
 lea rcx,[sim_aircraft]
 cmp dword [rcx+rax+AIR_ROLE],AIR_FIGHTER
 jne .priority_score
 mulss xmm0,[half]
.priority_score:
 comiss xmm0,[rsp+8]
 ja .sn
 movss [rsp+28],xmm0
 movss xmm4,[rsp+40]
 mov edi,[rsp+24]
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbp+AIR_Y]
 movss xmm2,[rbx+ENTITY_Z]
 movss xmm3,[rdx+ENTITY_X]
 movss xmm5,[rdx+ENTITY_Z]
 call terrain_los
 test eax,eax
 jz .sn
 mov r13d,[rsp+24]
 mov eax,[rsp+28]
 mov [rsp+8],eax
.sn:
 inc dword [rsp+20]
 dec dword [rsp+16]
 jnz .scan
.xn:
 inc r15d
 cmp r15d,1
 jle .x
.zn:
 inc r14d
 cmp r14d,1
 jle .z
 cmp r13d,-1
 je .next
 mov eax,r13d
 shl eax,5
 lea r14,[sim_entities]
 add r14,rax
.observed:
 mov dword [rbp+AIR_MODE],AIR_ATTACK
 mov [rbp+AIR_TARGET],r13d
 mov [rbx+ENTITY_TARGET],r13d
 cmp dword [rbp+AIR_AMMO],0
 je .empty
 cmp dword [rbp+AIR_COOLDOWN],0
 jne .next
 cmp dword [rbp+AIR_PASS_TICKS],0
 jne .next
 movss xmm0,[r14+ENTITY_X]
 subss xmm0,[rbx+ENTITY_X]
 movss xmm1,[r14+ENTITY_Z]
 subss xmm1,[rbx+ENTITY_Z]
 movaps xmm2,xmm0
 mulss xmm2,[rbp+AIR_VX]
 movaps xmm3,xmm1
 mulss xmm3,[rbp+AIR_VZ]
 addss xmm2,xmm3
 divss xmm2,[rbp+AIR_SPEED] ; ahead distance along current heading
 cmp dword [rbp+AIR_ROLE],AIR_FIGHTER
 je .gun
 movaps xmm3,xmm0
 mulss xmm3,[rbp+AIR_VZ]
 mulss xmm1,[rbp+AIR_VX]
 subss xmm3,xmm1
 divss xmm3,[rbp+AIR_SPEED]
 andps xmm3,[abs_mask]
 comiss xmm3,[bomb_cross]
 ja .next
 movss [rsp+32],xmm2
 movss xmm0,[r14+ENTITY_X]
 movss xmm1,[r14+ENTITY_Z]
 call terrain_height
 movss xmm1,[rbp+AIR_Y]
 subss xmm1,xmm0
 mulss xmm1,[two]
 divss xmm1,[grav]
 sqrtss xmm1,xmm1
 mulss xmm1,[rbp+AIR_SPEED]
 subss xmm1,[rsp+32]
 andps xmm1,[abs_mask]
 comiss xmm1,[release_margin]
 ja .next
 mov esi,PROJECTILE_BOMB
 jmp .launch
.gun:
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 sqrtss xmm0,xmm0
 maxss xmm0,[one]
 divss xmm2,xmm0
 comiss xmm2,[cone]
 jb .next
 mov edi,r13d
 call sim_entity_height
 subss xmm0,[rbp+AIR_Y]
 andps xmm0,[abs_mask]
 comiss xmm0,[bomb_cross]
 ja .next
 mov esi,PROJECTILE_AIR_GUN
.launch:
 mov edi,r12d
 call projectile_air_launch
 test eax,eax
 jnz .next
 dec dword [rbp+AIR_AMMO]
 mov dword [rbp+AIR_MODE],AIR_ATTACK
 mov dword [rbp+AIR_COOLDOWN],3
 cmp dword [rbp+AIR_ROLE],AIR_BOMBER
 jne .next
 mov dword [rbp+AIR_MODE],AIR_EGRESS
 mov dword [rbp+AIR_PASS_TICKS],210
 mov dword [rbp+AIR_TARGET],-1
 jmp .next
.empty:
 mov dword [rbp+AIR_MODE],AIR_RETURN
 mov dword [rbp+AIR_TARGET],-1
.next:
 inc r12d
 cmp r12d,[sim_count]
 jb .loop
 add rsp,104
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
.cell:
 movss xmm0,[rbx+ENTITY_X]
 mulss xmm0,[scale]
 cvttss2si eax,xmm0
 and eax,31
 movss xmm0,[rbx+ENTITY_Z]
 mulss xmm0,[scale]
 cvttss2si edx,xmm0
 and edx,31
 shl edx,5
 add eax,edx
 ret
air_hash:
 lea rsi,[sim_aircraft]
 mov ecx,[sim_count]
 shl ecx,6
 test ecx,ecx
 jz .done
.bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .bytes
.done:
 lea rsi,[air_defense]
 mov ecx,[sim_count]
 shl ecx,3
 test ecx,ecx
 jz .return
.defense_bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .defense_bytes
.return: ret
section .note.GNU-stack noalloc noexec nowrite progbits
