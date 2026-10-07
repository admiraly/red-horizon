; Pure longitudinal throttle/braking actuator; no arbitrary speed reset.
%include "schemas/air_flight.inc"
%include "schemas/air_speed.inc"
default rel
section .rodata
minimum: dd AIR_FLIGHT_MIN_SPEED
maximum: dd AIR_FLIGHT_MAX_SPEED
negative: dd -1.0
acceleration: dd AIR_SPEED_BOMBER_ACCEL,AIR_SPEED_FIGHTER_ACCEL
braking: dd AIR_SPEED_BOMBER_BRAKE,AIR_SPEED_FIGHTER_BRAKE
section .text
global air_speed_step
; EDI role0/1, XMM0 desired total airspeed, XMM1 previous total airspeed.
; ->EAX0, XMM0 new total speed, XMM1 signed change. Invalid ->-1/zeros.
; Preserves SysV nonvolatile registers/stack. No pointers/writes/allocations.
; Airborne1..7 envelope only; ground/stall/lift/drag remain separate.
air_speed_step:
 cmp edi,1
 ja .invalid
 ucomiss xmm0,[minimum]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 ucomiss xmm1,[minimum]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[maximum]
 ja .invalid
 subss xmm0,xmm1
 lea rax,[acceleration]
 minss xmm0,[rax+rdi*4]
 lea rax,[braking]
 movss xmm2,[rax+rdi*4]
 mulss xmm2,[negative]
 maxss xmm0,xmm2
 movaps xmm2,xmm0
 addss xmm0,xmm1
 minss xmm0,[maximum]
 maxss xmm0,[minimum]
 subss xmm0,xmm1
 movaps xmm2,xmm0 ; actual rounded/saturated delta
 addss xmm0,xmm1
 movaps xmm1,xmm2
 xor eax,eax
 ret
.invalid:
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
