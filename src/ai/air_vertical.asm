; Bounded vertical acceleration and conserved total airspeed; pure SysV/SSE2.
%include "schemas/air_flight.inc"
default rel
extern atan2f
section .rodata
minimum_speed: dd AIR_FLIGHT_MIN_SPEED
maximum_speed: dd AIR_FLIGHT_MAX_SPEED
vertical_limit: dd AIR_FLIGHT_VERTICAL_LIMIT
negative: dd -1.0
acceleration: dd AIR_FLIGHT_BOMBER_VERTICAL_ACCEL,AIR_FLIGHT_FIGHTER_VERTICAL_ACCEL
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global air_vertical_step
; EDI role0/1, XMM0 desired VY, XMM1 total speed, XMM2 previous VY.
; -> EAX0, XMM0 new VY, XMM1 horizontal speed, XMM2 pitch. Invalid -> -1, zeros.
; No pointers, authority writes, allocations or nonvolatile-register clobbers.
air_vertical_step:
 cmp edi,1
 ja .invalid
 movaps xmm3,xmm0
 andps xmm3,[abs_mask]
 ucomiss xmm3,[vertical_limit]
 jp .invalid
 ja .invalid
 ucomiss xmm1,[minimum_speed]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[maximum_speed]
 ja .invalid
 movaps xmm3,xmm2
 andps xmm3,[abs_mask]
 ucomiss xmm3,[vertical_limit]
 jp .invalid
 ja .invalid
 subss xmm0,xmm2
 lea rax,[acceleration]
 movss xmm3,[rax+rdi*4]
 minss xmm0,xmm3
 mulss xmm3,[negative]
 maxss xmm0,xmm3
 addss xmm0,xmm2
 ; Rounding never pushes the published vertical speed outside its bound.
 minss xmm0,[vertical_limit]
 movss xmm3,[vertical_limit]
 mulss xmm3,[negative]
 maxss xmm0,xmm3
 mulss xmm1,xmm1
 movaps xmm3,xmm0
 mulss xmm3,xmm3
 subss xmm1,xmm3
 sqrtss xmm1,xmm1
 sub rsp,24
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 call atan2f wrt ..plt
 movaps xmm2,xmm0
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 add rsp,24
 xor eax,eax
 ret
.invalid:
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 xorps xmm2,xmm2
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
