; Read-only deployment exclusion for real hostile explosives and recent impacts.
%include "schemas/combat.inc"
%include "schemas/aircraft.inc"
%include "schemas/player_blast.inc"
%include "schemas/world_contact.inc"
default rel
extern sim_projectiles,sim_events,sim_tick_count,world_contact_query
section .rodata
zero: dd 0.0
one: dd 1.0
gravity: dd 0.0109
margin: dd 20.0
maximum_radius: dd PLAYER_BLAST_MAX_RADIUS
maximum: dd 8000.0
minimum_y: dd -PLAYER_BLAST_MAX_Y
maximum_y: dd PLAYER_BLAST_MAX_Y
section .text
global deployment_blast_clear
; XMM0..2 candidate XYZ; EAX0clear,1unsafe. Preserves callee-owned registers.
; Conservative next90-tick swept blast-radius corridor, TTL/map bounded.
; Production static-contact forecast bounds near corridors; dynamic cover is
; conservatively ignored. No future body movement prediction or mutation.
deployment_blast_clear:
 push rbx
 push r12
 push r13
 sub rsp,96
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 ; Candidate is a current physical eye point, finite and within map bounds.
 xor ecx,ecx
.candidate:
 mov eax,[rsp+rcx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .unsafe
 inc ecx
 cmp ecx,3
 jb .candidate
 ucomiss xmm0,[zero]
 jb .unsafe
 ucomiss xmm0,[maximum]
 ja .unsafe
 ucomiss xmm2,[zero]
 jb .unsafe
 ucomiss xmm2,[maximum]
 ja .unsafe
 ucomiss xmm1,[minimum_y]
 jb .unsafe
 ucomiss xmm1,[maximum_y]
 ja .unsafe
 lea rbx,[sim_projectiles]
 mov r12d,PROJECTILE_CAPACITY
.projectile:
 cmp dword [rbx+PROJECTILE_ACTIVE],0
 je .next_projectile
 cmp dword [rbx+PROJECTILE_SIDE],1
 jne .next_projectile
 mov eax,[rbx+PROJECTILE_KIND]
 cmp eax,PROJECTILE_AIR_GUN
 je .next_projectile
 dec eax
 cmp eax,2
 ja .unsafe
 mov r13d,[rbx+PROJECTILE_TTL]
 cmp r13d,1
 jbe .next_projectile
 dec r13d ; production expires before sweeping the last TTL tick
 cmp r13d,90
 jbe .horizon
 mov r13d,90
.horizon:
 ; Active hostile malformed positions/velocities/radius fail closed.
 xor ecx,ecx
.finite:
 mov eax,[rbx+rcx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .unsafe
 inc ecx
 cmp ecx,6
 jb .finite
 movss xmm0,[rbx+PROJECTILE_RADIUS]
 call .radius
 test eax,eax
 jnz .unsafe
 mov eax,[rbx+PROJECTILE_X]
 mov [rsp+16],eax
 mov eax,[rbx+PROJECTILE_Y]
 mov [rsp+20],eax
 mov eax,[rbx+PROJECTILE_Z]
 mov [rsp+24],eax
 mov eax,[rbx+PROJECTILE_VY]
 mov [rsp+28],eax
 mov dword [rsp+48],0
.step:
 inc dword [rsp+48]
 movss xmm0,[rsp+16]
 addss xmm0,[rbx+PROJECTILE_VX]
 movss [rsp+32],xmm0
 movss xmm1,[rsp+20]
 addss xmm1,[rsp+28]
 movss [rsp+36],xmm1
 movss xmm2,[rsp+24]
 addss xmm2,[rbx+PROJECTILE_VZ]
 movss [rsp+40],xmm2
 ; Leaving the map expires before contact in production.
 ucomiss xmm0,[zero]
 jb .next_projectile
 ucomiss xmm0,[maximum]
 ja .next_projectile
 ucomiss xmm2,[zero]
 jb .next_projectile
 ucomiss xmm2,[maximum]
 ja .next_projectile
 ; Closest point on the actual linear fixed-tick segment, including endpoints.
 movss xmm3,[rsp+32]
 subss xmm3,[rsp+16]
 movss xmm4,[rsp+36]
 subss xmm4,[rsp+20]
 movss xmm5,[rsp+40]
 subss xmm5,[rsp+24]
 movss xmm0,[rsp]
 subss xmm0,[rsp+16]
 movss xmm1,[rsp+4]
 subss xmm1,[rsp+20]
 movss xmm2,[rsp+8]
 subss xmm2,[rsp+24]
 movaps xmm6,xmm3
 mulss xmm6,xmm3
 movaps xmm7,xmm4
 mulss xmm7,xmm4
 addss xmm6,xmm7
 movaps xmm7,xmm5
 mulss xmm7,xmm5
 addss xmm6,xmm7
 movaps xmm7,xmm0
 mulss xmm7,xmm3
 movaps xmm8,xmm1
 mulss xmm8,xmm4
 addss xmm7,xmm8
 movaps xmm8,xmm2
 mulss xmm8,xmm5
 addss xmm7,xmm8
 comiss xmm6,[zero]
 jbe .stationary
 divss xmm7,xmm6
 maxss xmm7,[zero]
 minss xmm7,[one]
 jmp .distance
.stationary:
 xorps xmm7,xmm7
.distance:
 mulss xmm3,xmm7
 mulss xmm4,xmm7
 mulss xmm5,xmm7
 subss xmm0,xmm3
 subss xmm1,xmm4
 subss xmm2,xmm5
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 mulss xmm2,xmm2
 addss xmm0,xmm1
 addss xmm0,xmm2
 ucomiss xmm0,[rsp+12]
 jp .unsafe
 jbe .verify
 mov eax,[rsp+32]
 mov [rsp+16],eax
 mov eax,[rsp+36]
 mov [rsp+20],eax
 mov eax,[rsp+40]
 mov [rsp+24],eax
 cmp dword [rbx+PROJECTILE_KIND],1
 je .next_step
 movss xmm0,[rsp+28]
 subss xmm0,[gravity]
 movss [rsp+28],xmm0
.next_step:
 dec r13d
 jnz .step
 jmp .next_projectile
; Only near corridors need physical forecasting. Static ground/solid contact
; bounds the dangerous flight. Moving actors and expiring wrecks cannot be
; assumed to intercept a future shot, so do not rely on those contacts.
.verify:
 mov r13d,[rsp+48]
 mov eax,[rbx+PROJECTILE_X]
 mov [rsp+16],eax
 mov eax,[rbx+PROJECTILE_Y]
 mov [rsp+20],eax
 mov eax,[rbx+PROJECTILE_Z]
 mov [rsp+24],eax
 mov eax,[rbx+PROJECTILE_VY]
 mov [rsp+28],eax
.verify_step:
 movss xmm0,[rsp+16]
 movss xmm1,[rsp+20]
 movss xmm2,[rsp+24]
 movaps xmm3,xmm0
 addss xmm3,[rbx+PROJECTILE_VX]
 movss [rsp+32],xmm3
 movaps xmm4,xmm1
 addss xmm4,[rsp+28]
 movss [rsp+36],xmm4
 movaps xmm5,xmm2
 addss xmm5,[rbx+PROJECTILE_VZ]
 movss [rsp+40],xmm5
 lea rdi,[rsp+64]
 mov esi,WORLD_CONTACT_BYTES
 mov edx,1
 call world_contact_query
 test eax,eax
 js .unsafe
 jz .verify_advance
 cmp dword [rsp+68],WORLD_CONTACT_SOLID
 ja .verify_advance
 ; Interpolate the real first static impact, with the conservative20m margin.
 movss xmm3,[rsp+64]
 movss xmm0,[rsp+32]
 subss xmm0,[rsp+16]
 mulss xmm0,xmm3
 addss xmm0,[rsp+16]
 subss xmm0,[rsp]
 movss xmm1,[rsp+36]
 subss xmm1,[rsp+20]
 mulss xmm1,xmm3
 addss xmm1,[rsp+20]
 subss xmm1,[rsp+4]
 movss xmm2,[rsp+40]
 subss xmm2,[rsp+24]
 mulss xmm2,xmm3
 addss xmm2,[rsp+24]
 subss xmm2,[rsp+8]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 mulss xmm2,xmm2
 addss xmm0,xmm1
 addss xmm0,xmm2
 ucomiss xmm0,[rsp+12]
 jp .unsafe
 jbe .unsafe
 jmp .next_projectile
.verify_advance:
 mov eax,[rsp+32]
 mov [rsp+16],eax
 mov eax,[rsp+36]
 mov [rsp+20],eax
 mov eax,[rsp+40]
 mov [rsp+24],eax
 cmp dword [rbx+PROJECTILE_KIND],1
 je .verify_next
 movss xmm0,[rsp+28]
 subss xmm0,[gravity]
 movss [rsp+28],xmm0
.verify_next:
 dec r13d
 jnz .verify_step
 jmp .unsafe
.next_projectile:
 add rbx,PROJECTILE_STRIDE
 dec r12d
 jnz .projectile
 lea rbx,[sim_events]
 mov r12d,EVENT_CAPACITY
.event:
 cmp dword [rbx+EVENT_SIDE],1
 jne .next_event
 mov eax,[sim_tick_count]
 sub eax,[rbx+EVENT_TICK]
 cmp eax,30
 ja .next_event
 mov eax,[rbx+EVENT_KIND]
 cmp eax,EVENT_TANK_IMPACT
 je .impact
 cmp eax,EVENT_ARTILLERY_IMPACT
 je .impact
 cmp eax,EVENT_BOMB_IMPACT
 jne .next_event
.impact:
 xor ecx,ecx
.event_finite:
 mov eax,[rbx+rcx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .unsafe
 inc ecx
 cmp ecx,3
 jb .event_finite
 movss xmm0,[rbx+EVENT_RADIUS]
 call .radius
 test eax,eax
 jnz .unsafe
 movss xmm0,[rbx+EVENT_X]
 subss xmm0,[rsp]
 movss xmm1,[rbx+EVENT_Y]
 subss xmm1,[rsp+4]
 movss xmm2,[rbx+EVENT_Z]
 subss xmm2,[rsp+8]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 mulss xmm2,xmm2
 addss xmm0,xmm1
 addss xmm0,xmm2
 ucomiss xmm0,[rsp+12]
 jp .unsafe
 jbe .unsafe
.next_event:
 add rbx,EVENT_STRIDE
 dec r12d
 jnz .event
 xor eax,eax
 jmp .return
.unsafe:
 mov eax,1
.return:
 add rsp,96
 pop r13
 pop r12
 pop rbx
 ret
; Radius on caller stack: nested call shifts RSP by8.
.radius:
 ucomiss xmm0,[zero]
 jp .bad_radius
 jbe .bad_radius
 ucomiss xmm0,[maximum_radius]
 ja .bad_radius
 addss xmm0,[margin]
 mulss xmm0,xmm0
 movss [rsp+20],xmm0
 xor eax,eax
 ret
.bad_radius:
 mov eax,1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
