; Authoritative fixed-30Hz tracked-hull actuator. SysV/SSE2; no allocation.
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/combat.inc"
%include "schemas/ground_motion.inc"
%include "schemas/ground_surfaces.inc"
%macro MATHCALL 1
%ifidn __OUTPUT_FORMAT__,elf64
 call %1 wrt ..plt
%else
 call %1
%endif
%endmacro
default rel
extern sim_entities,sim_count,sim_waypoints
extern sim_players,sim_player_vehicle,sim_vehicles,vehicle_entity_driver,vehicle_driver_generation
extern crowd_move,crowd_step,crowd_hull_step,terrain_road_body,sinf,cosf,atan2f
section .bss align=64
global sim_ground_motion,ground_enabled
sim_ground_motion: resb ENTITY_CAPACITY*GROUND_STRIDE
ground_enabled: resd 1
section .rodata
zero: dd 0.0
roundoff: dd 0.001
pi: dd 3.141592653589793
tau: dd 6.283185307179586
reverse_threshold: dd 2.35619449
sharp: dd 1.04719755
half: dd 0.5
eight: dd 8.0
one: dd 1.0
surface_multipliers: dd GROUND_TANK_OFFROAD,GROUND_ARTILLERY_OFFROAD
body_radii: dd GROUND_TANK_RADIUS,GROUND_ARTILLERY_RADIUS
source_max: dd 8000.0
map_min: dd -8000.0
map_max: dd 16000.0
align 16
abs_mask: times 4 dd 0x7fffffff
sign_mask: times 4 dd 0x80000000
caps: dd 0.6,0.2
ai_caps: dd 0.5,0.2
reverse_caps: dd 0.18,0.08
accel: dd 0.02,0.01
brake: dd 0.04,0.025
turn_caps: dd 0.04,0.025
stationary_turn: dd 0.06,0.025
section .text
global ground_init,ground_step,ground_hash
; Zero all authoritative sidecar state, then seed valid births from route.
ground_init:
 push rbx
 push r12
 sub rsp,8
 lea rdi,[sim_ground_motion]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*GROUND_STRIDE/8
 rep stosq
 mov dword [ground_enabled],1
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .done
 xor r12d,r12d
.loop:
 cmp r12d,[sim_count]
 jae .done
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .next
 mov eax,[rbx+ENTITY_KIND]
 sub eax,1
 cmp eax,1
 ja .next
 cmp dword [rbx+ENTITY_GENERATION],0
 je .next
 cmp dword [rbx+ENTITY_SIDE],1
 ja .next
 cmp dword [rbx+ENTITY_FRONT],2
 ja .next
 movss xmm0,[rbx+ENTITY_X]
 call valid_source_position
 test eax,eax
 jz .next
 movss xmm0,[rbx+ENTITY_Z]
 call valid_source_position
 test eax,eax
 jz .next
 mov edi,r12d
 call seed
.next:
 inc r12d
 jmp .loop
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
 ; Map sources require playable coordinates; only steering goals may extend wide.
valid_source_position:
 ucomiss xmm0,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[source_max]
 ja .invalid
 mov eax,1
 ret
.invalid:
 xor eax,eax
 ret
; finite bounded local steering coordinate XMM0 -> EAX boolean.
valid_position:
 ucomiss xmm0,[map_min]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[map_max]
 ja .invalid
 mov eax,1
 ret
.invalid:
 xor eax,eax
 ret
; RBX valid entity, EDI ID. Seed zeroed state and heading; preserves RBX.
seed:
 push r12
 sub rsp,16
 mov eax,edi
 shl eax,5
 lea r12,[sim_ground_motion]
 add r12,rax
 pxor xmm0,xmm0
 movups [r12],xmm0
 movups [r12+16],xmm0
 mov eax,[rbx+ENTITY_GENERATION]
 mov [r12+GROUND_GENERATION],eax
 mov eax,[rbx+ENTITY_KIND]
 mov [r12+GROUND_KIND],eax
 mov dword [r12+GROUND_FLAGS],GROUND_ACTIVE
 mov eax,[rbx+ENTITY_SIDE]
 imul eax,3
 add eax,[rbx+ENTITY_FRONT]
 lea rdx,[sim_waypoints]
 movss xmm0,[rdx+rax*8]
 movss [rsp],xmm0
 call valid_position
 test eax,eax
 jz .done
 mov eax,[rbx+ENTITY_SIDE]
 imul eax,3
 add eax,[rbx+ENTITY_FRONT]
 lea rdx,[sim_waypoints]
 movss xmm0,[rdx+rax*8+4]
 movss [rsp+4],xmm0
 call valid_position
 test eax,eax
 jz .done
 movss xmm0,[rsp]
 subss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rsp+4]
 subss xmm1,[rbx+ENTITY_Z]
 movaps xmm2,xmm0
 mulss xmm2,xmm2
 movaps xmm3,xmm1
 mulss xmm3,xmm3
 addss xmm2,xmm3
 ucomiss xmm2,[zero]
 je .done
 MATHCALL atan2f
 call canonical_zero
 movss [r12+GROUND_HEADING],xmm0
.done:
 add rsp,16
 pop r12
 ret
; EDI entity, ESI AI/driver. Input five floats; returns physical endpoint.
; Stack: input0..16, desiredangle20, delta24, targetspeed28, newheading32,
; signed speed36, endpoint40/44, sin48/cos52, role index56, mode60, ID64,
; original navigation goal distance68, deferred birth reset72, surface multiplier76.
ground_step:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,88
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 mov [rsp+60],esi
 mov [rsp+64],edi
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .out
 cmp edi,[sim_count]
 jae .out
 cmp esi,1
 ja .out
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 lea rbp,[sim_ground_motion]
 add rbp,rax
 cmp dword [rbx+ENTITY_HP],0
 je .out
 cmp dword [rbx+ENTITY_GENERATION],0
 je .out
 mov eax,[rbx+ENTITY_KIND]
 sub eax,1
 cmp eax,1
 ja .out
 mov [rsp+56],eax
 cmp dword [rbx+ENTITY_SIDE],1
 ja .out
 cmp dword [rbx+ENTITY_FRONT],2
 ja .out
 ; Exact authoritative source, no caller teleport or mismatched prediction.
 ucomiss xmm0,[rbx+ENTITY_X]
 jp .out
 jne .out
 ucomiss xmm1,[rbx+ENTITY_Z]
 jp .out
 jne .out
 movss xmm0,[rsp]
 call valid_source_position
 test eax,eax
 jz .out
 movss xmm0,[rsp+4]
 call valid_source_position
 test eax,eax
 jz .out
 mov r12d,2
.validate:
 movss xmm0,[rsp+r12*4]
 call valid_position
 test eax,eax
 jz .out
 inc r12d
 cmp r12d,4
 jb .validate
 movss xmm0,[rsp+16]
 ucomiss xmm0,[zero]
 jp .out
 jb .out
 movd eax,xmm0
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .out
 cmp dword [rsp+60],GROUND_DRIVER
 jne .validated
 cmp dword [rbx+ENTITY_KIND],1
 jne .out
 cmp dword [rbx+ENTITY_SIDE],0
 jne .out
 mov eax,[rsp+64]
 lea rdx,[vehicle_entity_driver]
 mov edi,[rdx+rax*4]
 cmp edi,PLAYER_CAPACITY
 jae .out
 lea rdx,[sim_player_vehicle]
 cmp [rdx+rdi*4],eax
 jne .out
 mov ecx,edi
 shl ecx,5
 lea rdx,[sim_vehicles]
 add rdx,rcx
 cmp dword [rdx+VEHICLE_ACTIVE],1
 jne .out
 cmp [rdx+VEHICLE_ENTITY],eax
 jne .out
 cmp [rdx+VEHICLE_DRIVER],edi
 jne .out
 mov ecx,[rbx+ENTITY_GENERATION]
 cmp [rdx+VEHICLE_ENTITY_GENERATION],ecx
 jne .out
 mov ecx,edi
 shl ecx,6
 lea rdx,[sim_players]
 add rdx,rcx
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .out
 cmp dword [rdx+PLAYER_HP],0
 je .out
 cmp dword [rdx+PLAYER_GENERATION],0
 je .out
 mov ecx,[rdx+PLAYER_GENERATION]
 lea rdx,[vehicle_driver_generation]
 cmp [rdx+rdi*4],ecx
 jne .out
.validated:
 cmp dword [ground_enabled],0
 je .legacy
 mov dword [rsp+72],0
 mov eax,[rbx+ENTITY_GENERATION]
 cmp [rbp+GROUND_GENERATION],eax
 jne .reset
 mov eax,[rbx+ENTITY_KIND]
 cmp [rbp+GROUND_KIND],eax
 jne .reset
 cmp dword [rbp+GROUND_FLAGS],GROUND_ACTIVE
 jne .reset
 ; Reject corrupted current state instead of producing NaNs or hidden mutation.
 xor r12d,r12d
.state_finite:
 mov eax,[rbp+r12*4]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .out
 inc r12d
 cmp r12d,5
 jb .state_finite
 movss xmm0,[rbp+GROUND_HEADING]
 andps xmm0,[abs_mask]
 ucomiss xmm0,[pi]
 ja .out
 mov eax,[rsp+56]
 lea rdx,[caps]
 movss xmm0,[rbp+GROUND_SPEED]
 andps xmm0,[abs_mask]
 ucomiss xmm0,[rdx+rax*4]
 ja .out
 lea rdx,[stationary_turn]
 movss xmm0,[rbp+GROUND_TURN]
 andps xmm0,[abs_mask]
 ucomiss xmm0,[rdx+rax*4]
 ja .out
 lea rdx,[caps]
 movss xmm1,[rdx+rax*4]
 addss xmm1,[roundoff]
 movss xmm0,[rbp+GROUND_VX]
 andps xmm0,[abs_mask]
 ucomiss xmm0,xmm1
 ja .out
 movss xmm0,[rbp+GROUND_VZ]
 andps xmm0,[abs_mask]
 ucomiss xmm0,xmm1
 ja .out
 jmp .surface
.reset:
 ; Delay reset until the stateless surface query succeeds: failed inputs never mutate.
 mov dword [rsp+72],1
.surface:
 mov eax,[rsp+56]
 lea rdx,[body_radii]
 movss xmm2,[rdx+rax*4]
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 call terrain_road_body
 cmp eax,1
 ja .out
 movss xmm0,[one]
 test eax,eax
 jnz .surface_ready
 mov eax,[rsp+56]
 lea rdx,[surface_multipliers]
 movss xmm0,[rdx+rax*4]
.surface_ready:
 movss [rsp+76],xmm0
 cmp dword [rsp+72],0
 je .evolve
 mov edi,[rsp+64]
 call seed
.evolve:
 mov eax,[rsp+56]
 lea rdx,[ai_caps]
 movss xmm4,[rdx+rax*4]
 mulss xmm4,[rsp+76]
 minss xmm4,[rsp+16]
 cmp dword [rsp+60],GROUND_DRIVER
 jne .intent
 ; Driver actual cap .6, not AI .5.
 movss xmm4,[caps]
 mulss xmm4,[rsp+76]
 minss xmm4,[rsp+16]
.intent:
 movss [rsp+16],xmm4
 ; Preserve distance to actual nav goal, not the crowd's one-tick intent point.
 movss xmm0,[rsp+8]
 subss xmm0,[rsp]
 mulss xmm0,xmm0
 movss xmm1,[rsp+12]
 subss xmm1,[rsp+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 sqrtss xmm0,xmm0
 movss [rsp+68],xmm0
 cmp dword [rsp+60],GROUND_AI
 jne .target
 ; Existing bounded AI navigation contributes intent, never free displacement.
 mov edi,[rsp+64]
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 call crowd_move
 movss [rsp+8],xmm0
 movss [rsp+12],xmm1
.target:
 movss xmm0,[rsp+8]
 subss xmm0,[rsp]
 movss xmm1,[rsp+12]
 subss xmm1,[rsp+4]
 movaps xmm2,xmm0
 mulss xmm2,xmm2
 movaps xmm3,xmm1
 mulss xmm3,xmm3
 addss xmm2,xmm3
 sqrtss xmm2,xmm2
 minss xmm2,[rsp+16]
 cmp dword [rsp+60],GROUND_AI
 jne .target_speed
 ; Invert exact discrete stopping distance S=n*v-b*n*(n-1)/2.
 ; n=floor((sqrt(1+8*d/b)-1)/2)+1 selects the stopping-speed interval.
 ; AI desired speed remains within the unchanged cap and brake envelope.
 ; Translation still follows the hull axis; no endpoint snap is used.
 mov eax,[rsp+56]
 lea rdx,[brake]
 movss xmm4,[rdx+rax*4]
 movss xmm3,[rsp+68]
 movaps xmm5,xmm3
 divss xmm5,xmm4
 mulss xmm5,[eight]
 addss xmm5,[one]
 sqrtss xmm5,xmm5
 subss xmm5,[one]
 mulss xmm5,[half]
 cvttss2si eax,xmm5
 inc eax
 cvtsi2ss xmm5,eax
 movaps xmm6,xmm5
 subss xmm6,[one]
 mulss xmm6,xmm5
 mulss xmm6,xmm4
 mulss xmm6,[half]
 addss xmm3,xmm6
 divss xmm3,xmm5
 minss xmm3,[rsp+68]
 minss xmm2,xmm3
.target_speed:
 movss [rsp+28],xmm2
 ucomiss xmm2,[zero]
 je .no_intent
 MATHCALL atan2f
 subss xmm0,[rbp+GROUND_HEADING]
 call wrap
 movaps xmm1,xmm0
 andps xmm1,[abs_mask]
 cmp dword [rsp+60],GROUND_AI
 je .forward
 ucomiss xmm1,[reverse_threshold]
 jbe .forward
 ; Rearward request: choose slow reverse rather than instant turn/reversal.
 ucomiss xmm0,[zero]
 jb .reverse_negative
 subss xmm0,[pi]
 jmp .reverse_target
.reverse_negative:
 addss xmm0,[pi]
.reverse_target:
 mov eax,[rsp+56]
 lea rdx,[reverse_caps]
 movss xmm1,[rdx+rax*4]
 mulss xmm1,[rsp+76]
 minss xmm1,[rsp+28]
 xorps xmm1,[sign_mask]
 movss [rsp+28],xmm1
.forward:
 movss [rsp+24],xmm0
 movaps xmm1,xmm0
 andps xmm1,[abs_mask]
 ucomiss xmm1,[sharp]
 jbe .turn
 mov dword [rsp+28],0
 jmp .turn
.no_intent:
 mov dword [rsp+24],0
 mov dword [rsp+28],0
.turn:
 mov eax,[rsp+56]
 lea rdx,[turn_caps]
 movss xmm1,[rdx+rax*4]
 movss xmm2,[rbp+GROUND_SPEED]
 andps xmm2,[abs_mask]
 ucomiss xmm2,[zero]
 jne .turn_cap
 lea rdx,[stationary_turn]
 movss xmm1,[rdx+rax*4]
.turn_cap:
 movss xmm0,[rsp+24]
 minss xmm0,xmm1
 xorps xmm1,[sign_mask]
 maxss xmm0,xmm1
 call canonical_zero
 movss [rbp+GROUND_TURN],xmm0
 addss xmm0,[rbp+GROUND_HEADING]
 call wrap
 call canonical_zero
 movss [rsp+32],xmm0
 movss [rbp+GROUND_HEADING],xmm0
 ; Accelerate toward requested signed speed, braking more strongly to zero.
 movss xmm0,[rbp+GROUND_SPEED]
 movss xmm1,[rsp+28]
 movaps xmm2,xmm0
 mulss xmm2,xmm1
 ucomiss xmm2,[zero]
 jb .brake_zero
 movaps xmm2,xmm0
 andps xmm2,[abs_mask]
 movaps xmm3,xmm1
 andps xmm3,[abs_mask]
 ucomiss xmm3,xmm2
 jb .decelerate
 mov eax,[rsp+56]
 lea rdx,[accel]
 movss xmm2,[rdx+rax*4]
 mulss xmm2,[rsp+76]
 jmp .apply_rate
.brake_zero:
 pxor xmm1,xmm1
.decelerate:
 lea rdx,[brake]
.rate:
 mov eax,[rsp+56]
 movss xmm2,[rdx+rax*4]
.apply_rate:
 subss xmm1,xmm0
 minss xmm1,xmm2
 xorps xmm2,[sign_mask]
 maxss xmm1,xmm2
 addss xmm0,xmm1
 ; Canonical +0 speed after braking.
 ucomiss xmm0,[zero]
 jne .speed_ready
 pxor xmm0,xmm0
.speed_ready:
 movss [rsp+36],xmm0
 movss xmm0,[rsp+32]
 MATHCALL sinf
 movss [rsp+48],xmm0
 movss xmm0,[rsp+32]
 MATHCALL cosf
 movss [rsp+52],xmm0
 mulss xmm0,[rsp+36]
 addss xmm0,[rsp+4]
 movss [rsp+44],xmm0
 movss xmm0,[rsp+48]
 mulss xmm0,[rsp+36]
 addss xmm0,[rsp]
 movss [rsp+40],xmm0
 mov edi,[rsp+64]
 mov esi,[rsp+60]
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+40]
 movss xmm3,[rsp+44]
 movss xmm4,[rsp+36]
 andps xmm4,[abs_mask]
 call crowd_hull_step
 ; Exact query promises full acceptance or hold. Reject malformed partial output.
 ucomiss xmm0,[rsp+40]
 jp .contact
 jne .contact
 ucomiss xmm1,[rsp+44]
 jp .contact
 jne .contact
 movss xmm2,[rsp+36]
 movss [rbp+GROUND_SPEED],xmm2
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 subss xmm2,[rsp]
 subss xmm3,[rsp+4]
 movss [rsp+40],xmm0
 movss [rsp+44],xmm1
 movaps xmm0,xmm2
 call canonical_zero
 movss [rbp+GROUND_VX],xmm0
 movaps xmm0,xmm3
 call canonical_zero
 movss [rbp+GROUND_VZ],xmm0
 movss xmm0,[rsp+40]
 movss xmm1,[rsp+44]
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 jmp .out
.contact:
 mov dword [rbp+GROUND_SPEED],0
 mov dword [rbp+GROUND_VX],0
 mov dword [rbp+GROUND_VZ],0
 jmp .out
.legacy:
 mov edi,[rsp+64]
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 cmp dword [rsp+60],GROUND_DRIVER
 je .legacy_driver
 call crowd_move
 jmp .legacy_return
.legacy_driver:
 call crowd_step
.legacy_return:
 movss [rsp],xmm0
 movss [rsp+4],xmm1
.out:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 add rsp,88
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
canonical_zero:
 ucomiss xmm0,[zero]
 jne .done
 pxor xmm0,xmm0
.done:
 ret
; Normalize finite angle within [-pi,pi], input bounded by 2pi+turn.
wrap:
 ucomiss xmm0,[pi]
 jbe .lower
 subss xmm0,[tau]
.lower:
 movss xmm1,[pi]
 xorps xmm1,[sign_mask]
 ucomiss xmm0,xmm1
 jae .done
 addss xmm0,[tau]
.done:
 ret
; FNV caller accumulator/prime; hash policy plus all 1MiB persistent records.
ground_hash:
 lea rsi,[ground_enabled]
 mov ecx,4
.policy:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .policy
 lea rsi,[sim_ground_motion]
 mov ecx,ENTITY_CAPACITY*GROUND_STRIDE
.state:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .state
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
