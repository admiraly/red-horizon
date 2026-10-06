; Bank is about local +Z: positive raises local +X wing, so positive bank
; turns heading negative. yaw = -g_per_tick_squared*tan(bank)/speed_per_tick.
%include "schemas/air_flight.inc"
default rel
extern atan2f,sinf,cosf
section .rodata
zero: dd 0.0
pi: dd 3.14159265
minimum_speed: dd AIR_FLIGHT_MIN_SPEED
maximum_speed: dd AIR_FLIGHT_MAX_SPEED
maximum_bank: dd AIR_FLIGHT_FIGHTER_EMERGENCY_BANK
gravity: dd AIR_FLIGHT_GRAVITY
negative: dd -1.0
gain: dd AIR_FLIGHT_HEADING_GAIN
normal_bank: dd AIR_FLIGHT_BOMBER_BANK,AIR_FLIGHT_FIGHTER_BANK
emergency_bank: dd AIR_FLIGHT_BOMBER_EMERGENCY_BANK,AIR_FLIGHT_FIGHTER_EMERGENCY_BANK
roll: dd AIR_FLIGHT_BOMBER_ROLL,AIR_FLIGHT_FIGHTER_ROLL
yaw_bound: dd AIR_FLIGHT_BOMBER_YAW_BOUND,AIR_FLIGHT_FIGHTER_YAW_BOUND
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global air_bank_step
; EDI role0/1,ESI emergency0/1,XMM0 heading error,XMM1 speed,XMM2 oldbank.
; ->EAX0 success/-1 invalid,XMM0 actual yaw delta,XMM1 newbank. No state writes.
air_bank_step:
 cmp edi,1
 ja .invalid_leaf
 cmp esi,1
 ja .invalid_leaf
 movaps xmm3,xmm0
 andps xmm3,[abs_mask]
 ucomiss xmm3,[pi]
 jp .invalid_leaf
 ja .invalid_leaf
 ucomiss xmm1,[minimum_speed]
 jp .invalid_leaf
 jb .invalid_leaf
 ucomiss xmm1,[maximum_speed]
 ja .invalid_leaf
 movaps xmm3,xmm2
 andps xmm3,[abs_mask]
 ucomiss xmm3,[maximum_bank]
 jp .invalid_leaf
 ja .invalid_leaf
 sub rsp,56
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 mov [rsp+12],edi
 mov [rsp+16],esi
 mulss xmm0,[gain]
 lea rcx,[yaw_bound]
 movss xmm1,[rcx+rdi*4]
 minss xmm0,xmm1
 mulss xmm1,[negative]
 maxss xmm0,xmm1
 mulss xmm0,[rsp+4]
 movss xmm1,[gravity]
 call atan2f wrt ..plt
 mulss xmm0,[negative]
 mov edi,[rsp+12]
 lea rcx,[normal_bank]
 cmp dword [rsp+16],0
 je .limit
 lea rcx,[emergency_bank]
.limit:
 movss xmm1,[rcx+rdi*4]
 minss xmm0,xmm1
 mulss xmm1,[negative]
 maxss xmm0,xmm1
 subss xmm0,[rsp+8]
 lea rcx,[roll]
 movss xmm1,[rcx+rdi*4]
 minss xmm0,xmm1
 mulss xmm1,[negative]
 maxss xmm0,xmm1
 addss xmm0,[rsp+8]
 movss [rsp+24],xmm0
 call sinf wrt ..plt
 movss [rsp+28],xmm0
 movss xmm0,[rsp+24]
 call cosf wrt ..plt
 movss xmm1,[rsp+28]
 divss xmm1,xmm0
 mulss xmm1,[gravity]
 mulss xmm1,[negative]
 divss xmm1,[rsp+4]
 movaps xmm0,xmm1
 movss xmm1,[rsp+24]
 xor eax,eax
 add rsp,56
 ret
.invalid_leaf:
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
