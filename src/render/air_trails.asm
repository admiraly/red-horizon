; Bounded cosmetic aircraft pose sampling. No authoritative writes or allocation.
default rel
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/player.inc"
global air_trails_update,air_trails_records,air_trails_active,air_trails_emitted
extern sim_entities,sim_aircraft,sim_count,sim_tick_count,sim_players
section .rodata
zero: dd 0.0
max_dt: dd 0.25
cadence: dd 0.1
engine_life: dd 0.8
smoke_life: dd 2.5
range2: dd 1440000.0
back: dd 1.4 ; velocity is metres/fixed tick: about4..8m aft
min_speed2: dd 0.01
section .bss
align 16
air_trails_records: resb 128*32 ; XYZ,remaining; radius,0,0,type6/7
owners: resd 128
generations: resd 128
next_slot: resd 1
scan_start: resd 1
clock: resd 1
last_tick: resd 1
air_trails_active: resd 1
air_trails_emitted: resd 1
view_x: resd 1
view_z: resd 1
section .text
; EDI local player; XMM0 render seconds. Cadence collapses stalled frames.
air_trails_update:
 push rbx
 push r12
 push r13
 push r14
 push r15
 and edi,3
 shl edi,6
 lea rax,[sim_players]
 add rax,rdi
 cmp dword [rax+PLAYER_CONNECTED],0
 je .clear
 movss xmm1,[rax+PLAYER_X]
 movss [view_x],xmm1
 movss xmm1,[rax+PLAYER_Z]
 movss [view_z],xmm1
 movd eax,xmm0
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .bad_dt
 ucomiss xmm0,[zero]
 jp .bad_dt
 jb .bad_dt
 minss xmm0,[max_dt]
 jmp .decay_start
.bad_dt:
 xorps xmm0,xmm0
.decay_start:
 addss xmm0,[clock] ; temporarily preserve accumulated clock in XMM7
 movaps xmm7,xmm0
 subss xmm0,[clock]
 lea rbx,[air_trails_records]
 xor r12d,r12d
 xor r15d,r15d
.decay:
 movss xmm1,[rbx+12]
 subss xmm1,xmm0
 maxss xmm1,[zero]
 lea rdx,[owners]
 mov eax,[rdx+r12*4]
 cmp eax,[sim_count]
 jae .invalidate
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .invalidate
 cmp dword [rdx+ENTITY_KIND],3
 jne .invalidate
 lea rcx,[generations]
 mov eax,[rcx+r12*4]
 cmp eax,[rdx+ENTITY_GENERATION]
 jne .invalidate
 lea rcx,[owners]
 mov eax,[rcx+r12*4]
 shl eax,6
 lea rcx,[sim_aircraft]
 add rcx,rax
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[rcx+AIR_GENERATION]
 jne .invalidate
 test dword [rcx+AIR_FLAGS],AIR_ACTIVE
 jz .invalidate
 movss xmm2,[rbx]
 subss xmm2,[view_x]
 mulss xmm2,xmm2
 movss xmm3,[rbx+8]
 subss xmm3,[view_z]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 ucomiss xmm2,[range2]
 ja .invalidate
 jmp .store
.invalidate:
 xorps xmm1,xmm1
.store:
 movss [rbx+12],xmm1
 add rbx,32
 inc r12d
 cmp r12d,128
 jb .decay
 movss [clock],xmm7
 ucomiss xmm7,[cadence]
 jb .count
 movss xmm1,[cadence]
 subss xmm7,xmm1
 minss xmm7,xmm1 ; no catch-up burst after long stalls
 movss [clock],xmm7
 mov eax,[sim_tick_count]
 cmp eax,[last_tick]
 je .count
 mov [last_tick],eax
 mov r12d,[scan_start]
 mov r13d,[sim_count]
 cmp r13d,ENTITY_CAPACITY
 jbe .bounded
 mov r13d,ENTITY_CAPACITY
.bounded:
 test r13d,r13d
 jz .count
 xor r14d,r14d
 xor r15d,r15d
.scan:
 cmp r12d,r13d
 jb .index
 xor r12d,r12d
.index:
 mov eax,r12d
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_KIND],3
 jne .next
 cmp dword [rbx+ENTITY_HP],0
 je .next
 mov eax,r12d
 shl eax,6
 lea rdx,[sim_aircraft]
 add rdx,rax
 mov eax,[rbx+ENTITY_GENERATION]
 cmp eax,[rdx+AIR_GENERATION]
 jne .next
 test dword [rdx+AIR_FLAGS],AIR_ACTIVE
 jz .next
 movss xmm1,[rbx+ENTITY_X]
 subss xmm1,[view_x]
 mulss xmm1,xmm1
 movss xmm2,[rbx+ENTITY_Z]
 subss xmm2,[view_z]
 mulss xmm2,xmm2
 addss xmm1,xmm2
 ucomiss xmm1,[range2]
 ja .next
 jp .next
 movss xmm1,[rdx+AIR_VX]
 mulss xmm1,xmm1
 movss xmm2,[rdx+AIR_VZ]
 mulss xmm2,xmm2
 addss xmm1,xmm2
 ucomiss xmm1,[min_speed2]
 jbe .next
 jp .next
 mov eax,[next_slot]
 lea rcx,[owners]
 mov [rcx+rax*4],r12d
 lea rcx,[generations]
 mov ecx,[rbx+ENTITY_GENERATION]
 lea rdi,[generations]
 mov [rdi+rax*4],ecx
 inc dword [next_slot]
 and dword [next_slot],127
 shl eax,5
 lea rdi,[air_trails_records]
 add rdi,rax
 movss xmm1,[rdx+AIR_VX]
 mulss xmm1,[back]
 movss xmm2,[rbx+ENTITY_X]
 subss xmm2,xmm1
 movss [rdi],xmm2
 movss xmm1,[rdx+AIR_VY]
 mulss xmm1,[back]
 movss xmm2,[rdx+AIR_Y]
 subss xmm2,xmm1
 movss [rdi+4],xmm2
 movss xmm1,[rdx+AIR_VZ]
 mulss xmm1,[back]
 movss xmm2,[rbx+ENTITY_Z]
 subss xmm2,xmm1
 movss [rdi+8],xmm2
 mov eax,6
 movss xmm1,[engine_life]
 mov dword [rdi+16],0x3f400000 ; .75m
 cmp dword [rbx+ENTITY_HP],100
 jae .emit
 mov eax,7
 movss xmm1,[smoke_life]
 mov dword [rdi+16],0x40000000 ;2m
.emit:
 movss [rdi+12],xmm1
 mov dword [rdi+20],0
 mov dword [rdi+24],0
 mov [rdi+28],eax
 inc dword [air_trails_emitted]
 inc r15d
.next:
 inc r12d
 inc r14d
 cmp r15d,32
 jae .scanned
 cmp r14d,r13d
 jb .scan
.scanned:
 mov [scan_start],r12d
.count:
 lea rbx,[air_trails_records]
 xor edx,edx
 mov ecx,128
.count_loop:
 movss xmm0,[rbx+12]
 ucomiss xmm0,[zero]
 jbe .count_next
 inc edx
.count_next:
 add rbx,32
 loop .count_loop
 mov [air_trails_active],edx
 jmp .done
.clear:
 lea rdi,[air_trails_records]
 xor eax,eax
 mov ecx,128*8
 rep stosd
 mov dword [air_trails_active],0
 mov dword [clock],0
 mov eax,[sim_tick_count]
 mov [last_tick],eax
.done:
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
