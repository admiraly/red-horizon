; Primary human ownership for actual mixed ground cohorts; own-state only.
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/company_control.inc"
default rel
extern company_transfer_init,company_transfer_hash
extern sim_entities,sim_count,sim_players,sim_tick_count,terrain_blocked,sim_spend
section .bss align=64
global company_controls,player_companies
company_controls: resb COMPANY_CONTROL_SLOTS*COMPANY_CONTROL_STRIDE
player_companies: resb COMPANY_CONTROL_PLAYERS*16
section .rodata
zero: dd 0.0
maximum: dd 8000.0
infinity: dd 0x7f800000
homes: dd 1000.0,1300.0,1000.0,3900.0,1000.0,6500.0
section .text
global company_control_init,company_assign,company_release,company_for_player
 global company_control_order,company_control_goal,company_control_hash,company_redeploy
company_control_init:
 lea rdi,[company_controls]
 xor eax,eax
 mov ecx,COMPANY_CONTROL_SLOTS*COMPANY_CONTROL_STRIDE/4+COMPANY_CONTROL_PLAYERS*4
 rep stosd
 lea rdi,[company_controls]
 mov ecx,COMPANY_CONTROL_SLOTS
.records:
 mov dword [rdi],-1
 add rdi,COMPANY_CONTROL_STRIDE
 loop .records
 lea rdi,[player_companies]
 mov ecx,COMPANY_CONTROL_PLAYERS
.players:
 mov dword [rdi],-1
 add rdi,16
 loop .players
 jmp company_transfer_init
; EDI live ground actor ->EAX own cohort key, or-1. No enemy reads.
key:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 cmp edi,[sim_count]
 jae .bad
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .bad
 cmp dword [rdx+ENTITY_GENERATION],0
 je .bad
 cmp dword [rdx+ENTITY_KIND],2
 ja .bad
 cmp dword [rdx+ENTITY_SIDE],0
 jne .bad
 mov eax,[rdx+ENTITY_FRONT]
 cmp eax,2
 ja .bad
 shl eax,8
 mov ecx,edi
 shr ecx,7
 add eax,ecx
 ret
.bad: mov eax,-1
 ret
; EDI live player ->EAX key or-1. Validate both directions and generation.
company_for_player:
 cmp edi,COMPANY_CONTROL_PLAYERS
 jae .bad
 mov eax,edi
 shl eax,6
 lea rdx,[sim_players]
 add rdx,rax
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .bad
 mov eax,[rdx+PLAYER_GENERATION]
 test eax,eax
 jz .bad
 mov ecx,edi
 shl ecx,4
 lea rsi,[player_companies]
 add rsi,rcx
 cmp eax,[rsi+4]
 jne .bad
 mov ecx,[rsi]
 cmp ecx,COMPANY_CONTROL_SLOTS
 jae .bad
 mov r8d,ecx
 shl ecx,5
 lea r9,[company_controls]
 add r9,rcx
 cmp edi,[r9]
 jne .bad
 cmp eax,[r9+4]
 jne .bad
 mov eax,r8d
 ret
.bad: mov eax,-1
 ret
; EDI player,ESI requested front. Pick nearest unowned own ground cohort.
company_assign:
 cmp edi,COMPANY_CONTROL_PLAYERS
 jae .bad
 cmp esi,2
 ja .bad
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 push rbx
 push rbp
 push r12
 push r13
 push r14
 mov r12d,edi
 mov r13d,esi
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .failed
 cmp esi,[rbx+PLAYER_FRONT]
 jne .failed
 call company_for_player
 cmp eax,-1
 jne .already
 xor ebp,ebp
 mov r14d,-1
 movss xmm4,[infinity]
.loop:
 mov edi,ebp
 call key
 cmp eax,-1
 je .next
 mov ecx,eax
 shr ecx,8
 cmp ecx,r13d
 jne .next
 mov ecx,eax
 shl ecx,5
 lea rsi,[company_controls]
 cmp dword [rsi+rcx],-1
 jne .next
 movss xmm0,[rdx+ENTITY_X]
 subss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rdx+ENTITY_Z]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,xmm4
 jp .next
 jae .next ; ascending stable IDs break exact ties
 movaps xmm4,xmm0
 mov r14d,eax
.next:
 inc ebp
 cmp ebp,[sim_count]
 jb .loop
 cmp r14d,-1
 je .failed
 mov eax,r14d
 shl eax,5
 lea rdx,[company_controls]
 add rdx,rax
 mov [rdx],r12d
 mov eax,[rbx+PLAYER_GENERATION]
 mov [rdx+4],eax
 mov ecx,r12d
 shl ecx,4
 lea rdx,[player_companies]
 add rdx,rcx
 mov [rdx],r14d
 mov [rdx+4],eax
 inc dword [rdx+8]
 mov eax,r14d
.already:
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
.failed:
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
.bad: mov eax,-1
 ret
; Genuine completed redeploy only: retain the same company and intent while
; rebinding the lease from exactly the preceding body generation. No spend/refill.
company_redeploy:
 cmp edi,COMPANY_CONTROL_PLAYERS
 jae .done
 mov eax,edi
 shl eax,6
 lea rdx,[sim_players]
 add rdx,rax
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .done
 mov r8d,[rdx+PLAYER_GENERATION]
 mov eax,edi
 shl eax,4
 lea rsi,[player_companies]
 add rsi,rax
 mov eax,[rsi]
 cmp eax,COMPANY_CONTROL_SLOTS
 jae .done
 mov ecx,[rsi+4]
 inc ecx
 cmp ecx,r8d
 jne .done
 shl eax,5
 lea rdx,[company_controls]
 add rdx,rax
 cmp edi,[rdx]
 jne .done
 mov ecx,[rsi+4]
 cmp ecx,[rdx+4]
 jne .done
 mov [rsi+4],r8d
 mov [rdx+4],r8d
 inc dword [rsi+8]
.done:
 ret
; EDI player. Leave/generation recovery releases own lease and explicit intent.
company_release:
 cmp edi,COMPANY_CONTROL_PLAYERS
 jae .done
 mov eax,edi
 shl eax,4
 lea rsi,[player_companies]
 add rsi,rax
 mov eax,[rsi]
 cmp eax,COMPANY_CONTROL_SLOTS
 jae .clear
 shl eax,5
 lea rdx,[company_controls]
 add rdx,rax
 cmp edi,[rdx]
 jne .clear
 mov eax,[rsi+4]
 cmp eax,[rdx+4]
 jne .clear
 xorps xmm0,xmm0
 movups [rdx],xmm0
 movups [rdx+16],xmm0
 mov dword [rdx],-1
.clear:
 mov dword [rsi],-1
 mov dword [rsi+4],0
 inc dword [rsi+8]
.done:
 ret
; EDI player,ESI key,EDX0advance/1hold/2retreat,XMM0/1 desired point.
; ->0 accepted,-1invalid,-2ownership,-3funds. Validate before one atomic spend.
company_control_order:
 cmp esi,COMPANY_CONTROL_SLOTS
 jae .bad
 cmp edx,2
 ja .bad
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 ucomiss xmm1,[zero]
 jp .bad
 jb .bad
 ucomiss xmm1,[maximum]
 ja .bad
 push rbx
 sub rsp,32
 mov [rsp],edi
 mov [rsp+4],esi
 mov [rsp+8],edx
 movss [rsp+16],xmm0
 movss [rsp+20],xmm1
 call company_for_player
 cmp eax,[rsp+4]
 jne .ownership
 mov ebx,eax
 shl ebx,5
 lea rax,[company_controls]
 add rbx,rax
 xor edi,edi
 movss xmm0,[rsp+16]
 movss xmm1,[rsp+20]
 call terrain_blocked
 test eax,eax
 jnz .invalid
 xor edi,edi
 mov esi,COMPANY_CONTROL_COST
 call sim_spend
 test eax,eax
 jnz .funds
 mov eax,[rsp+8]
 mov [rbx+8],eax
 mov dword [rbx+12],1
 mov eax,[rsp+16]
 mov [rbx+16],eax
 mov eax,[rsp+20]
 mov [rbx+20],eax
 inc dword [rbx+24]
 mov eax,[sim_tick_count]
 mov [rbx+28],eax
 xor eax,eax
 jmp .out
.ownership: mov eax,-2
 jmp .out
.funds: mov eax,-3
 jmp .out
.invalid: mov eax,-1
.out:
 add rsp,32
 pop rbx
 ret
.bad: mov eax,-1
 ret
; EDI actor ->EAX0move/1hold/-1autonomous, XMM0/1 actual owned command goal.
company_control_goal:
 sub rsp,8
 call key
 add rsp,8
 cmp eax,-1
 je .done
 shl eax,5
 lea rsi,[company_controls]
 add rsi,rax
 cmp dword [rsi+12],1
 jne .auto
 cmp dword [rsi+8],2
 ja .auto
 mov ecx,[rsi]
 cmp ecx,COMPANY_CONTROL_PLAYERS
 jae .auto
 mov eax,ecx
 shl eax,6
 lea r8,[sim_players]
 add r8,rax
 cmp dword [r8+PLAYER_CONNECTED],1
 jne .auto
 mov eax,[r8+PLAYER_GENERATION]
 cmp eax,[rsi+4]
 jne .auto
 shl ecx,4
 lea r8,[player_companies]
 add r8,rcx
 cmp eax,[r8+4]
 jne .auto
 mov eax,[r8]
 shl eax,5
 lea rcx,[company_controls]
 add rcx,rax
 cmp rcx,rsi
 jne .auto
 cmp dword [rsi+8],1
 je .hold
 movss xmm0,[rsi+16]
 movss xmm1,[rsi+20]
 cmp dword [rsi+8],2
 jne .move
 mov eax,[rdx+ENTITY_FRONT]
 lea rcx,[homes]
 movss xmm0,[rcx+rax*8]
 movss xmm1,[rcx+rax*8+4]
.move: xor eax,eax
.done: ret
.hold: mov eax,1
 ret
.auto: mov eax,-1
 ret
company_control_hash:
 lea rsi,[company_controls]
 mov ecx,COMPANY_CONTROL_SLOTS*COMPANY_CONTROL_STRIDE+COMPANY_CONTROL_PLAYERS*16
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 jmp company_transfer_hash
section .note.GNU-stack noalloc noexec nowrite progbits
