; Client-only read-only supply cache. Wire validation precedes publication.
%include "schemas/company_supply.inc"
%include "schemas/company_remote.inc"
default rel
extern net_company_for_player,net_company_records,sim_tick_count
section .bss align=16
global net_supply_record,net_supply_tick,net_supply_valid
net_supply_record: resb COMPANY_SUPPLY_PAYLOAD
net_supply_tick: resd 1
net_supply_valid: resd 1
section .text
global net_supply_reset,net_supply_receive,net_supply_report
net_supply_reset:
 lea rdi,[net_supply_record]
 xor eax,eax
 mov ecx,(COMPANY_SUPPLY_PAYLOAD+8)/4
 rep stosd
 ret
; RDI readable payload,ESI exact bytes,EDX tick,ECX recipient ->0/-1.
; Transport authenticates server/session; display separately corroborates lease.
net_supply_receive:
 test rdi,rdi
 jz .bad
 cmp esi,COMPANY_SUPPLY_PAYLOAD
 jne .bad
 cmp ecx,4
 jae .bad
 cmp dword [rdi],0
 je .bad
 cmp [rdi+4],ecx
 jne .bad
 cmp dword [rdi+8],0
 je .bad
 cmp dword [rdi+12],COMPANY_REMOTE_KEY_LIMIT
 jae .bad
 cmp qword [rdi+36],0
 jne .bad
 mov eax,[rdi+16]
 cmp eax,128
 ja .bad
 mov r8d,[rdi+32]
 cmp r8d,eax
 ja .bad
 sub eax,r8d
 cmp [rdi+20],eax
 ja .bad
 mov r8d,[rdi+20]
 cmp [rdi+24],r8d
 ja .bad
 ; Known healthy troops carry31..120; nonempty low troops1..30.
 ; This bounds the sum in both directions, preventing contradictory totals.
 mov eax,[rdi+16]
 sub eax,[rdi+32]
 sub eax,[rdi+20]
 mov r8d,eax
 imul eax,31
 mov r9d,[rdi+20]
 sub r9d,[rdi+24]
 add eax,r9d
 cmp [rdi+28],eax
 jb .bad
 imul r8d,120
 imul r9d,30
 add r8d,r9d
 cmp [rdi+28],r8d
 ja .bad
 cmp dword [net_supply_valid],0
 je .apply
 cmp edx,[net_supply_tick]
 jbe .bad
.apply:
 mov rsi,rdi
 lea rdi,[net_supply_record]
 mov ecx,COMPANY_SUPPLY_PAYLOAD/4
 rep movsd
 mov [net_supply_tick],edx
 mov dword [net_supply_valid],1
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
; EDI player,RSI disjoint writable output,EDX capacity>=40 ->0/-1.
; Unknown/unavailable never fabricates zero/full stock; failure preserves output.
net_supply_report:
 test rsi,rsi
 jz .bad
 cmp edx,COMPANY_SUPPLY_STRIDE
 jb .bad
 cmp dword [net_supply_valid],1
 jne .bad
 cmp edi,[net_supply_record+4]
 jne .bad
 mov eax,[sim_tick_count]
 cmp eax,[net_supply_tick]
 jb .bad
 sub eax,[net_supply_tick]
 cmp eax,COMPANY_SUPPLY_MAX_AGE
 ja .bad
 push rbx
 push r12
 sub rsp,8
 mov rbx,rsi
 mov r12d,edi
 call net_company_for_player
 cmp eax,[net_supply_record+12]
 jne .invalid
 imul eax,r12d,COMPANY_REMOTE_STRIDE
 lea rdx,[net_company_records]
 add rdx,rax
 mov eax,[rdx+8]
 cmp eax,[net_supply_record+8]
 jne .invalid
 mov eax,[rdx+12]
 cmp eax,[net_supply_record]
 jne .invalid
 lea rsi,[net_supply_record+4]
 mov rdi,rbx
 mov ecx,COMPANY_SUPPLY_STRIDE/8
 rep movsq
 xor eax,eax
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
.bad:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
