; Own-side bomber missions. Full friendly linked buckets, reviewed every30ticks.
; Flight and weapons remain in aircraft.asm. Never modifies pose/HP/ammunition.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_escort.inc"
%include "schemas/air_recovery.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,sim_tick_count
extern air_fuel_status
section .bss align=64
global sim_air_escorts
sim_air_escorts: resb ENTITY_CAPACITY*AIR_ESCORT_STRIDE
heads: resd 1024
links: resd ENTITY_CAPACITY
section .rodata
zero: dd 0.0
maximum: dd 8000.0
cell_scale: dd 0.004
assign_range: dd AIR_ESCORT_RANGE_SQUARED
break_range: dd AIR_ESCORT_BREAK_SQUARED
threat_range: dd AIR_ESCORT_THREAT_SQUARED
trail: dd AIR_ESCORT_TRAIL_TICKS
lateral: dd AIR_ESCORT_LATERAL
negative: dd -1.0
section .text
global air_escort_init,air_escort_tick,air_escort_goal,air_escort_threat,air_escort_hash
%macro VALID_AIR 3
 cmp dword [%1+ENTITY_HP],AIR_RECOVERY_CRITICAL_HP
 jbe %3
 cmp dword [%1+ENTITY_KIND],3
 jne %3
 cmp dword [%1+ENTITY_SIDE],1
 ja %3
 cmp dword [%1+ENTITY_FRONT],2
 ja %3
 mov eax,[%1+ENTITY_GENERATION]
 test eax,eax
 jz %3
 cmp eax,[%2+AIR_GENERATION]
 jne %3
 test dword [%2+AIR_FLAGS],AIR_ACTIVE
 jz %3
 cmp dword [%2+AIR_AMMO],0
 je %3
 cmp dword [%2+AIR_SPEED],0
 jbe %3
 cmp dword [%2+AIR_SPEED],__float32__(7.0)
 ja %3
 cmp dword [%1+ENTITY_X],__float32__(8000.0)
 ja %3
 cmp dword [%1+ENTITY_Z],__float32__(8000.0)
 ja %3
 ; Recovery reserve, empty or malformed fuel cannot accept a wing mission.
 mov rax,%1
 call air_escort_init.fuel
 test eax,eax
 jnz %3
%endmacro
air_escort_init:
 lea rdi,[sim_air_escorts]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*AIR_ESCORT_STRIDE/4
 rep stosd
 ret
; Validation preserves XMM0/1 (caller's fallback goal). EAX leader or-1.
; R11 leader entity/RCX leader aircraft on success; all scratch is caller-saved.
.validate:
 sub rsp,8
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .invalid
 cmp edi,[sim_count]
 jae .invalid
 cmp edi,ENTITY_CAPACITY
 jae .invalid
 mov eax,edi
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 mov eax,edi
 shl eax,6
 lea r9,[sim_aircraft]
 add r9,rax
 VALID_AIR r8,r9,.invalid
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 jne .invalid
 mov eax,edi
 shl eax,4
 lea r10,[sim_air_escorts]
 add r10,rax
 mov eax,[r8+ENTITY_GENERATION]
 cmp eax,[r10+AIR_ESCORT_OWNER_GENERATION]
 jne .invalid
 mov eax,[sim_tick_count]
 sub eax,[r10+AIR_ESCORT_UNTIL]
 jns .invalid
 mov eax,[r10+AIR_ESCORT_LEADER]
 cmp eax,[sim_count]
 jae .invalid
 cmp eax,ENTITY_CAPACITY
 jae .invalid
 mov edx,eax
 shl edx,5
 lea r11,[sim_entities]
 add r11,rdx
 shl eax,6
 lea rcx,[sim_aircraft]
 add rcx,rax
 VALID_AIR r11,rcx,.invalid
 cmp dword [rcx+AIR_ROLE],AIR_BOMBER
 jne .invalid
 mov eax,[r11+ENTITY_GENERATION]
 cmp eax,[r10+AIR_ESCORT_LEADER_GENERATION]
 jne .invalid
 mov eax,[r8+ENTITY_SIDE]
 cmp eax,[r11+ENTITY_SIDE]
 jne .invalid
 mov eax,[r8+ENTITY_FRONT]
 cmp eax,[r11+ENTITY_FRONT]
 jne .invalid
 movss xmm2,[r8+ENTITY_X]
 subss xmm2,[r11+ENTITY_X]
 mulss xmm2,xmm2
 movss xmm3,[r8+ENTITY_Z]
 subss xmm3,[r11+ENTITY_Z]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 comiss xmm2,[break_range]
 ja .invalid
 mov eax,[r10+AIR_ESCORT_LEADER]
 add rsp,8
 ret
.invalid:
 mov eax,-1
 add rsp,8
 ret
; RAX own entity pointer. Preserve the validator's friendly record addresses
; and owner ID across the shared read-only fuel query; XMM untouched.
.fuel:
 push rdi
 push rcx
 push rdx
 push r8
 push r9
 push r10
 push r11
 mov rdi,rax
 lea rax,[sim_entities]
 sub rdi,rax
 shr rdi,5
 call air_fuel_status
 pop r11
 pop r10
 pop r9
 pop r8
 pop rdx
 pop rcx
 pop rdi
 ret
air_escort_tick:
 mov eax,[sim_count]
 cmp eax,ENTITY_CAPACITY
 ja .done_leaf
 test eax,eax
 jz .done_leaf
 mov eax,[sim_tick_count]
 cmp eax,1
 je .review
 xor edx,edx
 mov ecx,AIR_ESCORT_REVIEW
 div ecx
 test edx,edx
 jnz .done_leaf
.review:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,72
 lea rdi,[heads]
 mov eax,-1
 mov ecx,1024
 rep stosd
 xor r12d,r12d
.index:
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 mov eax,r12d
 shl eax,6
 lea rbp,[sim_aircraft]
 add rbp,rax
 VALID_AIR rbx,rbp,.index_next
 cmp dword [rbp+AIR_ROLE],AIR_BOMBER
 jne .index_next
 call .cell
 lea rcx,[heads]
 mov edx,[rcx+rax*4]
 mov [rcx+rax*4],r12d
 lea rcx,[links]
 mov [rcx+r12*4],edx
.index_next:
 inc r12d
 cmp r12d,[sim_count]
 jb .index
 xor r12d,r12d
.owner:
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 mov eax,r12d
 shl eax,6
 lea rbp,[sim_aircraft]
 add rbp,rax
 mov eax,r12d
 shl eax,4
 lea rdx,[sim_air_escorts]
 add rdx,rax
 mov [rsp+24],rdx
 VALID_AIR rbx,rbp,.clear
 cmp dword [rbp+AIR_ROLE],AIR_FIGHTER
 jne .clear
 mov edi,r12d
 call air_escort_init.validate
 cmp eax,-1
 je .pick
 mov eax,[r10+AIR_ESCORT_UNTIL]
 sub eax,[sim_tick_count]
 cmp eax,AIR_ESCORT_REVIEW
 ja .owner_next
.pick:
 call .cell
 mov edx,eax
 and edx,31
 mov [rsp],edx
 shr eax,5
 mov [rsp+4],eax
 mov eax,[assign_range]
 mov [rsp+8],eax
 mov r15d,-1
 mov r13d,-6
.z:
 mov eax,[rsp+4]
 add eax,r13d
 cmp eax,31
 ja .zn
 shl eax,5
 mov [rsp+12],eax
 mov r14d,-6
.x:
 mov eax,[rsp]
 add eax,r14d
 cmp eax,31
 ja .xn
 add eax,[rsp+12]
 lea rcx,[heads]
 mov esi,[rcx+rax*4]
.scan:
 cmp esi,-1
 je .xn
 mov [rsp+16],esi
 mov eax,esi
 shl eax,5
 lea r11,[sim_entities]
 add r11,rax
 mov eax,[r11+ENTITY_SIDE]
 cmp eax,[rbx+ENTITY_SIDE]
 jne .scan_next
 mov eax,[r11+ENTITY_FRONT]
 cmp eax,[rbx+ENTITY_FRONT]
 jne .scan_next
 movss xmm0,[r11+ENTITY_X]
 subss xmm0,[rbx+ENTITY_X]
 mulss xmm0,xmm0
 movss xmm1,[r11+ENTITY_Z]
 subss xmm1,[rbx+ENTITY_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[rsp+8]
 ja .scan_next
 jb .select
 cmp esi,r15d
 jae .scan_next
.select:
 mov r15d,esi
 movss [rsp+8],xmm0
.scan_next:
 lea rcx,[links]
 mov eax,[rsp+16]
 mov esi,[rcx+rax*4]
 jmp .scan
.xn:
 inc r14d
 cmp r14d,6
 jle .x
.zn:
 inc r13d
 cmp r13d,6
 jle .z
 mov rdx,[rsp+24]
 mov qword [rdx],0
 mov qword [rdx+8],0
 cmp r15d,-1
 je .owner_next
 mov [rdx+AIR_ESCORT_LEADER],r15d
 mov eax,r15d
 shl eax,5
 lea rcx,[sim_entities]
 mov eax,[rcx+rax+ENTITY_GENERATION]
 mov [rdx+AIR_ESCORT_LEADER_GENERATION],eax
 mov eax,[rbx+ENTITY_GENERATION]
 mov [rdx+AIR_ESCORT_OWNER_GENERATION],eax
 mov eax,[sim_tick_count]
 add eax,AIR_ESCORT_COMMITMENT
 mov [rdx+AIR_ESCORT_UNTIL],eax
 jmp .owner_next
.clear:
 mov rdx,[rsp+24]
 mov qword [rdx],0
 mov qword [rdx+8],0
.owner_next:
 inc r12d
 cmp r12d,[sim_count]
 jb .owner
 add rsp,72
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
.done_leaf:
 ret
.cell:
 movss xmm0,[rbx+ENTITY_X]
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .xok
 mov eax,31
.xok:
 movss xmm0,[rbx+ENTITY_Z]
 mulss xmm0,[cell_scale]
 cvttss2si edx,xmm0
 cmp edx,31
 jbe .zok
 mov edx,31
.zok:
 shl edx,5
 add eax,edx
 ret
; EDI own fighter; returns1 with moving trailing/flank goal, or0 unchangedXMM0/1.
air_escort_goal:
 sub rsp,8
 call air_escort_init.validate
 add rsp,8
 cmp eax,-1
 je .none
 movss xmm2,[lateral]
 test edi,32
 jz .lane
 mulss xmm2,[negative]
.lane:
 ; Lateral spacing is metres in the ground plane, even during a climb.
 movss xmm3,[rcx+AIR_VX]
 mulss xmm3,xmm3
 movss xmm4,[rcx+AIR_VZ]
 mulss xmm4,xmm4
 addss xmm3,xmm4
 sqrtss xmm3,xmm3
 ucomiss xmm3,[zero]
 jp .none
 jbe .none
 divss xmm2,xmm3
 movss xmm0,[rcx+AIR_VX]
 mulss xmm0,[trail]
 movss xmm1,[r11+ENTITY_X]
 subss xmm1,xmm0
 movss xmm0,[rcx+AIR_VZ]
 mulss xmm0,xmm2
 addss xmm0,xmm1
 movss xmm1,[rcx+AIR_VZ]
 mulss xmm1,[trail]
 movss xmm3,[r11+ENTITY_Z]
 subss xmm3,xmm1
 movss xmm1,[rcx+AIR_VX]
 mulss xmm1,xmm2
 subss xmm3,xmm1
 movaps xmm1,xmm3
 mov eax,1
 ret
.none:
 xor eax,eax
 ret
; Pure scoring only. Candidate must still pass the caller's original range/LOS.
air_escort_threat:
 push rsi
 call air_escort_init.validate
 pop rsi
 cmp eax,-1
 je .none
 cmp esi,[sim_count]
 jae .none
 cmp esi,ENTITY_CAPACITY
 jae .none
 mov eax,esi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .none
 cmp dword [rdx+ENTITY_KIND],3
 jne .none
 mov eax,[rdx+ENTITY_SIDE]
 cmp eax,[r8+ENTITY_SIDE]
 je .none
 mov eax,esi
 shl eax,6
 lea r9,[sim_aircraft]
 add r9,rax
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[r9+AIR_GENERATION]
 jne .none
 test dword [r9+AIR_FLAGS],AIR_ACTIVE
 jz .none
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 jne .none
 movss xmm2,[rdx+ENTITY_X]
 subss xmm2,[r11+ENTITY_X]
 mulss xmm2,xmm2
 movss xmm3,[rdx+ENTITY_Z]
 subss xmm3,[r11+ENTITY_Z]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 movss xmm3,[r9+AIR_Y]
 subss xmm3,[rcx+AIR_Y]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 comiss xmm2,[threat_range]
 ja .none
 mov eax,1
 ret
.none:
 xor eax,eax
 ret
air_escort_hash:
 lea rsi,[sim_air_escorts]
 mov ecx,[sim_count]
 cmp ecx,ENTITY_CAPACITY
 ja .done
 shl ecx,4
 jz .done
.bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .bytes
.done:
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
