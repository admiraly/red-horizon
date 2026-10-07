; Confidence-weighted mission/pursuit guidance; no body or global reads.
%include "schemas/air_flight.inc"
default rel
section .rodata
zero: dd 0.0
one: dd 1.0
pi: dd 3.141592653589793
minus_pi: dd -3.141592653589793
tau: dd 6.283185307179586
climb: dd AIR_FLIGHT_VERTICAL_LIMIT
minus_climb: dd -AIR_FLIGHT_VERTICAL_LIMIT
section .text
global air_pursuit_blend
; EDI0 heading (radians),1 vertical velocity (metres/tick).
; XMM0 own mission,XMM1 observed pursuit,XMM2 confidence. EAX0/XMM0 result;
; invalid EAX-1/XMM0 zero. Shortest angular arc, deterministic antipodal tie.
air_pursuit_blend:
 cmp edi,1
 ja .bad
 ucomiss xmm2,[zero]
 jp .bad
 jb .bad
 ucomiss xmm2,[one]
 ja .bad
 movss xmm3,[pi]
 movss xmm4,[minus_pi]
 test edi,edi
 jz .validate
 movss xmm3,[climb]
 movss xmm4,[minus_climb]
.validate:
 ucomiss xmm0,xmm4
 jp .bad
 jb .bad
 ucomiss xmm0,xmm3
 ja .bad
 ucomiss xmm1,xmm4
 jp .bad
 jb .bad
 ucomiss xmm1,xmm3
 ja .bad
 ucomiss xmm2,[zero]
 je .done
 ucomiss xmm2,[one]
 je .pursuit
 subss xmm1,xmm0
 test edi,edi
 jnz .blend
 ucomiss xmm1,[pi]
 jbe .low
 subss xmm1,[tau]
.low:
 ucomiss xmm1,[minus_pi]
 jae .blend
 addss xmm1,[tau]
.blend:
 mulss xmm1,xmm2
 addss xmm0,xmm1
 test edi,edi
 jnz .done
 ucomiss xmm0,[pi]
 jbe .wrap_low
 subss xmm0,[tau]
.wrap_low:
 ucomiss xmm0,[minus_pi]
 jae .done
 addss xmm0,[tau]
.done:
 xor eax,eax
 ret
.pursuit:
 movaps xmm0,xmm1
 jmp .done
.bad:
 mov eax,-1
 xorps xmm0,xmm0
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
