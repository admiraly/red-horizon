; Pure finite-horizon final-path preview using the production physical actuators.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_approach.inc"
%include "schemas/air_flight.inc"
%include "schemas/air_speed.inc"
default rel
extern sim_entities,sim_aircraft,sim_count
extern air_base_goal,terrain_height,air_speed_step,air_bank_step,air_vertical_step,air_world_sweep
extern atan2f,sinf,cosf
section .rodata
one: dd 1.0
negative: dd -1.0
pi: dd 3.14159265
tau: dd 6.28318530
lookahead: dd AIR_APPROACH_LOOKAHEAD
threshold: dd 600.0
clearance: dd AIR_APPROACH_CLEARANCE
slope: dd AIR_APPROACH_SLOPE
gain: dd AIR_APPROACH_HEIGHT_GAIN
exit_distance: dd AIR_APPROACH_FINAL_EXIT
climb: dd AIR_FLIGHT_VERTICAL_LIMIT
minus_climb: dd -AIR_FLIGHT_VERTICAL_LIMIT
cruise: dd 110.0,140.0
final_speed: dd AIR_SPEED_FINAL_TARGET
section .text
global air_final_clear
; EDI physical own ID, ESI selected base -> 1clear,0contact,-1invalid/source.
; Read-only: no authority, private route, fuel, facility or traffic mutation.
; Forecasts uninterrupted final guidance only, not later external evasive orders.
; Fixed120-tick work/112 stack bytes; no allocation or all-actor scans.
air_final_clear:
 push rbx
 push r12
 push r13
 sub rsp,112
 mov ebx,edi
 mov r12d,esi
 cmp esi,6
 jae .invalid
 call air_base_goal
 cmp eax,r12d
 jne .invalid
 movss [rsp+36],xmm0 ; base X
 movss [rsp+40],xmm1 ; base Z
 movss xmm0,[negative]
 cmp r12d,3
 jb .direction
 movss xmm0,[one]
.direction:
 movss [rsp+44],xmm0
 mov eax,ebx
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 movss xmm0,[rdx+ENTITY_X]
 movss [rsp],xmm0
 movss xmm0,[rdx+ENTITY_Z]
 movss [rsp+8],xmm0
 shl eax,1
 lea rdx,[sim_aircraft]
 add rdx,rax
 mov eax,[rdx+AIR_ROLE]
 mov [rsp+32],eax
 ; Validate scalar state before any libm or actuator use. Negative zero for
 ; height is accepted, signed/NaN/Inf speed or nonfinite angles are rejected.
 movss xmm0,[rdx+AIR_Y]
 movss [rsp+4],xmm0
 mov eax,[rdx+AIR_Y]
 and eax,0x7fffffff
 cmp eax,__float32__(12000.0)
 ja .invalid
 mov eax,[rdx+AIR_SPEED]
 cmp eax,__float32__(AIR_FLIGHT_MIN_SPEED)
 jb .invalid
 cmp eax,__float32__(AIR_FLIGHT_MAX_SPEED)
 ja .invalid
 mov [rsp+12],eax
 mov eax,[rdx+AIR_HEADING]
 mov [rsp+16],eax
 and eax,0x7fffffff
 cmp eax,__float32__(3.14159265)
 ja .invalid
 mov eax,[rdx+AIR_BANK]
 mov [rsp+20],eax
 and eax,0x7fffffff
 cmp eax,__float32__(1.6)
 ja .invalid
 mov eax,[rdx+AIR_VY]
 mov [rsp+24],eax
 and eax,0x7fffffff
 cmp eax,__float32__(AIR_FLIGHT_VERTICAL_LIMIT)
 ja .invalid
 mov r13d,AIR_APPROACH_PREVIEW_TICKS
.tick:
 ; Stop at the existing go-around boundary: no descent is commanded beyond it.
 movss xmm0,[rsp]
 subss xmm0,[rsp+36]
 mulss xmm0,[rsp+44]
 mulss xmm0,[negative]
 ucomiss xmm0,[exit_distance]
 jb .clear
 ; Current-location height target is identical to final approach guidance.
 movss xmm0,[rsp]
 movss xmm1,[rsp+8]
 call terrain_height
 movss [rsp+48],xmm0
 movss xmm1,[rsp]
 subss xmm1,[rsp+36]
 mulss xmm1,[rsp+44]
 mulss xmm1,[negative]
 subss xmm1,[threshold]
 mulss xmm1,[slope]
 addss xmm1,[clearance]
 maxss xmm1,[clearance]
 mov eax,[rsp+32]
 lea rdx,[cruise]
 minss xmm1,[rdx+rax*4]
 addss xmm0,xmm1
 subss xmm0,[rsp+4]
 mulss xmm0,[gain]
 minss xmm0,[climb]
 maxss xmm0,[minus_climb]
 movss [rsp+28],xmm0
 ; The final goal is600m ahead along the runway direction, centred in Z.
 movss xmm0,[rsp+44]
 mulss xmm0,[lookahead]
 movss xmm1,[rsp+40]
 subss xmm1,[rsp+8]
 call atan2f wrt ..plt
 subss xmm0,[rsp+16]
 ucomiss xmm0,[pi]
 jbe .low
 subss xmm0,[tau]
.low:
 movss xmm1,[pi]
 mulss xmm1,[negative]
 ucomiss xmm0,xmm1
 jae .heading
 addss xmm0,[tau]
.heading:
 movss [rsp+68],xmm0
 mov edi,[rsp+32]
 movss xmm0,[final_speed]
 movss xmm1,[rsp+12]
 call air_speed_step
 test eax,eax
 jnz .invalid
 movss [rsp+12],xmm0
 movss xmm0,[rsp+68]
 mov edi,[rsp+32]
 xor esi,esi
 movss xmm1,[rsp+12]
 movss xmm2,[rsp+20]
 call air_bank_step
 test eax,eax
 jnz .invalid
 movss [rsp+20],xmm1
 addss xmm0,[rsp+16]
 ucomiss xmm0,[pi]
 jbe .wrap_low
 subss xmm0,[tau]
.wrap_low:
 movss xmm1,[pi]
 mulss xmm1,[negative]
 ucomiss xmm0,xmm1
 jae .wrapped
 addss xmm0,[tau]
.wrapped:
 movss [rsp+16],xmm0
 mov edi,[rsp+32]
 movss xmm0,[rsp+28]
 movss xmm1,[rsp+12]
 movss xmm2,[rsp+24]
 call air_vertical_step
 test eax,eax
 jnz .invalid
 movss [rsp+24],xmm0
 addss xmm0,[rsp+4]
 movss [rsp+60],xmm0
 movss [rsp+52],xmm1 ; conserved-speed horizontal component
 movss xmm0,[rsp+16]
 call sinf wrt ..plt
 mulss xmm0,[rsp+52]
 addss xmm0,[rsp]
 movss [rsp+56],xmm0
 movss xmm0,[rsp+16]
 call cosf wrt ..plt
 mulss xmm0,[rsp+52]
 addss xmm0,[rsp+8]
 movss [rsp+64],xmm0
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+56]
 movss xmm4,[rsp+60]
 movss xmm5,[rsp+64]
 lea rdi,[rsp+80]
 mov esi,16
 call air_world_sweep
 test eax,eax
 js .invalid
 jnz .contact
 mov eax,[rsp+56]
 mov [rsp],eax
 mov eax,[rsp+60]
 mov [rsp+4],eax
 mov eax,[rsp+64]
 mov [rsp+8],eax
 dec r13d
 jnz .tick
.clear:
 mov eax,1
 jmp .done
.contact:
 xor eax,eax
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,112
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
