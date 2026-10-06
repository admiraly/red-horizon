; Shared deterministic ground-vehicle death registry, bounded at1,024 wrecks.
%include "schemas/entity.inc"
%include "schemas/ground_motion.inc"
%include "schemas/ground_support.inc"
%include "schemas/wreck.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,sim_ground_motion
extern terrain_height,ground_support,ground_contact
section .bss align=64
global sim_wrecks,sim_wreck_count,sim_wreck_sequence
sim_wrecks: resb WRECK_CAPACITY*WRECK_STRIDE
seen_generation: resd ENTITY_CAPACITY
sim_wreck_count: resd 1
cursor: resd 1
sim_wreck_sequence: resd 1
; Derived query cache invalidation, excluded from the authoritative hash arena.
global wreck_query_revision
wreck_query_revision: resq 1
section .rodata
zero: dd 0.0
maximum: dd 8000.0
y_minimum: dd -2000.0
y_maximum: dd 2000.0
section .text
global wreck_init,wreck_register,wreck_tick,wreck_hash
wreck_init:
 inc qword [wreck_query_revision]
 lea rdi,[sim_wrecks]
 xor eax,eax
 mov ecx,(WRECK_CAPACITY*WRECK_STRIDE+ENTITY_CAPACITY*4+12)/4
 rep stosd
 ret
wreck_register:
 cmp edi,[sim_count]
 jae .invalid_leaf
 cmp edi,ENTITY_CAPACITY
 jae .invalid_leaf
 push rbx
 push r12
 push r13
 sub rsp,144
 mov r12d,edi
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 jne .invalid
 mov eax,[rbx+ENTITY_KIND]
 sub eax,1
 cmp eax,1
 ja .invalid
 cmp dword [rbx+ENTITY_SIDE],1
 ja .invalid
 mov r13d,[rbx+ENTITY_GENERATION]
 test r13d,r13d
 jz .invalid
 movss xmm0,[rbx+ENTITY_X]
 ucomiss xmm0,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 movss xmm1,[rbx+ENTITY_Z]
 ucomiss xmm1,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[maximum]
 ja .invalid
 lea rax,[seen_generation]
 cmp [rax+r12*4],r13d
 je .duplicate
 ; Validate live motion identity; missing/hostile support uses explicit fallback.
 mov dword [rsp+128],0
 mov dword [rsp+132],WRECK_ACTIVE|WRECK_UPRIGHT
 mov eax,r12d
 shl eax,5
 lea rdx,[sim_ground_motion]
 add rdx,rax
 cmp [rdx+GROUND_GENERATION],r13d
 jne .upright
 mov eax,[rbx+ENTITY_KIND]
 cmp [rdx+GROUND_KIND],eax
 jne .upright
 test dword [rdx+GROUND_FLAGS],GROUND_ACTIVE
 jz .upright
 movss xmm2,[rdx+GROUND_HEADING]
 movss [rsp+128],xmm2
 mov rdi,rsp
 mov esi,[rbx+ENTITY_KIND]
 mov edx,SUPPORT_STRIDE
 call ground_support
 test eax,eax
 jnz .upright
 lea rdi,[rsp+64]
 mov esi,[rbx+ENTITY_KIND]
 mov edx,SUPPORT_STRIDE
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 movss xmm2,[rsp+128]
 movss xmm3,[rsp+SUPPORT_PITCH]
 movss xmm4,[rsp+SUPPORT_BANK]
 call ground_contact
 test eax,eax
 jnz .upright
 movss xmm0,[rsp+SUPPORT_Y]
 maxss xmm0,[rsp+64+SUPPORT_Y]
 movss [rsp+SUPPORT_Y],xmm0
 mov dword [rsp+132],WRECK_ACTIVE
 jmp .height_check
.upright:
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 call terrain_height
 movss [rsp+SUPPORT_Y],xmm0
 mov dword [rsp+SUPPORT_PITCH],0
 mov dword [rsp+SUPPORT_BANK],0
 mov dword [rsp+128],0
.height_check:
 ucomiss xmm0,[y_minimum]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[y_maximum]
 ja .invalid
 inc qword [wreck_query_revision]
 ; Commit only after every dependency and input has passed validation.
 mov eax,[cursor]
 shl eax,6
 lea rdx,[sim_wrecks]
 add rdx,rax
 test dword [rdx+WRECK_FLAGS],WRECK_ACTIVE
 jnz .occupied
 inc dword [sim_wreck_count]
.occupied:
 mov eax,[rbx+ENTITY_X]
 mov [rdx+WRECK_X],eax
 mov eax,[rsp+SUPPORT_Y]
 mov [rdx+WRECK_Y],eax
 mov eax,[rbx+ENTITY_Z]
 mov [rdx+WRECK_Z],eax
 mov eax,[rsp+128]
 mov [rdx+WRECK_HEADING],eax
 mov eax,[rsp+SUPPORT_PITCH]
 mov [rdx+WRECK_PITCH],eax
 mov eax,[rsp+SUPPORT_BANK]
 mov [rdx+WRECK_BANK],eax
 mov eax,[rbx+ENTITY_KIND]
 mov [rdx+WRECK_KIND],eax
 mov eax,[rbx+ENTITY_SIDE]
 mov [rdx+WRECK_SIDE],eax
 mov [rdx+WRECK_ENTITY],r12d
 mov [rdx+WRECK_GENERATION],r13d
 mov eax,[sim_tick_count]
 mov [rdx+WRECK_BIRTH],eax
 add eax,WRECK_LIFETIME_TICKS
 mov [rdx+WRECK_EXPIRY],eax
 mov eax,[sim_wreck_sequence]
 inc eax
 jnz .sequence_ok
 inc eax
.sequence_ok:
 mov [sim_wreck_sequence],eax
 mov [rdx+WRECK_SEQUENCE],eax
 mov eax,[rsp+132]
 mov [rdx+WRECK_FLAGS],eax
 mov qword [rdx+56],0
 lea rax,[seen_generation]
 mov [rax+r12*4],r13d
 inc dword [cursor]
 and dword [cursor],WRECK_CAPACITY-1
 xor eax,eax
 jmp .done
.duplicate:
 mov eax,1
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,144
 pop r13
 pop r12
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
wreck_tick:
 lea rdx,[sim_wrecks]
 mov ecx,WRECK_CAPACITY
 mov r8d,[sim_tick_count]
.loop:
 test dword [rdx+WRECK_FLAGS],WRECK_ACTIVE
 jz .next
 mov eax,r8d
 sub eax,[rdx+WRECK_BIRTH]
 cmp eax,WRECK_LIFETIME_TICKS
 jb .next
 inc qword [wreck_query_revision]
 and dword [rdx+WRECK_FLAGS],~WRECK_ACTIVE
 dec dword [sim_wreck_count]
.next:
 add rdx,WRECK_STRIDE
 loop .loop
 ret
wreck_hash:
 lea rsi,[sim_wrecks]
 mov ecx,WRECK_CAPACITY*WRECK_STRIDE+ENTITY_CAPACITY*4+12
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
