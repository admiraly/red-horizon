; Read-only authoritative owned-company rifle stock report prerequisite.
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/infantry_weapon.inc"
%include "schemas/company_supply.inc"
default rel
extern company_for_player,sim_count,sim_entities,infantry_weapons
section .text
global company_supply_report
; EDI player,RSI caller-owned disjoint writable buffer,EDXbytes>=40 ->0/-1.
; Failure leaves output unchanged. Success writes exactly40bytes. Sequential
; authority safe point; no allocation, enemy reads or persistent mutation.
; Validate bidirectional lease/body/front, then at most128 physical own IDs.
; Unknown/generation-mismatched/corrupt stocks are counted explicitly, never
; presented as full or empty. Low<=30 includes empty. Preserves SysV GPRs.
company_supply_report:
 push rbx
 push r12
 push r13
 push r14
 sub rsp,56
 mov r13,rsi
 test rsi,rsi
 jz .bad
 cmp edx,COMPANY_SUPPLY_STRIDE
 jb .bad
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 mov [rsp+48],edi
 call company_for_player
 cmp eax,768
 jae .bad
 mov r12d,eax
 shr eax,8
 cmp [rdx+PLAYER_FRONT],eax
 jne .bad
 mov ecx,[rdx+PLAYER_GENERATION]
 xor eax,eax
 mov [rsp],rax
 mov [rsp+8],rax
 mov [rsp+16],rax
 mov [rsp+24],rax
 mov [rsp+32],rax
 mov eax,[rsp+48]
 mov [rsp],eax
 mov [rsp+4],ecx
 mov [rsp+8],r12d
 mov r14d,r12d
 and r14d,255
 shl r14d,7
 lea eax,[r14+128]
 cmp eax,[sim_count]
 jbe .end
 mov eax,[sim_count]
.end:
 mov [rsp+40],eax
 shr r12d,8
.loop:
 cmp r14d,[rsp+40]
 jae .publish
 mov eax,r14d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .next
 cmp dword [rbx+ENTITY_KIND],0
 jne .next
 cmp dword [rbx+ENTITY_SIDE],0
 jne .next
 cmp [rbx+ENTITY_FRONT],r12d
 jne .next
 cmp dword [rbx+ENTITY_GENERATION],0
 je .next
 inc dword [rsp+12]
 lea r8,[infantry_weapons]
 add r8,rax
 mov eax,[rbx+ENTITY_GENERATION]
 cmp [r8],eax
 jne .unknown
 cmp dword [r8+4],INFANTRY_MAGAZINE
 ja .unknown
 cmp dword [r8+8],INFANTRY_RESERVE
 ja .unknown
 cmp dword [r8+12],INFANTRY_RELOAD_TICKS
 ja .unknown
 cmp dword [r8+24],INFANTRY_RECEIVED_LIMIT
 ja .unknown
 mov ecx,[r8+24]
 add ecx,INFANTRY_MAGAZINE+INFANTRY_RESERVE
 cmp [r8+16],ecx
 ja .unknown
 mov eax,[r8+4]
 add eax,[r8+8]
 mov edx,eax
 add edx,[r8+16]
 cmp edx,ecx
 jne .unknown
 cmp dword [r8+12],0
 je .known
 cmp dword [r8+4],0
 jne .unknown
.known:
 add [rsp+24],eax
 cmp eax,COMPANY_SUPPLY_LOW_ROUNDS
 ja .next
 inc dword [rsp+16]
 test eax,eax
 jnz .next
 inc dword [rsp+20]
 jmp .next
.unknown:
 inc dword [rsp+28]
.next:
 inc r14d
 jmp .loop
.publish:
 mov rax,[rsp]
 mov [r13],rax
 mov rax,[rsp+8]
 mov [r13+8],rax
 mov rax,[rsp+16]
 mov [r13+16],rax
 mov rax,[rsp+24]
 mov [r13+24],rax
 mov rax,[rsp+32]
 mov [r13+32],rax
 xor eax,eax
 jmp .out
.bad:
 mov eax,-1
.out:
 add rsp,56
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
