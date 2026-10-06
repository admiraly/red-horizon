%include "schemas/wreck.inc"
%include "schemas/wreck_query.inc"
default rel
extern sim_wrecks,sim_wreck_count,wreck_query_revision,sinf,cosf,segment_box
section .bss align=64
heads: resd 16384
next: resd 1024
global wreck_query_bounds,wreck_query_candidates
wreck_query_bounds: resb 1024*24
wreck_query_candidates: resd 1
cache_valid: resd 1
cache_revision: resq 1
cache_source: resq 1
query_source: resq 1
query_revision: resq 1
query_count: resd 1
section .rodata
zero: dd 0.0
mapmax: dd 8000.0
cell: dd 62.5
padding: dd 6.0
body_min_y: dd -16000.0
body_max_y: dd 16000.0
skin: dd 0.002
align 16
abs_mask: dd 0x7fffffff,0x7fffffff,0x7fffffff,0x7fffffff
; Local union frame0 bounds, rounded outward from actual battle.rham audit.
local_centers: dd 0.0,1.31645,0.0, 0.0,1.60815,0.0
local_extents: dd 1.895,1.30455,3.0, 2.528,1.59185,3.5
section .text
; Internal rebuild; return0 success or-2 corrupted active record. Calls aligned.
rebuild:
 push rbx
 push r12
 push r13
 sub rsp,112
 mov dword [cache_valid],0
 lea rdi,[heads]
 mov eax,-1
 mov ecx,16384+1024
 rep stosd
 xor r12d,r12d
 xor r13d,r13d
.loop:
 mov eax,r12d
 shl eax,6
 mov rbx,[query_source]
 add rbx,rax
 test dword [rbx+WRECK_FLAGS],WRECK_ACTIVE
 jz .next
 cmp dword [rbx+WRECK_FLAGS],3
 ja .bad
 mov eax,[rbx+WRECK_KIND]
 sub eax,1
 cmp eax,1
 ja .bad
 imul eax,12
 mov [rsp+96],eax
 cmp dword [rbx+WRECK_SIDE],1
 ja .bad
 cmp dword [rbx+WRECK_ENTITY],32768
 jae .bad
 cmp dword [rbx+WRECK_GENERATION],0
 je .bad
 cmp dword [rbx+WRECK_SEQUENCE],0
 je .bad
 cmp qword [rbx+56],0
 jne .bad
 movss xmm0,[rbx+WRECK_X]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[mapmax]
 ja .bad
 movss xmm0,[rbx+WRECK_Z]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[mapmax]
 ja .bad
 mov eax,[rbx+WRECK_Y]
 and eax,0x7fffffff
 cmp eax,__float32__(2000.0)
 ja .bad
 mov ecx,3
.validate:
 mov eax,[rbx+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(16.0)
 ja .bad
 inc ecx
 cmp ecx,6
 jb .validate
 ; trig scratch: sy/cy/sp/cp/sb/cb at0..20; matrix rows at32..64.
 movss xmm0,[rbx+12+0]
 call sinf wrt ..plt
 movss [rsp+0],xmm0
 movss xmm0,[rbx+12+0]
 call cosf wrt ..plt
 movss [rsp+4],xmm0
 movss xmm0,[rbx+12+4]
 call sinf wrt ..plt
 movss [rsp+8],xmm0
 movss xmm0,[rbx+12+4]
 call cosf wrt ..plt
 movss [rsp+12],xmm0
 movss xmm0,[rbx+12+8]
 call sinf wrt ..plt
 movss [rsp+16],xmm0
 movss xmm0,[rbx+12+8]
 call cosf wrt ..plt
 movss [rsp+20],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+4]
 mulss xmm1,[rsp+20]
 addss xmm0,xmm1
 movss xmm1,[rsp+0]
 mulss xmm1,[rsp+8]
 mulss xmm1,[rsp+16]
 subss xmm0,xmm1
 movss [rsp+32],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+4]
 mulss xmm1,[rsp+16]
 subss xmm0,xmm1
 movss xmm1,[rsp+0]
 mulss xmm1,[rsp+8]
 mulss xmm1,[rsp+20]
 subss xmm0,xmm1
 movss [rsp+36],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+0]
 mulss xmm1,[rsp+12]
 addss xmm0,xmm1
 movss [rsp+40],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+12]
 mulss xmm1,[rsp+16]
 addss xmm0,xmm1
 movss [rsp+44],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+12]
 mulss xmm1,[rsp+20]
 addss xmm0,xmm1
 movss [rsp+48],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+8]
 addss xmm0,xmm1
 movss [rsp+52],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+0]
 mulss xmm1,[rsp+20]
 subss xmm0,xmm1
 movss xmm1,[rsp+4]
 mulss xmm1,[rsp+8]
 mulss xmm1,[rsp+16]
 subss xmm0,xmm1
 movss [rsp+56],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+0]
 mulss xmm1,[rsp+16]
 addss xmm0,xmm1
 movss xmm1,[rsp+4]
 mulss xmm1,[rsp+8]
 mulss xmm1,[rsp+20]
 subss xmm0,xmm1
 movss [rsp+60],xmm0
 xorps xmm0,xmm0
 movss xmm1,[rsp+4]
 mulss xmm1,[rsp+12]
 addss xmm0,xmm1
 movss [rsp+64],xmm0
 mov eax,[rsp+96]
 lea r8,[local_centers]
 add r8,rax
 lea r9,[local_extents]
 add r9,rax
 mov eax,r12d
 imul eax,24
 lea r10,[wreck_query_bounds]
 add r10,rax
 xor ecx,ecx
.rows:
 xorps xmm0,xmm0
 xorps xmm2,xmm2
 xor edx,edx
.cols:
 mov eax,ecx
 imul eax,12
 lea eax,[eax+edx*4]
 movss xmm1,[rsp+rax+32]
 movaps xmm3,xmm1
 mulss xmm1,[r8+rdx*4]
 addss xmm0,xmm1
 andps xmm3,[abs_mask]
 mulss xmm3,[r9+rdx*4]
 addss xmm2,xmm3
 inc edx
 cmp edx,3
 jb .cols
 addss xmm0,[rbx+rcx*4]
 addss xmm2,[skin]
 movaps xmm1,xmm0
 subss xmm1,xmm2
 addss xmm0,xmm2
 movss [r10+rcx*4],xmm1
 movss [r10+rcx*4+12],xmm0
 inc ecx
 cmp ecx,3
 jb .rows
 movss xmm0,[rbx+WRECK_X]
 call coordinate_cell
 mov [rsp+100],eax
 movss xmm0,[rbx+WRECK_Z]
 call coordinate_cell
 shl eax,7
 add eax,[rsp+100]
 lea rdx,[heads]
 mov ecx,[rdx+rax*4]
 mov [rdx+rax*4],r12d
 lea rdx,[next]
 mov [rdx+r12*4],ecx
 inc r13d
.next:
 inc r12d
 cmp r12d,WRECK_CAPACITY
 jb .loop
 cmp r13d,[query_count]
 jne .bad
 mov rax,[query_revision]
 mov [cache_revision],rax
 mov rax,[query_source]
 mov [cache_source],rax
 mov dword [cache_valid],1
 xor eax,eax
 jmp .done
.bad:
 mov eax,-2
.done:
 add rsp,112
 pop r13
 pop r12
 pop rbx
 ret
; finite coordinate ->clamped cell0..31; no calls.
coordinate_cell:
 divss xmm0,[cell]
 maxss xmm0,[zero]
 cvttss2si eax,xmm0
 cmp eax,127
 mov edx,127
 cmova eax,edx
 ret

global wreck_query,wreck_body_query,wreck_query_context,wreck_body_query_context
; Explicit source context: RDX records1024x64, ECX active count, R8 revision.
; Caller owns readable stable source and advances revision after any mutation.
wreck_body_query:
 lea rdx,[sim_wrecks]
 mov ecx,[sim_wreck_count]
 mov r8,[wreck_query_revision]
wreck_body_query_context:
 movaps xmm6,xmm4
 movaps xmm5,xmm3
 movaps xmm3,xmm2
 movaps xmm2,xmm1
 xorps xmm1,xmm1
 xorps xmm4,xmm4
 mov r9d,1
 jmp query_start
wreck_query:
 lea rdx,[sim_wrecks]
 mov ecx,[sim_wreck_count]
 mov r8,[wreck_query_revision]
wreck_query_context:
 xor r9d,r9d
 xorps xmm6,xmm6
query_start:
 test rdx,rdx
 jz .invalid_leaf
 cmp ecx,WRECK_CAPACITY
 ja .invalid_leaf
 test rdi,rdi
 jz .invalid_leaf
 cmp esi,WRECK_QUERY_BYTES
 jb .invalid_leaf
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,112
 mov r15,rdi
 mov [rsp+72],r9d
 mov [rsp+80],rdx
 mov [rsp+88],ecx
 mov [rsp+96],r8
 movss [rsp+76],xmm6
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
 mov eax,[rsp+76]
 and eax,0x7fffffff
 cmp eax,__float32__(4.491)
 ja .invalid
 movss xmm0,[rsp+76]
 ucomiss xmm0,[zero]
 jb .invalid
 mov rax,[rsp+80]
 mov [query_source],rax
 mov eax,[rsp+88]
 mov [query_count],eax
 mov rax,[rsp+96]
 mov [query_revision],rax
 mov dword [wreck_query_candidates],0
 mov rax,[query_source]
 cmp rax,[cache_source]
 jne .refresh
 cmp dword [cache_valid],1
 jne .refresh
 mov rax,[query_revision]
 cmp rax,[cache_revision]
 je .cached
.refresh:
 call rebuild
 test eax,eax
 jnz .done
.cached:
 ; Inclusive cell rectangle with6m margin catches all rotated source corners.
 movss xmm0,[rsp]
 minss xmm0,[rsp+12]
 subss xmm0,[padding]
 subss xmm0,[rsp+76]
 call coordinate_cell
 mov [rsp+24],eax
 movss xmm0,[rsp]
 maxss xmm0,[rsp+12]
 addss xmm0,[padding]
 addss xmm0,[rsp+76]
 call coordinate_cell
 mov [rsp+28],eax
 movss xmm0,[rsp+8]
 minss xmm0,[rsp+20]
 subss xmm0,[padding]
 subss xmm0,[rsp+76]
 call coordinate_cell
 mov r12d,eax
 movss xmm0,[rsp+8]
 maxss xmm0,[rsp+20]
 addss xmm0,[padding]
 addss xmm0,[rsp+76]
 call coordinate_cell
 mov [rsp+32],eax
 mov dword [rsp+36],-1 ; selected slot
 mov dword [rsp+40],__float32__(2.0)
.row:
 mov r13d,[rsp+24]
.cell:
 mov eax,r12d
 shl eax,7
 add eax,r13d
 lea rdx,[heads]
 mov ebx,[rdx+rax*4]
.list:
 cmp ebx,-1
 je .next_cell
 inc dword [wreck_query_candidates]
 mov eax,ebx
 imul eax,24
 lea rdi,[wreck_query_bounds]
 add rdi,rax
 cmp dword [rsp+72],0
 je .clip
 movss xmm0,[rsp+76]
 movss xmm1,[rdi]
 subss xmm1,xmm0
 movss [rsp+48],xmm1
 movss xmm1,[body_min_y]
 movss [rsp+52],xmm1
 movss xmm1,[rdi+8]
 subss xmm1,xmm0
 movss [rsp+56],xmm1
 movss xmm1,[rdi+12]
 addss xmm1,xmm0
 movss [rsp+60],xmm1
 movss xmm1,[body_max_y]
 movss [rsp+64],xmm1
 movss xmm1,[rdi+20]
 addss xmm1,xmm0
 movss [rsp+68],xmm1
 lea rdi,[rsp+48]
 mov rsi,rsp
 call body_escape
 test eax,eax
 jnz .next_record
.clip:
 mov esi,24
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
 call segment_box
 cmp eax,1
 jne .next_record
 cmp dword [rsp+36],-1
 je .select
 ucomiss xmm0,[rsp+40]
 jb .select
 ja .next_record
 ; Deterministic physical identity tie, independent of side and bucket order.
 mov eax,ebx
 shl eax,6
 mov r8,[query_source]
 add r8,rax
 mov eax,[rsp+36]
 shl eax,6
 mov r9,[query_source]
 add r9,rax
 mov eax,[r8+WRECK_ENTITY]
 cmp eax,[r9+WRECK_ENTITY]
 jb .select
 ja .next_record
 mov eax,[r8+WRECK_GENERATION]
 cmp eax,[r9+WRECK_GENERATION]
 jb .select
 ja .next_record
 mov eax,[r8+WRECK_SEQUENCE]
 cmp eax,[r9+WRECK_SEQUENCE]
 jae .next_record
.select:
 mov [rsp+36],ebx
 movss [rsp+40],xmm0
.next_record:
 lea rdx,[next]
 mov ebx,[rdx+rbx*4]
 jmp .list
.next_cell:
 inc r13d
 cmp r13d,[rsp+28]
 jbe .cell
 inc r12d
 cmp r12d,[rsp+32]
 jbe .row
 mov eax,[rsp+36]
 cmp eax,-1
 je .clear
 mov [r15+4],eax
 shl eax,6
 mov rdx,[query_source]
 add rdx,rax
 mov eax,[rsp+40]
 mov [r15],eax
 mov rax,[rdx+WRECK_ENTITY]
 mov [r15+8],rax
 mov eax,[rdx+WRECK_SEQUENCE]
 mov [r15+16],eax
 mov dword [r15+20],0
 mov eax,1
 jmp .done
.clear:
 xor eax,eax
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,112
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
; Ignore a start-overlap only if at least one initial minimum-depth face
; has nonincreasing distance along the requested nonzero segment. The minimum
; of affine face distances can then never exceed initial depth, even mid-path.
; Output1 allowed overlap escape/slide;0 ordinary closed contact query.
body_escape:
 movss xmm0,[rsi]
 ucomiss xmm0,[rdi]
 jb .block
 ucomiss xmm0,[rdi+12]
 ja .block
 movss xmm1,[rsi+8]
 ucomiss xmm1,[rdi+8]
 jb .block
 ucomiss xmm1,[rdi+20]
 ja .block
 movaps xmm2,xmm0
 subss xmm2,[rdi]
 movss xmm3,[rdi+12]
 subss xmm3,xmm0
 movaps xmm4,xmm1
 subss xmm4,[rdi+8]
 movss xmm5,[rdi+20]
 subss xmm5,xmm1
 movaps xmm6,xmm2
 minss xmm6,xmm3
 minss xmm6,xmm4
 minss xmm6,xmm5
 movss xmm0,[rsi+12]
 subss xmm0,[rsi]
 movss xmm1,[rsi+20]
 subss xmm1,[rsi+8]
 ucomiss xmm0,[zero]
 jne .moving
 ucomiss xmm1,[zero]
 je .block
.moving:
 ucomiss xmm2,xmm6
 jne .right
 ucomiss xmm0,[zero]
 jbe .allow
.right:
 ucomiss xmm3,xmm6
 jne .back
 ucomiss xmm0,[zero]
 jae .allow
.back:
 ucomiss xmm4,xmm6
 jne .front
 ucomiss xmm1,[zero]
 jbe .allow
.front:
 ucomiss xmm5,xmm6
 jne .block
 ucomiss xmm1,[zero]
 jae .allow
.block:
 xor eax,eax
 ret
.allow:
 mov eax,1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
