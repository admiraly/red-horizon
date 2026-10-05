; Immutable ground body snapshots and bounded conservative local steering.
%include "schemas/entity.inc"
%include "schemas/crowd.inc"
default rel
%define GRID_SIDE 1001
%define GRID_SIZE (GRID_SIDE*GRID_SIDE)
%define SNAP_SIZE 32
%define LIMIT 512
extern sim_entities,sim_count,terrain_move,vehicle_entity_driver
section .rodata align=16
zero: dd 0.0
one: dd 1.0
maximum: dd 8000.0
cell_scale: dd 0.125
near_sq: dd 64.0
epsilon: dd 0.000001
radii: dd 0.55,2.5,2.0
steps: dd 0.12,0.5,0.2
driver_step: dd 0.6
; Forward, right/left30,60,90,135, and backwards. Goal-relative handedness
; reverses automatically for opposing directions; no side labels are read.
angles:
 dd 1.0,0.0
 dd 0.8660254,0.5
 dd 0.8660254,-0.5
 dd 0.5,0.8660254
 dd 0.5,-0.8660254
 dd 0.0,1.0
 dd 0.0,-1.0
 dd -0.7071068,0.7071068
 dd -0.7071068,-0.7071068
 dd -1.0,0.0
section .bss align=64
global crowd_enabled,crowd_metrics
crowd_enabled: resd 1
crowd_metrics: resq 8
heads: resd GRID_SIZE
occupied: resd ENTITY_CAPACITY
occupied_count: resd 1
snap_count: resd 1
; x,z,radius,maxstep,kind,generation,next,reserved
snaps: resb SNAP_SIZE*ENTITY_CAPACITY
section .text
global crowd_init,crowd_begin,crowd_move,crowd_hash
crowd_init:
 mov dword [crowd_enabled],1
 mov dword [occupied_count],0
 mov dword [snap_count],0
 lea rdi,[heads]
 mov ecx,GRID_SIZE
 mov eax,-1
 rep stosd
 lea rdi,[snaps]
 mov ecx,SNAP_SIZE*ENTITY_CAPACITY/8
 xor eax,eax
 rep stosq
 lea rdi,[crowd_metrics]
 mov ecx,8
 rep stosq
 ret
crowd_begin:
 push rbx
 push r12
 push r13
 lea rbx,[heads]
 lea rsi,[occupied]
 mov ecx,[occupied_count]
.clear:
 test ecx,ecx
 jz .cleared
 dec ecx
 mov eax,[rsi+rcx*4]
 mov dword [rbx+rax*4],-1
 jmp .clear
.cleared:
 mov dword [occupied_count],0
 lea rdi,[snaps]
 mov ecx,SNAP_SIZE*ENTITY_CAPACITY/8
 xor eax,eax
 rep stosq
 mov eax,[sim_count]
 cmp eax,ENTITY_CAPACITY
 ja .empty
 mov [snap_count],eax
 mov r12d,eax
 lea r13,[sim_entities]
 lea rdi,[snaps]
 xor esi,esi
.actor:
 cmp esi,r12d
 jae .done
 cmp dword [r13+ENTITY_HP],0
 je .next
 mov edx,[r13+ENTITY_KIND]
 cmp edx,2
 ja .next
 mov ecx,[r13+ENTITY_GENERATION]
 test ecx,ecx
 jz .next
 movss xmm0,[r13+ENTITY_X]
 movss xmm1,[r13+ENTITY_Z]
 ucomiss xmm0,[zero]
 jp .next
 jb .next
 ucomiss xmm0,[maximum]
 ja .next
 ucomiss xmm1,[zero]
 jp .next
 jb .next
 ucomiss xmm1,[maximum]
 ja .next
 movss [rdi],xmm0
 movss [rdi+4],xmm1
 lea rax,[radii]
 movss xmm2,[rax+rdx*4]
 movss [rdi+8],xmm2
 lea rax,[steps]
 movss xmm2,[rax+rdx*4]
 cmp edx,1
 jne .ordinary_step
 lea rax,[vehicle_entity_driver]
 cmp dword [rax+rsi*4],0
 jl .ordinary_step
 movss xmm2,[driver_step]
.ordinary_step:
 movss [rdi+12],xmm2
 mov [rdi+16],edx
 mov [rdi+20],ecx
 mulss xmm0,[cell_scale]
 mulss xmm1,[cell_scale]
 cvttss2si eax,xmm0
 cvttss2si edx,xmm1
 imul edx,GRID_SIDE
 add eax,edx
 mov edx,[rbx+rax*4]
 mov [rdi+24],edx
 cmp edx,-1
 jne .existing
 mov ecx,[occupied_count]
 lea rdx,[occupied]
 mov [rdx+rcx*4],eax
 inc dword [occupied_count]
.existing:
 mov [rbx+rax*4],esi
 inc qword [crowd_metrics]
.next:
 inc esi
 add r13,ENTITY_STRIDE
 add rdi,SNAP_SIZE
 jmp .actor
.empty: mov dword [snap_count],0
.done:
 pop r13
 pop r12
 pop rbx
 ret
; Locals: ID0 kind4 step8 start12/16 goal20/24 unit28/32 endpoint36/40
; segment44/48 len252 radius56 overlap60 candidate64 visits68 cellX72/Z76
; grid scan80/84, neighborhood IDs128..2176. Stack remains 16-byte aligned.
crowd_move:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,2248
 mov [rsp],edi
 movss [rsp+8],xmm4
 movss [rsp+12],xmm0
 movss [rsp+16],xmm1
 movss [rsp+20],xmm2
 movss [rsp+24],xmm3
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .unchanged
 cmp edi,[sim_count]
 jae .unchanged
 mov r12d,edi
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .unchanged
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,2
 ja .unchanged
 mov [rsp+4],eax
 ; All supplied coordinates finite and map-valid. Maxstep finite and positive.
 xor ecx,ecx
.validate:
 movss xmm5,[rsp+12+rcx*4]
 ucomiss xmm5,[zero]
 jp .bad_input
 jb .bad_input
 ucomiss xmm5,[maximum]
 ja .bad_input
 inc ecx
 cmp ecx,4
 jb .validate
 ucomiss xmm4,[zero]
 jp .unchanged
 jbe .unchanged
 lea rcx,[steps]
 minss xmm4,[rcx+rax*4]
 movss [rsp+8],xmm4
 cmp dword [crowd_enabled],0
 je .legacy
 cmp r12d,[snap_count]
 jae .unchanged
 lea r13,[snaps]
 mov eax,r12d
 shl eax,5
 add r13,rax
 mov eax,[r13+20]
 test eax,eax
 jz .unchanged
 cmp eax,[rbx+ENTITY_GENERATION]
 jne .unchanged
 mov eax,[r13+16]
 cmp eax,[rbx+ENTITY_KIND]
 jne .unchanged
 movss xmm5,[rsp+12]
 ucomiss xmm5,[r13]
 jne .unchanged
 movss xmm5,[rsp+16]
 ucomiss xmm5,[r13+4]
 jne .unchanged
 inc qword [crowd_metrics+8]
 movss xmm5,[r13+8]
 movss [rsp+56],xmm5
 movss xmm2,[rsp+20]
 subss xmm2,[rsp+12]
 movss xmm3,[rsp+24]
 subss xmm3,[rsp+16]
 movaps xmm5,xmm2
 mulss xmm5,xmm5
 movaps xmm6,xmm3
 mulss xmm6,xmm6
 addss xmm5,xmm6
 ucomiss xmm5,[epsilon]
 jbe .unchanged
 sqrtss xmm5,xmm5
 ; Do not overshoot a nearby goal, even for rotated candidates.
 minss xmm4,xmm5
 movss [rsp+8],xmm4
 divss xmm2,xmm5
 divss xmm3,xmm5
 movss [rsp+28],xmm2
 movss [rsp+32],xmm3
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 mulss xmm0,[cell_scale]
 mulss xmm1,[cell_scale]
 cvttss2si eax,xmm0
 cvttss2si edx,xmm1
 mov [rsp+72],eax
 mov [rsp+76],edx
 mov dword [rsp+80],-1
 xor r14d,r14d
 mov dword [rsp+68],0
 mov dword [rsp+92],0
.cell_z:
 mov eax,[rsp+76]
 add eax,[rsp+80]
 cmp eax,GRID_SIDE
 jae .next_z
 imul eax,GRID_SIDE
 mov [rsp+88],eax
 mov dword [rsp+84],-1
.cell_x:
 mov eax,[rsp+72]
 add eax,[rsp+84]
 cmp eax,GRID_SIDE
 jae .next_x
 add eax,[rsp+88]
 lea rcx,[heads]
 mov ebp,[rcx+rax*4]
.chain:
 cmp ebp,-1
 je .next_x
 cmp ebp,r12d
 je .next_neighbor
 cmp dword [rsp+68],LIMIT
 jae .truncated
 inc dword [rsp+68]
 mov eax,ebp
 shl eax,5
 lea rbx,[snaps]
 add rbx,rax
 lea rcx,[sim_entities]
 add rcx,rax
 cmp dword [rcx+ENTITY_HP],0
 je .next_neighbor
 mov eax,[rbx+20]
 cmp eax,[rcx+ENTITY_GENERATION]
 jne .next_neighbor
 mov eax,[rbx+16]
 cmp eax,[rcx+ENTITY_KIND]
 jne .next_neighbor
 movss xmm0,[rbx]
 subss xmm0,[rsp+12]
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+16]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[near_sq]
 ja .next_neighbor
 ucomiss xmm0,[epsilon]
 ja .no_coincident
 cmp dword [rsp+92],0
 jne .no_coincident
 mov eax,1
 cmp r12d,ebp
 jb .coincident_sign
 mov eax,-1
.coincident_sign:
 mov [rsp+92],eax
.no_coincident:
 mov [rsp+128+r14*4],ebp
 inc r14d
.next_neighbor:
 mov eax,ebp
 shl eax,5
 lea rcx,[snaps]
 mov ebp,[rcx+rax+24]
 jmp .chain
.next_x:
 inc dword [rsp+84]
 cmp dword [rsp+84],1
 jle .cell_x
.next_z:
 inc dword [rsp+80]
 cmp dword [rsp+80],1
 jle .cell_z
 call .account
 cmp dword [rsp+92],0
 je .desired_direction
 mov dword [rsp+28],0
 cvtsi2ss xmm0,dword [rsp+92]
 movss [rsp+32],xmm0
.desired_direction:
 xor r15d,r15d
.candidate:
 movss xmm2,[rsp+28]
 movss xmm3,[rsp+32]
 lea rax,[angles]
 movss xmm5,[rax+r15*8]
 movss xmm6,[rax+r15*8+4]
 ; Rotate normalized desired direction.
 movaps xmm7,xmm2
 mulss xmm2,xmm5
 mulss xmm7,xmm6
 movaps xmm8,xmm3
 mulss xmm3,xmm5
 mulss xmm8,xmm6
 subss xmm2,xmm8
 addss xmm3,xmm7
 mulss xmm2,[rsp+8]
 mulss xmm3,[rsp+8]
 addss xmm2,[rsp+12]
 addss xmm3,[rsp+16]
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 movss xmm4,[rsp+8]
 mov edi,[rsp+4]
 call terrain_move
 movss [rsp+36],xmm0
 movss [rsp+40],xmm1
 subss xmm0,[rsp+12]
 subss xmm1,[rsp+16]
 movss [rsp+44],xmm0
 movss [rsp+48],xmm1
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movss [rsp+52],xmm0
 ucomiss xmm0,[epsilon]
 jbe .reject
 xor ebp,ebp
 mov dword [rsp+60],0
.check:
 cmp ebp,r14d
 jae .accept
 mov eax,[rsp+128+rbp*4]
 shl eax,5
 lea rbx,[snaps]
 add rbx,rax
 ; Initial squared center distance, radius sum, and nearest swept distance.
 movss xmm0,[rbx]
 subss xmm0,[rsp+12]
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+16]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 mulss xmm2,xmm2
 mulss xmm3,xmm3
 addss xmm2,xmm3
 movss xmm4,[rbx+8]
 addss xmm4,[rsp+56]
 movaps xmm5,xmm4
 mulss xmm5,xmm5
 ; Projection onto source segment, clamped [0,1].
 movaps xmm6,xmm0
 mulss xmm6,[rsp+44]
 movaps xmm7,xmm1
 mulss xmm7,[rsp+48]
 addss xmm6,xmm7
 divss xmm6,[rsp+52]
 maxss xmm6,[zero]
 minss xmm6,[one]
 movaps xmm7,xmm6
 mulss xmm6,[rsp+44]
 mulss xmm7,[rsp+48]
 subss xmm0,xmm6
 subss xmm1,xmm7
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm2,xmm5
 jb .overlap
 ; Conservative independent-motion clearance: target may advance its entire
 ; role maximum step toward any point on this segment in the same tick.
 addss xmm4,[rbx+12]
 mulss xmm4,xmm4
 ucomiss xmm0,xmm4
 jae .checked
 ; If already inside an anticipation margin, outward/tangent motion may
 ; escape safely rather than freeze. Its sweep must not decrease distance.
 ucomiss xmm2,xmm4
 jae .reject
 addss xmm0,[epsilon]
 ucomiss xmm0,xmm2
 jb .reject
 jmp .checked
.overlap:
 ; Existing overlaps cannot vanish instantly. Require a genuine outward
 ; radial component for noncoincident bodies: equal tangential displacement
 ; of two overlapping actors cannot masquerade as recovery.
 ucomiss xmm2,[epsilon]
 jbe .coincident_recovery
 movss xmm6,[rbx]
 subss xmm6,[rsp+12]
 mulss xmm6,[rsp+44]
 movss xmm7,[rbx+4]
 subss xmm7,[rsp+16]
 mulss xmm7,[rsp+48]
 addss xmm6,xmm7
 addss xmm6,[epsilon]
 ucomiss xmm6,[zero]
 jae .reject
.coincident_recovery:
 ; Never deepen along the sweep,
 ; and strictly increase separation at endpoint, with normal role step only.
 addss xmm0,[epsilon]
 ucomiss xmm0,xmm2
 jb .reject
 movss xmm0,[rbx]
 subss xmm0,[rsp+36]
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+40]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 addss xmm2,[epsilon]
 ucomiss xmm0,xmm2
 jbe .reject
 mov dword [rsp+60],1
.checked:
 inc ebp
 jmp .check
.reject:
 inc r15d
 cmp r15d,10
 jb .candidate
 inc qword [crowd_metrics+32]
 jmp .unchanged
.accept:
 test r15d,r15d
 jz .not_corrected
 inc qword [crowd_metrics+24]
.not_corrected:
 cmp dword [rsp+60],0
 je .result
 inc qword [crowd_metrics+40]
.result:
 movss xmm0,[rsp+36]
 movss xmm1,[rsp+40]
 jmp .out
.truncated:
 call .account
 inc qword [crowd_metrics+48]
 inc qword [crowd_metrics+32]
 jmp .unchanged
.account:
 mov eax,[rsp+76]
 add [crowd_metrics+16],rax
 cmp rax,[crowd_metrics+56]
 jbe .account_done
 mov [crowd_metrics+56],rax
.account_done: ret
.bad_input:
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 movss [rsp+12],xmm0
 movss [rsp+16],xmm1
 jmp .unchanged
.legacy:
 mov edi,[rsp+4]
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 movss xmm2,[rsp+20]
 movss xmm3,[rsp+24]
 movss xmm4,[rsp+8]
 call terrain_move
 jmp .out
.unchanged:
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 maxss xmm0,[zero]
 minss xmm0,[maximum]
 maxss xmm1,[zero]
 minss xmm1,[maximum]
.out:
 add rsp,2248
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
crowd_hash:
 lea rsi,[crowd_enabled]
 mov ecx,4
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
