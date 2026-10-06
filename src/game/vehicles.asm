; Allied player-operated armor. SysV AMD64, SSE2; static single-thread state.
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/combat.inc"
%include "schemas/ground_motion.inc"
%include "schemas/ground_eye.inc"
default rel
extern sim_entities,sim_count,sim_players,player_deaths
extern sim_shell_ammo,sim_shell_cooldown,projectile_launch,combat_event
extern crowd_begin,crowd_step,crowd_occupied
extern ground_step,ground_eye,sim_ground_motion
extern terrain_height,terrain_body_blocked,terrain_los,sinf,cosf
section .bss align=64
global sim_vehicles,sim_player_vehicle,vehicle_entity_driver,vehicle_shots
sim_vehicles: resb VEHICLE_CAPACITY*VEHICLE_STRIDE
sim_player_vehicle: resd VEHICLE_CAPACITY
vehicle_entity_driver: resd ENTITY_CAPACITY
vehicle_shots: resd VEHICLE_CAPACITY
section .bss align=16
previous_buttons: resd VEHICLE_CAPACITY
global vehicle_driver_generation
vehicle_driver_generation: resd VEHICLE_CAPACITY
section .rodata
zero: dd 0.0
one: dd 1.0
minus_one: dd -1.0
entry_radius2: dd 64.0
eye: dd 1.8
drive_step: dd 0.6
cannon_range: dd 600.0
world_max: dd 8000.0
min_y: dd -1000.0
max_y: dd 1000.0
yaw_min: dd -10000.0
yaw_max: dd 10000.0
pitch_min: dd -1.3
pitch_max: dd 1.3
destroy_radius: dd 10.0
exit_offsets: dd -6.0,0.0,6.0,0.0,0.0,-6.0,0.0,6.0,-6.0,-6.0,6.0,6.0,-6.0,6.0,6.0,-6.0
section .text
global vehicle_init,vehicle_enter,vehicle_exit,vehicle_detach,vehicle_tick_player,vehicle_hash
vehicle_init:
 lea rdi,[sim_vehicles]
 xor eax,eax
 mov ecx,VEHICLE_CAPACITY*VEHICLE_STRIDE/4
 rep stosd
 lea rdi,[sim_player_vehicle]
 mov eax,-1
 mov ecx,VEHICLE_CAPACITY+ENTITY_CAPACITY
 rep stosd
 lea rdi,[vehicle_shots]
 xor eax,eax
 mov ecx,VEHICLE_CAPACITY
 rep stosd
 lea rdi,[previous_buttons]
 mov ecx,VEHICLE_CAPACITY
 rep stosd
 lea rdi,[vehicle_driver_generation]
 mov ecx,VEHICLE_CAPACITY
 rep stosd
 lea rdx,[sim_vehicles]
 xor ecx,ecx
.loop:
 mov dword [rdx+VEHICLE_ENTITY],-1
 mov [rdx+VEHICLE_DRIVER],ecx
 add rdx,VEHICLE_STRIDE
 inc ecx
 cmp ecx,VEHICLE_CAPACITY
 jb .loop
 ret
; Validate ownership+generation. EDI=id->EAX index/-1, RDX hull pointer on success.
claim:
 cmp edi,VEHICLE_CAPACITY
 jae .bad
 lea rdx,[sim_player_vehicle]
 mov eax,[rdx+rdi*4]
 cmp eax,[sim_count]
 jae .bad
 mov ecx,edi
 shl ecx,5
 lea r8,[sim_vehicles]
 add r8,rcx
 cmp dword [r8+VEHICLE_ACTIVE],1
 jne .bad
 cmp [r8+VEHICLE_ENTITY],eax
 jne .bad
 lea r9,[vehicle_entity_driver]
 cmp [r9+rax*4],edi
 jne .bad
 mov ecx,eax
 shl ecx,5
 lea rdx,[sim_entities]
 add rdx,rcx
 mov ecx,[rdx+ENTITY_GENERATION]
 cmp ecx,[r8+VEHICLE_ENTITY_GENERATION]
 jne .bad
 cmp dword [rdx+ENTITY_SIDE],0
 jne .bad
 cmp dword [rdx+ENTITY_KIND],1
 jne .bad
 mov ecx,edi
 shl ecx,6
 lea r9,[sim_players]
 add r9,rcx
 lea r10,[vehicle_driver_generation]
 mov ecx,[r10+rdi*4]
 test ecx,ecx
 jz .bad
 cmp ecx,[r9+PLAYER_GENERATION]
 jne .bad
 ret
.bad:
 mov eax,-1
 ret
; Clear claim without changing edge history or persistent cannon resources.
clear_claim:
 cmp edi,VEHICLE_CAPACITY
 jae .done
 lea rdx,[vehicle_driver_generation]
 mov dword [rdx+rdi*4],0
 lea rdx,[sim_player_vehicle]
 mov eax,[rdx+rdi*4]
 cmp eax,ENTITY_CAPACITY
 jae .record
 lea rcx,[vehicle_entity_driver]
 cmp [rcx+rax*4],edi
 jne .record
 mov dword [rcx+rax*4],-1
.record:
 mov dword [rdx+rdi*4],-1
 mov eax,edi
 shl eax,5
 lea rdx,[sim_vehicles]
 add rdx,rax
 mov dword [rdx+VEHICLE_ENTITY],-1
 mov dword [rdx+VEHICLE_ENTITY_GENERATION],0
 mov dword [rdx+VEHICLE_ACTIVE],0
 mov dword [rdx+VEHICLE_AMMO],0
 mov dword [rdx+VEHICLE_COOLDOWN],0
 mov dword [rdx+VEHICLE_FLAGS],0
.done:
 ret
vehicle_detach:
 push rbp
 mov rbp,rsp
 call clear_claim
 cmp edi,VEHICLE_CAPACITY
 jae .done
 lea rdx,[previous_buttons]
 mov dword [rdx+rdi*4],0
.done:
 pop rbp
 ret
vehicle_enter:
 cmp edi,VEHICLE_CAPACITY
 jae .bad
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,32
 mov r12d,edi
 call claim
 cmp eax,-1
 jne .failed
 mov eax,r12d
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .failed
 cmp dword [rbx+PLAYER_HP],0
 je .failed
 cmp dword [rbx+PLAYER_GENERATION],0
 je .failed
 xor r13d,r13d
 mov r14d,-1
 movss xmm0,[entry_radius2]
 movss [rsp],xmm0
 lea r15,[sim_entities]
.scan:
 cmp r13d,[sim_count]
 jae .choose
 cmp dword [r15+ENTITY_HP],0
 je .next
 cmp dword [r15+ENTITY_SIDE],0
 jne .next
 cmp dword [r15+ENTITY_KIND],1
 jne .next
 lea rax,[vehicle_entity_driver]
 cmp dword [rax+r13*4],-1
 jne .next
 movss xmm0,[r15+ENTITY_X]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[r15+ENTITY_Z]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[rsp]
 jp .next
 ja .next
 movss [rsp],xmm0
 mov r14d,r13d
.next:
 add r15,ENTITY_STRIDE
 inc r13d
 jmp .scan
.choose:
 cmp r14d,-1
 je .failed
 mov eax,r14d
 shl eax,5
 lea r15,[sim_entities]
 add r15,rax
 movss xmm0,[r15+ENTITY_X]
 movss xmm1,[r15+ENTITY_Z]
 mov edi,1
 call terrain_body_blocked
 test eax,eax
 jnz .failed
 lea rdi,[rsp+8]
 mov esi,r14d
 call hull_eye_query
 test eax,eax
 jnz .failed
 movss xmm4,[rsp+12]
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Y]
 movss xmm2,[rbx+PLAYER_Z]
 movss xmm3,[rsp+8]
 movss xmm5,[rsp+16]
 call terrain_los
 test eax,eax
 jz .failed
 mov edi,r12d
 call clear_claim
 lea rdx,[sim_player_vehicle]
 mov [rdx+r12*4],r14d
 lea rdx,[vehicle_entity_driver]
 mov [rdx+r14*4],r12d
 mov eax,r12d
 shl eax,5
 lea rdx,[sim_vehicles]
 add rdx,rax
 mov [rdx+VEHICLE_ENTITY],r14d
 mov eax,[r15+ENTITY_GENERATION]
 mov [rdx+VEHICLE_ENTITY_GENERATION],eax
 mov dword [rdx+VEHICLE_ACTIVE],1
 lea rax,[vehicle_driver_generation]
 mov ecx,[rbx+PLAYER_GENERATION]
 mov [rax+r12*4],ecx
 inc dword [rdx+VEHICLE_GENERATION]
 lea rax,[sim_shell_ammo]
 mov eax,[rax+r14*4]
 mov [rdx+VEHICLE_AMMO],eax
 lea rax,[sim_shell_cooldown]
 mov eax,[rax+r14*4]
 mov [rdx+VEHICLE_COOLDOWN],eax
 mov eax,[rsp+8]
 mov [rbx+PLAYER_X],eax
 mov eax,[rsp+16]
 mov [rbx+PLAYER_Z],eax
 mov eax,[rsp+12]
 mov [rbx+PLAYER_Y],eax
 xor eax,eax
 jmp .out
.failed:
 mov eax,-1
.out:
 add rsp,32
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
.bad:
 mov eax,-1
 ret
; Try eight bounded, solid/actor-clear candidates. Failed exit preserves ownership.
vehicle_exit:
 cmp edi,VEHICLE_CAPACITY
 jae .bad
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,32
 mov r12d,edi
 call claim
 cmp eax,-1
 je .failed
 mov r14d,eax
 mov r15,rdx
 mov eax,r12d
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 ; Rebuild once before bounded disembark candidate queries.
 call crowd_begin
 xor r13d,r13d
.candidate:
 lea rax,[exit_offsets]
 movss xmm0,[r15+ENTITY_X]
 addss xmm0,[rax+r13*8]
 movss xmm1,[r15+ENTITY_Z]
 addss xmm1,[rax+r13*8+4]
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 xor edi,edi
 call terrain_body_blocked
 test eax,eax
 jnz .next
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 call terrain_height
 addss xmm0,[eye]
 movss [rsp+8],xmm0
 movaps xmm4,xmm0
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Y]
 movss xmm2,[rbx+PLAYER_Z]
 movss xmm3,[rsp]
 movss xmm5,[rsp+4]
 call terrain_los
 test eax,eax
 jz .next
 mov edi,r12d
 add edi,ENTITY_CAPACITY
 xor esi,esi
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 call crowd_occupied
 test eax,eax
 jnz .next
 mov eax,[rsp]
 mov [rbx+PLAYER_X],eax
 mov eax,[rsp+4]
 mov [rbx+PLAYER_Z],eax
 mov eax,[rsp+8]
 mov [rbx+PLAYER_Y],eax
 mov edi,r12d
 call clear_claim
 xor eax,eax
 jmp .out
.next:
 inc r13d
 cmp r13d,8
 jb .candidate
.failed:
 mov eax,-1
.out:
 add rsp,32
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
.bad:
 mov eax,-1
 ret
; Tick consumes interaction edges exactly once, including while dead/disconnected.
vehicle_tick_player:
 cmp edi,VEHICLE_CAPACITY
 jae .unhandled
 ; Reject before edge history, boarding, destruction or ownership can mutate.
 test esi,~127
 jnz .invalid_input
 ucomiss xmm0,[minus_one]
 jp .invalid_input
 jb .invalid_input
 ucomiss xmm0,[one]
 ja .invalid_input
 ucomiss xmm1,[minus_one]
 jp .invalid_input
 jb .invalid_input
 ucomiss xmm1,[one]
 ja .invalid_input
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,64
 mov r12d,edi
 mov r13d,esi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 lea rdx,[previous_buttons]
 mov eax,[rdx+r12*4]
 not eax
 and eax,esi
 mov [rsp+8],eax
 mov [rdx+r12*4],esi
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 call claim
 cmp eax,-1
 je .noclaim
 mov r14d,eax
 mov r15,rdx
 cmp dword [r15+ENTITY_HP],0
 je .destroyed
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .detach
 cmp dword [rbx+PLAYER_HP],0
 je .detach
 test dword [rsp+8],INPUT_EXIT
 jz .drive
 mov edi,r12d
 call vehicle_exit
 test eax,eax
 jz .detach_return
 jmp .drive
.noclaim:
 ; Invalid/recycled actor references must not leave a stale AI ownership mask.
 mov edi,r12d
 call clear_claim
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .detach_return
 cmp dword [rbx+PLAYER_HP],0
 je .detach_return
 test dword [rsp+8],INPUT_ENTER
 jz .detach_return
 test dword [rsp+8],INPUT_EXIT
 jnz .detach_return
 mov edi,r12d
 call vehicle_enter
 test eax,eax
 jnz .detach_return
 mov edi,r12d
 call claim
 mov r14d,eax
 mov r15,rdx
.drive:
 ; Validate current stamped support before movement or cannon aim.
 lea rdi,[rsp+40]
 mov esi,r14d
 call hull_eye_query
 test eax,eax
 jnz .refresh
 ; Direct helper calls also refresh bounded bodies; common-player calls may
 ; have just boarded/exited another slot. No stale placement/controller index.
 call crowd_begin
 ; Direct and common-player inputs were validated before interaction edges.
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[r15+ENTITY_X]
 addss xmm2,xmm0
 movss xmm3,[r15+ENTITY_Z]
 addss xmm3,xmm1
 movss xmm0,[r15+ENTITY_X]
 movss xmm1,[r15+ENTITY_Z]
 movss xmm4,[drive_step]
 mov edi,r14d
 mov esi,1
 call ground_step
 movss [r15+ENTITY_X],xmm0
 movss [r15+ENTITY_Z],xmm1
 lea rdi,[rsp+40]
 mov esi,r14d
 call hull_eye_query
 test eax,eax
 jnz .refresh
 mov eax,[rsp+40]
 mov [rbx+PLAYER_X],eax
 mov eax,[rsp+44]
 mov [rbx+PLAYER_Y],eax
 mov eax,[rsp+48]
 mov [rbx+PLAYER_Z],eax
 test r13d,INPUT_FIRE
 jz .refresh
 ; All cannon aim is server player state, never client position or damage.
 movss xmm0,[rbx+PLAYER_YAW]
 ucomiss xmm0,[yaw_min]
 jp .refresh
 jb .refresh
 ucomiss xmm0,[yaw_max]
 ja .refresh
 movss xmm0,[rbx+PLAYER_PITCH]
 ucomiss xmm0,[pitch_min]
 jp .refresh
 jb .refresh
 ucomiss xmm0,[pitch_max]
 ja .refresh
 movss xmm0,[rbx+PLAYER_YAW]
 call sinf wrt ..plt
 movss [rsp+16],xmm0
 movss xmm0,[rbx+PLAYER_YAW]
 call cosf wrt ..plt
 movss [rsp+20],xmm0
 movss xmm0,[rbx+PLAYER_PITCH]
 call sinf wrt ..plt
 movss [rsp+24],xmm0
 movss xmm0,[rbx+PLAYER_PITCH]
 call cosf wrt ..plt
 mulss xmm0,[cannon_range]
 movaps xmm1,xmm0
 mulss xmm0,[rsp+16]
 addss xmm0,[rbx+PLAYER_X]
 mulss xmm1,[rsp+20]
 addss xmm1,[rbx+PLAYER_Z]
 movss [rsp+28],xmm0
 movss [rsp+32],xmm1
 movss xmm1,[rsp+24]
 mulss xmm1,[cannon_range]
 addss xmm1,[rbx+PLAYER_Y]
 movss xmm2,[rsp+32]
 movss xmm0,[rsp+28]
 ; Range-clamp target coordinates; swept shell collision still stops at solids.
 maxss xmm0,[zero]
 minss xmm0,[world_max]
 maxss xmm2,[zero]
 minss xmm2,[world_max]
 maxss xmm1,[min_y]
 minss xmm1,[max_y]
 mov edi,r14d
 mov esi,1
 call projectile_launch
 test eax,eax
 jnz .refresh
 lea rdx,[vehicle_shots]
 inc dword [rdx+r12*4]
.refresh:
 mov eax,r12d
 shl eax,5
 lea rdx,[sim_vehicles]
 add rdx,rax
 lea rax,[sim_shell_ammo]
 mov eax,[rax+r14*4]
 mov [rdx+VEHICLE_AMMO],eax
 lea rax,[sim_shell_cooldown]
 mov eax,[rax+r14*4]
 mov [rdx+VEHICLE_COOLDOWN],eax
.handled:
 mov eax,1
 jmp .out
.destroyed:
 cmp dword [rbx+PLAYER_HP],0
 je .emit_destroyed
 mov dword [rbx+PLAYER_HP],0
 mov dword [rbx+PLAYER_RESPAWN],30
 mov dword [rbx+PLAYER_RELOAD],0
 inc dword [player_deaths]
.emit_destroyed:
 movss xmm0,[r15+ENTITY_X]
 movss xmm1,[r15+ENTITY_Z]
 call terrain_height
 movaps xmm1,xmm0
 movss xmm0,[r15+ENTITY_X]
 movss xmm2,[r15+ENTITY_Z]
 movss xmm3,[destroy_radius]
 mov edi,EVENT_VEHICLE_DESTROYED
 xor esi,esi
 call combat_event
 mov edi,r12d
 call clear_claim
 mov eax,1
 jmp .out
.detach:
 mov edi,r12d
 call clear_claim
.detach_return:
 xor eax,eax
.out:
 add rsp,64
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
.invalid_input:
 push rbp
 mov rbp,rsp
 call claim ; read-only, preserve all simulation and interaction state
 cmp eax,-1
 setne al
 movzx eax,al
 pop rbp
 ret
.unhandled:
 xor eax,eax
 ret
 ; Internal read-only eye query. RDI output12, ESI hull ID, EAX status.
 ; Validate live entity/motion identity before loading any stamped axis.
hull_eye_query:
 cmp esi,[sim_count]
 jae .bad
 mov eax,esi
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 lea r9,[sim_ground_motion]
 add r9,rax
 cmp dword [r8+ENTITY_KIND],1
 jne .bad
 cmp dword [r8+ENTITY_SIDE],0
 jne .bad
 cmp dword [r8+ENTITY_HP],0
 je .bad
 mov eax,[r8+ENTITY_GENERATION]
 test eax,eax
 jz .bad
 cmp eax,[r9+GROUND_GENERATION]
 jne .bad
 cmp dword [r9+GROUND_KIND],1
 jne .bad
 test dword [r9+GROUND_FLAGS],GROUND_ACTIVE
 jz .bad
 movss xmm0,[r8+ENTITY_X]
 movss xmm1,[r8+ENTITY_Z]
 movss xmm2,[r9+GROUND_HEADING]
 mov esi,1
 mov edx,EYE_STRIDE
 jmp ground_eye
.bad:
 mov eax,-1
 ret
vehicle_hash:
 lea rsi,[sim_vehicles]
 mov ecx,VEHICLE_CAPACITY*VEHICLE_STRIDE+VEHICLE_CAPACITY*4+ENTITY_CAPACITY*4+VEHICLE_CAPACITY*4
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 lea rsi,[previous_buttons]
 mov ecx,VEHICLE_CAPACITY*4
.edges:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .edges
 lea rsi,[vehicle_driver_generation]
 mov ecx,VEHICLE_CAPACITY*4
.drivers:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .drivers
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
