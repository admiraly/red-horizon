; Client-only own-player ammunition report cache; never authorizes gameplay.
%include "schemas/player.inc"
%include "schemas/player_ammunition.inc"
default rel
extern sim_players,sim_tick_count
section .bss align=16
global net_player_ammunition_record,net_player_ammunition_tick,net_player_ammunition_valid
net_player_ammunition_record: resb PLAYER_AMMUNITION_REPORT_BYTES
net_player_ammunition_tick: resd 1
net_player_ammunition_valid: resd 1
section .text
global net_player_ammunition_reset,net_player_ammunition_receive,net_player_ammunition_report
net_player_ammunition_reset:
 lea rdi,[net_player_ammunition_record]
 xor eax,eax
 mov ecx,(PLAYER_AMMUNITION_REPORT_BYTES+8)/4
 rep stosd
 ret
; RDI readable40-byte payload,ESI bytes,EDX packet tick,ECX current recipient.
; Transport authenticates server/session; complete validation before mutation.
net_player_ammunition_receive:
 test rdi,rdi
 jz .bad
 cmp esi,PLAYER_AMMUNITION_REPORT_BYTES
 jne .bad
 cmp ecx,PLAYER_CAPACITY
 jae .bad
 cmp [rdi],ecx
 jne .bad
 cmp dword [rdi+4],0
 je .bad
 cmp dword [rdi+36],0
 jne .bad
 cmp dword [rdi+32],0
 je .unknown
 cmp dword [rdi+32],PLAYER_AMMUNITION_KNOWN
 jne .bad
 cmp dword [rdi+8],PLAYER_AMMUNITION_MAGAZINE
 ja .bad
 cmp dword [rdi+12],PLAYER_AMMUNITION_RESERVE
 ja .bad
 cmp dword [rdi+20],PLAYER_AMMUNITION_RECEIVED_LIMIT
 ja .bad
 cmp dword [rdi+28],PLAYER_AMMUNITION_INITIAL
 jne .bad
 mov eax,[rdi+20]
 test eax,eax
 jz .no_receipt
 cmp dword [rdi+24],0
 je .bad
 cmp [rdi+24],edx
 ja .bad
 jmp .conservation
.no_receipt:
 cmp dword [rdi+24],0
 jne .bad
.conservation:
 add eax,PLAYER_AMMUNITION_INITIAL
 cmp [rdi+16],eax
 ja .bad
 mov r8d,[rdi+8]
 add r8d,[rdi+12]
 add r8d,[rdi+16]
 cmp eax,r8d
 jne .bad
 jmp .ordered
.unknown:
 cmp qword [rdi+8],0
 jne .bad
 cmp qword [rdi+16],0
 jne .bad
 cmp qword [rdi+24],0
 jne .bad
.ordered:
 cmp dword [net_player_ammunition_valid],0
 je .apply
 cmp edx,[net_player_ammunition_tick]
 jbe .bad
 ; Reordered older bodies cannot replace a later-generation cache, even when
 ; their packet tick was forged larger in a static validation fixture.
 mov eax,[rdi+4]
 cmp eax,[net_player_ammunition_record+4]
 jb .bad
.apply:
 mov rsi,rdi
 lea rdi,[net_player_ammunition_record]
 mov ecx,PLAYER_AMMUNITION_REPORT_BYTES/4
 rep movsd
 mov [net_player_ammunition_tick],edx
 mov dword [net_player_ammunition_valid],1
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
; EDI own player,RSI disjoint caller buffer,EDX bytes>=40 ->0/-1.
; Corroborate current connected body and magazine; unavailable leaves output.
net_player_ammunition_report:
 test rsi,rsi
 jz .bad
 cmp edx,PLAYER_AMMUNITION_REPORT_BYTES
 jb .bad
 cmp edi,PLAYER_CAPACITY
 jae .bad
 cmp dword [net_player_ammunition_valid],1
 jne .bad
 cmp [net_player_ammunition_record],edi
 jne .bad
 mov eax,[sim_tick_count]
 sub eax,[net_player_ammunition_tick]
 cmp eax,PLAYER_AMMUNITION_REPORT_MAX_AGE
 ja .bad
 mov eax,edi
 shl eax,6
 lea rdx,[sim_players]
 add rdx,rax
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .bad
 cmp dword [rdx+PLAYER_FRONT],2
 ja .bad
 cmp dword [rdx+PLAYER_HP],100
 ja .bad
 mov eax,[rdx+PLAYER_GENERATION]
 cmp eax,[net_player_ammunition_record+4]
 jne .bad
 cmp dword [net_player_ammunition_record+32],PLAYER_AMMUNITION_KNOWN
 jne .publish
 cmp dword [rdx+PLAYER_HP],0
 je .bad
 mov eax,[rdx+PLAYER_AMMO]
 cmp eax,[net_player_ammunition_record+8]
 jne .bad
.publish:
 mov rdi,rsi
 lea rsi,[net_player_ammunition_record]
 mov ecx,PLAYER_AMMUNITION_REPORT_BYTES/8
 rep movsq
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
