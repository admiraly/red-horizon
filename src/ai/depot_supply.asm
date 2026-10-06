; Read-only finite physical depot inventory report. No regeneration or debit.
%include "schemas/player.inc"
%include "schemas/depot_ammunition.inc"
%include "schemas/depot_supply.inc"
default rel
extern sim_players,sim_sites,depot_ammunition
section .text
global depot_supply_report
; EDI player,RSI disjoint caller-owned writable output,EDXbytes>=304 ->0/-1.
; Sequential authority safe point. Failure preserves output; success writes304.
; Only allied currently owned role1 sites; never reads enemy inventory records.
depot_supply_report:
 cmp edi,PLAYER_CAPACITY
 jae .bad
 test rsi,rsi
 jz .bad
 cmp edx,DEPOT_SUPPLY_BYTES
 jb .bad
 mov eax,edi
 shl eax,6
 lea rdx,[sim_players]
 add rdx,rax
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .bad
 cmp dword [rdx+PLAYER_GENERATION],0
 je .bad
 cmp dword [rdx+PLAYER_FRONT],2
 ja .bad
 sub rsp,DEPOT_SUPPLY_BYTES+8
 mov r11,rsi
 mov r10d,edi
 mov r9d,[rdx+PLAYER_GENERATION]
 mov rdi,rsp
 xor eax,eax
 mov ecx,DEPOT_SUPPLY_BYTES/8
 rep stosq
 mov [rsp],r10d
 mov [rsp+4],r9d
 lea rdi,[rsp+DEPOT_SUPPLY_HEADER]
 lea rsi,[sim_sites]
 lea rdx,[depot_ammunition]
 xor r8d,r8d
.site:
 cmp dword [rsi+8],0
 jne .next
 cmp dword [rsi+16],1
 jne .next
 mov [rdi],r8d
 xor r9d,r9d
 cmp dword [rsi+20],1
 jne .contest
 or r9d,DEPOT_SUPPLY_CONNECTED
.contest:
 test dword [rsi+28],4
 jz .health
 or r9d,DEPOT_SUPPLY_CONTESTED
.health:
 cmp dword [rsi+24],0
 jne .inventory
 or r9d,DEPOT_SUPPLY_DESTROYED
.inventory:
 cmp dword [rdx+12],0
 jne .unknown
 mov eax,[rdx+8]
 cmp eax,DEPOT_AMMUNITION_INITIAL
 je .seeded
 test eax,eax
 jnz .unknown
 cmp qword [rdx],0
 jne .unknown
 jmp .known
.seeded:
 cmp dword [rdx],DEPOT_AMMUNITION_INITIAL
 ja .unknown
 cmp dword [rdx+4],DEPOT_AMMUNITION_INITIAL
 ja .unknown
 mov eax,[rdx]
 add eax,[rdx+4]
 cmp eax,DEPOT_AMMUNITION_INITIAL
 jne .unknown
.known:
 or r9d,DEPOT_SUPPLY_KNOWN
 mov rax,[rdx]
 mov [rdi+4],rax
 mov eax,[rdx+8]
 mov [rdi+12],eax
 cmp dword [rdx],0
 je .unknown
 cmp r9d,DEPOT_SUPPLY_KNOWN|DEPOT_SUPPLY_CONNECTED
 jne .unknown
 or r9d,DEPOT_SUPPLY_AVAILABLE
.unknown:
 mov [rdi+16],r9d
 inc dword [rsp+8]
 add rdi,DEPOT_SUPPLY_RECORD
.next:
 inc r8d
 add rsi,32
 add rdx,DEPOT_AMMUNITION_STRIDE
 cmp r8d,DEPOT_SUPPLY_COUNT
 jb .site
 mov rsi,rsp
 mov rdi,r11
 mov ecx,DEPOT_SUPPLY_BYTES/8
 rep movsq
 add rsp,DEPOT_SUPPLY_BYTES+8
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
