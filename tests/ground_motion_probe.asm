%include "schemas/entity.inc"
default rel
extern ground_step,ground_hash
section .bss align=64
global sim_entities,sim_count,sim_waypoints,sim_players,sim_player_vehicle,sim_vehicles,vehicle_entity_driver
sim_entities: resb ENTITY_CAPACITY*ENTITY_STRIDE
sim_count: resd 1
global sim_tick_count
sim_tick_count: resd 1
sim_waypoints: resq 6
sim_players: resb 4*64
sim_player_vehicle: resd 4
sim_vehicles: resb 4*32
vehicle_entity_driver: resd ENTITY_CAPACITY
global vehicle_driver_generation
vehicle_driver_generation: resd 4
global test_blocked,test_partial,test_collision_calls,test_collision_mode,test_collision_budget
test_blocked: resd 1
test_partial: resd 1
test_collision_calls: resd 1
test_collision_mode: resd 1
test_collision_budget: resd 1
global test_surface,test_surface_calls,test_surface_radius,test_surface_alignment
test_surface: resd 1
test_surface_calls: resd 1
test_surface_radius: resd 1
test_surface_alignment: resd 1
section .text
; Development ONLY: clear exact path stub and explicit blocked/partial returns.
; This actuator probe does not establish production terrain/body collision.
%ifndef GROUND_REAL_COLLISION
global terrain_road_body,crowd_hull_step,crowd_move,crowd_step
; Explicit controlled surface stub, including query call-site alignment and radius.
terrain_road_body:
 inc dword [test_surface_calls]
 movss [test_surface_radius],xmm2
 mov rax,rsp
 and eax,15
 mov [test_surface_alignment],eax
 ; Exercise caller-saved clobbers: actuator must retain inputs in its stack.
 pxor xmm0,xmm0
 pxor xmm1,xmm1
 pxor xmm2,xmm2
 pxor xmm3,xmm3
 pxor xmm4,xmm4
 pxor xmm5,xmm5
 pxor xmm6,xmm6
 pxor xmm7,xmm7
 pxor xmm8,xmm8
 pxor xmm9,xmm9
 pxor xmm10,xmm10
 pxor xmm11,xmm11
 pxor xmm12,xmm12
 pxor xmm13,xmm13
 pxor xmm14,xmm14
 pxor xmm15,xmm15
 xor edi,edi
 xor esi,esi
 xor edx,edx
 xor ecx,ecx
 xor r8d,r8d
 xor r9d,r9d
 xor r10d,r10d
 xor r11d,r11d
 mov eax,[test_surface]
 ret
crowd_hull_step:
 inc dword [test_collision_calls]
 mov [test_collision_mode],esi
 movss [test_collision_budget],xmm4
 cmp dword [test_blocked],0
 jne .hold
 movaps xmm0,xmm2
 movaps xmm1,xmm3
 cmp dword [test_partial],0
 je .hold
 addss xmm0,[half]
.hold:
 ret
; Development legacy/AI-intent stub: normalize wish to min(distance, budget).
crowd_move:
crowd_step:
 subss xmm2,xmm0
 subss xmm3,xmm1
 movaps xmm5,xmm2
 mulss xmm5,xmm5
 movaps xmm6,xmm3
 mulss xmm6,xmm6
 addss xmm5,xmm6
 sqrtss xmm5,xmm5
 ucomiss xmm5,[zero]
 je .done
 minss xmm4,xmm5
 divss xmm4,xmm5
 mulss xmm2,xmm4
 mulss xmm3,xmm4
 addss xmm0,xmm2
 addss xmm1,xmm3
.done:
 ret
%endif
global test_ground_step,test_ground_hash
test_ground_step:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rdx
 mov ebx,0x12345
 mov ebp,0x23456
 mov r12d,0x34567
 mov r13d,0x45678
 mov r14d,0x56789
 mov r15d,0x6789a
 movss xmm0,[rdx]
 movss xmm1,[rdx+4]
 movss xmm2,[rdx+8]
 movss xmm3,[rdx+12]
 movss xmm4,[rdx+16]
 call ground_step
 mov rdx,[rsp]
 movss [rdx],xmm0
 movss [rdx+4],xmm1
 xor eax,eax
 cmp rbx,0x12345
 jne .out
 cmp rbp,0x23456
 jne .out
 cmp r12,0x34567
 jne .out
 cmp r13,0x45678
 jne .out
 cmp r14,0x56789
 jne .out
 cmp r15,0x6789a
 jne .out
 inc eax
.out:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
test_ground_hash:
 mov rax,rdi
 mov r8,rsi
 jmp ground_hash
section .rodata
half: dd 0.5
zero: dd 0.0
section .note.GNU-stack noalloc noexec nowrite progbits
