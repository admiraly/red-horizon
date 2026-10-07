; Actual visible incoming cannon traces. No hidden shooter-pose/target reads.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/combat.inc"
%include "schemas/air_evasion.inc"
%define SEARCH_WIDTH (AIR_EVADE_CELL_RADIUS*2+1)
%define SEARCH_CELLS (SEARCH_WIDTH*SEARCH_WIDTH)
default rel
extern sim_entities,sim_aircraft,sim_count,sim_tick_count,sim_projectiles,world_los
section .bss align=64
heads: resd 1024
links: resd PROJECTILE_CAPACITY
index_ready: resd 1
index_tick: resd 1
global air_threat_metrics
; Per-build diagnostics: slots,indexed,queries,cells,candidates,LOS,warnings,caps.
air_threat_metrics: resq 8
section .rodata
zero: dd 0.0
one: dd 1.0
negative: dd -1.0
maximum: dd 8000.0
max_y: dd 1000.0
max_velocity: dd 32.0
round_min_sq: dd 783.9
round_max_sq: dd 784.1
minimum_speed: dd 5.0
maximum_speed: dd 7.0
own_min_sq: dd 24.9
own_max_sq: dd 49.1
range_sq: dd AIR_EVADE_RANGE_SQ
view_sq: dd AIR_EVADE_VIEW_COS_SQ
predict_ticks: dd AIR_EVADE_PREDICT_TICKS
miss_sq: dd AIR_EVADE_MISS_SQ
cell_scale: dd 0.004
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global air_threats_reset,air_threats_build,air_threat_query
air_threats_reset:
 mov dword [index_ready],0
 ret
; RDI gun record; validates current metadata and finite physical trace, EAX0/1.
; Source may be dead: a conserved round remains dangerous after its shooter dies.
valid_round:
 cmp dword [rdi+PROJECTILE_ACTIVE],1
 jne .bad
 cmp dword [rdi+PROJECTILE_KIND],PROJECTILE_AIR_GUN
 jne .bad
 cmp dword [rdi+PROJECTILE_DAMAGE],24
 jne .bad
 cmp dword [rdi+PROJECTILE_RADIUS],0
 jne .bad
 cmp dword [rdi+PROJECTILE_GENERATION],0
 je .bad
 cmp dword [rdi+PROJECTILE_TTL],1
 jb .bad
 cmp dword [rdi+PROJECTILE_TTL],40
 ja .bad
 cmp dword [rdi+PROJECTILE_SIDE],1
 ja .bad
 mov eax,[rdi+PROJECTILE_SOURCE]
 cmp eax,[sim_count]
 jae .bad
 cmp eax,ENTITY_CAPACITY
 jae .bad
 mov edx,eax
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 cmp dword [r8+ENTITY_KIND],3
 jne .bad
 mov ecx,[r8+ENTITY_SIDE]
 cmp ecx,[rdi+PROJECTILE_SIDE]
 jne .bad
 mov ecx,[r8+ENTITY_GENERATION]
 test ecx,ecx
 jz .bad
 cmp ecx,[rdi+PROJECTILE_SOURCE_GENERATION]
 jne .bad
 shl edx,6
 lea r9,[sim_aircraft]
 add r9,rdx
 cmp ecx,[r9+AIR_GENERATION]
 jne .bad
 test dword [r9+AIR_FLAGS],AIR_ACTIVE
 jz .bad
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 jne .bad
%macro coordinate 1
 movss xmm0,[rdi+%1]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
%endmacro
 coordinate PROJECTILE_X
 coordinate PROJECTILE_Z
%unmacro coordinate 1
 movss xmm0,[rdi+PROJECTILE_Y]
 andps xmm0,[abs_mask]
 ucomiss xmm0,[max_y]
 jp .bad
 ja .bad
 xorps xmm2,xmm2
%macro velocity 1
 movss xmm0,[rdi+%1]
 movaps xmm1,xmm0
 andps xmm1,[abs_mask]
 ucomiss xmm1,[max_velocity]
 jp .bad
 ja .bad
 mulss xmm0,xmm0
 addss xmm2,xmm0
%endmacro
 velocity PROJECTILE_VX
 velocity PROJECTILE_VY
 velocity PROJECTILE_VZ
%unmacro velocity 1
 ucomiss xmm2,[round_min_sq]
 jb .bad
 ucomiss xmm2,[round_max_sq]
 ja .bad
 mov eax,1
 ret
.bad:
 xor eax,eax
 ret
; Rebuild once before continuous air movement. Fixed512 slots, no allocations.
air_threats_build:
 push rbx
 push rbp
 push r12
 mov dword [index_ready],0
 lea rdi,[air_threat_metrics]
 xor eax,eax
 mov ecx,8
 rep stosq
 lea rdi,[heads]
 mov eax,-1
 mov ecx,1024
 rep stosd
 lea rdi,[links]
 mov ecx,PROJECTILE_CAPACITY
 rep stosd
 lea rbx,[sim_projectiles]
 xor r12d,r12d
.loop:
 inc qword [air_threat_metrics]
 mov rdi,rbx
 call valid_round
 test eax,eax
 jz .next
 movss xmm0,[rbx+PROJECTILE_X]
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .x
 mov eax,31
.x:
 mov ebp,eax
 movss xmm0,[rbx+PROJECTILE_Z]
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .z
 mov eax,31
.z:
 shl eax,5
 add eax,ebp
 lea rcx,[heads]
 mov edx,[rcx+rax*4]
 mov [rcx+rax*4],r12d
 lea rcx,[links]
 mov [rcx+r12*4],edx
 inc qword [air_threat_metrics+8]
.next:
 add rbx,PROJECTILE_STRIDE
 inc r12d
 cmp r12d,PROJECTILE_CAPACITY
 jb .loop
 mov eax,[sim_tick_count]
 mov [index_tick],eax
 mov dword [index_ready],1
 pop r12
 pop rbp
 pop rbx
 ret
; EDI own aircraft. EAX nearest visible incoming slot/-1, XMM0 break error +/-1/0.
; Gameplay state read-only; only per-build diagnostic counters are updated.
; Search at most49cells/64records/2LOS calls, rotating cell priority by tick+ID.
air_threat_query:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,120
 mov r12d,edi
 cmp edi,[sim_count]
 jae .none
 cmp edi,ENTITY_CAPACITY
 jae .none
 cmp dword [index_ready],1
 jne .none
 mov eax,[sim_tick_count]
 cmp eax,[index_tick]
 jne .none
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .none
 cmp dword [rbx+ENTITY_KIND],3
 jne .none
 cmp dword [rbx+ENTITY_SIDE],1
 ja .none
 cmp dword [rbx+ENTITY_FRONT],2
 ja .none
 mov eax,edi
 shl eax,6
 lea rbp,[sim_aircraft]
 add rbp,rax
 mov eax,[rbx+ENTITY_GENERATION]
 test eax,eax
 jz .none
 cmp eax,[rbp+AIR_GENERATION]
 jne .none
 test dword [rbp+AIR_FLAGS],AIR_ACTIVE
 jz .none
 cmp dword [rbp+AIR_ROLE],1
 ja .none
 movss xmm0,[rbp+AIR_SPEED]
 ucomiss xmm0,[minimum_speed]
 jp .none
 jb .none
 ucomiss xmm0,[maximum_speed]
 ja .none
%macro owncoord 2
 movss xmm0,[%1+%2]
 ucomiss xmm0,[zero]
 jp .none
 jb .none
 ucomiss xmm0,[maximum]
 ja .none
%endmacro
 owncoord rbx,ENTITY_X
 owncoord rbx,ENTITY_Z
%unmacro owncoord 2
 movss xmm0,[rbp+AIR_Y]
 andps xmm0,[abs_mask]
 ucomiss xmm0,[max_y]
 jp .none
 ja .none
 xorps xmm2,xmm2
%macro ownvelocity 1
 movss xmm0,[rbp+%1]
 mulss xmm0,xmm0
 addss xmm2,xmm0
%endmacro
 ownvelocity AIR_VX
 ownvelocity AIR_VY
 ownvelocity AIR_VZ
%unmacro ownvelocity 1
 ucomiss xmm2,[own_min_sq]
 jp .none
 jb .none
 ucomiss xmm2,[own_max_sq]
 ja .none
 movss [rsp+76],xmm2
 inc qword [air_threat_metrics+16]
 movss xmm0,[rbx+ENTITY_X]
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .ownx
 mov eax,31
.ownx:
 mov [rsp+4],eax
 movss xmm0,[rbx+ENTITY_Z]
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .ownz
 mov eax,31
.ownz:
 mov [rsp+8],eax
 mov eax,[sim_tick_count]
 add eax,r12d
 xor edx,edx
 mov ecx,SEARCH_CELLS
 div ecx
 mov [rsp+12],edx
 mov dword [rsp+16],0
 mov dword [rsp+20],0
 mov dword [rsp+24],AIR_EVADE_LOS_CALLS
 mov dword [rsp+28],-1
 mov eax,[predict_ticks]
 mov [rsp+32],eax
.cell:
 mov eax,[rsp+16]
 cmp eax,SEARCH_CELLS
 jae .result
 add eax,[rsp+12]
 cmp eax,SEARCH_CELLS
 jb .wrapped
 sub eax,SEARCH_CELLS
.wrapped:
 xor edx,edx
 mov ecx,SEARCH_WIDTH
 div ecx
 add edx,[rsp+4]
 sub edx,AIR_EVADE_CELL_RADIUS
 cmp edx,31
 ja .nextcell
 add eax,[rsp+8]
 sub eax,AIR_EVADE_CELL_RADIUS
 cmp eax,31
 ja .nextcell
 shl eax,5
 add eax,edx
 inc qword [air_threat_metrics+24]
 lea rcx,[heads]
 mov r13d,[rcx+rax*4]
.record:
 cmp r13d,PROJECTILE_CAPACITY
 jae .nextcell
 cmp dword [rsp+20],AIR_EVADE_CANDIDATES
 jae .capped
 inc dword [rsp+20]
 inc qword [air_threat_metrics+32]
 lea rcx,[links]
 mov eax,[rcx+r13*4]
 mov [rsp+64],eax
 mov eax,r13d
 shl eax,6
 lea r14,[sim_projectiles]
 add r14,rax
 mov rdi,r14
 call valid_round
 test eax,eax
 jz .nextrecord
 mov eax,[r14+PROJECTILE_SIDE]
 cmp eax,[rbx+ENTITY_SIDE]
 je .nextrecord
 movss xmm0,[r14+PROJECTILE_X]
 subss xmm0,[rbx+ENTITY_X]
 movss [rsp+40],xmm0
 movss xmm1,[r14+PROJECTILE_Y]
 subss xmm1,[rbp+AIR_Y]
 movss [rsp+44],xmm1
 movss xmm2,[r14+PROJECTILE_Z]
 subss xmm2,[rbx+ENTITY_Z]
 movss [rsp+48],xmm2
 movaps xmm3,xmm0
 mulss xmm3,xmm3
 movaps xmm4,xmm1
 mulss xmm4,xmm4
 addss xmm3,xmm4
 movaps xmm4,xmm2
 mulss xmm4,xmm4
 addss xmm3,xmm4
 comiss xmm3,[range_sq]
 ja .nextrecord
 ; Actual forward-flight cone, using only an in-range physical trace.
 mulss xmm0,[rbp+AIR_VX]
 mulss xmm1,[rbp+AIR_VY]
 addss xmm0,xmm1
 mulss xmm2,[rbp+AIR_VZ]
 addss xmm0,xmm2
 comiss xmm0,[zero]
 jbe .nextrecord
 mulss xmm0,xmm0
 mulss xmm3,[rsp+76]
 mulss xmm3,[view_sq]
 comiss xmm0,xmm3
 jb .nextrecord
 movss xmm0,[r14+PROJECTILE_VX]
 subss xmm0,[rbp+AIR_VX]
 movss xmm1,[r14+PROJECTILE_VY]
 subss xmm1,[rbp+AIR_VY]
 movss xmm2,[r14+PROJECTILE_VZ]
 subss xmm2,[rbp+AIR_VZ]
 movaps xmm3,xmm0
 mulss xmm3,xmm3
 movaps xmm4,xmm1
 mulss xmm4,xmm4
 addss xmm3,xmm4
 movaps xmm4,xmm2
 mulss xmm4,xmm4
 addss xmm3,xmm4
 movaps xmm4,xmm0
 mulss xmm4,[rsp+40]
 movaps xmm5,xmm1
 mulss xmm5,[rsp+44]
 addss xmm4,xmm5
 movaps xmm5,xmm2
 mulss xmm5,[rsp+48]
 addss xmm4,xmm5
 mulss xmm4,[negative]
 divss xmm4,xmm3
 comiss xmm4,[zero]
 jbe .nextrecord
 comiss xmm4,[predict_ticks]
 ja .nextrecord
 cvtsi2ss xmm5,dword [r14+PROJECTILE_TTL]
 comiss xmm4,xmm5
 ja .nextrecord
 comiss xmm4,[rsp+32]
 ja .nextrecord
 jne .possible
 cmp r13d,[rsp+28]
 jae .nextrecord
.possible:
 mulss xmm0,xmm4
 addss xmm0,[rsp+40]
 movss [rsp+52],xmm0
 mulss xmm1,xmm4
 addss xmm1,[rsp+44]
 mulss xmm2,xmm4
 addss xmm2,[rsp+48]
 movss [rsp+56],xmm2
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 mulss xmm2,xmm2
 addss xmm0,xmm2
 comiss xmm0,[miss_sq]
 ja .nextrecord
 cmp dword [rsp+24],0
 je .nextrecord
 dec dword [rsp+24]
 inc qword [air_threat_metrics+40]
 movss [rsp+60],xmm4
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbp+AIR_Y]
 movss xmm2,[rbx+ENTITY_Z]
 movss xmm3,[r14+PROJECTILE_X]
 movss xmm4,[r14+PROJECTILE_Y]
 movss xmm5,[r14+PROJECTILE_Z]
 call world_los
 test eax,eax
 jz .nextrecord
 mov [rsp+28],r13d
 mov eax,[rsp+60]
 mov [rsp+32],eax
 ; Roll away from the predicted lateral close-pass point. Exact central
 ; approaches use stable physical-ID parity, independent of faction label.
 movss xmm0,[rsp+52]
 mulss xmm0,[rbp+AIR_VZ]
 movss xmm1,[rsp+56]
 mulss xmm1,[rbp+AIR_VX]
 subss xmm0,xmm1
 comiss xmm0,[zero]
 ja .left
 jb .right
 test r12d,1
 jz .right
.left:
 mov eax,__float32__(-1.0)
 jmp .direction
.right:
 mov eax,__float32__(1.0)
.direction:
 mov [rsp+36],eax
.nextrecord:
 mov r13d,[rsp+64]
 jmp .record
.nextcell:
 inc dword [rsp+16]
 jmp .cell
.capped:
 inc qword [air_threat_metrics+56]
.result:
 mov eax,[rsp+28]
 cmp eax,-1
 je .none
 inc qword [air_threat_metrics+48]
 movss xmm0,[rsp+36]
 jmp .out
.none:
 mov eax,-1
 xorps xmm0,xmm0
.out:
 add rsp,120
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
