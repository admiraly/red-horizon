; Continuous fixed-step aircraft. All perception is range/LOS limited.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_escort.inc"
%include "schemas/air_flight.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,sim_waypoints,terrain_height,world_los
extern air_bank_step,air_vertical_step,air_pursuit_blend,air_recovery_goal
extern air_observation_init,air_observation_capture,air_observation_goal,air_observation_hash,sim_air_observations
extern air_separation_init,air_separation_build,air_separation_step,air_separation_hash,sim_air_separation
extern air_threats_reset,air_threats_build,air_threat_query
extern sinf,cosf,atan2f,projectile_air_launch,air_bomb_fall_time
extern air_gun_solution_ready,air_gun_intercept
extern air_escort_init,air_escort_tick,air_escort_goal,air_escort_threat,air_escort_hash
extern air_admission_init,air_admission_begin,air_admission_request
extern air_admission_flush,air_admission_hash,air_admission_enabled
section .bss align=64
global sim_aircraft
sim_aircraft: resb ENTITY_CAPACITY*AIR_STRIDE
; Private fixed state: remaining maneuver and refractory ticks, indexed by stable ID.
air_defense: resd ENTITY_CAPACITY*2
air_break_direction: resd ENTITY_CAPACITY
air_boundary: resd ENTITY_CAPACITY
; Last physically observed strike position; no enemy reads during recall.
global sim_air_strikes
sim_air_strikes: resb ENTITY_CAPACITY*AIR_FLIGHT_STRIKE_STRIDE
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
climb: dd AIR_FLIGHT_VERTICAL_LIMIT
minus_climb: dd -AIR_FLIGHT_VERTICAL_LIMIT
corner_margin: dd AIR_FLIGHT_CORNER_MARGIN
corner_edge: dd 6800.0 ; fixed8000m map minus policy1200m corner margin
pitch_scale: dd 0.15
half: dd 0.5
scale: dd 0.004
margin: dd AIR_FLIGHT_CORNER_MARGIN
edge: dd 6800.0
centre: dd 4000.0
range2: dd 562500.0
bomber_range2: dd 1440000.0
cone: dd 0.985
bomb_cross: dd 28.0
release_margin: dd 18.0
grav: dd 0.0109
bomb_max_fall: dd 240.0
two: dd 2.0
round_speed2: dd 784.0
world_edge: dd 8000.0
strike_approach: dd AIR_FLIGHT_STRIKE_APPROACH
strike_reached: dd AIR_FLIGHT_STRIKE_REACHED_SQ
strike_passed: dd -100.0
escort_weight: dd AIR_ESCORT_THREAT_WEIGHT
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
 lea rdi,[air_break_direction]
 mov ecx,ENTITY_CAPACITY
 rep stosd
 lea rdi,[air_boundary]
 mov ecx,ENTITY_CAPACITY
 rep stosd
 lea rdi,[sim_air_strikes]
 mov ecx,ENTITY_CAPACITY*AIR_FLIGHT_STRIKE_STRIDE/4
 rep stosd
 sub rsp,8
 call air_separation_init
 call air_observation_init
 call air_threats_reset
 call air_escort_init
 add rsp,8
 jmp air_admission_init
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
 lea rdx,[air_break_direction]
 mov eax,__float32__(1.0)
 test edi,1
 jz .direction
 mov eax,__float32__(-1.0)
.direction:
 mov [rdx+rdi*4],eax
 imul eax,edi,AIR_FLIGHT_STRIKE_STRIDE
 lea rdx,[sim_air_strikes]
 mov dword [rdx+rax+32],0 ; defensive abort requires a fresh straight approach
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
 call air_separation_build
 call air_threats_build
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
 ; Genuine new/uninitialized generation, not an in-flight recovery refill.
 xorps xmm0,xmm0
 movups [rbp],xmm0
 movups [rbp+16],xmm0
 movups [rbp+32],xmm0
 movups [rbp+48],xmm0
 mov edi,r12d
 shl edi,6
 lea rcx,[sim_air_observations]
 add rcx,rdi
 movups [rcx],xmm0
 movups [rcx+16],xmm0
 movups [rcx+32],xmm0
 movups [rcx+48],xmm0
 mov eax,r12d
 shl eax,4
 lea rcx,[sim_air_separation]
 mov qword [rcx+rax],0
 mov qword [rcx+rax+8],0
 lea rcx,[air_defense]
 mov qword [rcx+r12*8],0
 lea rcx,[air_break_direction]
 mov dword [rcx+r12*4],0
 lea rcx,[air_boundary]
 mov dword [rcx+r12*4],0
 imul edx,r12d,AIR_FLIGHT_STRIKE_STRIDE
 lea rcx,[sim_air_strikes]
 mov qword [rcx+rdx],0
 mov qword [rcx+rdx+8],0
 mov qword [rcx+rdx+16],0
 mov qword [rcx+rdx+24],0
 mov qword [rcx+rdx+32],0
 mov eax,[rbx+ENTITY_GENERATION]
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
 mov dword [rsp+52],0 ; no vertical emergency override
 mov dword [rsp+56],0 ; no current-frame fighter intercept point yet
 lea rcx,[air_defense]
 cmp dword [rcx+r12*8+4],0
 je .cooldown
 dec dword [rcx+r12*8+4]
 .cooldown:
 lea rcx,[air_defense]
 cmp dword [rcx+r12*8+4],0
 jne .weapon_cooldown
 cmp dword [rcx+r12*8],0
 jne .weapon_cooldown
 mov edi,r12d
 call air_threat_query
 cmp eax,-1
 je .weapon_cooldown
 ; Query observes the round, not its shooter's hidden pose or intended target.
 mov edi,r12d
 call air_hit
 lea rcx,[air_break_direction]
 movss [rcx+r12*4],xmm0
.weapon_cooldown:
 lea rcx,[air_defense]
 mov esi,[rcx+r12*8]
 mov edi,r12d
 call air_separation_step
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
 mov eax,r12d
 shl eax,4
 lea rcx,[sim_air_separation]
 cmp dword [rcx+rax+4],0
 je .recovery_goal
 mov dword [rbp+AIR_MODE],AIR_EGRESS
 mov dword [rbp+AIR_TARGET],-1
 mov dword [rbx+ENTITY_TARGET],-1
 mov dword [rbp+AIR_PASS_TICKS],0
 imul eax,r12d,AIR_FLIGHT_STRIKE_STRIDE
 lea rcx,[sim_air_strikes]
 mov dword [rcx+rax+32],0
 jmp .boundary
.recovery_goal:
 mov edi,r12d
 call air_recovery_goal
 test eax,eax
 jz .egress_goal
 mov dword [rbp+AIR_MODE],AIR_RETURN
 mov dword [rbp+AIR_TARGET],-1
 mov dword [rbx+ENTITY_TARGET],-1
 mov dword [rbp+AIR_PASS_TICKS],0
 jmp .boundary
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
 cmp dword [rbp+AIR_ROLE],AIR_FIGHTER
 je .fighter_goal
.strike_goal:
 mov edi,r12d
 call air_strike_goal
 test eax,eax
 jz .boundary
 imul edx,r12d,AIR_FLIGHT_STRIKE_STRIDE
 lea rcx,[sim_air_strikes]
 add rcx,rdx
 cmp dword [rcx+32],0
 jne .passed_strike
 movaps xmm2,xmm0
 subss xmm2,[rbx+ENTITY_X]
 movaps xmm3,xmm1
 subss xmm3,[rbx+ENTITY_Z]
 mulss xmm2,xmm2
 mulss xmm3,xmm3
 addss xmm2,xmm3
 comiss xmm2,[strike_reached]
 ja .boundary
 mov dword [rcx+32],1
 jmp .strike_recall
.passed_strike:
 movaps xmm2,xmm0
 subss xmm2,[rbx+ENTITY_X]
 mulss xmm2,[rcx+24]
 movaps xmm3,xmm1
 subss xmm3,[rbx+ENTITY_Z]
 mulss xmm3,[rcx+28]
 addss xmm2,xmm3
 comiss xmm2,[strike_passed]
 jae .boundary
 mov dword [rcx+32],0
.strike_recall:
 mov edi,r12d
 call air_strike_goal
 jmp .boundary
.escort_goal:
 mov edi,r12d
 call air_escort_goal
 jmp .boundary
.fighter_goal:
 mov edi,r12d
 call air_escort_goal ; own friendly mission, never hidden enemy ground truth
 ; Enemy guidance uses only our last fresh visual snapshot, not its live body.
 movss [rsp+32],xmm0
 movss [rsp+36],xmm1
 mov edi,r12d
 call air_observation_goal
 test eax,eax
 jz .no_observation
 movss [rsp+60],xmm6
 movss [rsp],xmm0
 movss [rsp+8],xmm1
 movss [rsp+4],xmm2
 subss xmm0,[rbx+ENTITY_X]
 subss xmm1,[rbp+AIR_Y]
 subss xmm2,[rbx+ENTITY_Z]
 call air_gun_intercept
 test eax,eax
 jnz .intercept_fallback
 addss xmm0,[rbx+ENTITY_X]
 addss xmm1,[rbp+AIR_Y]
 addss xmm2,[rbx+ENTITY_Z]
 movss [rsp],xmm0
 movss [rsp+8],xmm1
 movss [rsp+4],xmm2
.intercept_fallback:
 mov dword [rsp+56],1 ; observed or estimated lead is also the pitch goal
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 jmp .boundary
.no_observation:
 movss xmm0,[rsp+32]
 movss xmm1,[rsp+36]
 jmp .escort_goal
.boundary:
 mov dword [rsp+48],0
 lea rcx,[air_boundary]
 cmp dword [rcx+r12*4],0
 je .boundary_check
 ; Finish the banked recovery before handing steering back to the mission.
 movss xmm2,[rbx+ENTITY_X]
 comiss xmm2,[corner_margin]
 jb .centre
 comiss xmm2,[corner_edge]
 ja .centre
 movss xmm2,[rbx+ENTITY_Z]
 comiss xmm2,[corner_margin]
 jb .centre
 comiss xmm2,[corner_edge]
 ja .centre
 mov dword [rcx+r12*4],0
.boundary_check:
 movss xmm2,[rbx+ENTITY_X]
 comiss xmm2,[margin]
 jb .centre
 comiss xmm2,[edge]
 ja .centre
 movss xmm2,[rbx+ENTITY_Z]
 comiss xmm2,[margin]
 jb .centre
 comiss xmm2,[edge]
 ja .centre
 ; Corner turn envelopes need more room than single-edge turns.
 movss xmm2,[rbx+ENTITY_X]
 comiss xmm2,[corner_margin]
 jb .corner_z
 comiss xmm2,[corner_edge]
 jbe .steer
.corner_z:
 movss xmm2,[rbx+ENTITY_Z]
 comiss xmm2,[corner_margin]
 jb .centre
 comiss xmm2,[corner_edge]
 jbe .steer
.centre:
 lea rcx,[air_boundary]
 mov dword [rcx+r12*4],1
 mov dword [rsp+48],1
 movss xmm0,[centre]
 movaps xmm1,xmm0
.steer:
 subss xmm0,[rbx+ENTITY_X]
 subss xmm1,[rbx+ENTITY_Z]
 call atan2f wrt ..plt
 cmp dword [rsp+48],0
 jne .heading_ready
 cmp dword [rsp+56],0
 je .heading_ready
 movss [rsp+16],xmm0
 movss xmm0,[rsp+32]
 subss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rsp+36]
 subss xmm1,[rbx+ENTITY_Z]
 call atan2f wrt ..plt
 movss xmm1,[rsp+16]
 movss xmm2,[rsp+60]
 xor edi,edi
 call air_pursuit_blend
.heading_ready:
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
 jz .separation_turn
 lea rcx,[air_break_direction]
 movss xmm0,[rcx+r12*4]
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
 jmp .turn_limit
.separation_turn:
 mov eax,r12d
 shl eax,4
 lea rcx,[sim_air_separation]
 cmp dword [rcx+rax+4],0
 je .turn_limit
 movss xmm0,[one] ; same local right-turn rule for converging friendly pilots
.turn_limit:
 mov edi,[rbp+AIR_ROLE]
 mov esi,[rsp+48]
 movss xmm1,[rbp+AIR_SPEED]
 movss xmm2,[rbp+AIR_BANK]
 call air_bank_step
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
 ; Preview one horizontal step for terrain clearance, without moving yet.
 movss xmm1,[rbx+ENTITY_Z]
 addss xmm1,[rbp+AIR_VZ]
 call terrain_height
 mov eax,[rbp+AIR_ROLE]
 lea rcx,[altitude]
 addss xmm0,[rcx+rax*4]
 movss [rsp+24],xmm0 ; own terrain-clearance altitude
 ; Fighters climb toward physically acquired opposing aircraft.
 cmp eax,AIR_FIGHTER
 jne .height
 cmp dword [rsp+56],0
 je .height
 ; Pitch the flight nose toward the same lead point used by horizontal
 ; steering, including the target's current vertical motion. A fixed climb
 ; to its present altitude cannot aim a physically forward-firing cannon.
 movss xmm1,[rsp]
 subss xmm1,[rbx+ENTITY_X]
 mulss xmm1,xmm1
 movss xmm2,[rsp+4]
 subss xmm2,[rbx+ENTITY_Z]
 mulss xmm2,xmm2
 addss xmm1,xmm2
 sqrtss xmm1,xmm1
 maxss xmm1,[one]
 movss xmm0,[rsp+8]
 subss xmm0,[rbp+AIR_Y]
 mulss xmm0,[rbp+AIR_SPEED]
 divss xmm0,xmm1
 addss xmm0,[rbp+AIR_Y]
 jmp .height
.height:
 lea rcx,[air_defense]
 cmp dword [rcx+r12*8],0
 je .height_delta
 mov dword [rsp+52],1
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
 cmp dword [rsp+52],0
 jne .vertical_ready
 cmp dword [rsp+56],0
 je .vertical_ready
 movaps xmm1,xmm0
 movss xmm0,[rsp+24]
 subss xmm0,[rbp+AIR_Y]
 minss xmm0,[climb]
 maxss xmm0,[minus_climb]
 movss xmm2,[rsp+60]
 mov edi,1
 call air_pursuit_blend
.vertical_ready:
 mov edi,[rbp+AIR_ROLE]
 movss xmm1,[rbp+AIR_SPEED]
 movss xmm2,[rbp+AIR_VY]
 call air_vertical_step
 test eax,eax
 jnz .next ; Invalid flight inputs publish no position or vertical-state writes.
 movss [rbp+AIR_VY],xmm0
 addss xmm0,[rbp+AIR_Y]
 movss [rbp+AIR_Y],xmm0
 movss [rbp+AIR_PITCH],xmm2
 ; Climbing uses part of total airspeed; heading-aligned horizontal travel
 ; is reduced accordingly rather than adding vertical speed for free.
 divss xmm1,[rbp+AIR_SPEED]
 movss xmm0,[rbp+AIR_VX]
 mulss xmm0,xmm1
 movss [rbp+AIR_VX],xmm0
 addss xmm0,[rbx+ENTITY_X]
 movss [rbx+ENTITY_X],xmm0
 movss xmm0,[rbp+AIR_VZ]
 mulss xmm0,xmm1
 movss [rbp+AIR_VZ],xmm0
 addss xmm0,[rbx+ENTITY_Z]
 movss [rbx+ENTITY_Z],xmm0
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
 call air_admission_begin
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
 call air_escort_tick
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
 mov eax,r12d
 shl eax,4
 lea rcx,[sim_air_separation]
 cmp dword [rcx+rax+4],0
 je .separation_clear
 mov dword [rbp+AIR_TARGET],-1
 mov dword [rbx+ENTITY_TARGET],-1
 mov dword [rbp+AIR_MODE],AIR_EGRESS
 jmp .next
.separation_clear:
 mov edi,r12d
 call air_recovery_goal
 test eax,eax
 jz .combat_engage
 mov dword [rbp+AIR_TARGET],-1
 mov dword [rbx+ENTITY_TARGET],-1
 mov dword [rbp+AIR_PASS_TICKS],0
 mov dword [rbp+AIR_MODE],AIR_RETURN
 jmp .next
.combat_engage:
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
 call world_los
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
 mov r14d,-AIR_ACQUIRE_CELLS
.z:
 mov eax,[rsp+4]
 add eax,r14d
 cmp eax,31
 ja .zn
 shl eax,5
 mov [rsp+12],eax
 mov r15d,-AIR_ACQUIRE_CELLS
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
 mov edi,r12d
 mov esi,[rsp+24]
 call air_escort_threat
 test eax,eax
 jz .escort_score_ready
 mulss xmm0,[escort_weight]
.escort_score_ready:
 comiss xmm0,[rsp+8]
 ja .sn
 movss [rsp+28],xmm0
 mov edi,r12d
 mov esi,[rsp+24]
 call air_observation_capture
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
 cmp r15d,AIR_ACQUIRE_CELLS
 jle .x
.zn:
 inc r14d
 cmp r14d,AIR_ACQUIRE_CELLS
 jle .z
 cmp r13d,-1
 je .next
 mov eax,r13d
 shl eax,5
 lea r14,[sim_entities]
 add r14,rax
.observed:
 cmp dword [rbp+AIR_ROLE],AIR_BOMBER
 jne .strike_saved
 imul edx,r12d,AIR_FLIGHT_STRIKE_STRIDE
 lea rcx,[sim_air_strikes]
 add rcx,rdx
 mov eax,[rbx+ENTITY_GENERATION]
 cmp eax,[rcx+16]
 je .strike_direction_saved
 ; Strike ingress is a unit XZ direction, independent of climb speed.
 movss xmm2,[rbp+AIR_VX]
 mulss xmm2,xmm2
 movss xmm3,[rbp+AIR_VZ]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 sqrtss xmm2,xmm2
 ucomiss xmm2,[zero]
 jp .next
 jbe .next
 movss xmm0,[rbp+AIR_VX]
 divss xmm0,xmm2
 movss [rcx+24],xmm0
 movss xmm0,[rbp+AIR_VZ]
 divss xmm0,xmm2
 movss [rcx+28],xmm0
 mov dword [rcx+32],1
.strike_direction_saved:
 mov eax,[r14+ENTITY_X]
 mov [rcx],eax
 mov eax,[r14+ENTITY_Z]
 mov [rcx+4],eax
 mov [rcx+8],r13d
 mov eax,[r14+ENTITY_GENERATION]
 mov [rcx+12],eax
 mov eax,[rbx+ENTITY_GENERATION]
 mov [rcx+16],eax
 mov eax,[sim_tick_count]
 add eax,AIR_FLIGHT_STRIKE_MEMORY
 mov [rcx+20],eax
.strike_saved:
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
 ; Project ground distances on the actual unit XZ direction.
 movss xmm4,[rbp+AIR_VX]
 mulss xmm4,xmm4
 movss xmm5,[rbp+AIR_VZ]
 mulss xmm5,xmm5
 addss xmm4,xmm5
 sqrtss xmm4,xmm4
 ucomiss xmm4,[zero]
 jp .next
 jbe .next
 movss [rsp+44],xmm4
 divss xmm2,xmm4 ; ahead distance along current horizontal heading
 cmp dword [rbp+AIR_ROLE],AIR_FIGHTER
 je .gun
 movaps xmm3,xmm0
 mulss xmm3,[rbp+AIR_VZ]
 mulss xmm1,[rbp+AIR_VX]
 subss xmm3,xmm1
 divss xmm3,xmm4
 andps xmm3,[abs_mask]
 comiss xmm3,[bomb_cross]
 ja .next
 movss [rsp+32],xmm2
 movss xmm0,[r14+ENTITY_X]
 movss xmm1,[r14+ENTITY_Z]
 call terrain_height
 movss xmm1,[rbp+AIR_Y]
 subss xmm1,xmm0
 ; Bombs inherit climb/descent, and position advances before gravity.
 ; h + (vy + g/2)t - (g/2)t^2 = 0 on discrete tick endpoints.
 movaps xmm0,xmm1
 movss xmm1,[rbp+AIR_VY]
 call air_bomb_fall_time
 movaps xmm1,xmm0
 comiss xmm1,[zero]
 jbe .next
 comiss xmm1,[bomb_max_fall]
 ja .next
 mulss xmm1,[rsp+44] ; bomb inherits actual horizontal displacement
 subss xmm1,[rsp+32]
 andps xmm1,[abs_mask]
 comiss xmm1,[release_margin]
 ja .next
 mov esi,PROJECTILE_BOMB
 jmp .launch
.gun:
 ; Common producer predicate compares the full current flight nose against
 ; the physically acquired target. Never aim the round vertically for it.
 mov edi,r12d
 call air_gun_solution_ready
 test eax,eax
 jnz .next
 mov esi,PROJECTILE_AIR_GUN
.launch:
 cmp dword [air_admission_enabled],0
 je .legacy_launch
 mov edi,r12d
 mov esi,r13d
 call air_admission_request
 jmp .next
.legacy_launch:
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
 call air_admission_flush
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
global air_strike_goal
; EDI owner, XMM0/1 fallback -> EAX valid, XMM0/1 remembered XZ if valid.
; Stored target identity is audit data; recall never reads the target entity.
air_strike_goal:
 cmp edi,[sim_count]
 jae .invalid
 cmp edi,ENTITY_CAPACITY
 jae .invalid
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .invalid
 cmp dword [rdx+ENTITY_KIND],3
 jne .invalid
 mov eax,edi
 shl eax,6
 lea rcx,[sim_aircraft]
 add rcx,rax
 test dword [rcx+AIR_FLAGS],AIR_ACTIVE
 jz .invalid
 cmp dword [rcx+AIR_ROLE],AIR_BOMBER
 jne .invalid
 cmp dword [rcx+AIR_AMMO],0
 je .invalid
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[rcx+AIR_GENERATION]
 jne .invalid
 imul edi,AIR_FLIGHT_STRIKE_STRIDE
 lea rcx,[sim_air_strikes]
 add rcx,rdi
 cmp eax,[rcx+16]
 jne .invalid
 mov eax,[rcx+20]
 sub eax,[sim_tick_count]
 jle .invalid
 cmp eax,AIR_FLIGHT_STRIKE_MEMORY
 ja .invalid
 movss xmm2,[rcx]
 ucomiss xmm2,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm2,[world_edge]
 ja .invalid
 movss xmm3,[rcx+4]
 ucomiss xmm3,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm3,[world_edge]
 ja .invalid
 movss xmm0,[rcx]
 movss xmm1,[rcx+4]
 cmp dword [rcx+32],0
 jne .success
 movss xmm2,[rcx+24]
 mulss xmm2,[strike_approach]
 subss xmm0,xmm2
 movss xmm2,[rcx+28]
 mulss xmm2,[strike_approach]
 subss xmm1,xmm2
.success:
 mov eax,1
 ret
.invalid:
 xor eax,eax
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
.return:
 lea rsi,[air_boundary]
 mov ecx,[sim_count]
 shl ecx,2
 test ecx,ecx
 jz .strikes
.boundary_bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .boundary_bytes
.strikes:
 lea rsi,[air_break_direction]
 mov ecx,[sim_count]
 shl ecx,2
 test ecx,ecx
 jz .strike_memory
.direction_bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .direction_bytes
.strike_memory:
 lea rsi,[sim_air_strikes]
 imul ecx,[sim_count],AIR_FLIGHT_STRIKE_STRIDE
 test ecx,ecx
 jz .missions
.strike_bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .strike_bytes
.missions:
 sub rsp,8
 call air_separation_hash
 call air_observation_hash
 call air_escort_hash
 add rsp,8
 jmp air_admission_hash
section .note.GNU-stack noalloc noexec nowrite progbits
