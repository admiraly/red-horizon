; Private same-tick admission queues. SysV, no allocation or wire state.
%include "schemas/entity.inc"
%include "schemas/ordnance.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,vehicle_entity_driver
extern sim_shell_ammo,sim_shell_cooldown,sim_projectile_count,projectile_spawn
section .data align=16
global ordnance_enabled
ordnance_enabled: dd 1
section .bss align=64
global ordnance_metrics,ordnance_cursors
ordnance_cursors: resd ORDNANCE_GROUPS
ordnance_metrics: resq ORDNANCE_GROUPS*4
requests: resb ENTITY_CAPACITY*ORDNANCE_REQUEST_STRIDE
heads: resd ORDNANCE_GROUPS
tails: resd ORDNANCE_GROUPS
counts: resd ORDNANCE_GROUPS
iters: resd ORDNANCE_GROUPS
remaining: resd ORDNANCE_GROUPS
ranks: resd ORDNANCE_GROUPS
section .text
global ordnance_init,ordnance_begin,ordnance_request,ordnance_flush,ordnance_hash
ordnance_init:
 mov dword [ordnance_enabled],1
 lea rdi,[ordnance_cursors]
 mov eax,-1
 mov ecx,ORDNANCE_GROUPS
 rep stosd
 lea rdi,[ordnance_metrics]
 xor eax,eax
 mov ecx,ORDNANCE_GROUPS*8
 rep stosd
 jmp ordnance_begin
ordnance_begin:
 ; Capacity-clear prevents a changed count or malformed caller reviving queues.
 lea rdi,[requests]
 mov eax,-1
 mov ecx,ENTITY_CAPACITY*ORDNANCE_REQUEST_STRIDE/4
 rep stosd
 lea rdi,[heads]
 mov ecx,ORDNANCE_GROUPS*2
 rep stosd
 lea rdi,[counts]
 xor eax,eax
 mov ecx,ORDNANCE_GROUPS*3
 rep stosd
 ret
; Leaf validation. EDI/ESI source/target preserved, EAX group or -1.
; Does not infer targets: caller must submit an actual acquired target.
validate:
 mov eax,[sim_count]
 cmp eax,ENTITY_CAPACITY
 ja .bad
 cmp edi,eax
 jae .bad
 cmp esi,eax
 jae .bad
 lea rdx,[sim_entities]
 mov eax,edi
 shl eax,5
 lea r9,[rdx+rax]
 mov eax,esi
 shl eax,5
 lea r10,[rdx+rax]
 cmp dword [r9+ENTITY_HP],0
 je .bad
 cmp dword [r10+ENTITY_HP],0
 je .bad
 cmp dword [r9+ENTITY_GENERATION],0
 je .bad
 cmp dword [r10+ENTITY_GENERATION],0
 je .bad
 mov eax,[r9+ENTITY_KIND]
 dec eax
 cmp eax,1
 ja .bad
 mov ecx,[r9+ENTITY_SIDE]
 cmp ecx,1
 ja .bad
 mov edx,[r10+ENTITY_SIDE]
 cmp edx,1
 ja .bad
 cmp edx,ecx
 je .bad
 lea rdx,[vehicle_entity_driver]
 cmp dword [rdx+rdi*4],-1
 jne .bad
 lea rdx,[sim_shell_ammo]
 cmp dword [rdx+rdi*4],0
 je .bad
 lea rdx,[sim_shell_cooldown]
 cmp dword [rdx+rdi*4],0
 jne .bad
 lea eax,[rax+rcx*2]
 ret
.bad: mov eax,-1
 ret
ordnance_request:
 cmp dword [ordnance_enabled],0
 je .bad
 sub rsp,8
 call validate
 add rsp,8
 test eax,eax
 js .bad
 lea rdx,[requests]
 mov ecx,edi
 shl ecx,4
 add rdx,rcx
 cmp dword [rdx+ORDNANCE_TARGET],-1
 jne .bad
 mov [rdx+ORDNANCE_TARGET],esi
 mov ecx,[r9+ENTITY_GENERATION]
 mov [rdx+ORDNANCE_SOURCE_GENERATION],ecx
 mov ecx,[r10+ENTITY_GENERATION]
 mov [rdx+ORDNANCE_TARGET_GENERATION],ecx
 ; Existing tail points to the new node. World submits ascending stable IDs.
 lea r8,[tails]
 mov ecx,[r8+rax*4]
 test ecx,ecx
 js .first
 shl ecx,4
 lea r11,[requests]
 mov [r11+rcx+ORDNANCE_NEXT],edi
 jmp .tail
.first:
 lea r11,[heads]
 mov [r11+rax*4],edi
.tail:
 mov [r8+rax*4],edi
 lea r8,[counts]
 inc dword [r8+rax*4]
 shl eax,5
 lea r8,[ordnance_metrics]
 inc qword [r8+rax]
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
ordnance_flush:
 cmp dword [ordnance_enabled],0
 je .empty
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 ; Choose each group's first submitted ID after its last real success cursor.
 xor ebx,ebx
 xor r14d,r14d
.prepare:
 lea rax,[counts]
 mov ecx,[rax+rbx*4]
 add r14d,ecx
 lea rdx,[remaining]
 mov [rdx+rbx*4],ecx
 lea rax,[heads]
 mov edx,[rax+rbx*4]
 mov esi,edx
 lea rax,[ordnance_cursors]
 mov edi,[rax+rbx*4]
.find:
 test edx,edx
 js .fallback
 cmp edx,edi
 jg .start
 mov eax,edx
 shl eax,4
 lea rcx,[requests]
 mov edx,[rcx+rax+ORDNANCE_NEXT]
 jmp .find
.fallback: mov edx,esi
.start:
 lea rax,[iters]
 mov [rax+rbx*4],edx
 inc ebx
 cmp ebx,ORDNANCE_GROUPS
 jb .prepare
 ; Rank nonempty groups by physical lowest source ID, not side labels.
 ; Empty heads are unsigned UINT_MAX and sort last. Constant four-way sort.
 lea r8,[ranks]
 mov dword [r8],0
 mov dword [r8+4],1
 mov dword [r8+8],2
 mov dword [r8+12],3
 lea r9,[heads]
 xor edi,edi
.sort_outer:
 mov esi,edi
 mov ecx,edi
 inc ecx
.sort_inner:
 mov eax,[r8+rsi*4]
 mov r10d,[r9+rax*4]
 mov eax,[r8+rcx*4]
 mov r11d,[r9+rax*4]
 cmp r11d,r10d
 jae .sort_next
 mov esi,ecx
.sort_next:
 inc ecx
 cmp ecx,ORDNANCE_GROUPS
 jb .sort_inner
 mov eax,[r8+rdi*4]
 mov edx,[r8+rsi*4]
 mov [r8+rdi*4],edx
 mov [r8+rsi*4],eax
 inc edi
 cmp edi,ORDNANCE_GROUPS-1
 jb .sort_outer
 mov r15d,[sim_tick_count]
 and r15d,3
.visit:
 test r14d,r14d
 jz .done
 lea rax,[ranks]
 mov ebx,[rax+r15*4]
 lea rax,[remaining]
 cmp dword [rax+rbx*4],0
 je .next_group
 dec dword [rax+rbx*4]
 dec r14d
 lea rax,[iters]
 mov r12d,[rax+rbx*4]
 mov ebp,r12d
 shl ebp,4
 lea r13,[requests]
 add r13,rbp
 mov edx,[r13+ORDNANCE_NEXT]
 test edx,edx
 jns .next_node
 lea rdx,[heads]
 mov edx,[rdx+rbx*4]
.next_node:
 mov [rax+rbx*4],edx
 mov edi,r12d
 mov esi,[r13+ORDNANCE_TARGET]
 call validate
 cmp eax,ebx
 jne .invalidated
 mov eax,[r9+ENTITY_GENERATION]
 cmp eax,[r13+ORDNANCE_SOURCE_GENERATION]
 jne .invalidated
 mov eax,[r10+ENTITY_GENERATION]
 cmp eax,[r13+ORDNANCE_TARGET_GENERATION]
 jne .invalidated
 ; Preserve actual refusal diagnostics by always invoking production spawn.
 mov eax,[sim_projectile_count]
 mov [rsp],eax
 mov edi,r12d
 mov esi,[r13+ORDNANCE_TARGET]
 call projectile_spawn
 test eax,eax
 js .refused
 lea rax,[ordnance_cursors]
 mov [rax+rbx*4],r12d
 mov eax,ebx
 shl eax,5
 lea rdx,[ordnance_metrics]
 inc qword [rdx+rax+8]
 jmp .next_group
.refused:
 cmp dword [rsp],416
 jb .invalidated
 mov eax,ebx
 shl eax,5
 lea rdx,[ordnance_metrics]
 inc qword [rdx+rax+16]
 jmp .next_group
.invalidated:
 mov eax,ebx
 shl eax,5
 lea rdx,[ordnance_metrics]
 inc qword [rdx+rax+24]
.next_group:
 inc r15d
 and r15d,3
 jmp .visit
.done:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
.empty: ret
; Only persistent future-affecting policy/cursors participate, in byte order.
ordnance_hash:
 lea rsi,[ordnance_enabled]
 mov ecx,4
.enabled:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .enabled
 lea rsi,[ordnance_cursors]
 mov ecx,ORDNANCE_GROUPS*4
.cursor:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .cursor
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
