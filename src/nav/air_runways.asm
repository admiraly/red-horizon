; Static paved runway rectangles; authority geometry exists without graphics.
%include "schemas/air_bases.inc"
default rel
section .rodata align=32
%include "schemas/air_bases_data.inc"
maximum: dd 8000.0
zero: dd 0.0
align 16
abs_mask: dq 0x7fffffffffffffff,0
section .text
global air_runway_body
; XMM0/1 own XZ and XMM2 finite nonnegative conservative circle radius.
; ->EAX1 inside one rectangle/0off/-1invalid. No sources/inputs/world writes.
; Subtract exact room from float32 coordinate differences promoted to double,
; then compare radius, avoiding outward rounding of tiny positive edge radii.
; GPR/SIMD scratch caller-saved only, SysV nonvolatile preserved; no calls/heap.
air_runway_body:
%macro coordinate 1
 ucomiss %1,[zero]
 jp .invalid
 jb .invalid
 ucomiss %1,[maximum]
 ja .invalid
%endmacro
 coordinate xmm0
 coordinate xmm1
 coordinate xmm2
%unmacro coordinate 1
 cvtss2sd xmm3,xmm0
 cvtss2sd xmm4,xmm1
 cvtss2sd xmm5,xmm2
 xor ecx,ecx
 lea rdx,[air_bases]
.loop:
 cvtss2sd xmm6,[rdx]
 subsd xmm6,xmm3
 andpd xmm6,[abs_mask]
 cvtss2sd xmm7,[rdx+8]
 subsd xmm7,xmm6
 ucomisd xmm7,xmm5
 jb .next
 cvtss2sd xmm6,[rdx+4]
 subsd xmm6,xmm4
 andpd xmm6,[abs_mask]
 cvtss2sd xmm7,[rdx+12]
 subsd xmm7,xmm6
 ucomisd xmm7,xmm5
 jb .next
 mov eax,1
 ret
.next:
 add rdx,AIR_BASE_STRIDE
 inc ecx
 cmp ecx,AIR_BASE_COUNT
 jb .loop
 xor eax,eax
 ret
.invalid:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
