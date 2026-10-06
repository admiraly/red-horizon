; Finite army rifle magazines and carried reserves, at authoritative30Hz.
%include "schemas/entity.inc"
%include "schemas/infantry_weapon.inc"
default rel
extern sim_entities,sim_count,sim_tick_count
section .bss align=64
global infantry_weapons
infantry_weapons: resb ENTITY_CAPACITY*INFANTRY_WEAPON_STRIDE
section .text
global infantry_weapon_init,infantry_weapon_tick,infantry_weapon_fire,infantry_weapon_hash
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
 ; Corrupt stocks never become an automatic source of ammunition.
 cmp dword [r8+4],INFANTRY_MAGAZINE
 ja .next
 cmp dword [r8+8],INFANTRY_RESERVE
 ja .next
 cmp dword [r8+12],INFANTRY_RELOAD_TICKS
 ja .next
 cmp dword [r8+16],INFANTRY_MAGAZINE+INFANTRY_RESERVE
 ja .next
 mov eax,[r8+4]
 add eax,[r8+8]
 add eax,[r8+16]
 cmp eax,INFANTRY_MAGAZINE+INFANTRY_RESERVE
 jne .next
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
 cmp dword [r8+4],INFANTRY_MAGAZINE
 ja .invalid
 cmp dword [r8+8],INFANTRY_RESERVE
 ja .invalid
 cmp dword [r8+12],INFANTRY_RELOAD_TICKS
 ja .invalid
 cmp dword [r8+16],INFANTRY_MAGAZINE+INFANTRY_RESERVE
 ja .invalid
 mov eax,[r8+4]
 add eax,[r8+8]
 add eax,[r8+16]
 cmp eax,INFANTRY_MAGAZINE+INFANTRY_RESERVE
 jne .invalid
 cmp dword [r8+12],0
 je .loaded
 cmp dword [r8+4],0
 jne .invalid
 jmp .unavailable
.loaded:
 cmp dword [r8+4],0
 je .unavailable
 cmp dword [r8+16],INFANTRY_MAGAZINE+INFANTRY_RESERVE
 jae .invalid
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
; RAX rolling checksum,R8 FNV prime; includes all persistent bounded records.
infantry_weapon_hash:
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
section .note.GNU-stack noalloc noexec nowrite progbits
