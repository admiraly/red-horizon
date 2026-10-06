%include "schemas/terrain_height.inc"
%include "schemas/terrain_ground_query.inc"
%include "schemas/terrain_relief.inc"
default rel
extern terrain_relief_count,terrain_relief_fields
section .rodata
zero: dq 0.0
one: dq 1.0
two: dq 2.0
four: dq 4.0
half: dq 0.5
center: dd TERRAIN_HEIGHT_CENTER
xscale: dd TERRAIN_HEIGHT_X_SCALE
zscale: dd TERRAIN_HEIGHT_Z_SCALE
ridge_scale: dd TERRAIN_HEIGHT_RIDGE_SCALE
ridge_height: dd TERRAIN_HEIGHT_RIDGE_HEIGHT
base: dd TERRAIN_HEIGHT_BASE
skin: dd TERRAIN_GROUND_QUERY_SKIN
mapmax: dd 8000.0
xz_offsets: dd 0,8,12,20
section .text
global terrain_ground_query
terrain_ground_query:
 test rdi,rdi
 jz .invalid_leaf
 cmp esi,TERRAIN_GROUND_QUERY_BYTES
 jb .invalid_leaf
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,304
 mov r15,rdi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 xor ecx,ecx
.validate:
 mov eax,[rsp+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .invalid
 inc ecx
 cmp ecx,6
 jb .validate
 lea r8,[xz_offsets]
 xor ecx,ecx
.map:
 mov edx,[r8+rcx*4]
 movss xmm0,[rsp+rdx]
 xorps xmm1,xmm1
 ucomiss xmm0,xmm1
 jb .invalid
 ucomiss xmm0,[mapmax]
 ja .invalid
 inc ecx
 cmp ecx,4
 jb .map
 cmp dword [terrain_relief_count],1
 ja .bad_source
 je .field
 jmp .prepare
.field:
 lea r8,[terrain_relief_fields]
 cmp dword [r8+36],1
 ja .bad_source
 je .field_coords
 jmp .prepare
.field_coords:
 xor ecx,ecx
.fc:
 movss xmm0,[r8+rcx*4]
 xorps xmm1,xmm1
 ucomiss xmm0,xmm1
 jp .bad_source
 jb .bad_source
 ucomiss xmm0,[mapmax]
 ja .bad_source
 inc ecx
 cmp ecx,8
 jb .fc
 movss xmm0,[r8+32]
 ucomiss xmm0,xmm1
 jp .bad_source
 jb .bad_source
 mov eax,[r8+32]
 cmp eax,__float32__(2000.0)
 ja .bad_source
 xor ecx,ecx
.order:
 movss xmm0,[r8+rcx]
 ucomiss xmm0,[r8+rcx+4]
 jae .bad_source
 movss xmm0,[r8+rcx+4]
 ucomiss xmm0,[r8+rcx+8]
 ja .bad_source
 movss xmm0,[r8+rcx+8]
 ucomiss xmm0,[r8+rcx+12]
 jae .bad_source
 add ecx,16
 cmp ecx,32
 jb .order
.prepare:
 cvtss2sd xmm0,[rsp+12]
 cvtss2sd xmm1,[rsp]
 subsd xmm0,xmm1
 movsd [rsp+256],xmm0
 cvtss2sd xmm0,[rsp+20]
 cvtss2sd xmm1,[rsp+8]
 subsd xmm0,xmm1
 movsd [rsp+264],xmm0
 movsd xmm0,[zero]
 movsd [rsp+32],xmm0
 movsd xmm0,[one]
 movsd [rsp+40],xmm0
 mov r12d,2
 ; Ridge support edges are derived from the actual promoted f32 coefficient.
 movsd xmm0,[one]
 cvtss2sd xmm1,[ridge_scale]
 divsd xmm0,xmm1
 cvtss2sd xmm1,[center]
 subsd xmm1,xmm0
 movapd xmm0,xmm1
 mov rdi,rsp
 call .append_x
 cvtss2sd xmm0,[center]
 mov rdi,rsp
 call .append_x
 movsd xmm0,[one]
 cvtss2sd xmm1,[ridge_scale]
 divsd xmm0,xmm1
 cvtss2sd xmm1,[center]
 addsd xmm0,xmm1
 mov rdi,rsp
 call .append_x
 cmp dword [terrain_relief_count],0
 je .sort
 test dword [terrain_relief_fields+36],RELIEF_ACTIVE
 jz .sort
 xor r14d,r14d
.cuts:
 lea r8,[terrain_relief_fields]
 cvtss2sd xmm0,[r8+r14*4]
 mov rdi,rsp
 cmp r14d,4
 jae .zcut
 call .append_x
 jmp .cut_next
.zcut:
 call .append_z
.cut_next:
 inc r14d
 cmp r14d,8
 jb .cuts
.sort:
 mov r14d,1
.sort_outer:
 movsd xmm0,[rsp+r14*8+32]
 mov ecx,r14d
 dec ecx
.shift:
 test ecx,ecx
 js .insert
 movsd xmm1,[rsp+rcx*8+32]
 ucomisd xmm1,xmm0
 jbe .insert
 movsd [rsp+rcx*8+40],xmm1
 dec ecx
 jmp .shift
.insert:
 movsd [rsp+rcx*8+40],xmm0
 inc r14d
 cmp r14d,r12d
 jb .sort_outer
 xor ebx,ebx
.piece:
 movsd xmm0,[rsp+rbx*8+32]
 movsd xmm1,[rsp+rbx*8+40]
 ucomisd xmm0,xmm1
 jae .next_piece
 movsd [rsp+160],xmm0
 movsd [rsp+168],xmm1
 mov rdi,rsp
 call .gap
 movsd [rsp+176],xmm0
 ucomisd xmm0,[zero]
 jbe .at_lo
 movsd xmm0,[rsp+160]
 addsd xmm0,[rsp+168]
 mulsd xmm0,[half]
 mov rdi,rsp
 call .gap
 movsd [rsp+184],xmm0
 movsd xmm0,[rsp+168]
 mov rdi,rsp
 call .gap
 movsd [rsp+192],xmm0
 ; g(u)=a*u*u+b*u+c on normalized piece u[0,1].
 addsd xmm0,[rsp+176]
 movsd xmm1,[rsp+184]
 mulsd xmm1,[two]
 subsd xmm0,xmm1
 mulsd xmm0,[two]
 movsd [rsp+200],xmm0
 movsd xmm1,[rsp+192]
 subsd xmm1,[rsp+176]
 subsd xmm1,xmm0
 movsd [rsp+208],xmm1
 ucomisd xmm0,[zero]
 jne .quadratic
 ucomisd xmm1,[zero]
 jae .next_piece
 xorpd xmm0,xmm0
 subsd xmm0,[rsp+176]
 divsd xmm0,xmm1
 jmp .try_root
.quadratic:
 movapd xmm2,xmm1
 mulsd xmm2,xmm1
 movsd xmm3,[rsp+200]
 mulsd xmm3,[rsp+176]
 mulsd xmm3,[four]
 subsd xmm2,xmm3
 ucomisd xmm2,[zero]
 jb .next_piece
 sqrtsd xmm2,xmm2
 ucomisd xmm1,[zero]
 jb .negative_b
 addsd xmm1,xmm2
 jmp .q
.negative_b:
 subsd xmm1,xmm2
.q:
 mulsd xmm1,[half]
 xorpd xmm2,xmm2
 subsd xmm2,xmm1
 ucomisd xmm2,[zero]
 je .double_root
 movapd xmm0,xmm2
 divsd xmm0,[rsp+200]
 movsd xmm1,[rsp+176]
 divsd xmm1,xmm2
 movapd xmm2,xmm0
 minsd xmm0,xmm1
 maxsd xmm1,xmm2
 movsd [rsp+224],xmm1
 ucomisd xmm0,[zero]
 jb .second_root
 ucomisd xmm0,[one]
 jbe .hit_root
.second_root:
 movsd xmm0,[rsp+224]
 jmp .try_root
.double_root:
 xorpd xmm0,xmm0
 subsd xmm0,[rsp+208]
 divsd xmm0,[rsp+200]
 mulsd xmm0,[half]
.try_root:
 ucomisd xmm0,[zero]
 jb .next_piece
 ucomisd xmm0,[one]
 ja .next_piece
.hit_root:
 movsd xmm1,[rsp+168]
 subsd xmm1,[rsp+160]
 mulsd xmm0,xmm1
 addsd xmm0,[rsp+160]
 jmp .hit
.at_lo:
 movsd xmm0,[rsp+160]
.hit:
 cvtsd2ss xmm0,xmm0
 movss [r15],xmm0
 mov dword [r15+4],0
 mov qword [r15+8],0
 mov eax,1
 jmp .done
.next_piece:
 inc ebx
 mov eax,ebx
 inc eax
 cmp eax,r12d
 jb .piece
 xor eax,eax
 jmp .done
.bad_source:
 mov eax,-2
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,304
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
.append_x:
 xor ecx,ecx
 mov edx,256
 jmp .append
.append_z:
 mov ecx,8
 mov edx,264
.append:
 movsd xmm2,[rdi+rdx]
 ucomisd xmm2,[zero]
 je .append_done
 cvtss2sd xmm1,[rdi+rcx]
 subsd xmm0,xmm1
 divsd xmm0,xmm2
 ucomisd xmm0,[zero]
 jbe .append_done
 ucomisd xmm0,[one]
 jae .append_done
 movsd [rdi+r12*8+32],xmm0
 inc r12d
.append_done:
 ret
; Double profile evaluation at t; RDI stable packed f32 source endpoints.
.gap:
 sub rsp,8
 movapd xmm14,xmm0
 cvtss2sd xmm6,[rdi]
 cvtss2sd xmm0,[rdi+12]
 subsd xmm0,xmm6
 mulsd xmm0,xmm14
 addsd xmm6,xmm0
 cvtss2sd xmm7,[rdi+8]
 cvtss2sd xmm0,[rdi+20]
 subsd xmm0,xmm7
 mulsd xmm0,xmm14
 addsd xmm7,xmm0
 cvtss2sd xmm15,[rdi+4]
 cvtss2sd xmm0,[rdi+16]
 subsd xmm0,xmm15
 mulsd xmm0,xmm14
 addsd xmm15,xmm0
 cvtss2sd xmm8,[base]
 cvtss2sd xmm0,[center]
 movapd xmm1,xmm6
 subsd xmm1,xmm0
 movapd xmm2,xmm7
 subsd xmm2,xmm0
 movapd xmm3,xmm1
 mulsd xmm3,xmm1
 cvtss2sd xmm4,[xscale]
 mulsd xmm3,xmm4
 addsd xmm8,xmm3
 mulsd xmm2,xmm2
 cvtss2sd xmm4,[zscale]
 mulsd xmm2,xmm4
 addsd xmm8,xmm2
 xorpd xmm0,xmm0
 subsd xmm0,xmm1
 maxsd xmm1,xmm0 ; abs(x-center)
 cvtss2sd xmm2,[ridge_scale]
 mulsd xmm1,xmm2
 movsd xmm2,[one]
 subsd xmm2,xmm1
 maxsd xmm2,[zero]
 cvtss2sd xmm3,[ridge_height]
 mulsd xmm2,xmm3
 addsd xmm8,xmm2
 cmp dword [terrain_relief_count],0
 je .no_relief
 test dword [terrain_relief_fields+36],RELIEF_ACTIVE
 jz .no_relief
 lea r8,[terrain_relief_fields]
 movapd xmm0,xmm6
 call .factor
 movapd xmm9,xmm0
 lea r8,[terrain_relief_fields+16]
 movapd xmm0,xmm7
 call .factor
 mulsd xmm0,xmm9
 cvtss2sd xmm1,[terrain_relief_fields+32]
 mulsd xmm0,xmm1
 addsd xmm8,xmm0
.no_relief:
 movapd xmm0,xmm15
 subsd xmm0,xmm8
 cvtss2sd xmm1,[skin]
 subsd xmm0,xmm1
 add rsp,8
 ret
.factor:
 cvtss2sd xmm1,[r8]
 ucomisd xmm0,xmm1
 jbe .factor_zero
 cvtss2sd xmm4,[r8+12]
 ucomisd xmm0,xmm4
 jae .factor_zero
 cvtss2sd xmm2,[r8+4]
 ucomisd xmm0,xmm2
 jb .factor_rise
 cvtss2sd xmm3,[r8+8]
 ucomisd xmm0,xmm3
 ja .factor_fall
 movsd xmm0,[one]
 ret
.factor_rise:
 subsd xmm0,xmm1
 subsd xmm2,xmm1
 divsd xmm0,xmm2
 ret
.factor_fall:
 movapd xmm2,xmm4
 subsd xmm4,xmm0
 subsd xmm2,xmm3
 divsd xmm4,xmm2
 movapd xmm0,xmm4
 ret
.factor_zero:
 xorpd xmm0,xmm0
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
