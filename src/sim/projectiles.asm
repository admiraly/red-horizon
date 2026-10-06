%include "schemas/world_contact.inc"
; Authoritative bounded moving shells, fixed30Hz. Cosmetic ring is independent.
%include "schemas/entity.inc"
%include "schemas/combat.inc"
%include "schemas/aircraft.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,sim_blast,world_contact_query
extern sim_aircraft,sim_entity_height,sim_air_damage
extern terrain_height
section .bss align=64
global sim_projectiles,sim_projectile_count,sim_projectile_dropped
global sim_shell_ammo,sim_shell_cooldown,sim_events,sim_event_count,sim_event_sequence
sim_projectiles: resb PROJECTILE_CAPACITY*PROJECTILE_STRIDE
sim_projectile_count: resd 1
sim_projectile_dropped: resd 1
cursor: resd 1
sim_shell_ammo: resd ENTITY_CAPACITY
sim_shell_cooldown: resd ENTITY_CAPACITY
sim_events: resb EVENT_CAPACITY*EVENT_STRIDE
sim_event_count: resd 1
sim_event_sequence: resd 1
section .rodata
blast_contact_skin: dd WORLD_CONTACT_BLAST_SKIN
zero: dd 0.0
one: dd 1.0
half: dd 0.5
max_coord: dd 8000.0
min_y: dd -1000.0
max_y: dd 1000.0
muzzle_height: dd 3.0
air_height: dd 90.0
gravity: dd 0.0109
shell_step: dd 0.0,10.0,6.0
blast_radius: dd 0.0,18.0,35.0
blast_damage: dd 0,80,100
shell_cadence: dd 0,30,90
section .text
global projectile_init,projectile_spawn,projectile_launch,projectile_tick,projectile_hash
; Event ABI: XMM0/1/2 xyz, EDI kind, ESI side, XMM3 radius.
global combat_event,reset_event_ring
reset_event_ring:
 lea rdi,[sim_events]
 xor eax,eax
 mov ecx,(EVENT_CAPACITY*EVENT_STRIDE+8)/4
 rep stosd
 ret
combat_event:
 inc dword [sim_event_sequence]
 mov eax,[sim_event_sequence]
 mov edx,eax
 and edx,EVENT_CAPACITY-1
 shl edx,5
 lea rcx,[sim_events]
 add rcx,rdx
 movss [rcx+EVENT_X],xmm0
 movss [rcx+EVENT_Y],xmm1
 movss [rcx+EVENT_Z],xmm2
 mov [rcx+EVENT_KIND],edi
 mov [rcx+EVENT_SIDE],esi
 mov edx,[sim_tick_count]
 mov [rcx+EVENT_TICK],edx
 movss [rcx+EVENT_RADIUS],xmm3
 mov [rcx+EVENT_SEQUENCE],eax
 cmp dword [sim_event_count],EVENT_CAPACITY
 jae .done
 inc dword [sim_event_count]
.done: ret
projectile_init:
 lea rdi,[sim_projectiles]
 xor eax,eax
 mov ecx,(PROJECTILE_CAPACITY*PROJECTILE_STRIDE+12+ENTITY_CAPACITY*8)/4
 rep stosd
 lea rdi,[sim_shell_ammo]
 lea rsi,[sim_entities]
 mov ecx,[sim_count]
.ammo:
 mov eax,[rsi+ENTITY_KIND]
 cmp eax,1
 je .ground
 cmp eax,2
 jne .next
.ground: mov dword [rdi],64
.next:
 add rdi,4
 add rsi,ENTITY_STRIDE
 loop .ammo
 jmp reset_event_ring
; Spawn toward a validated opposing live entity; no network damage trust.
projectile_spawn:
 cmp edi,[sim_count]
 jae .bad
 cmp esi,[sim_count]
 jae .bad
 push rbx
 sub rsp,32
 mov [rsp],edi
 mov eax,esi
 imul rax,ENTITY_STRIDE
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .failed
 mov eax,edi
 imul rax,ENTITY_STRIDE
 lea rdx,[sim_entities]
 mov ecx,[rdx+rax+ENTITY_SIDE]
 cmp ecx,[rbx+ENTITY_SIDE]
 je .failed
 cmp dword [rdx+rax+ENTITY_HP],0
 je .failed
 mov ecx,[rdx+rax+ENTITY_KIND]
 cmp ecx,1
 je .shell_source
 cmp ecx,2
 jne .failed
.shell_source:
 lea rdx,[sim_shell_ammo]
 cmp dword [rdx+rdi*4],0
 je .failed
 lea rdx,[sim_shell_cooldown]
 cmp dword [rdx+rdi*4],0
 jne .failed
 cmp dword [sim_projectile_count],PROJECTILE_CAPACITY-32-64
 jb .ai_capacity
 inc dword [sim_projectile_dropped]
 jmp .failed
.ai_capacity:
 mov edi,esi
 call sim_entity_height
 movaps xmm1,xmm0
 movss xmm0,[rbx+ENTITY_X]
 movss xmm2,[rbx+ENTITY_Z]
 mov edi,[rsp]
 mov eax,edi
 imul rax,ENTITY_STRIDE
 lea rdx,[sim_entities]
 mov esi,[rdx+rax+ENTITY_KIND]
 call projectile_launch
 jmp .out
.failed: mov eax,-1
.out:
 add rsp,32
 pop rbx
 ret
.bad: mov eax,-1
 ret
; Source index EDI, kind1/2 ESI; fixed target point XYZ in XMM0/1/2.
projectile_launch:
 cmp edi,[sim_count]
 jae .bad
 cmp esi,1
 jb .bad
 cmp esi,2
 ja .bad
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[max_coord]
 ja .bad
 ucomiss xmm2,[zero]
 jp .bad
 jb .bad
 ucomiss xmm2,[max_coord]
 ja .bad
 ucomiss xmm1,[min_y]
 jp .bad
 jb .bad
 ucomiss xmm1,[max_y]
 ja .bad
 push rbx
 push rbp
 push r12
 push r13
 push r14
 sub rsp,96
 mov r12d,edi
 mov r13d,esi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 mov eax,edi
 imul rax,ENTITY_STRIDE
 lea rbp,[sim_entities]
 add rbp,rax
 cmp dword [rbp+ENTITY_HP],0
 je .failed
 cmp [rbp+ENTITY_KIND],esi
 jne .failed
 lea rdx,[sim_shell_ammo]
 cmp dword [rdx+r12*4],0
 je .failed
 lea rdx,[sim_shell_cooldown]
 cmp dword [rdx+r12*4],0
 jne .failed
 mov ebx,[cursor]
 mov r14d,PROJECTILE_CAPACITY
.find:
 mov eax,ebx
 shl eax,6
 lea rdx,[sim_projectiles]
 cmp dword [rdx+rax+PROJECTILE_ACTIVE],0
 je .found
 inc ebx
 and ebx,PROJECTILE_CAPACITY-1
 dec r14d
 jnz .find
 inc dword [sim_projectile_dropped]
 jmp .failed
.found:
 add rdx,rax
 mov [rsp+72],rdx
 movss xmm0,[rbp+ENTITY_X]
 movss xmm1,[rbp+ENTITY_Z]
 call terrain_height
 addss xmm0,[muzzle_height]
 movss [rsp+12],xmm0
 movss xmm1,[rsp]
 subss xmm1,[rbp+ENTITY_X]
 movss xmm2,[rsp+8]
 subss xmm2,[rbp+ENTITY_Z]
 movaps xmm3,xmm1
 mulss xmm3,xmm3
 movaps xmm4,xmm2
 mulss xmm4,xmm4
 addss xmm3,xmm4
 ; Direct rounds normalize the full XYZ displacement, including cannon pitch.
 ; Ballistic time bounds both horizontal and vertical displacement; close/high
 ; targets must not manufacture an unbounded one-tick vertical velocity.
 movss xmm4,[rsp+4]
 subss xmm4,[rsp+12]
 movss [rsp+28],xmm4
 movaps xmm5,xmm4
 mulss xmm5,xmm5
 cmp r13d,1
 jne .ballistic_distance
 addss xmm3,xmm5
 sqrtss xmm3,xmm3
 ucomiss xmm3,[zero]
 jbe .failed
 jmp .flight_time
.ballistic_distance:
 sqrtss xmm3,xmm3
 sqrtss xmm5,xmm5
 maxss xmm3,xmm5
 ucomiss xmm3,[zero]
 jbe .failed
.flight_time:
 lea rax,[shell_step]
 divss xmm3,[rax+r13*4]
 maxss xmm3,[one] ; short direct rounds never overshoot their aim in tick one
 cmp r13d,2
 jne .time_ready
 ; Integer paired time makes the discrete gravity trajectory reach its aim
 ; at a fixed tick, rather than using a continuous formula with half-step drift.
 cvttss2si eax,xmm3
 cvtsi2ss xmm5,eax
 ucomiss xmm5,xmm3
 jae .rounded_time
 addss xmm5,[one]
.rounded_time:
 movaps xmm3,xmm5
.time_ready:
 movss [rsp+16],xmm3
 divss xmm1,xmm3
 divss xmm2,xmm3
 movss [rsp+20],xmm1
 movss [rsp+24],xmm2
 movss xmm4,[rsp+28]
 divss xmm4,xmm3
 cmp r13d,2
 jne .linear_shell
 movaps xmm5,xmm3
 subss xmm5,[one] ; position advances BEFORE gravity each tick
 mulss xmm5,[gravity]
 mulss xmm5,[half]
 addss xmm4,xmm5
.linear_shell:
 mov rdx,[rsp+72]
 mov eax,[rdx+PROJECTILE_GENERATION]
 inc eax
 mov [rdx+PROJECTILE_GENERATION],eax
 mov eax,[rbp+ENTITY_X]
 mov [rdx+PROJECTILE_X],eax
 movss xmm0,[rsp+12]
 movss [rdx+PROJECTILE_Y],xmm0
 mov eax,[rbp+ENTITY_Z]
 mov [rdx+PROJECTILE_Z],eax
 movss xmm1,[rsp+20]
 movss [rdx+PROJECTILE_VX],xmm1
 movss [rdx+PROJECTILE_VY],xmm4
 movss xmm2,[rsp+24]
 movss [rdx+PROJECTILE_VZ],xmm2
 mov dword [rdx+PROJECTILE_TTL],240
 mov eax,[rbp+ENTITY_SIDE]
 mov [rdx+PROJECTILE_SIDE],eax
 mov [rdx+PROJECTILE_KIND],r13d
 lea rcx,[blast_damage]
 mov eax,[rcx+r13*4]
 mov [rdx+PROJECTILE_DAMAGE],eax
 lea rcx,[blast_radius]
 mov eax,[rcx+r13*4]
 mov [rdx+PROJECTILE_RADIUS],eax
 mov [rdx+PROJECTILE_SOURCE],r12d
 mov eax,[rbp+ENTITY_GENERATION]
 mov [rdx+PROJECTILE_SOURCE_GENERATION],eax
 mov dword [rdx+PROJECTILE_ACTIVE],1
 inc dword [sim_projectile_count]
 inc ebx
 and ebx,PROJECTILE_CAPACITY-1
 mov [cursor],ebx
 lea rax,[sim_shell_ammo]
 dec dword [rax+r12*4]
 lea rax,[shell_cadence]
 mov eax,[rax+r13*4]
 lea rcx,[sim_shell_cooldown]
 mov [rcx+r12*4],eax
 movss xmm0,[rdx+PROJECTILE_X]
 movss xmm1,[rdx+PROJECTILE_Y]
 movss xmm2,[rdx+PROJECTILE_Z]
 movss xmm3,[rdx+PROJECTILE_RADIUS]
 mov edi,r13d
 mov esi,[rdx+PROJECTILE_SIDE]
 call combat_event
 xor eax,eax
 jmp .out
.failed: mov eax,-1
.out:
 add rsp,96
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
.bad: mov eax,-1
 ret
projectile_tick:
 push rbx
 push r12
 push r13
 sub rsp,96
 lea rax,[sim_shell_cooldown]
 mov ecx,[sim_count]
.cooldown:
 cmp dword [rax],0
 je .cool_next
 dec dword [rax]
.cool_next:
 add rax,4
 loop .cooldown
 lea rbx,[sim_projectiles]
 xor r12d,r12d
.loop:
 cmp dword [rbx+PROJECTILE_ACTIVE],0
 je .next
 movss xmm0,[rbx+PROJECTILE_X]
 movss xmm1,[rbx+PROJECTILE_Y]
 movss xmm2,[rbx+PROJECTILE_Z]
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movaps xmm3,xmm0
 movaps xmm4,xmm1
 movaps xmm5,xmm2
 addss xmm3,[rbx+PROJECTILE_VX]
 addss xmm4,[rbx+PROJECTILE_VY]
 addss xmm5,[rbx+PROJECTILE_VZ]
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 cmp dword [rbx+PROJECTILE_KIND],2
 je .gravity
 cmp dword [rbx+PROJECTILE_KIND],PROJECTILE_BOMB
 jne .no_gravity
.gravity:
 movss xmm0,[rbx+PROJECTILE_VY]
 subss xmm0,[gravity]
 movss [rbx+PROJECTILE_VY],xmm0
.no_gravity:
 ; Bound map/TTL before running physical sweep.
 movss xmm0,[rsp+12]
 ucomiss xmm0,[zero]
 jb .expire
 ucomiss xmm0,[max_coord]
 ja .expire
 movss xmm0,[rsp+20]
 ucomiss xmm0,[zero]
 jb .expire
 ucomiss xmm0,[max_coord]
 ja .expire
 dec dword [rbx+PROJECTILE_TTL]
 jz .expire
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
 lea rdi,[rsp+64]
 mov esi,WORLD_CONTACT_BYTES
 mov edx,[rbx+PROJECTILE_SIDE]
 call world_contact_query
 test eax,eax
 js .expire ; malformed cover fails closed; never let a projectile pass through
 jnz .impact
 mov eax,[rsp+12]
 mov [rbx+PROJECTILE_X],eax
 mov eax,[rsp+16]
 mov [rbx+PROJECTILE_Y],eax
 mov eax,[rsp+20]
 mov [rbx+PROJECTILE_Z],eax
 jmp .next
.impact:
 mov eax,[rsp+68]
 mov [rsp+60],eax
 mov eax,[rsp+72]
 mov [rsp+52],eax
 mov eax,[rsp+76]
 mov [rsp+56],eax
 movss xmm6,[rsp+64]
 movss xmm0,[rsp+12]
 subss xmm0,[rsp]
 mulss xmm0,xmm6
 addss xmm0,[rsp]
 movss xmm1,[rsp+16]
 subss xmm1,[rsp+4]
 mulss xmm1,xmm6
 addss xmm1,[rsp+4]
 movss xmm2,[rsp+20]
 subss xmm2,[rsp+8]
 mulss xmm2,xmm6
 addss xmm2,[rsp+8]
 movss [rsp+40],xmm0
 movss [rsp+44],xmm1
 movss [rsp+48],xmm2
.emit_impact:
 cmp dword [rbx+PROJECTILE_KIND],PROJECTILE_AIR_GUN
 je .air_hit
 movss xmm0,[rsp+40]
 movss xmm1,[rsp+44]
 movss xmm2,[rsp+48]
 mov edi,[rbx+PROJECTILE_KIND]
 add edi,2
 cmp dword [rbx+PROJECTILE_KIND],PROJECTILE_BOMB
 jne .event_kind
 mov edi,EVENT_BOMB_IMPACT
.event_kind:
 mov esi,[rbx+PROJECTILE_SIDE]
 movss xmm3,[rbx+PROJECTILE_RADIUS]
 call combat_event
 ; The event is on the closed contact boundary. For explosive cover impacts,
 ; place the blast evaluation at most1cm toward the incoming clear segment,
 ; clamped to its start. This avoids a wall boundary occluding its entire blast.
 movss xmm6,[rsp+64]
 cmp dword [rsp+60],WORLD_CONTACT_SOLID
 je .outside_blast
 cmp dword [rsp+60],WORLD_CONTACT_WRECK
 jne .blast_origin
.outside_blast:
 movss xmm0,[rsp+12]
 subss xmm0,[rsp]
 mulss xmm0,xmm0
 movss xmm1,[rsp+16]
 subss xmm1,[rsp+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movss xmm1,[rsp+20]
 subss xmm1,[rsp+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 sqrtss xmm0,xmm0
 ucomiss xmm0,[zero]
 jbe .blast_origin
 movss xmm1,[blast_contact_skin]
 divss xmm1,xmm0
 subss xmm6,xmm1
 maxss xmm6,[zero]
.blast_origin:
 movss xmm0,[rsp+12]
 subss xmm0,[rsp]
 mulss xmm0,xmm6
 addss xmm0,[rsp]
 movss xmm1,[rsp+20]
 subss xmm1,[rsp+8]
 mulss xmm1,xmm6
 addss xmm1,[rsp+8]
 movss xmm3,[rsp+16]
 subss xmm3,[rsp+4]
 mulss xmm3,xmm6
 addss xmm3,[rsp+4]
 ; A ground event lies on the closed height skin. Evaluate its blast1cm
 ; above that contact to avoid rejecting every outgoing LOS ray at t=0.
 cmp dword [rsp+60],WORLD_CONTACT_GROUND
 jne .blast_ready
 addss xmm3,[blast_contact_skin]
.blast_ready:
 movss xmm2,[rbx+PROJECTILE_RADIUS]
 mov edi,[rbx+PROJECTILE_SIDE]
 mov esi,[rbx+PROJECTILE_DAMAGE]
 call sim_blast
 jmp .expire
.air_hit:
 ; A cover identity can equal a recycled actor index. Only the typed live
 ; actor contact with its captured generation can enter direct damage.
 cmp dword [rsp+60],WORLD_CONTACT_ACTOR
 jne .expire
 mov edi,[rsp+52]
 cmp edi,[sim_count]
 jae .expire
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 mov ecx,[rsp+56]
 cmp [rdx+rax+ENTITY_GENERATION],ecx
 jne .expire
 mov esi,[rbx+PROJECTILE_DAMAGE]
 call sim_air_damage
.expire:
 mov dword [rbx+PROJECTILE_ACTIVE],0
 dec dword [sim_projectile_count]
.next:
 add rbx,PROJECTILE_STRIDE
 inc r12d
 cmp r12d,PROJECTILE_CAPACITY
 jb .loop
 add rsp,96
 pop r13
 pop r12
 pop rbx
 ret
projectile_hash:
 lea rsi,[sim_projectiles]
 mov ecx,PROJECTILE_CAPACITY*PROJECTILE_STRIDE+12+ENTITY_CAPACITY*8
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits 
section .rodata
airgun_step: dd 28.0
airgun_radius: dd 1.0
section .text
global projectile_air_launch
; EDI verified aircraft index, ESI bomb3/gun4. Finite stores owned by air FSM.
projectile_air_launch:
 cmp edi,[sim_count]
 jae .bad
 cmp esi,3
 jb .bad
 cmp esi,4
 ja .bad
 push rbx
 push rbp
 push r12
 push r13
 sub rsp,40
 mov r12d,edi
 mov r13d,esi
 mov eax,edi
 shl eax,5
 lea rbp,[sim_entities]
 add rbp,rax
 cmp dword [rbp+ENTITY_HP],0
 je .failed
 cmp dword [rbp+ENTITY_KIND],3
 jne .failed
 mov eax,r12d
 shl eax,6
 lea rcx,[sim_aircraft]
 add rcx,rax
 test dword [rcx+AIR_FLAGS],AIR_ACTIVE
 jz .failed
 mov eax,[rbp+ENTITY_GENERATION]
 cmp [rcx+AIR_GENERATION],eax
 jne .failed
 cmp dword [rcx+AIR_AMMO],0
 je .failed
 cmp dword [rcx+AIR_COOLDOWN],0
 jne .failed
 cmp r13d,PROJECTILE_BOMB
 jne .validate_gun
 cmp dword [rcx+AIR_ROLE],AIR_BOMBER
 jne .failed
 jmp .validated
.validate_gun:
 cmp dword [rcx+AIR_ROLE],AIR_FIGHTER
 jne .failed
 mov eax,[rcx+AIR_TARGET]
 cmp eax,[sim_count]
 jae .failed
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .failed
 cmp dword [rdx+ENTITY_KIND],3
 jne .failed
 mov eax,[rdx+ENTITY_SIDE]
 cmp eax,[rbp+ENTITY_SIDE]
 je .failed
.validated:
 cmp dword [sim_projectile_count],PROJECTILE_CAPACITY-32
 jb .capacity_ok
 inc dword [sim_projectile_dropped]
 jmp .failed
.capacity_ok:
 mov ebx,[cursor]
 mov ecx,PROJECTILE_CAPACITY
.find:
 mov eax,ebx
 shl eax,6
 lea rdx,[sim_projectiles]
 add rdx,rax
 cmp dword [rdx+PROJECTILE_ACTIVE],0
 je .found
 inc ebx
 and ebx,PROJECTILE_CAPACITY-1
 loop .find
 jmp .failed
.found:
 mov eax,[rbp+ENTITY_X]
 mov [rdx+PROJECTILE_X],eax
 mov eax,[rbp+ENTITY_Z]
 mov [rdx+PROJECTILE_Z],eax
 mov eax,r12d
 shl eax,6
 lea rcx,[sim_aircraft]
 add rcx,rax
 mov eax,[rcx+AIR_Y]
 mov [rdx+PROJECTILE_Y],eax
 movss xmm0,[rcx+AIR_VX]
 movss xmm1,[rcx+AIR_VY]
 movss xmm2,[rcx+AIR_VZ]
 cmp r13d,PROJECTILE_BOMB
 je .velocity
 ; Forward rounds follow aircraft's nose; aim alignment is checked by FSM.
 divss xmm0,[rcx+AIR_SPEED]
 divss xmm2,[rcx+AIR_SPEED]
 mulss xmm0,[airgun_step]
 mulss xmm2,[airgun_step]
 mov edi,[rcx+AIR_TARGET]
 mov eax,edi
 shl eax,5
 lea rcx,[sim_entities]
 add rax,rcx
 movss xmm1,[rax+ENTITY_X]
 subss xmm1,[rbp+ENTITY_X]
 mulss xmm1,xmm1
 movss xmm3,[rax+ENTITY_Z]
 subss xmm3,[rbp+ENTITY_Z]
 mulss xmm3,xmm3
 addss xmm1,xmm3
 sqrtss xmm1,xmm1
 maxss xmm1,[one]
 movss [rsp],xmm1
 mov [rsp+24],rdx
 movss [rsp+12],xmm0
 movss [rsp+16],xmm2
 call sim_entity_height
 mov eax,r12d
 shl eax,6
 lea rcx,[sim_aircraft]
 subss xmm0,[rcx+rax+AIR_Y]
 divss xmm0,[rsp]
 mulss xmm0,[airgun_step]
 movaps xmm1,xmm0
 movss xmm0,[rsp+12]
 movss xmm2,[rsp+16]
 mov rdx,[rsp+24]
.velocity:
 movss [rdx+PROJECTILE_VX],xmm0
 movss [rdx+PROJECTILE_VY],xmm1
 movss [rdx+PROJECTILE_VZ],xmm2
 mov dword [rdx+PROJECTILE_TTL],240
 cmp r13d,PROJECTILE_BOMB
 je .ttl
 mov dword [rdx+PROJECTILE_TTL],40
.ttl:
 mov eax,[rbp+ENTITY_SIDE]
 mov [rdx+PROJECTILE_SIDE],eax
 mov [rdx+PROJECTILE_KIND],r13d
 mov dword [rdx+PROJECTILE_DAMAGE],140
 mov dword [rdx+PROJECTILE_RADIUS],0x42100000 ;36m
 cmp r13d,PROJECTILE_BOMB
 je .damage
 mov dword [rdx+PROJECTILE_DAMAGE],24
 mov dword [rdx+PROJECTILE_RADIUS],0
.damage:
 mov [rdx+PROJECTILE_SOURCE],r12d
 mov eax,[rbp+ENTITY_GENERATION]
 mov [rdx+PROJECTILE_SOURCE_GENERATION],eax
 inc dword [rdx+PROJECTILE_GENERATION]
 mov dword [rdx+PROJECTILE_ACTIVE],1
 inc dword [sim_projectile_count]
 inc ebx
 and ebx,PROJECTILE_CAPACITY-1
 mov [cursor],ebx
 movss xmm0,[rdx+PROJECTILE_X]
 movss xmm1,[rdx+PROJECTILE_Y]
 movss xmm2,[rdx+PROJECTILE_Z]
 movss xmm3,[rdx+PROJECTILE_RADIUS]
 mov edi,EVENT_BOMB_LAUNCH
 cmp r13d,PROJECTILE_BOMB
 je .event
 mov edi,EVENT_AIR_GUN
.event:
 mov esi,[rdx+PROJECTILE_SIDE]
 call combat_event
 xor eax,eax
 jmp .out
.failed: mov eax,-1
.out:
 add rsp,40
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
.dropped:
 inc dword [sim_projectile_dropped]
.bad: mov eax,-1
 ret
