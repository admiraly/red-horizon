; Pure cruise-envelope kinetic/potential energy and coordinated-turn drag.
%include "schemas/air_flight.inc"
%include "schemas/air_speed.inc"
%include "schemas/air_energy.inc"
default rel
extern air_speed_step,cosf
section .rodata
minimum: dd AIR_FLIGHT_MIN_SPEED
maximum: dd AIR_FLIGHT_MAX_SPEED
bank_limit: dd AIR_ENERGY_MAX_BANK
vertical_limit: dd AIR_FLIGHT_VERTICAL_LIMIT
gravity: dd AIR_FLIGHT_GRAVITY
one: dd 1.0
two: dd 2.0
negative: dd -1.0
induced: dd AIR_ENERGY_BOMBER_INDUCED,AIR_ENERGY_FIGHTER_INDUCED
coast: dd AIR_ENERGY_BOMBER_COAST,AIR_ENERGY_FIGHTER_COAST
acceleration: dd AIR_SPEED_BOMBER_ACCEL,AIR_SPEED_FIGHTER_ACCEL
braking: dd AIR_SPEED_BOMBER_BRAKE,AIR_SPEED_FIGHTER_BRAKE
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global air_energy_step
; EDI role0/1,ESI powered0/1; XMM0 desired,XMM1 previous total speed,
; XMM2 previous bank,XMM3 previous vertical displacement per tick.
; EAX0/XMM0 new speed/XMM1 actual delta; invalid -1/zeros.
; No authority writes/pointers/allocations. SysV nonvolatile registers preserved.
; Uses last completed physical bank/climb; same lag in authoritative preview.
; Cruise5..7 and existing total acceleration/braking caps remain safeguards;
; saturation does not represent a stall/ground-contact/whole-aerodynamics model.
air_energy_step:
 cmp edi,1
 ja .invalid
 cmp esi,1
 ja .invalid
 movaps xmm4,xmm2
 andps xmm4,[abs_mask]
 ucomiss xmm4,[bank_limit]
 jp .invalid
 ja .invalid
 movaps xmm4,xmm3
 andps xmm4,[abs_mask]
 ucomiss xmm4,[vertical_limit]
 jp .invalid
 ja .invalid
 ; Validate desired even when no engine work is available.
 ucomiss xmm0,[minimum]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 sub rsp,40 ; aligned for SysV calls
 mov [rsp],edi
 mov [rsp+4],esi
 movss [rsp+8],xmm1
 movss [rsp+12],xmm2
 movss [rsp+16],xmm3
 test esi,esi
 jnz .throttle
 movaps xmm0,xmm1
.throttle:
 call air_speed_step
 test eax,eax
 jnz .invalid_frame
 movss [rsp+20],xmm0
 movss xmm0,[rsp+12]
 call cosf wrt ..plt
 mulss xmm0,xmm0
 movss xmm1,[one]
 divss xmm1,xmm0
 subss xmm1,[one] ; tan(bank)^2 = coordinated n^2-1
 maxss xmm1,[zero] ; rounding must not invent thrust
 mov edi,[rsp]
 lea rax,[induced]
 mulss xmm1,[rax+rdi*4]
 cmp dword [rsp+4],0
 jne .drag_ready
 lea rax,[coast]
 addss xmm1,[rax+rdi*4]
.drag_ready:
 mulss xmm1,[rsp+8]
 mulss xmm1,[two] ; drag work in speed-squared units
 movss xmm0,[rsp+20]
 mulss xmm0,xmm0
 subss xmm0,xmm1
 movss xmm1,[rsp+16]
 mulss xmm1,[gravity]
 mulss xmm1,[two]
 subss xmm0,xmm1 ; potential gain removes kinetic energy; descent adds it
 maxss xmm0,[zero]
 sqrtss xmm0,xmm0
 subss xmm0,[rsp+8]
 lea rax,[acceleration]
 minss xmm0,[rax+rdi*4]
 lea rax,[braking]
 movss xmm1,[rax+rdi*4]
 mulss xmm1,[negative]
 maxss xmm0,xmm1
 addss xmm0,[rsp+8]
 minss xmm0,[maximum]
 maxss xmm0,[minimum]
 movaps xmm1,xmm0
 subss xmm1,[rsp+8]
 xor eax,eax
 add rsp,40
 ret
.invalid_frame:
 add rsp,40
.invalid:
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 mov eax,-1
 ret
section .rodata
zero: dd 0.0
section .note.GNU-stack noalloc noexec nowrite progbits
