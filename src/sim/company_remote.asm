; Read-only company view consumed by the connected client, never authority AI.
%include "schemas/player.inc"
%include "schemas/company_remote.inc"
default rel
extern sim_players,sim_tick_count
section .bss align=16
global net_company_records,net_company_tick,net_company_valid,net_company_transfers
net_company_records: resb COMPANY_REMOTE_COUNT*COMPANY_REMOTE_STRIDE
net_company_tick: resd 1
net_company_valid: resd 1
net_company_transfers: resb COMPANY_TRANSFER_PLAYERS*COMPANY_TRANSFER_STRIDE
section .rodata
zero: dd 0.0
maximum: dd 8000.0
section .text
global net_company_reset,net_company_receive,net_company_for_player
net_company_reset:
 lea rdi,[net_company_records]
 xor eax,eax
 mov ecx,(COMPANY_REMOTE_COUNT*COMPANY_REMOTE_STRIDE+8)/4
 rep stosd
 lea rdi,[net_company_transfers]
 mov ecx,COMPANY_TRANSFER_PLAYERS*COMPANY_TRANSFER_STRIDE/8
 rep stosq
 lea rdi,[net_company_records]
 mov ecx,COMPANY_REMOTE_COUNT
.clear:
 mov dword [rdi+4],-1
 add rdi,COMPANY_REMOTE_STRIDE
 loop .clear
 ret
; RDI readable records,ESI exact count,EDX server tick ->0 apply,-1 reject.
; No partial writes, no authoritative player/entity/command/funds mutation.
net_company_receive:
 test rdi,rdi
 jz .bad
 cmp esi,COMPANY_REMOTE_COUNT
 jne .bad
 cmp dword [net_company_valid],0
 je .validate
 cmp edx,[net_company_tick]
 jbe .bad
.validate:
 xor r8d,r8d
 mov rsi,rdi
.record:
 cmp [rsi],r8d
 jne .bad
 mov eax,[rsi+4]
 cmp eax,-1
 je .unassigned
 cmp eax,COMPANY_REMOTE_KEY_LIMIT
 jae .bad
 cmp dword [rsi+8],0
 je .bad
 cmp dword [rsi+16],3
 ja .bad
 cmp dword [rsi+20],1
 ja .bad
 mov ecx,[rsi+36]
 cmp ecx,edx
 ja .bad
 movss xmm0,[rsi+24]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 movss xmm0,[rsi+28]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 cmp dword [rsi+20],0
 jne .duplicates
 ; No explicit intent must not smuggle an executable/displayable plan.
 cmp dword [rsi+16],0
 jne .bad
 cmp qword [rsi+24],0
 jne .bad
 cmp qword [rsi+32],0
 jne .bad
.duplicates:
 xor ecx,ecx
 mov r9,rdi
.previous:
 cmp ecx,r8d
 jae .next
 cmp eax,[r9+4]
 je .bad
 add r9,COMPANY_REMOTE_STRIDE
 inc ecx
 jmp .previous
.unassigned:
 cmp dword [rsi+8],0
 jne .bad
 cmp qword [rsi+16],0
 jne .bad
 cmp qword [rsi+24],0
 jne .bad
 cmp qword [rsi+32],0
 jne .bad
.next:
 add rsi,COMPANY_REMOTE_STRIDE
 inc r8d
 cmp r8d,COMPANY_REMOTE_COUNT
 jb .record
 ; Transfer proposals share the same atomic snapshot as their lease sources.
 xor r8d,r8d
.offer:
 cmp dword [rsi],1
 ja .bad
 cmp qword [rsi+40],0
 jne .bad
 cmp dword [rsi],0
 je .empty_offer
 cmp dword [rsi+36],0
 je .bad
 cmp dword [rsi+36],-1
 je .bad
 mov eax,[rsi+4]
 cmp eax,COMPANY_REMOTE_COUNT
 jae .bad
 cmp eax,r8d
 je .bad
 mov ecx,[rsi+32]
 cmp ecx,edx
 jbe .bad
 sub ecx,edx
 cmp ecx,COMPANY_TRANSFER_LIFETIME
 ja .bad
 imul eax,COMPANY_REMOTE_STRIDE
 lea r9,[rdi+rax]
 imul eax,r8d,COMPANY_REMOTE_STRIDE
 lea r10,[rdi+rax]
 mov eax,[rsi+8]
 cmp eax,[r10+4]
 jne .bad
 mov eax,[rsi+12]
 cmp eax,[r9+4]
 jne .bad
 cmp eax,COMPANY_REMOTE_KEY_LIMIT
 jae .bad
 cmp dword [r10+4],COMPANY_REMOTE_KEY_LIMIT
 jae .bad
 mov eax,[rsi+16]
 cmp eax,[r10+8]
 jne .bad
 mov eax,[rsi+20]
 cmp eax,[r9+8]
 jne .bad
 mov eax,[rsi+24]
 cmp eax,[r10+12]
 jne .bad
 mov eax,[rsi+28]
 cmp eax,[r9+12]
 jne .bad
 jmp .offer_next
.empty_offer:
 cmp qword [rsi],0
 jne .bad
 cmp qword [rsi+8],0
 jne .bad
 cmp qword [rsi+16],0
 jne .bad
 cmp qword [rsi+24],0
 jne .bad
 cmp dword [rsi+32],0
 jne .bad
.offer_next:
 add rsi,COMPANY_TRANSFER_STRIDE
 inc r8d
 cmp r8d,COMPANY_TRANSFER_PLAYERS
 jb .offer
 mov [net_company_tick],edx
 mov dword [net_company_valid],1
 mov rsi,rdi
 lea rdi,[net_company_records]
 mov ecx,COMPANY_REMOTE_COUNT*COMPANY_REMOTE_STRIDE/8
 rep movsq
 lea rdi,[net_company_transfers]
 mov ecx,COMPANY_TRANSFER_PLAYERS*COMPANY_TRANSFER_STRIDE/8
 rep movsq
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
; EDI player ->EAX key or-1. Bind display to current connected body generation
; and front. Reordered company/state packets hide ownership until corroborated.
net_company_for_player:
 cmp edi,COMPANY_REMOTE_COUNT
 jae .bad
 cmp dword [net_company_valid],1
 jne .bad
 imul eax,edi,COMPANY_REMOTE_STRIDE
 lea rsi,[net_company_records]
 add rsi,rax
 mov eax,[rsi+4]
 cmp eax,COMPANY_REMOTE_KEY_LIMIT
 jae .bad
 mov ecx,edi
 shl ecx,6
 lea rdx,[sim_players]
 add rdx,rcx
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .bad
 mov ecx,[rsi+8]
 cmp ecx,[rdx+PLAYER_GENERATION]
 jne .bad
 shr eax,8
 cmp eax,[rdx+PLAYER_FRONT]
 jne .bad
 mov eax,[rsi+4]
 ret
.bad: mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits

section .text
global net_company_offer
; EDI recipient,ESI requester ->EAX current exact sequence or-1.
net_company_offer:
 cmp edi,COMPANY_REMOTE_COUNT
 jae .bad
 cmp esi,COMPANY_REMOTE_COUNT
 jae .bad
 cmp edi,esi
 je .bad
 push rbx
 push r12
 sub rsp,8
 mov r12d,edi
 imul eax,esi,COMPANY_TRANSFER_STRIDE
 lea rbx,[net_company_transfers]
 add rbx,rax
 cmp dword [rbx],1
 jne .invalid
 cmp edi,[rbx+4]
 jne .invalid
 mov eax,[sim_tick_count]
 cmp eax,[rbx+32]
 jae .invalid
 mov edi,esi
 call net_company_for_player
 cmp eax,[rbx+8]
 jne .invalid
 mov edi,r12d
 call net_company_for_player
 cmp eax,[rbx+12]
 jne .invalid
 mov eax,[rbx+36]
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
