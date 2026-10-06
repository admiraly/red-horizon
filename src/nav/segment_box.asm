; Read-only segment versus closed3D AABB, validated bounded f32 coordinates.
%include "schemas/segment_box.inc"
default rel
section .rodata
zero: dq 0.0
one: dq 1.0
section .text
global segment_box
segment_box:
 test rdi,rdi
 jz .invalid_leaf
 cmp esi,SEGMENT_BOX_BYTES
 jb .invalid_leaf
 sub rsp,32
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 xor ecx,ecx
.validate:
 ; Positive IEEE magnitude ordering rejects NaN/Inf as well as oversized values.
 mov eax,[rsp+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(SEGMENT_BOX_COORD_LIMIT)
 ja .invalid
 mov eax,[rdi+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(SEGMENT_BOX_COORD_LIMIT)
 ja .invalid
 inc ecx
 cmp ecx,6
 jb .validate
 xor ecx,ecx
.order:
 movss xmm8,[rdi+rcx*4]
 ucomiss xmm8,[rdi+rcx*4+12]
 ja .invalid
 inc ecx
 cmp ecx,3
 jb .order
 xorpd xmm6,xmm6 ; first t=0
 movsd xmm7,[one] ; last t=1
 xor ecx,ecx
.axis:
 cvtss2sd xmm8,[rsp+rcx*4]
 cvtss2sd xmm9,[rsp+rcx*4+12]
 subsd xmm9,xmm8
 cvtss2sd xmm10,[rdi+rcx*4]
 cvtss2sd xmm11,[rdi+rcx*4+12]
 ucomisd xmm9,[zero]
 jne .direction
 ucomisd xmm8,xmm10
 jb .clear
 ucomisd xmm8,xmm11
 ja .clear
 jmp .next
.direction:
 movapd xmm12,xmm10
 subsd xmm12,xmm8
 divsd xmm12,xmm9
 movapd xmm13,xmm11
 subsd xmm13,xmm8
 divsd xmm13,xmm9
 movapd xmm14,xmm12
 minsd xmm14,xmm13
 maxsd xmm12,xmm13
 maxsd xmm6,xmm14
 minsd xmm7,xmm12
 ucomisd xmm6,xmm7
 ja .clear
.next:
 inc ecx
 cmp ecx,3
 jb .axis
 cvtsd2ss xmm0,xmm6
 mov eax,1
 jmp .done
.clear:
 xor eax,eax
 movss xmm0,[rsp]
 jmp .done
.invalid:
 mov eax,-1
 movss xmm0,[rsp]
.done:
 add rsp,32
 ret
.invalid_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
