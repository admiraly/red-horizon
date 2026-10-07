; Generation-aware shared runway admission. NASM/SysV, single authority thread.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_bases.inc"
%include "schemas/air_traffic.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,sim_tick_count
extern air_recovery_goal,air_fuel_status,air_base_goal
section .bss align=64
global sim_air_traffic
sim_air_traffic: resb AIR_BASE_COUNT*AIR_TRAFFIC_STRIDE
section .text
global air_traffic_init,air_traffic_request,air_traffic_release,air_traffic_hash
air_traffic_init:
 lea rdi,[sim_air_traffic]
 xor eax,eax
 mov ecx,AIR_BASE_COUNT*AIR_TRAFFIC_STRIDE/4
 rep stosd
 ret
; EDI own ID, ESI selected base ->1 exclusive grant/renew,0busy,-1invalid.
; Public entities/facilities/fuel read-only, changes only selected lease.
; All SysV nonvolatile and XMM0..7 preserved; remaining scratch caller-saved.
; Aligned nested calls, constant six-base storage, no unbounded scans/allocation.
air_traffic_request:
 push rbx
 push rbp
 push r12
 sub rsp,128
%assign x 0
%rep 8
 movdqu [rsp+x*16],xmm %+ x
%assign x x+1
%endrep
 mov ebx,edi
 mov ebp,esi
 cmp ebp,AIR_BASE_COUNT
 jae .invalid
 call air_recovery_goal
 cmp eax,1
 jne .invalid
 mov edi,ebx
 call air_fuel_status
 cmp eax,1
 ja .invalid
 mov edi,ebx
 call air_base_goal
 cmp eax,ebp
 jne .invalid
 mov eax,ebx
 shl eax,5
 lea r12,[sim_entities]
 add r12,rax
 mov eax,ebp
 shl eax,4
 lea r10,[sim_air_traffic]
 add r10,rax
 mov r11d,[sim_tick_count]
 mov eax,[r10]
 test eax,eax
 jnz .occupied
 cmp qword [r10+4],0
 jne .invalid
 cmp dword [r10+12],0
 jne .invalid
 jmp .grant
.occupied:
 cmp eax,ENTITY_CAPACITY
 ja .invalid
 cmp dword [r10+4],0
 je .invalid
 cmp dword [r10+12],1
 ja .invalid
 mov edx,r11d
 sub edx,[r10+8]
 test edx,0x80000000
 jnz .invalid ; Future/ambiguous timestamp fails closed; natural wrap works.
 cmp edx,AIR_TRAFFIC_LEASE_TICKS
 jae .grant
 mov ecx,[r12+ENTITY_SIDE]
 cmp [r10+12],ecx
 jne .grant ; Captured capability invalidates old side before actor reads.
 dec eax
 cmp eax,[sim_count]
 jae .grant
 mov ecx,eax
 shl ecx,5
 lea rdx,[sim_entities]
 add rdx,rcx
 mov ecx,[r12+ENTITY_SIDE]
 cmp [rdx+ENTITY_SIDE],ecx
 jne .grant ; Never inspect an enemy occupant's condition/private aircraft.
 cmp dword [rdx+ENTITY_HP],0
 je .grant
 cmp dword [rdx+ENTITY_KIND],3
 jne .grant
 mov ecx,[r10+4]
 cmp [rdx+ENTITY_GENERATION],ecx
 jne .grant
 mov edx,eax
 shl edx,6
 lea rcx,[sim_aircraft]
 add rcx,rdx
 mov edx,[r10+4]
 cmp [rcx+AIR_GENERATION],edx
 jne .grant
 test dword [rcx+AIR_FLAGS],AIR_ACTIVE
 jz .grant
 cmp eax,ebx
 jne .busy
.grant:
 lea eax,[rbx+1]
 mov [r10],eax
 mov eax,[r12+ENTITY_GENERATION]
 mov [r10+4],eax
 mov [r10+8],r11d
 mov eax,[r12+ENTITY_SIDE]
 mov [r10+12],eax
 mov eax,1
 jmp .done
.busy:
 xor eax,eax
 jmp .done
.invalid:
 mov eax,-1
.done:
%assign x 0
%rep 8
 movdqu xmm %+ x,[rsp+x*16]
%assign x x+1
%endrep
 add rsp,128
 pop r12
 pop rbp
 pop rbx
 ret
; EDI owned stable ID ->EAX released count (0..6), or-1 invalid bounds.
; Releases this ID's own claims, including old generations after ID reuse.
; No actor/side/facility inspection, no other owners changed; SIMD untouched.
air_traffic_release:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .invalid
 cmp edi,[sim_count]
 jae .invalid
 cmp edi,ENTITY_CAPACITY
 jae .invalid
 inc edi
 lea rdx,[sim_air_traffic]
 xor eax,eax
 mov ecx,AIR_BASE_COUNT
.loop:
 cmp [rdx],edi
 jne .next
 mov qword [rdx],0
 mov qword [rdx+8],0
 inc eax
.next:
 add rdx,AIR_TRAFFIC_STRIDE
 dec ecx
 jnz .loop
 ret
.invalid:
 mov eax,-1
 ret
air_traffic_hash:
 lea rsi,[sim_air_traffic]
 mov ecx,AIR_BASE_COUNT*AIR_TRAFFIC_STRIDE
.bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .bytes
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
