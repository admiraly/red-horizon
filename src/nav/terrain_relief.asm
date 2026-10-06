; Stateless raised-relief component, NASM x86-64/SSE2, SysV.
%include "schemas/terrain_relief.inc"
default rel
section .rodata align=16
%include "schemas/terrain_relief_data.inc"
%if TERRAIN_RELIEF_COUNT != 1 || TERRAIN_RELIEF_COUNT > TERRAIN_RELIEF_LIMIT
 %error "relief count outside bounded component contract"
%endif
zero: dd 0.0
one: dd 1.0
maximum: dd 8000.0
section .text
global terrain_relief
; XMM0 X, XMM1 Z -> extra height XMM0, dX XMM1, dZ XMM2, EAX0 valid.
; Invalid finite/map input: EAX-1, scalar float outputs canonical +0.
; Preserves SysV nonvolatile registers; caller-saved integer/SIMD clobbered.
; Reads only static one-field data; private stack, no allocation/world writes.
terrain_relief:
 sub rsp,40
 ucomiss xmm0,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 ucomiss xmm1,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[maximum]
 ja .invalid
 movss [rsp],xmm1
 test dword [terrain_relief_fields+RELIEF_FLAGS],RELIEF_ACTIVE
 jz .empty
 lea rdi,[terrain_relief_fields+RELIEF_X0]
 call factor
 movss [rsp+4],xmm0
 movss [rsp+8],xmm1
 movss xmm0,[rsp]
 lea rdi,[terrain_relief_fields+RELIEF_Z0]
 call factor
 movaps xmm2,xmm1
 mulss xmm2,[rsp+4]
 mulss xmm2,[terrain_relief_fields+RELIEF_HEIGHT]
 movaps xmm1,xmm0
 mulss xmm1,[rsp+8]
 mulss xmm1,[terrain_relief_fields+RELIEF_HEIGHT]
 mulss xmm0,[rsp+4]
 mulss xmm0,[terrain_relief_fields+RELIEF_HEIGHT]
 xor eax,eax
 jmp .done
.empty:
 pxor xmm0,xmm0
 pxor xmm1,xmm1
 pxor xmm2,xmm2
 xor eax,eax
 jmp .done
.invalid:
 pxor xmm0,xmm0
 pxor xmm1,xmm1
 pxor xmm2,xmm2
 mov eax,-1
.done:
 add rsp,40
 ret
; XMM0 coordinate, RDI four canonical ordered breaks -> factor/dFactor.
; Exact breaks choose derivative +0; continuous height, no grade clearance claim.
factor:
 ucomiss xmm0,[rdi]
 jbe .outside
 ucomiss xmm0,[rdi+12]
 jae .outside
 ucomiss xmm0,[rdi+4]
 je .plateau
 jb .up
 ucomiss xmm0,[rdi+8]
 jbe .plateau
 movss xmm1,[rdi+12]
 subss xmm1,[rdi+8]
 movss xmm2,[rdi+12]
 subss xmm2,xmm0
 divss xmm2,xmm1
 movaps xmm0,xmm2
 movss xmm2,[zero]
 subss xmm2,[one]
 divss xmm2,xmm1
 movaps xmm1,xmm2
 ret
.up:
 subss xmm0,[rdi]
 movss xmm1,[rdi+4]
 subss xmm1,[rdi]
 divss xmm0,xmm1
 movss xmm2,[one]
 divss xmm2,xmm1
 movaps xmm1,xmm2
 ret
.plateau:
 movss xmm0,[one]
 pxor xmm1,xmm1
 ret
.outside:
 pxor xmm0,xmm0
 pxor xmm1,xmm1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
