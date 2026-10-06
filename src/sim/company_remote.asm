; Read-only company view consumed by the connected client, never authority AI.
%include "schemas/player.inc"
%include "schemas/company_remote.inc"
default rel
extern sim_players
section .bss align=16
global net_company_records,net_company_tick,net_company_valid
net_company_records: resb COMPANY_REMOTE_COUNT*COMPANY_REMOTE_STRIDE
net_company_tick: resd 1
net_company_valid: resd 1
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
 cmp dword [rsi+16],2
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
 mov [net_company_tick],edx
 mov dword [net_company_valid],1
 mov rsi,rdi
 lea rdi,[net_company_records]
 mov ecx,COMPANY_REMOTE_COUNT*COMPANY_REMOTE_STRIDE/8
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
