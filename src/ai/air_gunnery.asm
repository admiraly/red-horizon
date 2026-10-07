; Fighter fire discipline: straight physical rounds, constant observed motion.
; This predicts a useful shot; it never changes a projectile trajectory.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/shell_contact.inc"
default rel
extern sim_entities,sim_aircraft,projectile_air_gun_ready
section .rodata
speed: dd 28.0
zero: dd 0.0
lifetime: dd 40.0
contact: dd SHELL_CONTACT_RADIUS ; share the actual physical actor envelope
section .text
global air_gun_solution_ready
; EDI source -> EAX0 useful current forward shot/-1 wait or invalid.
; Read-only; same source/target metadata and cone guards as the producer.
air_gun_solution_ready:
 sub rsp,40
 mov [rsp+32],edi
 call projectile_air_gun_ready
 test eax,eax
 jnz .invalid
 ; w = actual round velocity minus currently observed target velocity.
 mov edi,[rsp+32]
 mov eax,edi
 shl eax,6
 lea r9,[sim_aircraft]
 add r9,rax
 mov eax,[r9+AIR_TARGET]
 mov edx,eax
 shl edx,5
 lea r8,[sim_entities]
 add r8,rdx
 shl eax,6
 lea r10,[sim_aircraft]
 add r10,rax
 mulss xmm0,[speed]
 mulss xmm1,[speed]
 mulss xmm2,[speed]
 subss xmm0,[r10+AIR_VX]
 subss xmm1,[r10+AIR_VY]
 subss xmm2,[r10+AIR_VZ]
 mov eax,edi
 shl eax,5
 lea r11,[sim_entities]
 add r11,rax
 movss xmm3,[r8+ENTITY_X]
 subss xmm3,[r11+ENTITY_X]
 movss xmm4,[r10+AIR_Y]
 subss xmm4,[r9+AIR_Y]
 movss xmm5,[r8+ENTITY_Z]
 subss xmm5,[r11+ENTITY_Z]
 ; Closest approach along r - w*t, within the real40tick round lifetime.
 movaps xmm6,xmm0
 mulss xmm6,xmm3
 movaps xmm7,xmm1
 mulss xmm7,xmm4
 addss xmm6,xmm7
 movaps xmm7,xmm2
 mulss xmm7,xmm5
 addss xmm6,xmm7
 movaps xmm7,xmm0
 mulss xmm7,xmm7
 movaps xmm8,xmm1
 mulss xmm8,xmm8
 addss xmm7,xmm8
 movaps xmm8,xmm2
 mulss xmm8,xmm8
 addss xmm7,xmm8
 divss xmm6,xmm7
 ucomiss xmm6,[zero]
 jp .invalid
 jbe .invalid
 ucomiss xmm6,[lifetime]
 ja .invalid
 mulss xmm0,xmm6
 mulss xmm1,xmm6
 mulss xmm2,xmm6
 subss xmm3,xmm0
 subss xmm4,xmm1
 subss xmm5,xmm2
 mulss xmm3,xmm3
 mulss xmm4,xmm4
 mulss xmm5,xmm5
 addss xmm3,xmm4
 addss xmm3,xmm5
 movss xmm4,[contact]
 mulss xmm4,xmm4
 ucomiss xmm3,xmm4
 jp .invalid
 ja .invalid
 xor eax,eax
 add rsp,40
 ret
.invalid:
 mov eax,-1
 add rsp,40
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
