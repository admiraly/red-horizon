; Finite army rifle magazines and carried reserves, at authoritative30Hz.
%include "schemas/entity.inc"
%include "schemas/infantry_weapon.inc"
default rel
extern sim_entities,sim_count,sim_tick_count,sim_sites
extern depot_ammunition_take,terrain_height,world_los
section .bss align=64
global infantry_weapons
infantry_weapons: resb ENTITY_CAPACITY*INFANTRY_WEAPON_STRIDE
global infantry_shot_cooldowns
infantry_shot_cooldowns: resd ENTITY_CAPACITY
section .text
global infantry_weapon_shot,infantry_weapon_init,infantry_weapon_tick,infantry_weapon_fire,infantry_weapon_hash,infantry_weapon_resupply,infantry_weapon_resupply_tick
; EDI stable actor ->RDX own entity,R8 stock record, EAX0 valid or-1.
; Validity does not reset/refill or change state. No enemy reads.
record:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .invalid
 cmp edi,[sim_count]
 jae .invalid
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_KIND],0
 jne .invalid
 cmp dword [rdx+ENTITY_HP],0
 je .invalid
 cmp dword [rdx+ENTITY_GENERATION],0
 je .invalid
 cmp dword [rdx+ENTITY_SIDE],1
 ja .invalid
 cmp dword [rdx+ENTITY_FRONT],2
 ja .invalid
 lea r8,[infantry_weapons]
 add r8,rax
 xor eax,eax
 ret
.invalid:
 mov eax,-1
 ret
; RDX valid living infantry, R8 record. Only different body generation resets
; stocks, including initial births. Side/front/ownership changes do not refill.
birth:
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[r8]
 je .done
 mov [r8],eax
 mov dword [r8+4],INFANTRY_MAGAZINE
 mov dword [r8+8],INFANTRY_RESERVE
 mov qword [r8+12],0
 mov qword [r8+20],0
 mov dword [r8+28],0
 lea r9,[infantry_shot_cooldowns]
 mov dword [r9+rdi*4],0
.done:
 ret
; Explicit fresh-world initialization. Invalid count is atomic/no-op.
infantry_weapon_init:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 push rbx
 lea rdi,[infantry_weapons]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*INFANTRY_WEAPON_STRIDE/8
 rep stosq
 lea rdi,[infantry_shot_cooldowns]
 mov ecx,ENTITY_CAPACITY
 rep stosd
 xor ebx,ebx
.loop:
 cmp ebx,[sim_count]
 jae .done
 mov edi,ebx
 call record
 test eax,eax
 jnz .next
 call birth
.next:
 inc ebx
 jmp .loop
.done:
 pop rbx
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
; One bounded own-state pass. Dead actors freeze stocks/reload, while genuine
; newly born generations get declared initial equipment exactly once.
infantry_weapon_tick:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 push rbx
 xor ebx,ebx
.loop:
 cmp ebx,[sim_count]
 jae .done
 mov edi,ebx
 call record
 test eax,eax
 jnz .next
 call birth
 call stock_valid
 test eax,eax
 jnz .next
 lea r9,[infantry_shot_cooldowns]
 cmp dword [r9+rbx*4],INFANTRY_SHOT_TICKS
 ja .next
 cmp dword [r9+rbx*4],0
 je .cooldown_ready
 dec dword [r9+rbx*4]
.cooldown_ready:
 cmp dword [r8+12],0
 je .ready
 cmp dword [r8+4],0
 jne .next
 dec dword [r8+12]
 jnz .next
 ; Transfer rounds from finite carried reserves only when reload completes.
 mov eax,[r8+8]
 cmp eax,INFANTRY_MAGAZINE
 jbe .transfer
 mov eax,INFANTRY_MAGAZINE
.transfer:
 sub [r8+8],eax
 mov [r8+4],eax
 jmp .next
.ready:
 cmp dword [r8+4],0
 jne .next
 cmp dword [r8+8],0
 je .next
 mov dword [r8+12],INFANTRY_RELOAD_TICKS
.next:
 inc ebx
 jmp .loop
.done:
 pop rbx
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
; EDI actor ->0 one round spent,1 unavailable,-1 invalid. Caller must have
; already acquired a living enemy within range with actual clear LOS. This
; stock-only gate never applies damage, selects targets or invents ammunition.
infantry_weapon_fire:
 sub rsp,8
 call record
 add rsp,8
 test eax,eax
 jnz .done
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[r8]
 jne .invalid
 sub rsp,8
 call stock_valid
 add rsp,8
 test eax,eax
 jnz .invalid
 cmp dword [r8+12],0
 je .loaded
 cmp dword [r8+4],0
 jne .invalid
 jmp .unavailable
.loaded:
 cmp dword [r8+4],0
 je .unavailable
 dec dword [r8+4]
 inc dword [r8+16]
 cmp dword [r8+4],0
 jne .fired
 cmp dword [r8+8],0
 je .empty
 mov dword [r8+12],INFANTRY_RELOAD_TICKS
 jmp .fired
.empty:
 mov eax,[sim_tick_count]
 mov [r8+20],eax
.fired:
 xor eax,eax
.done:
 ret
.unavailable:
 mov eax,1
 ret
.invalid:
 mov eax,-1
 ret
; EDI actor: the sole gameplay shot gate for army and human rifle targets.
; Same return contract as stock-only fire. Caller acquires actual range/LOS.
; A successful finite shot starts8ticks; blocked/invalid requests change nothing.
infantry_weapon_shot:
 push rbx
 call record
 test eax,eax
 jnz .done
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[r8]
 jne .invalid
 call stock_valid
 test eax,eax
 jnz .invalid
 lea rbx,[infantry_shot_cooldowns]
 lea rbx,[rbx+rdi*4]
 cmp dword [rbx],INFANTRY_SHOT_TICKS
 ja .invalid
 cmp dword [rbx],0
 jne .unavailable
 call infantry_weapon_fire
 test eax,eax
 jnz .done
 mov dword [rbx],INFANTRY_SHOT_TICKS
.done:
 pop rbx
 ret
.unavailable:
 mov eax,1
 jmp .done
.invalid:
 mov eax,-1
 jmp .done
; R8 own record ->EAX0valid/-1 corrupt. No writes; RDX/R8 preserved.
; Per-body received rounds are bounded by all12 finite initial depot stores.
stock_valid:
 cmp dword [r8+4],INFANTRY_MAGAZINE
 ja .invalid
 cmp dword [r8+8],INFANTRY_RESERVE
 ja .invalid
 cmp dword [r8+12],INFANTRY_RELOAD_TICKS
 ja .invalid
 cmp dword [r8+24],INFANTRY_RECEIVED_LIMIT
 ja .invalid
 mov ecx,[r8+24]
 add ecx,INFANTRY_MAGAZINE+INFANTRY_RESERVE
 cmp [r8+16],ecx
 ja .invalid
 mov eax,[r8+4]
 add eax,[r8+8]
 add eax,[r8+16]
 cmp eax,ecx
 jne .invalid
 cmp dword [r8+12],0
 je .valid
 cmp dword [r8+4],0
 jne .invalid
.valid:
 xor eax,eax
 ret
.invalid:
 mov eax,-1
 ret
 ; Read-only carried-round query for supply-aware tactics. No birth/refill.
; EDI actor ->EAX0..120, or-1 invalid/dead/noninfantry/stale/corrupt stock.
; All nonvolatile GPRs preserved. Source pointers remain private authority data.
global infantry_weapon_rounds
infantry_weapon_rounds:
 sub rsp,8
 call record
 test eax,eax
 jnz .done
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[r8]
 jne .unknown
 call stock_valid
 test eax,eax
 jnz .done
 mov eax,[r8+4]
 add eax,[r8+8]
 jmp .done
.unknown:
 mov eax,-1
.done:
 add rsp,8
 ret

; Own/source XMM0/1XZ ->EAX1valid/0invalid; bounded finite map coordinates.
position_valid:
 ucomiss xmm0,xmm0
 jp .bad
 ucomiss xmm1,xmm1
 jp .bad
 comiss xmm0,[supply_zero]
 jb .bad
 comiss xmm1,[supply_zero]
 jb .bad
 comiss xmm0,[supply_max]
 ja .bad
 comiss xmm1,[supply_max]
 ja .bad
 mov eax,1
 ret
.bad:
 xor eax,eax
 ret
; EDI actor ->EAX rounds credited0..90/-1invalid. Single-thread transaction:
; living matching body, stock capacity, finite position, <=60m and clear actual
; ground/solid/wreck LOS, eligible owner/healthy/connected/uncontested depot.
; Debit precedes non-failing credit. No enemy reads, generation or pose changes.
; Reload remains necessary; credit goes only into reserves. At most one success
; per actor per authority tick. Every nonvolatile register preserved.
infantry_weapon_resupply:
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,32
 mov ebx,edi
 call record
 test eax,eax
 jnz .invalid
 mov r12,rdx
 mov r13,r8
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[r8]
 jne .invalid
 call stock_valid
 test eax,eax
 jnz .invalid
 mov eax,[sim_tick_count]
 cmp [r13+28],eax
 je .none
 mov r15d,INFANTRY_RESERVE
 sub r15d,[r13+8]
 jz .none
 mov eax,INFANTRY_RECEIVED_LIMIT
 sub eax,r15d
 cmp [r13+24],eax
 ja .invalid
 movss xmm0,[r12+ENTITY_X]
 movss xmm1,[r12+ENTITY_Z]
 call position_valid
 test eax,eax
 jz .invalid
 movss [rsp],xmm0
 movss [rsp+8],xmm1
 call terrain_height
 addss xmm0,[supply_eye]
 movss [rsp+4],xmm0
 xor r14d,r14d
.site:
 mov eax,r14d
 shl eax,5
 lea r10,[sim_sites]
 add r10,rax
 cmp dword [r10+16],1
 jne .next
 mov eax,[r12+ENTITY_SIDE]
 cmp [r10+8],eax
 jne .next
 cmp dword [r10+20],1
 jne .next
 cmp dword [r10+24],0
 je .next
 test dword [r10+28],4
 jnz .next
 movss xmm0,[r10]
 movss xmm1,[r10+4]
 call position_valid
 test eax,eax
 jz .next
 movaps xmm2,xmm0
 subss xmm2,[rsp]
 mulss xmm2,xmm2
 movaps xmm3,xmm1
 subss xmm3,[rsp+8]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 comiss xmm2,[supply_radius_sq]
 ja .next
 movss [rsp+12],xmm0
 movss [rsp+20],xmm1
 call terrain_height
 addss xmm0,[supply_eye]
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
 mov esi,[r12+ENTITY_SIDE]
 mov edx,r15d
 call depot_ammunition_take
 test eax,eax
 js .invalid
 jz .next
 add [r13+8],eax
 add [r13+24],eax
 mov edx,[sim_tick_count]
 mov [r13+28],edx
 mov dword [r13+20],0
 jmp .out
.next:
 inc r14d
 cmp r14d,12
 jb .site
.none:
 xor eax,eax
 jmp .out
.invalid:
 mov eax,-1
.out:
 add rsp,32
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
; Bounded physical-ID stagger once/second, after current operation connectivity.
; EAX0/-1invalid count; death/invalid actors do not debit stores.
infantry_weapon_resupply_tick:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 push rbx
 mov eax,[sim_tick_count]
 xor edx,edx
 mov ecx,INFANTRY_RESUPPLY_PERIOD
 div ecx
 xor ebx,ebx
 test edx,edx
 jz .loop
 mov ebx,INFANTRY_RESUPPLY_PERIOD
 sub ebx,edx
.loop:
 cmp ebx,[sim_count]
 jae .done
 mov edi,ebx
 call infantry_weapon_resupply
 add ebx,INFANTRY_RESUPPLY_PERIOD
 jmp .loop
.done:
 pop rbx
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
; RAX rolling checksum,R8 FNV prime; includes all persistent bounded records.
infantry_weapon_hash:
 lea rsi,[infantry_shot_cooldowns]
 mov ecx,ENTITY_CAPACITY*4
.cooldown_hash:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .cooldown_hash
 lea rsi,[infantry_weapons]
 mov ecx,ENTITY_CAPACITY*INFANTRY_WEAPON_STRIDE
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 ret
section .rodata
supply_zero: dd 0.0
supply_max: dd 8000.0
supply_radius_sq: dd INFANTRY_RESUPPLY_RADIUS_SQ
supply_eye: dd INFANTRY_RESUPPLY_EYE
section .note.GNU-stack noalloc noexec nowrite progbits
