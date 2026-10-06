; Explicit two-human company exchange, bounded and entirely server-authoritative.
%include "schemas/company_transfer.inc"
%include "schemas/company_control.inc"
%include "schemas/player.inc"
default rel
extern sim_players,sim_tick_count,company_for_player,player_companies,company_controls
section .bss align=16
global company_transfers
company_transfers: resb COMPANY_TRANSFER_PLAYERS*COMPANY_TRANSFER_STRIDE
section .text
global company_transfer_init,company_transfer,company_transfer_tick,company_transfer_hash
company_transfer_init:
 lea rdi,[company_transfers]
 xor eax,eax
 mov ecx,COMPANY_TRANSFER_PLAYERS*COMPANY_TRANSFER_STRIDE/8
 rep stosq
 ret
; RDI proposal pointer: invalidate metadata, retain monotonic request identity.
.clear:
 mov eax,[rdi+36]
 pxor xmm0,xmm0
 movups [rdi],xmm0
 movups [rdi+16],xmm0
 movups [rdi+32],xmm0
 mov [rdi+36],eax
 ret
; EDI participant: invalidate every request involving this player.
.invalidate:
 mov r10d,edi
 lea rdi,[company_transfers]
 xor r11d,r11d
.scan:
 cmp r11d,r10d
 je .wipe
 cmp dword [rdi],1
 jne .next
 cmp [rdi+4],r10d
 jne .next
.wipe:
 sub rsp,8
 call company_transfer_init.clear
 add rsp,8
.next:
 add rdi,COMPANY_TRANSFER_STRIDE
 inc r11d
 cmp r11d,COMPANY_TRANSFER_PLAYERS
 jb .scan
 ret
; Validate full source identity, not just a state named pending.
; RDI proposal,ESI requester ->0 valid/-1 invalid. Preserve RDI/ESI, nonvolatile.
.valid:
 push rbx
 push r12
 push r13
 mov rbx,rdi
 mov r12d,esi
 cmp dword [rbx],1
 jne .bad
 cmp dword [rbx+4],COMPANY_TRANSFER_PLAYERS
 jae .bad
 cmp [rbx+4],r12d
 je .bad
 mov eax,[sim_tick_count]
 cmp eax,[rbx+32]
 jae .bad
 mov edi,r12d
 call company_for_player
 cmp eax,[rbx+8]
 jne .bad
 cmp eax,768
 jae .bad
 mov r13d,eax
 mov edi,[rbx+4]
 call company_for_player
 cmp eax,[rbx+12]
 jne .bad
 cmp eax,768
 jae .bad
 cmp eax,r13d
 je .bad
 ; Both current leases and current player fronts must corroborate snapshot.
 mov ecx,r12d
 shl ecx,4
 lea rdx,[player_companies]
 mov eax,[rdx+rcx+4]
 cmp eax,[rbx+16]
 jne .bad
 mov eax,[rdx+rcx+8]
 cmp eax,[rbx+24]
 jne .bad
 mov ecx,[rbx+4]
 shl ecx,4
 mov eax,[rdx+rcx+4]
 cmp eax,[rbx+20]
 jne .bad
 mov eax,[rdx+rcx+8]
 cmp eax,[rbx+28]
 jne .bad
 lea rdx,[sim_players]
 mov ecx,r12d
 shl ecx,6
 mov eax,[rbx+8]
 shr eax,8
 cmp eax,[rdx+rcx+PLAYER_FRONT]
 jne .bad
 mov ecx,[rbx+4]
 shl ecx,6
 mov eax,[rbx+12]
 shr eax,8
 cmp eax,[rdx+rcx+PLAYER_FRONT]
 jne .bad
 xor eax,eax
 jmp .done
.bad:
 mov eax,-1
.done:
 mov rdi,rbx
 mov esi,r12d
 pop r13
 pop r12
 pop rbx
 ret
; EDI actor,ESI other,EDX action0..3,ECX exact proposal sequence (0 propose).
; ->0 applied,-1 malformed,-2 stale/expired/unowned. No spending, no pose writes.
company_transfer:
 cmp edi,COMPANY_TRANSFER_PLAYERS
 jae .bad_leaf
 cmp esi,COMPANY_TRANSFER_PLAYERS
 jae .bad_leaf
 cmp edi,esi
 je .bad_leaf
 cmp edx,3
 ja .bad_leaf
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov r12d,edi
 mov r13d,esi
 mov r14d,edx
 mov r15d,ecx
 mov ebp,edi
 cmp edx,1
 je .recipient
 cmp edx,2
 jne .pointer
.recipient:
 mov ebp,esi
.pointer:
 imul eax,ebp,COMPANY_TRANSFER_STRIDE
 lea rbx,[company_transfers]
 add rbx,rax
 test r14d,r14d
 jz .propose
 cmp dword [rbx],1
 jne .stale
 cmp [rbx+36],r15d
 jne .stale
 mov eax,r13d
 cmp r14d,3
 je .target
 mov eax,r12d
.target:
 cmp eax,[rbx+4]
 jne .stale
 mov rdi,rbx
 mov esi,ebp
 call company_transfer_init.valid
 test eax,eax
 jnz .stale
 cmp r14d,1
 je .accept
 mov rdi,rbx
 call company_transfer_init.clear
 jmp .success
.propose:
 cmp dword [rbx+36],0xfffffffe
 jae .stale
 test r15d,r15d
 jnz .invalid
 mov edi,r12d
 call company_for_player
 cmp eax,768
 jae .stale
 mov [rsp],eax
 mov ecx,r12d
 shl ecx,6
 lea rdx,[sim_players]
 shr eax,8
 cmp eax,[rdx+rcx+PLAYER_FRONT]
 jne .stale
 mov edi,r13d
 call company_for_player
 cmp eax,768
 jae .stale
 cmp eax,[rsp]
 je .stale
 mov ebp,eax
 mov ecx,r13d
 shl ecx,6
 lea rdx,[sim_players]
 shr eax,8
 cmp eax,[rdx+rcx+PLAYER_FRONT]
 jne .stale
 mov eax,[sim_tick_count]
 add eax,COMPANY_TRANSFER_LIFETIME
 jc .stale
 ; Complete validation precedes all writes. Replaces own earlier proposal only.
 mov [rbx+32],eax
 mov dword [rbx],1
 mov [rbx+4],r13d
 mov eax,[rsp]
 mov [rbx+8],eax
 mov [rbx+12],ebp
 mov ecx,r12d
 shl ecx,4
 lea rdx,[player_companies]
 mov eax,[rdx+rcx+4]
 mov [rbx+16],eax
 mov eax,[rdx+rcx+8]
 mov [rbx+24],eax
 mov ecx,r13d
 shl ecx,4
 mov eax,[rdx+rcx+4]
 mov [rbx+20],eax
 mov eax,[rdx+rcx+8]
 mov [rbx+28],eax
 inc dword [rbx+36]
 jmp .success
.accept:
 ; Requester EBP, consenting recipient R12. Both retain a company atomically.
 lea r8,[player_companies]
 mov eax,ebp
 shl eax,4
 add r8,rax
 lea r9,[player_companies]
 mov eax,r12d
 shl eax,4
 add r9,rax
 mov eax,[rbx+12]
 mov [r8],eax
 mov eax,[rbx+8]
 mov [r9],eax
 inc dword [r8+8]
 inc dword [r9+8]
 lea r10,[company_controls]
 mov eax,[rbx+8]
 shl eax,5
 add r10,rax
 mov [r10],r12d
 mov eax,[rbx+20]
 mov [r10+4],eax
 lea r10,[company_controls]
 mov eax,[rbx+12]
 shl eax,5
 add r10,rax
 mov [r10],ebp
 mov eax,[rbx+16]
 mov [r10+4],eax
 ; Deployment/front authority follows the company, without teleporting humans.
 lea rdx,[sim_players]
 mov ecx,ebp
 shl ecx,6
 mov eax,[rbx+12]
 shr eax,8
 mov [rdx+rcx+PLAYER_FRONT],eax
 mov ecx,r12d
 shl ecx,6
 mov eax,[rbx+8]
 shr eax,8
 mov [rdx+rcx+PLAYER_FRONT],eax
 mov edi,ebp
 call company_transfer_init.invalidate
 mov edi,r12d
 call company_transfer_init.invalidate
.success:
 xor eax,eax
 jmp .return
.invalid:
 mov eax,-1
 jmp .return
.stale:
 mov eax,-2
.return:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
.bad_leaf:
 mov eax,-1
 ret
; Expire or invalidate stale generation/lease requests every authoritative tick.
company_transfer_tick:
 push rbx
 push r12
 sub rsp,8
 lea rbx,[company_transfers]
 xor r12d,r12d
.loop:
 cmp dword [rbx],1
 jne .next
 mov rdi,rbx
 mov esi,r12d
 call company_transfer_init.valid
 test eax,eax
 jz .next
 mov rdi,rbx
 call company_transfer_init.clear
.next:
 add rbx,COMPANY_TRANSFER_STRIDE
 inc r12d
 cmp r12d,COMPANY_TRANSFER_PLAYERS
 jb .loop
 add rsp,8
 pop r12
 pop rbx
 ret
company_transfer_hash:
 lea rsi,[company_transfers]
 mov ecx,COMPANY_TRANSFER_PLAYERS*COMPANY_TRANSFER_STRIDE
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
