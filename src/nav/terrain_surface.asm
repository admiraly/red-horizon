; Stateless analytic height/gradient and bounded center-road sampler, SSE2/SysV.
%include "schemas/terrain_surface.inc"
default rel
extern terrain_height,terrain_relief
section .rodata align=16
%include "schemas/terrain_roads.inc"
%if TERRAIN_ROAD_COUNT < 1 || TERRAIN_ROAD_COUNT > TERRAIN_ROAD_LIMIT
 %error "terrain road count exceeds stateless bounded contract"
%endif
zero: dd 0.0
one: dd 1.0
one_double: dq 1.0
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
; private stack; clobbers caller-saved registers. Aligned external height and derivative-component calls.
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
 ; terrain_height already includes relief height exactly once. Add derivatives
 ; once, preserving the existing center-road classification and invalid policy.
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 call terrain_relief
 addss xmm1,[rsp+12]
 addss xmm2,[rsp+16]
 movss [rsp+12],xmm1
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
; Whole conservative body circle inside a single road capsule. Double scalar
; SSE2 geometry avoids float32 closest-point cancellation near narrow margins.
; Inputs are float32; no tolerance enlarges the paved boundary. Union junctions
; may conservatively report off-road even when their combined pavement covers it.
global terrain_road_body
terrain_road_body:
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
 ucomiss xmm2,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm2,[maximum]
 ja .invalid
 cvtss2sd xmm8,xmm0
 cvtss2sd xmm9,xmm1
 cvtss2sd xmm10,xmm2
 pxor xmm11,xmm11
 xor ecx,ecx
 lea rdx,[terrain_road_segments]
.road:
 cmp ecx,TERRAIN_ROAD_COUNT
 jae .offroad
 test dword [rdx+TERRAIN_ROAD_FLAGS],TERRAIN_ROAD_ACTIVE
 jz .next
 cvtss2sd xmm7,[rdx+TERRAIN_ROAD_HALF_WIDTH]
 ucomisd xmm7,xmm10
 jb .next
 ; Error-free TwoDiff residual detects a radius too small to change the
 ; rounded double margin. Round the margin inward only when subtraction
 ; rounded upward, preserving exact inclusive boundaries (including r=0).
 movapd xmm14,xmm7
 subsd xmm7,xmm10
 movapd xmm12,xmm14
 subsd xmm12,xmm7
 movapd xmm13,xmm7
 addsd xmm13,xmm12
 subsd xmm14,xmm13
 subsd xmm12,xmm10
 addsd xmm14,xmm12
 ucomisd xmm14,xmm11
 jae .margin_ready
 movq rax,xmm7
 dec rax
 movq xmm7,rax
.margin_ready:
 mulsd xmm7,xmm7
 cvtss2sd xmm0,[rdx+TERRAIN_ROAD_FROM_X]
 cvtss2sd xmm1,[rdx+TERRAIN_ROAD_FROM_Z]
 cvtss2sd xmm3,[rdx+TERRAIN_ROAD_TO_X]
 cvtss2sd xmm4,[rdx+TERRAIN_ROAD_TO_Z]
 subsd xmm3,xmm0
 subsd xmm4,xmm1
 movapd xmm5,xmm8
 movapd xmm6,xmm9
 subsd xmm5,xmm0
 subsd xmm6,xmm1
 movapd xmm12,xmm3
 movapd xmm13,xmm4
 mulsd xmm12,xmm3
 mulsd xmm13,xmm4
 addsd xmm12,xmm13
 mulsd xmm5,xmm3
 mulsd xmm6,xmm4
 addsd xmm5,xmm6
 divsd xmm5,xmm12
 maxsd xmm5,xmm11
 minsd xmm5,[one_double]
 mulsd xmm3,xmm5
 mulsd xmm4,xmm5
 addsd xmm3,xmm0
 addsd xmm4,xmm1
 subsd xmm3,xmm8
 subsd xmm4,xmm9
 mulsd xmm3,xmm3
 mulsd xmm4,xmm4
 addsd xmm3,xmm4
 ucomisd xmm3,xmm7
 jbe .onroad
.next:
 add rdx,TERRAIN_ROAD_STRIDE
 inc ecx
 jmp .road
.offroad:
 xor eax,eax
 ret
.onroad:
 mov eax,TERRAIN_ROAD
 ret
.invalid:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
