; Stateless analytic height/gradient and bounded center-road sampler, SSE2/SysV.
%include "schemas/terrain_surface.inc"
default rel
extern terrain_height
section .rodata align=16
%include "schemas/terrain_roads.inc"
%if TERRAIN_ROAD_COUNT < 1 || TERRAIN_ROAD_COUNT > TERRAIN_ROAD_LIMIT
 %error "terrain road count exceeds stateless bounded contract"
%endif
zero: dd 0.0
one: dd 1.0
maximum: dd 8000.0
center: dd 4000.0
ridge_extent: dd 800.0
ridge_gradient: dd 0.0225
xgradient: dd 0.000002
zgradient: dd 0.000001
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global terrain_surface
; XMM0/1 XZ -> XMM0 height, XMM1/2 analytic gradient X/Z; EAX center class.
; Invalid input: EAX=-1, all three scalar outputs canonical +0. No writes except
; private stack; clobbers caller-saved registers. Single aligned external call.
terrain_surface:
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
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 call terrain_height
 movss [rsp+8],xmm0
 movss xmm1,[rsp]
 subss xmm1,[center]
 movaps xmm3,xmm1
 mulss xmm1,[xgradient]
 movaps xmm4,xmm3
 andps xmm4,[abs_mask]
 ; At ridge apex and endpoints choose ridge derivative0. The smooth base
 ; derivative remains present; no claim of differentiability/grade clearance.
 ucomiss xmm4,[ridge_extent]
 jae .gradient_ready
 ucomiss xmm3,[zero]
 je .gradient_ready
 jb .ridge_left
 subss xmm1,[ridge_gradient]
 jmp .gradient_ready
.ridge_left:
 addss xmm1,[ridge_gradient]
.gradient_ready:
 movss [rsp+12],xmm1
 movss xmm2,[rsp+4]
 subss xmm2,[center]
 mulss xmm2,[zgradient]
 movss [rsp+16],xmm2
 xor ecx,ecx
 lea rdx,[terrain_road_segments]
.road:
 cmp ecx,TERRAIN_ROAD_COUNT
 jae .offroad
 test dword [rdx+TERRAIN_ROAD_FLAGS],TERRAIN_ROAD_ACTIVE
 jz .next
 movss xmm3,[rdx+TERRAIN_ROAD_TO_X]
 subss xmm3,[rdx+TERRAIN_ROAD_FROM_X]
 movss xmm4,[rdx+TERRAIN_ROAD_TO_Z]
 subss xmm4,[rdx+TERRAIN_ROAD_FROM_Z]
 movss xmm5,[rsp]
 subss xmm5,[rdx+TERRAIN_ROAD_FROM_X]
 movss xmm6,[rsp+4]
 subss xmm6,[rdx+TERRAIN_ROAD_FROM_Z]
 movaps xmm7,xmm3
 mulss xmm7,xmm3
 movaps xmm8,xmm4
 mulss xmm8,xmm4
 addss xmm7,xmm8
 mulss xmm5,xmm3
 mulss xmm6,xmm4
 addss xmm5,xmm6
 divss xmm5,xmm7
 maxss xmm5,[zero]
 minss xmm5,[one]
 mulss xmm3,xmm5
 mulss xmm4,xmm5
 addss xmm3,[rdx+TERRAIN_ROAD_FROM_X]
 addss xmm4,[rdx+TERRAIN_ROAD_FROM_Z]
 movss xmm5,[rsp]
 subss xmm5,xmm3
 movss xmm6,[rsp+4]
 subss xmm6,xmm4
 mulss xmm5,xmm5
 mulss xmm6,xmm6
 addss xmm5,xmm6
 movss xmm7,[rdx+TERRAIN_ROAD_HALF_WIDTH]
 mulss xmm7,xmm7
 ucomiss xmm5,xmm7
 jbe .onroad
.next:
 add rdx,TERRAIN_ROAD_STRIDE
 inc ecx
 jmp .road
.offroad:
 xor eax,eax
 jmp .result
.onroad:
 mov eax,TERRAIN_ROAD
.result:
 movss xmm0,[rsp+8]
 movss xmm1,[rsp+12]
 movss xmm2,[rsp+16]
 add rsp,40
 ret
.invalid:
 pxor xmm0,xmm0
 pxor xmm1,xmm1
 pxor xmm2,xmm2
 mov eax,-1
 add rsp,40
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
