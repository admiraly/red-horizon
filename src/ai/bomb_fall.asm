; SSE2 discrete-endpoint gravity prediction. No source or authority writes.
default rel
section .rodata
g: dd 0.0109
half: dq 0.5
two: dq 2.0
zero: dq 0.0
section .text
global air_bomb_fall_time
; XMM0 height above intended surface, XMM1 inherited vertical metres/tick.
; XMM0 positive tick time, or zero for nonfinite/invalid height.
air_bomb_fall_time:
 cvtss2sd xmm0,xmm0
 cvtss2sd xmm1,xmm1
 ucomisd xmm0,[zero]
 jp .bad
 jbe .bad
 movapd xmm2,xmm0
 subsd xmm2,xmm0
 ucomisd xmm2,[zero]
 jp .bad
 movapd xmm2,xmm1
 subsd xmm2,xmm1
 ucomisd xmm2,[zero]
 jp .bad
 movss xmm2,[g]
 cvtss2sd xmm2,xmm2
 movapd xmm3,xmm2
 mulsd xmm3,[half]
 addsd xmm1,xmm3
 movapd xmm3,xmm1
 mulsd xmm3,xmm3
 movapd xmm4,xmm0
 mulsd xmm4,xmm2
 mulsd xmm4,[two]
 addsd xmm3,xmm4
 sqrtsd xmm3,xmm3
 ucomisd xmm1,[zero]
 jb .descending
 addsd xmm3,xmm1
 divsd xmm3,xmm2
 cvtsd2ss xmm0,xmm3
 ret
.descending:
 subsd xmm3,xmm1
 mulsd xmm0,[two]
 divsd xmm0,xmm3
 cvtsd2ss xmm0,xmm0
 ret
.bad:
 pxor xmm0,xmm0
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
