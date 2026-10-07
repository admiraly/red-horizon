; Lift-constrained vertical response followed by the production velocity actuator.
%include "schemas/air_flight.inc"
%include "schemas/air_load.inc"
%include "schemas/air_lift.inc"
default rel
extern cosf,air_vertical_step
section .rodata
minimum: dd AIR_FLIGHT_MIN_SPEED
maximum: dd AIR_FLIGHT_MAX_SPEED
vertical: dd AIR_FLIGHT_VERTICAL_LIMIT
minus_vertical: dd -AIR_FLIGHT_VERTICAL_LIMIT
bank_limit: dd AIR_LIFT_MAX_BANK
stall: dd AIR_LOAD_BOMBER_STALL_SPEED,AIR_LOAD_FIGHTER_STALL_SPEED
one: dd 1.0
gravity: dd AIR_FLIGHT_GRAVITY
align 16
absolute_mask: dd 0x7fffffff,0,0,0
section .text
global air_lift_step
; EDI role0/1; XMM0 desired VY,XMM1 total speed,XMM2 previous VY,XMM3 bank.
; ->EAX0/XMM0 actual VY/XMM1 conserved-speed horizontal/XMM2 pitch.
; Malformed ->-1/zeros. Pure SysV, no pointers/authority/allocations.
; Available upward load=(speed/level_stall_reference)^2*cos(bank).
; Below one, commanded VY cannot exceed previousVY-g*(1-available_load).
; Existing bounded vertical acceleration and +/-0.5 terminal sink remain;
; this is a practical lift-deficit stall response, not spin/angle-of-attack CFD.
air_lift_step:
 cmp edi,1
 ja .invalid
 movaps xmm4,xmm0
 andps xmm4,[absolute_mask]
 ucomiss xmm4,[vertical]
 jp .invalid
 ja .invalid
 ucomiss xmm1,[minimum]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[maximum]
 ja .invalid
 movaps xmm4,xmm2
 andps xmm4,[absolute_mask]
 ucomiss xmm4,[vertical]
 jp .invalid
 ja .invalid
 movaps xmm4,xmm3
 andps xmm4,[absolute_mask]
 ucomiss xmm4,[bank_limit]
 jp .invalid
 ja .invalid
 sub rsp,24
 mov [rsp],edi
 movss [rsp+4],xmm0
 movss [rsp+8],xmm1
 movss [rsp+12],xmm2
 movaps xmm0,xmm3
 call cosf wrt ..plt
 mov edi,[rsp]
 movss xmm1,[rsp+8]
 lea rax,[stall]
 divss xmm1,[rax+rdi*4]
 mulss xmm1,xmm1
 mulss xmm1,xmm0
 movss xmm0,[rsp+4]
 ucomiss xmm1,[one]
 jae .response
 movss xmm2,[one]
 subss xmm2,xmm1
 mulss xmm2,[gravity]
 movss xmm1,[rsp+12]
 subss xmm1,xmm2
 maxss xmm1,[minus_vertical]
 minss xmm0,xmm1
.response:
 movss xmm1,[rsp+8]
 movss xmm2,[rsp+12]
 add rsp,24
 jmp air_vertical_step wrt ..plt
.invalid:
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 xorps xmm2,xmm2
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
