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
section .rodata
zero: dd 0.0
mapmax: dd 8000.0
cell: dd 62.5
padding: dd 6.0
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
 lea rbx,[sim_wrecks]
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
 cmp r13d,[sim_wreck_count]
 jne .bad
 mov rax,[wreck_query_revision]
 mov [cache_revision],rax
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

global wreck_query
wreck_query:
 test rdi,rdi
 jz .invalid_leaf
 cmp esi,WRECK_QUERY_BYTES
 jb .invalid_leaf
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,80
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
 mov dword [wreck_query_candidates],0
 cmp dword [cache_valid],1
 jne .refresh
 mov rax,[wreck_query_revision]
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
 call coordinate_cell
 mov [rsp+24],eax
 movss xmm0,[rsp]
 maxss xmm0,[rsp+12]
 addss xmm0,[padding]
 call coordinate_cell
 mov [rsp+28],eax
 movss xmm0,[rsp+8]
 minss xmm0,[rsp+20]
 subss xmm0,[padding]
 call coordinate_cell
 mov r12d,eax
 movss xmm0,[rsp+8]
 maxss xmm0,[rsp+20]
 addss xmm0,[padding]
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
 lea r8,[sim_wrecks]
 add r8,rax
 mov eax,[rsp+36]
 shl eax,6
 lea r9,[sim_wrecks]
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
 lea rdx,[sim_wrecks]
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
 add rsp,80
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
