; Stateless whole swept-body grade bound, baseline SSE2/SysV.
%include "schemas/terrain_grade.inc"
default rel
section .rodata align=16
%include "schemas/terrain_grade_data.inc"
%if TERRAIN_GRADE_COUNT < 1 || TERRAIN_GRADE_COUNT > TERRAIN_GRADE_LIMIT
 %error "grade facet count exceeds bounded contract"
%endif
zero: dd 0.0
maximum: dd 8000.0
map_max_double: dq 8000.0
center: dq 4000.0
base_x: dq GRADE_BASE_X
base_z: dq GRADE_BASE_Z
guard: dq GRADE_GUARD_SQ
limits: dq GRADE_INF_LIMIT_SQ,GRADE_TANK_LIMIT_SQ,GRADE_ARTY_LIMIT_SQ
radii: dd BODY_INF_SWEEP_RADIUS,BODY_TANK_SWEEP_RADIUS,BODY_ARTY_SWEEP_RADIUS
section .text
global terrain_grade_clear
; EDI role, XMM0/1 startXZ,XMM2/3 endXZ -> EAX1clear,0blocked,-1invalid.
; Caller-saved GPR/XMM clobbers only; no calls, stack writes, heap or future state.
terrain_grade_clear:
 cmp edi,3
 ja .invalid
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
 ucomiss xmm3,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm3,[maximum]
 ja .invalid
 cmp edi,3
 je .clear
 cvtss2sd xmm8,xmm0
 cvtss2sd xmm9,xmm1
 cvtss2sd xmm10,xmm2
 cvtss2sd xmm11,xmm3
 movapd xmm0,xmm8
 movapd xmm1,xmm9
 minsd xmm8,xmm10
 minsd xmm9,xmm11
 maxsd xmm10,xmm0
 maxsd xmm11,xmm1
 lea rax,[radii]
 cvtss2sd xmm4,[rax+rdi*4]
 subsd xmm8,xmm4
 subsd xmm9,xmm4
 addsd xmm10,xmm4
 addsd xmm11,xmm4
 pxor xmm0,xmm0
 ucomisd xmm8,xmm0
 jb .blocked
 ucomisd xmm9,xmm0
 jb .blocked
 ucomisd xmm10,[map_max_double]
 ja .blocked
 ucomisd xmm11,[map_max_double]
 ja .blocked
 lea rax,[limits]
 movsd xmm7,[rax+rdi*8]
 lea rdx,[terrain_grade_facets]
 xor r8d,r8d
.facet:
 cmp r8d,TERRAIN_GRADE_COUNT
 jae .clear
 test qword [rdx+GRADE_FLAGS],1
 jz .next
 movapd xmm12,xmm8
 movapd xmm13,xmm9
 movapd xmm14,xmm10
 movapd xmm15,xmm11
 maxsd xmm12,[rdx+GRADE_XMIN]
 maxsd xmm13,[rdx+GRADE_ZMIN]
 minsd xmm14,[rdx+GRADE_XMAX]
 minsd xmm15,[rdx+GRADE_ZMAX]
 ; Closed rectangles include both one-sided gradients at every cusp.
 ucomisd xmm12,xmm14
 ja .next
 ucomisd xmm13,xmm15
 ja .next
 xor ecx,ecx
.corner:
 movapd xmm0,xmm12
 test ecx,1
 jz .z_corner
 movapd xmm0,xmm14
.z_corner:
 movapd xmm1,xmm13
 test ecx,2
 jz .gradient
 movapd xmm1,xmm15
.gradient:
 movapd xmm2,xmm0
 subsd xmm2,[center]
 mulsd xmm2,[base_x]
 movapd xmm3,xmm1
 mulsd xmm3,[rdx+GRADE_CROSS]
 addsd xmm3,[rdx+GRADE_XCONST]
 addsd xmm2,xmm3
 subsd xmm1,[center]
 mulsd xmm1,[base_z]
 mulsd xmm0,[rdx+GRADE_CROSS]
 addsd xmm0,[rdx+GRADE_ZCONST]
 addsd xmm1,xmm0
 mulsd xmm2,xmm2
 mulsd xmm1,xmm1
 addsd xmm2,xmm1
 addsd xmm2,[guard]
 ucomisd xmm2,xmm7
 ja .blocked
 inc ecx
 cmp ecx,4
 jb .corner
.next:
 add rdx,TERRAIN_GRADE_STRIDE
 inc r8d
 jmp .facet
.clear:
 mov eax,1
 ret
.blocked:
 xor eax,eax
 ret
.invalid:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
