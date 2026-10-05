; Authoritative bounded moving shells, fixed30Hz. Cosmetic ring is independent.
%include "schemas/entity.inc"
%include "schemas/combat.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,sim_blast,sim_shell_contact
extern terrain_height,terrain_los
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
zero: dd 0.0
one: dd 1.0
half: dd 0.5
max_coord: dd 8000.0
min_y: dd -1000.0
max_y: dd 1000.0
muzzle_height: dd 3.0
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
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 call terrain_height
 addss xmm0,[one]
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
 sqrtss xmm3,xmm3
 maxss xmm3,[one]
 lea rax,[shell_step]
 divss xmm3,[rax+r13*4] ; flight ticks T
 movss [rsp+16],xmm3
 divss xmm1,xmm3
 divss xmm2,xmm3
 movss [rsp+20],xmm1
 movss [rsp+24],xmm2
 movss xmm4,[rsp+4]
 subss xmm4,[rsp+12]
 divss xmm4,xmm3
 cmp r13d,2
 jne .linear_shell
 movaps xmm5,xmm3
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
 jne .no_gravity
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
 call segment_clear
 test eax,eax
 jz .impact
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
 mov edi,[rbx+PROJECTILE_SIDE]
 call sim_shell_contact
 cmp eax,-1
 jne .actor_impact
 mov eax,[rsp+12]
 mov [rbx+PROJECTILE_X],eax
 mov eax,[rsp+16]
 mov [rbx+PROJECTILE_Y],eax
 mov eax,[rsp+20]
 mov [rbx+PROJECTILE_Z],eax
 jmp .next
.actor_impact:
 mov eax,[rsp+12]
 mov [rsp+40],eax
 mov eax,[rsp+16]
 mov [rsp+44],eax
 mov eax,[rsp+20]
 mov [rsp+48],eax
 jmp .emit_impact
.impact:
 ; Eight bisections locate the last clear point, keeping blast outside solids.
 mov dword [rsp+24],0
 mov dword [rsp+28],0x3f800000
 mov r13d,8
.bisect:
 movss xmm6,[rsp+24]
 addss xmm6,[rsp+28]
 mulss xmm6,[half]
 movss [rsp+32],xmm6
 movss xmm3,[rsp+12]
 subss xmm3,[rsp]
 mulss xmm3,xmm6
 addss xmm3,[rsp]
 movss xmm4,[rsp+16]
 subss xmm4,[rsp+4]
 mulss xmm4,xmm6
 addss xmm4,[rsp+4]
 movss xmm5,[rsp+20]
 subss xmm5,[rsp+8]
 mulss xmm5,xmm6
 addss xmm5,[rsp+8]
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 call segment_clear
 test eax,eax
 mov eax,[rsp+32]
 jz .high
 mov [rsp+24],eax
 jmp .bisect_next
.high: mov [rsp+28],eax
.bisect_next:
 dec r13d
 jnz .bisect
 movss xmm6,[rsp+24]
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
 movss xmm0,[rsp+40]
 movss xmm1,[rsp+44]
 movss xmm2,[rsp+48]
 mov edi,[rbx+PROJECTILE_KIND]
 add edi,2
 mov esi,[rbx+PROJECTILE_SIDE]
 movss xmm3,[rbx+PROJECTILE_RADIUS]
 call combat_event
 movss xmm0,[rsp+40]
 movss xmm1,[rsp+48]
 movss xmm2,[rbx+PROJECTILE_RADIUS]
 movss xmm3,[rsp+44]
 mov edi,[rbx+PROJECTILE_SIDE]
 mov esi,[rbx+PROJECTILE_DAMAGE]
 call sim_blast
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
; Exact authored-solid sweep plus endpoint ground check.
segment_clear:
 sub rsp,40
 movss [rsp],xmm3
 movss [rsp+4],xmm4
 movss [rsp+8],xmm5
 call terrain_los
 test eax,eax
 jz .out
 movss xmm0,[rsp]
 movss xmm1,[rsp+8]
 call terrain_height
 comiss xmm0,[rsp+4]
 setb al
 movzx eax,al
.out:
 add rsp,40
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
