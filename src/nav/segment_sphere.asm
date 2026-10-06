%include "schemas/segment_sphere.inc"
default rel
section .rodata
zero: dq 0.0
one: dq 1.0
section .text
global segment_sphere
segment_sphere:
 test rdi,rdi
 jz .invalid_leaf
 cmp esi,SEGMENT_SPHERE_BYTES
 jb .invalid_leaf
 sub rsp,32
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 xor ecx,ecx
.validate_segment:
 mov eax,[rsp+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(SEGMENT_SPHERE_COORD_LIMIT)
 ja .invalid
 inc ecx
 cmp ecx,6
 jb .validate_segment
 xor ecx,ecx
.validate_center:
 mov eax,[rdi+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(SEGMENT_SPHERE_COORD_LIMIT)
 ja .invalid
 inc ecx
 cmp ecx,3
 jb .validate_center
 mov eax,[rdi+12]
 cmp eax,__float32__(SEGMENT_SPHERE_RADIUS_MIN)
 jb .invalid
 cmp eax,__float32__(SEGMENT_SPHERE_RADIUS_MAX)
 ja .invalid
 ; m=start-center, d=end-start; double sums preserve tiny directions.
 xorpd xmm6,xmm6 ; a=d dot d
 xorpd xmm7,xmm7 ; b=m dot d
 xorpd xmm8,xmm8 ; m dot m
 xor ecx,ecx
.sums:
 cvtss2sd xmm9,[rsp+rcx*4]
 cvtss2sd xmm10,[rdi+rcx*4]
 subsd xmm9,xmm10
 cvtss2sd xmm10,[rsp+rcx*4+12]
 cvtss2sd xmm11,[rsp+rcx*4]
 subsd xmm10,xmm11
 movapd xmm11,xmm10
 mulsd xmm11,xmm10
 addsd xmm6,xmm11
 movapd xmm11,xmm9
 mulsd xmm11,xmm10
 addsd xmm7,xmm11
 mulsd xmm9,xmm9
 addsd xmm8,xmm9
 inc ecx
 cmp ecx,3
 jb .sums
 cvtss2sd xmm12,[rdi+12]
 mulsd xmm12,xmm12
 ucomisd xmm8,xmm12
 jbe .inside
 ucomisd xmm6,[zero]
 je .clear
 ucomisd xmm7,[zero]
 jae .clear
 ; Closest-line projection avoids b*b-a*c cancellation for distant spheres.
 xorpd xmm13,xmm13
 subsd xmm13,xmm7
 divsd xmm13,xmm6 ; tc=-b/a
 xorpd xmm8,xmm8
 xor ecx,ecx
.closest:
 cvtss2sd xmm9,[rsp+rcx*4]
 cvtss2sd xmm10,[rdi+rcx*4]
 subsd xmm9,xmm10
 cvtss2sd xmm10,[rsp+rcx*4+12]
 cvtss2sd xmm11,[rsp+rcx*4]
 subsd xmm10,xmm11
 mulsd xmm10,xmm13
 addsd xmm9,xmm10
 mulsd xmm9,xmm9
 addsd xmm8,xmm9
 inc ecx
 cmp ecx,3
 jb .closest
 ucomisd xmm8,xmm12
 ja .clear
 subsd xmm12,xmm8
 divsd xmm12,xmm6
 sqrtsd xmm12,xmm12
 subsd xmm13,xmm12
 maxsd xmm13,[zero]
 ucomisd xmm13,[one]
 ja .clear
 cvtsd2ss xmm0,xmm13
 mov eax,1
 jmp .done
.inside:
 xorps xmm0,xmm0
 mov eax,1
 jmp .done
.clear:
 xor eax,eax
 jmp .restore
.invalid:
 mov eax,-1
.restore:
 movss xmm0,[rsp]
.done:
 add rsp,32
 ret
.invalid_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
