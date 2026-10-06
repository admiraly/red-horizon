; Read-only server-owned finite depot cache; no stock debit or world mutation.
%include "schemas/depot_supply.inc"
%include "schemas/depot_ammunition.inc"
%include "schemas/player.inc"
default rel
extern sim_players,sim_sites,sim_tick_count
section .bss align=16
global net_depot_records,net_depot_tick,net_depot_valid
net_depot_records: resb DEPOT_SUPPLY_BYTES
net_depot_tick: resd 1
net_depot_valid: resd 1
section .text
global net_depot_reset,net_depot_receive,net_depot_report
net_depot_reset:
 lea rdi,[net_depot_records]
 xor eax,eax
 mov ecx,(DEPOT_SUPPLY_BYTES+8)/8
 rep stosq
 ret
; RDI readable304 bytes,ESI exact bytes,EDX tick,ECX recipient ->0/-1.
net_depot_receive:
 test rdi,rdi
 jz .bad
 cmp esi,DEPOT_SUPPLY_BYTES
 jne .bad
 cmp ecx,PLAYER_CAPACITY
 jae .bad
 cmp [rdi],ecx
 jne .bad
 cmp dword [rdi+4],0
 je .bad
 cmp dword [rdi+8],DEPOT_SUPPLY_COUNT
 ja .bad
 cmp dword [rdi+12],0
 jne .bad
 cmp dword [net_depot_valid],0
 je .validate
 cmp edx,[net_depot_tick]
 jbe .bad
.validate:
 mov r10d,[rdi+8]
 lea rsi,[rdi+DEPOT_SUPPLY_HEADER]
 xor r8d,r8d
 mov r11d,-1
.record:
 cmp r8d,r10d
 jae .padding
 mov eax,[rsi]
 cmp eax,DEPOT_SUPPLY_COUNT
 jae .bad
 test r8d,r8d
 jz .index
 cmp eax,r11d
 jbe .bad
.index:
 mov r11d,eax
 cmp dword [rsi+20],0
 jne .bad
 mov r9d,[rsi+16]
 cmp r9d,31
 ja .bad
 test r9d,DEPOT_SUPPLY_KNOWN
 jz .unknown
 mov eax,[rsi+12]
 test eax,eax
 jz .zero
 cmp eax,DEPOT_AMMUNITION_INITIAL
 jne .bad
 cmp dword [rsi+4],DEPOT_AMMUNITION_INITIAL
 ja .bad
 cmp dword [rsi+8],DEPOT_AMMUNITION_INITIAL
 ja .bad
 mov eax,[rsi+4]
 add eax,[rsi+8]
 cmp eax,DEPOT_AMMUNITION_INITIAL
 jne .bad
 jmp .available
.zero:
 cmp qword [rsi+4],0
 jne .bad
 jmp .available
.unknown:
 cmp qword [rsi+4],0
 jne .bad
 cmp dword [rsi+12],0
 jne .bad
.available:
 mov eax,r9d
 and eax,15
 cmp eax,DEPOT_SUPPLY_KNOWN|DEPOT_SUPPLY_CONNECTED
 jne .unavailable
 cmp dword [rsi+4],0
 je .unavailable
 test r9d,DEPOT_SUPPLY_AVAILABLE
 jz .bad
 jmp .next
.unavailable:
 test r9d,DEPOT_SUPPLY_AVAILABLE
 jnz .bad
.next:
 add rsi,DEPOT_SUPPLY_RECORD
 inc r8d
 jmp .record
.padding:
 cmp r8d,DEPOT_SUPPLY_COUNT
 jae .apply
 cmp qword [rsi],0
 jne .bad
 cmp qword [rsi+8],0
 jne .bad
 cmp qword [rsi+16],0
 jne .bad
 add rsi,DEPOT_SUPPLY_RECORD
 inc r8d
 jmp .padding
.apply:
 mov rsi,rdi
 lea rdi,[net_depot_records]
 mov ecx,DEPOT_SUPPLY_BYTES/8
 rep movsq
 mov [net_depot_tick],edx
 mov dword [net_depot_valid],1
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
; Display requires current connected owner generation and corroborating site
; owner/role/connectivity/contest/health. Reordering hides until coherent.
; EDIplayer,RSI disjoint writable304-byte output,EDXcapacity ->0/-1.
net_depot_report:
 test rsi,rsi
 jz .bad
 cmp edx,DEPOT_SUPPLY_BYTES
 jb .bad
 cmp edi,PLAYER_CAPACITY
 jae .bad
 cmp dword [net_depot_valid],1
 jne .bad
 cmp edi,[net_depot_records]
 jne .bad
 mov eax,edi
 shl eax,6
 lea rdx,[sim_players]
 add rdx,rax
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .bad
 cmp dword [rdx+PLAYER_FRONT],2
 ja .bad
 mov eax,[rdx+PLAYER_GENERATION]
 cmp eax,[net_depot_records+4]
 jne .bad
 mov eax,[sim_tick_count]
 cmp eax,[net_depot_tick]
 jb .bad
 sub eax,[net_depot_tick]
 cmp eax,DEPOT_SUPPLY_MAX_AGE
 ja .bad
 mov r11,rsi
 lea rdi,[net_depot_records+16]
 mov ecx,[net_depot_records+8]
 xor r9d,r9d
 lea rdx,[sim_sites]
.site:
 cmp r9d,DEPOT_SUPPLY_COUNT
 jae .complete
 cmp dword [rdx+8],0
 jne .next_site
 cmp dword [rdx+16],1
 jne .next_site
 test ecx,ecx
 jz .bad
 cmp [rdi],r9d
 jne .bad
 xor r8d,r8d
 cmp dword [rdx+20],1
 jne .contest
 or r8d,DEPOT_SUPPLY_CONNECTED
.contest:
 test dword [rdx+28],4
 jz .health
 or r8d,DEPOT_SUPPLY_CONTESTED
.health:
 cmp dword [rdx+24],0
 jne .compare
 or r8d,DEPOT_SUPPLY_DESTROYED
.compare:
 mov eax,[rdi+16]
 and eax,14
 cmp eax,r8d
 jne .bad
 add rdi,DEPOT_SUPPLY_RECORD
 dec ecx
.next_site:
 inc r9d
 add rdx,32
 jmp .site
.complete:
 test ecx,ecx
 jnz .bad
.publish:
 lea rsi,[net_depot_records]
 mov rdi,r11
 mov ecx,DEPOT_SUPPLY_BYTES/8
 rep movsq
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
