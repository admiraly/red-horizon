; Finite per-body player rifle stock; no movement, damage or automatic birth.
%include "schemas/player.inc"
%include "schemas/player_ammunition.inc"
%include "schemas/depot_ammunition.inc"
default rel
extern sim_players,sim_sites,sim_tick_count,sim_player_vehicle
extern terrain_height,world_los,depot_ammunition_take
section .bss align=64
global player_ammunition,player_ammunition_receipts
player_ammunition: resb PLAYER_CAPACITY*PLAYER_AMMUNITION_STRIDE
player_ammunition_receipts: resq 1
section .rodata
zero: dd 0.0
maximum: dd 8000.0
eye: dd 1.0
height_min: dd -1000.0
height_max: dd 1000.0
radius_sq: dd PLAYER_AMMUNITION_SUPPLY_RADIUS_SQ
section .text
global player_ammunition_init,player_ammunition_equip,player_ammunition_reserve
 global player_ammunition_fire,player_ammunition_reload_finish,player_ammunition_resupply,player_ammunition_hash
player_ammunition_init:
 lea rdi,[player_ammunition]
 xor eax,eax
 mov ecx,(PLAYER_CAPACITY*PLAYER_AMMUNITION_STRIDE+8)/8
 rep stosq
 ret
; EDI player ->RDX player,R8 stock,0valid or-1; private leaf, no mutation.
body:
 cmp edi,PLAYER_CAPACITY
 jae .bad
 mov eax,edi
 shl eax,6
 lea rdx,[sim_players]
 add rdx,rax
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .bad
 cmp dword [rdx+PLAYER_HP],0
 je .bad
 cmp dword [rdx+PLAYER_HP],100
 ja .bad
 cmp dword [rdx+PLAYER_FRONT],2
 ja .bad
 cmp dword [rdx+PLAYER_GENERATION],0
 je .bad
 shr eax,1
 lea r8,[player_ammunition]
 add r8,rax
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
stock:
 call body
 test eax,eax
 jnz .bad
 mov eax,[rdx+PLAYER_GENERATION]
 cmp eax,[r8]
 jne .bad
 cmp dword [r8+20],PLAYER_AMMUNITION_INITIAL
 jne .bad
 cmp qword [r8+24],0
 jne .bad
 cmp dword [rdx+PLAYER_AMMO],PLAYER_AMMUNITION_MAGAZINE
 ja .bad
 cmp dword [rdx+PLAYER_RELOAD],PLAYER_AMMUNITION_RELOAD_TICKS
 ja .bad
 cmp dword [r8+4],PLAYER_AMMUNITION_RESERVE
 ja .bad
 cmp dword [r8+12],PLAYER_AMMUNITION_RECEIVED_LIMIT
 ja .bad
 cmp dword [r8+8],PLAYER_AMMUNITION_INITIAL+PLAYER_AMMUNITION_RECEIVED_LIMIT
 ja .bad
 cmp qword [player_ammunition_receipts],PLAYER_AMMUNITION_RECEIVED_LIMIT
 ja .bad
 mov eax,[r8+12]
 cmp rax,[player_ammunition_receipts]
 ja .bad
 test eax,eax
 jz .no_receipt
 cmp dword [r8+16],0
 je .bad
 mov eax,[sim_tick_count]
 cmp [r8+16],eax
 ja .bad
 jmp .conservation
.no_receipt:
 cmp dword [r8+16],0
 jne .bad
.conservation:
 mov eax,[rdx+PLAYER_AMMO]
 add eax,[r8+4]
 add eax,[r8+8]
 mov ecx,[r8+12]
 add ecx,PLAYER_AMMUNITION_INITIAL
 cmp eax,ecx
 jne .bad
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
; Genuine successful spawn caller only. 1new equipment,0same valid body,-1bad.
; Same-generation corruption cannot reset stock. No queries call this function.
player_ammunition_equip:
 call body
 test eax,eax
 jnz .bad
 mov eax,[rdx+PLAYER_GENERATION]
 cmp eax,[r8]
 je stock
 cmp dword [rdx+PLAYER_AMMO],PLAYER_AMMUNITION_MAGAZINE
 jne .bad
 cmp dword [rdx+PLAYER_RELOAD],0
 jne .bad
 mov [r8],eax
 mov dword [r8+4],PLAYER_AMMUNITION_RESERVE
 mov qword [r8+8],0
 mov qword [r8+16],0
 mov dword [r8+20],PLAYER_AMMUNITION_INITIAL
 mov qword [r8+24],0
 mov eax,1
 ret
.bad: mov eax,-1
 ret
player_ammunition_reserve:
 call stock
 test eax,eax
 jnz .return
 mov eax,[r8+4]
.return: ret
; 1consumed,0empty/reloading,-1unknown. Single-thread debit and spent count.
player_ammunition_fire:
 call stock
 test eax,eax
 jnz .return
 cmp dword [rdx+PLAYER_RELOAD],0
 jne .return
 cmp dword [rdx+PLAYER_AMMO],0
 je .return
 dec dword [rdx+PLAYER_AMMO]
 inc dword [r8+8]
 mov eax,1
.return: ret
; Call after real countdown reaches0. Transfer only existing reserve into room.
player_ammunition_reload_finish:
 call stock
 test eax,eax
 jnz .return
 cmp dword [rdx+PLAYER_RELOAD],0
 jne .return
 mov eax,PLAYER_AMMUNITION_MAGAZINE
 sub eax,[rdx+PLAYER_AMMO]
 cmp eax,[r8+4]
 jbe .transfer
 mov eax,[r8+4]
.transfer:
 sub [r8+4],eax
 add [rdx+PLAYER_AMMO],eax
.return: ret
position:
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm1,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 ucomiss xmm1,[maximum]
 ja .bad
 mov eax,1
 ret
.bad: xor eax,eax
 ret
; Living on-foot player, real ground/solid/wreck LOS and <=60m, reserve credit.
; Debit first, no refill or ownership changes; at most one success per tick.
player_ammunition_resupply:
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,32
 mov ebx,edi
 call stock
 test eax,eax
 jnz .invalid
 mov r12,rdx
 mov r13,r8
 lea rax,[sim_player_vehicle]
 cmp dword [rax+rbx*4],-1
 jne .none
 mov eax,[sim_tick_count]
 cmp [r13+16],eax
 je .none
 mov r15d,PLAYER_AMMUNITION_RESERVE
 sub r15d,[r13+4]
 jz .none
 mov eax,PLAYER_AMMUNITION_RECEIVED_LIMIT
 sub eax,r15d
 cmp [r13+12],eax
 ja .invalid
 mov ecx,PLAYER_AMMUNITION_RECEIVED_LIMIT
 sub ecx,r15d
 cmp [player_ammunition_receipts],rcx
 ja .invalid
 movss xmm2,[r12+PLAYER_Y]
 ucomiss xmm2,[height_min]
 jp .invalid
 jb .invalid
 ucomiss xmm2,[height_max]
 ja .invalid
 movss xmm0,[r12+PLAYER_X]
 movss xmm1,[r12+PLAYER_Z]
 call position
 test eax,eax
 jz .invalid
 movss [rsp],xmm0
 movss [rsp+8],xmm1
 call terrain_height
 addss xmm0,[eye]
 movss [rsp+4],xmm0
 xor r14d,r14d
.site:
 mov eax,r14d
 shl eax,5
 lea r10,[sim_sites]
 add r10,rax
 cmp dword [r10+8],0
 jne .next
 cmp dword [r10+16],1
 jne .next
 cmp dword [r10+20],1
 jne .next
 cmp dword [r10+24],0
 je .next
 test dword [r10+28],4
 jnz .next
 movss xmm0,[r10]
 movss xmm1,[r10+4]
 call position
 test eax,eax
 jz .next
 movaps xmm2,xmm0
 subss xmm2,[rsp]
 mulss xmm2,xmm2
 movaps xmm3,xmm1
 subss xmm3,[rsp+8]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 comiss xmm2,[radius_sq]
 ja .next
 movss [rsp+12],xmm0
 movss [rsp+20],xmm1
 call terrain_height
 addss xmm0,[eye]
 movss [rsp+16],xmm0
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
 call world_los
 test eax,eax
 jz .next
 mov edi,r14d
 xor esi,esi
 mov edx,r15d
 call depot_ammunition_take
 test eax,eax
 js .invalid
 jz .next
 add [r13+4],eax
 add [r13+12],eax
 add [player_ammunition_receipts],rax
 mov edx,[sim_tick_count]
 mov [r13+16],edx
 jmp .out
.next:
 inc r14d
 cmp r14d,DEPOT_AMMUNITION_SITES
 jb .site
.none: xor eax,eax
 jmp .out
.invalid: mov eax,-1
.out:
 add rsp,32
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
player_ammunition_hash:
 lea rsi,[player_ammunition]
 mov ecx,PLAYER_CAPACITY*PLAYER_AMMUNITION_STRIDE+8
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 ret
global player_ammunition_report
; EDI own player,RSI disjoint caller buffer,EDX capacity>=40 ->0/-1.
; Atomic staged read-only report; valid connected body with unknown stock gets
; explicit all-zero quantities/flags, never a fabricated empty/full reserve.
; payload: player0,body generation4,magazine8,reserve12,spent16,received20,
; last supply tick24,initial28,KNOWN flag32,reserved0 at36.
player_ammunition_report:
 push rbx
 push r12
 push r13
 sub rsp,48
 test rsi,rsi
 jz .bad
 cmp edx,PLAYER_AMMUNITION_REPORT_BYTES
 jb .bad
 cmp edi,PLAYER_CAPACITY
 jae .bad
 mov r12,rsi
 mov ebx,edi
 mov eax,edi
 shl eax,6
 lea r13,[sim_players]
 add r13,rax
 cmp dword [r13+PLAYER_CONNECTED],1
 jne .bad
 cmp dword [r13+PLAYER_HP],100
 ja .bad
 cmp dword [r13+PLAYER_FRONT],2
 ja .bad
 mov ecx,[r13+PLAYER_GENERATION]
 test ecx,ecx
 jz .bad
 xor eax,eax
 mov [rsp],rax
 mov [rsp+8],rax
 mov [rsp+16],rax
 mov [rsp+24],rax
 mov [rsp+32],rax
 mov [rsp],ebx
 mov [rsp+4],ecx
 mov edi,ebx
 call stock
 test eax,eax
 jnz .publish
 mov eax,[r13+PLAYER_AMMO]
 mov [rsp+8],eax
 mov eax,[r8+4]
 mov [rsp+12],eax
 mov eax,[r8+8]
 mov [rsp+16],eax
 mov eax,[r8+12]
 mov [rsp+20],eax
 mov eax,[r8+16]
 mov [rsp+24],eax
 mov eax,[r8+20]
 mov [rsp+28],eax
 mov dword [rsp+32],PLAYER_AMMUNITION_KNOWN
.publish:
 mov rdi,r12
 mov rsi,rsp
 mov ecx,PLAYER_AMMUNITION_REPORT_BYTES/8
 rep movsq
 xor eax,eax
 jmp .done
.bad: mov eax,-1
.done:
 add rsp,48
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
