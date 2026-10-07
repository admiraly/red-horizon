; Finite per-generation sortie fuel. Fixed private records; NASM/SysV only.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_flight.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,sim_tick_count
section .bss align=64
global sim_air_fuel
sim_air_fuel: resb ENTITY_CAPACITY*16 ; generation, units, last tick, role+1
section .rodata
capacities: dd AIR_FUEL_BOMBER_UNITS,AIR_FUEL_FIGHTER_UNITS
section .text
global air_fuel_init,air_fuel_step,air_fuel_status,air_fuel_hash
air_fuel_init:
 lea rdi,[sim_air_fuel]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*4
 rep stosd
 ret
; Pure validity/address query; never clobbers XMM registers or nonvolatile GPRs.
valid:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 cmp edi,[sim_count]
 jae .bad
 cmp edi,ENTITY_CAPACITY
 jae .bad
 mov eax,edi
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 shl eax,1
 lea r9,[sim_aircraft]
 add r9,rax
 cmp dword [r8+ENTITY_HP],0
 je .bad
 cmp dword [r8+ENTITY_KIND],3
 jne .bad
 cmp dword [r8+ENTITY_SIDE],1
 ja .bad
 cmp dword [r8+ENTITY_FRONT],2
 ja .bad
 mov eax,[r8+ENTITY_GENERATION]
 test eax,eax
 jz .bad
 cmp eax,[r9+AIR_GENERATION]
 jne .bad
 test dword [r9+AIR_FLAGS],AIR_ACTIVE
 jz .bad
 mov eax,[r9+AIR_ROLE]
 cmp eax,1
 ja .bad
 lea r10,[capacities]
 mov r11d,[r10+rax*4]
 mov eax,edi
 shl eax,4
 lea r10,[sim_air_fuel]
 add r10,rax
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
; EDI owned body ->0normal/missing,1reserve,2empty,-1invalid. Read-only.
air_fuel_status:
 sub rsp,8
 call valid
 add rsp,8
 test eax,eax
 js .done
 mov eax,[r8+ENTITY_GENERATION]
 cmp eax,[r10]
 jne .missing
 mov eax,[r9+AIR_ROLE]
 inc eax
 cmp eax,[r10+12]
 jne .bad
 mov eax,[r10+4]
 cmp eax,r11d
 ja .bad
 test eax,eax
 jz .empty
 cmp eax,AIR_FUEL_RESERVE_UNITS
 jbe .reserve
.missing:
 xor eax,eax
.done: ret
.reserve: mov eax,1
 ret
.empty: mov eax,2
 ret
.bad: mov eax,-1
 ret
; EDI owned body ->same status. Birth refills once; duplicate tick never burns.
; Invalid body/flight/private record changes nothing. Saturating integer units.
air_fuel_step:
 sub rsp,8
 call valid
 add rsp,8
 test eax,eax
 js .done
 mov eax,[r9+AIR_SPEED]
 cmp eax,__float32__(AIR_FLIGHT_MIN_SPEED)
 jb .bad
 cmp eax,__float32__(AIR_FLIGHT_MAX_SPEED)
 ja .bad
 mov eax,[r9+AIR_BANK]
 and eax,0x7fffffff
 cmp eax,__float32__(1.6)
 ja .bad
 mov edx,[r9+AIR_VY]
 and edx,0x7fffffff
 cmp edx,__float32__(0.5)
 ja .bad
 mov edx,[r8+ENTITY_GENERATION]
 cmp edx,[r10]
 jne .birth
 mov edx,[r9+AIR_ROLE]
 inc edx
 cmp edx,[r10+12]
 jne .bad
 cmp [r10+4],r11d
 ja .bad
 mov edx,[sim_tick_count]
 cmp edx,[r10+8]
 je .status
 mov [r10+8],edx
 mov edx,1
 cmp eax,__float32__(AIR_FUEL_BANK_THRESHOLD)
 jb .climb
 inc edx
.climb:
 mov eax,[r9+AIR_VY]
 test eax,eax
 js .consume
 cmp eax,__float32__(AIR_FUEL_CLIMB_THRESHOLD)
 jbe .consume
 inc edx
.consume:
 mov eax,[r10+4]
 sub eax,edx
 jnc .store
 xor eax,eax
.store:
 mov [r10+4],eax
.status:
 jmp air_fuel_status
.birth:
 mov [r10],edx
 mov [r10+4],r11d
 mov edx,[sim_tick_count]
 mov [r10+8],edx
 mov edx,[r9+AIR_ROLE]
 inc edx
 mov [r10+12],edx
 xor eax,eax
.done: ret
.bad: mov eax,-1
 ret
; Existing incoming RAX/R8 FNV convention; include all private fuel lifecycle.
air_fuel_hash:
 mov ecx,[sim_count]
 cmp ecx,ENTITY_CAPACITY
 ja .done
 shl ecx,4
 jz .done
 lea rsi,[sim_air_fuel]
.bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .bytes
.done:ret
section .note.GNU-stack noalloc noexec nowrite progbits
