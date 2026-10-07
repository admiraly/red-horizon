; Owned recovery facilities and public authored terrain-conforming runway layout.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_bases.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,sim_sites
extern air_bases
section .text
global air_base_goal
; EDI owned physical aircraft -> EAX selected base ID or-1 unavailable/invalid.
; Success XMM0/1 centre XZ. Failure preserves XMM0/1. All sources read-only.
; R8/R9 and all SysV nonvolatile GPRs preserved; private fixed stack only.
air_base_goal:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .none_leaf
 cmp edi,[sim_count]
 jae .none_leaf
 cmp edi,ENTITY_CAPACITY
 jae .none_leaf
 mov eax,edi
 shl eax,5
 lea r10,[sim_entities]
 add r10,rax
 cmp dword [r10+ENTITY_HP],0
 je .none_leaf
 cmp dword [r10+ENTITY_KIND],3
 jne .none_leaf
 cmp dword [r10+ENTITY_SIDE],1
 ja .none_leaf
 cmp dword [r10+ENTITY_FRONT],2
 ja .none_leaf
 mov eax,[r10+ENTITY_X]
 cmp eax,__float32__(8000.0)
 ja .none_leaf
 mov eax,[r10+ENTITY_Z]
 cmp eax,__float32__(8000.0)
 ja .none_leaf
 mov eax,edi
 shl eax,6
 lea r11,[sim_aircraft]
 add r11,rax
 mov eax,[r10+ENTITY_GENERATION]
 test eax,eax
 jz .none_leaf
 cmp eax,[r11+AIR_GENERATION]
 jne .none_leaf
 test dword [r11+AIR_FLAGS],AIR_ACTIVE
 jz .none_leaf
 cmp dword [r11+AIR_ROLE],AIR_FIGHTER
 ja .none_leaf
 push rbx
 push r12
 push r13
 sub rsp,16
 mov rbx,r10
 mov r12d,[rbx+ENTITY_SIDE]
 ; Prefer the original assigned-front runway while its own facility is usable.
 imul edi,r12d,3
 add edi,[rbx+ENTITY_FRONT]
 mov r13d,edi
 call .available
 test eax,eax
 jnz .selected
 mov dword [rsp],-1
 mov dword [rsp+4],0x7f800000
 xor r13d,r13d
.scan:
 mov edi,r13d
 call .available
 test eax,eax
 jz .next
 movss xmm2,[r10]
 subss xmm2,[rbx+ENTITY_X]
 mulss xmm2,xmm2
 movss xmm3,[r10+4]
 subss xmm3,[rbx+ENTITY_Z]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 ucomiss xmm2,[rsp+4]
 jae .next ; Stable lowest ID wins exact ties.
 movss [rsp+4],xmm2
 mov [rsp],r13d
.next:
 inc r13d
 cmp r13d,AIR_BASE_COUNT
 jb .scan
 mov r13d,[rsp]
 cmp r13d,-1
 je .none
 mov eax,r13d
 shl eax,5
 lea r10,[air_bases]
 add r10,rax
.selected:
 movss xmm0,[r10]
 movss xmm1,[r10+4]
 mov eax,r13d
 jmp .done
.none:
 mov eax,-1
.done:
 add rsp,16
 pop r13
 pop r12
 pop rbx
 ret
.none_leaf:
 mov eax,-1
 ret
; EDI bounded static base ID, R12D own side ->EAX1/0, R10 descriptor.
; Check ownership before reading own facility capacity/condition, never inventory.
.available:
 mov eax,edi
 shl eax,5
 lea r10,[air_bases]
 add r10,rax
 mov eax,[r10+16]
 shl eax,5
 lea r11,[sim_sites]
 add r11,rax
 cmp [r11+8],r12d
 jne .no
 cmp dword [r11+16],1
 ja .no
 cmp dword [r11+20],1
 jne .no
 cmp dword [r11+24],0
 je .no
 cmp dword [r11+24],1000
 ja .no
 test dword [r11+28],~3 ; contested or malformed flags deny capability.
 jnz .no
 mov eax,1
 ret
.no:
 xor eax,eax
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
