; Pure wheel braking with signed slope gravity, no engine thrust.
%include "schemas/air_rollout.inc"
%include "schemas/air_flight.inc"
default rel
section .rodata
one: dd 1.0
maximum: dd AIR_ROLLOUT_MAX_SPEED
grade_limit: dd AIR_ROLLOUT_MAX_GRADE
gravity: dd AIR_FLIGHT_GRAVITY
brake: dd AIR_ROLLOUT_BOMBER_BRAKE,AIR_ROLLOUT_FIGHTER_BRAKE
align 16
absolute_mask: dd 0x7fffffff,0,0,0
section .text
global air_ground_speed_step
; EDI role, XMM0 previous total ground speed, XMM1 signed uphill grade.
; EAX0 / XMM0 new total speed / XMM1 delta. Invalid -1 and zeros.
; max(0,old-brake-g*grade/sqrt(1+grade^2)); no reverse rolling.
air_ground_speed_step:
 cmp edi,1
 ja .invalid
 xorps xmm2,xmm2
 ucomiss xmm0,xmm2
 jp .invalid
 jb .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 movaps xmm2,xmm1
 andps xmm2,[absolute_mask]
 ucomiss xmm2,[grade_limit]
 jp .invalid
 ja .invalid
 movaps xmm3,xmm0
 movaps xmm2,xmm1
 mulss xmm2,xmm2
 addss xmm2,[one]
 sqrtss xmm2,xmm2
 divss xmm1,xmm2
 mulss xmm1,[gravity]
 lea rax,[brake]
 subss xmm0,[rax+rdi*4]
 subss xmm0,xmm1
 xorps xmm2,xmm2
 maxss xmm0,xmm2
 movaps xmm1,xmm0
 subss xmm1,xmm3
 xor eax,eax
 ret
.invalid:
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
