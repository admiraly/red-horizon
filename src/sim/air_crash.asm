; Fixed-step ballistic dead airframes; no living entity/HP/store writes.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_flight.inc"
%include "schemas/air_crash.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,sim_tick_count,terrain_height
section .bss align=64
global sim_air_crashes,sim_air_crash_count,sim_air_crash_sequence
sim_air_crashes: resb AIR_CRASH_CAPACITY*AIR_CRASH_STRIDE
seen: resd ENTITY_CAPACITY
sim_air_crash_count: resd 1
cursor: resd 1
sim_air_crash_sequence: resd 1
last_tick: resd 1
section .rodata
zero: dd 0.0
maximum: dd 8000.0
height_limit: dd 1000.0
pi: dd 3.141592653589793
tau: dd 6.283185307179586
minus_pi: dd -3.141592653589793
pitch_floor: dd AIR_CRASH_PITCH_FLOOR
pitch_step: dd AIR_CRASH_PITCH_RATE
bank_step: dd AIR_CRASH_BANK_RATE
minus_bank_step: dd -AIR_CRASH_BANK_RATE
gravity: dd AIR_FLIGHT_GRAVITY
min_speed_sq: dd 24.9
max_speed_sq: dd 49.1
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global air_crash_init,air_crash_register,air_crash_tick,air_crash_hash
air_crash_init:
 lea rdi,[sim_air_crashes]
 xor eax,eax
 mov ecx,(AIR_CRASH_CAPACITY*AIR_CRASH_STRIDE+ENTITY_CAPACITY*4+16)/4
 rep stosd
 ret
; EDI actual dead aircraft.0 added,1 duplicate,-1 invalid (atomic).
air_crash_register:
 cmp edi,[sim_count]
 jae .bad
 cmp edi,ENTITY_CAPACITY
 jae .bad
 mov eax,edi
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 cmp dword [r8+ENTITY_HP],0
 jne .bad
 cmp dword [r8+ENTITY_KIND],3
 jne .bad
 cmp dword [r8+ENTITY_SIDE],1
 ja .bad
 mov eax,edi
 shl eax,6
 lea r9,[sim_aircraft]
 add r9,rax
 mov edx,[r8+ENTITY_GENERATION]
 test edx,edx
 jz .bad
 cmp edx,[r9+AIR_GENERATION]
 jne .bad
 test dword [r9+AIR_FLAGS],AIR_ACTIVE
 jz .bad
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 ja .bad
%macro coordinate 2
 movss xmm0,[%1+%2]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
%endmacro
 coordinate r8,ENTITY_X
 coordinate r8,ENTITY_Z
%unmacro coordinate 2
 movss xmm0,[r9+AIR_Y]
 andps xmm0,[abs_mask]
 ucomiss xmm0,[height_limit]
 jp .bad
 ja .bad
%macro angle 1
 movss xmm0,[r9+%1]
 andps xmm0,[abs_mask]
 ucomiss xmm0,[pi]
 jp .bad
 ja .bad
%endmacro
 angle AIR_HEADING
 angle AIR_PITCH
 angle AIR_BANK
%unmacro angle 1
 xorps xmm1,xmm1
%macro velocity 1
 movss xmm0,[r9+%1]
 mulss xmm0,xmm0
 addss xmm1,xmm0
%endmacro
 velocity AIR_VX
 velocity AIR_VY
 velocity AIR_VZ
%unmacro velocity 1
 ucomiss xmm1,[min_speed_sq]
 jp .bad
 jb .bad
 ucomiss xmm1,[max_speed_sq]
 ja .bad
 lea r10,[seen]
 cmp [r10+rdi*4],edx
 je .duplicate
 mov eax,[cursor]
 imul eax,AIR_CRASH_STRIDE
 lea r11,[sim_air_crashes]
 add r11,rax
 cmp dword [r11+AIR_CRASH_STATE],0
 jne .occupied
 inc dword [sim_air_crash_count]
.occupied:
 ; Full record clear prevents retired velocity/state/reserved data revival.
 xorps xmm0,xmm0
 movups [r11],xmm0
 movups [r11+16],xmm0
 movups [r11+32],xmm0
 movups [r11+48],xmm0
 movups [r11+64],xmm0
 movups [r11+80],xmm0
 mov eax,[r8+ENTITY_X]
 mov [r11+AIR_CRASH_X],eax
 mov eax,[r9+AIR_Y]
 mov [r11+AIR_CRASH_Y],eax
 mov eax,[r8+ENTITY_Z]
 mov [r11+AIR_CRASH_Z],eax
%macro copy 2
 mov eax,[r9+%1]
 mov [r11+%2],eax
%endmacro
 copy AIR_VX,AIR_CRASH_VX
 copy AIR_VY,AIR_CRASH_VY
 copy AIR_VZ,AIR_CRASH_VZ
 copy AIR_HEADING,AIR_CRASH_HEADING
 copy AIR_PITCH,AIR_CRASH_PITCH
 copy AIR_BANK,AIR_CRASH_BANK
 copy AIR_ROLE,AIR_CRASH_ROLE
%unmacro copy 2
 mov eax,[r8+ENTITY_SIDE]
 mov [r11+AIR_CRASH_SIDE],eax
 mov [r11+AIR_CRASH_ENTITY],edi
 mov [r11+AIR_CRASH_GENERATION],edx
 mov [r10+rdi*4],edx
 mov eax,[sim_tick_count]
 mov [r11+AIR_CRASH_BIRTH],eax
 inc dword [sim_air_crash_sequence]
 jnz .sequence
 inc dword [sim_air_crash_sequence]
.sequence:
 mov eax,[sim_air_crash_sequence]
 mov [r11+AIR_CRASH_SEQUENCE],eax
 mov dword [r11+AIR_CRASH_STATE],AIR_CRASH_FALLING
 inc dword [cursor]
 and dword [cursor],AIR_CRASH_CAPACITY-1
 xor eax,eax
 ret
.duplicate:
 mov eax,1
 ret
.bad:
 mov eax,-1
 ret
air_crash_tick:
 mov eax,[sim_tick_count]
 cmp eax,[last_tick]
 je .done_leaf
 mov [last_tick],eax
 push rbx
 push r12
 sub rsp,8
 lea rbx,[sim_air_crashes]
 xor r12d,r12d
.loop:
 cmp dword [rbx+AIR_CRASH_STATE],0
 je .next
 mov eax,[sim_tick_count]
 sub eax,[rbx+AIR_CRASH_BIRTH]
 cmp eax,AIR_CRASH_LIFETIME
 jae .expire
 test eax,eax
 jz .next
 cmp dword [rbx+AIR_CRASH_STATE],AIR_CRASH_FALLING
 jne .next
%macro travel 2
 movss xmm0,[rbx+%1]
 addss xmm0,[rbx+%2]
 ucomiss xmm0,[zero]
 jb %%stop
 ucomiss xmm0,[maximum]
 jbe %%store
%%stop:
 minss xmm0,[maximum]
 maxss xmm0,[zero]
 mov dword [rbx+%2],0
%%store:
 movss [rbx+%1],xmm0
%endmacro
 travel AIR_CRASH_X,AIR_CRASH_VX
 travel AIR_CRASH_Z,AIR_CRASH_VZ
%unmacro travel 2
 movss xmm0,[rbx+AIR_CRASH_Y]
 addss xmm0,[rbx+AIR_CRASH_VY]
 movss [rbx+AIR_CRASH_Y],xmm0
 movss xmm0,[rbx+AIR_CRASH_VY]
 subss xmm0,[gravity]
 movss [rbx+AIR_CRASH_VY],xmm0
 movss xmm0,[rbx+AIR_CRASH_PITCH]
 subss xmm0,[pitch_step]
 maxss xmm0,[pitch_floor]
 movss [rbx+AIR_CRASH_PITCH],xmm0
 movss xmm0,[bank_step]
 test dword [rbx+AIR_CRASH_ENTITY],1
 jz .bank
 movss xmm0,[minus_bank_step]
.bank:
 addss xmm0,[rbx+AIR_CRASH_BANK]
 ucomiss xmm0,[pi]
 jbe .low
 subss xmm0,[tau]
.low:
 ucomiss xmm0,[minus_pi]
 jae .rotation
 addss xmm0,[tau]
.rotation:
 movss [rbx+AIR_CRASH_BANK],xmm0
 movss xmm0,[rbx+AIR_CRASH_X]
 movss xmm1,[rbx+AIR_CRASH_Z]
 call terrain_height
 ucomiss xmm0,[rbx+AIR_CRASH_Y]
 jb .next
 movss [rbx+AIR_CRASH_Y],xmm0
 mov qword [rbx+AIR_CRASH_VX],0
 mov dword [rbx+AIR_CRASH_VZ],0
 mov qword [rbx+AIR_CRASH_PITCH],0
 mov dword [rbx+AIR_CRASH_STATE],AIR_CRASH_LANDED
 jmp .next
.expire:
 mov dword [rbx+AIR_CRASH_STATE],0
 dec dword [sim_air_crash_count]
.next:
 add rbx,AIR_CRASH_STRIDE
 inc r12d
 cmp r12d,AIR_CRASH_CAPACITY
 jb .loop
 add rsp,8
 pop r12
 pop rbx
.done_leaf:
 ret
air_crash_hash:
 lea rsi,[sim_air_crashes]
 mov ecx,AIR_CRASH_CAPACITY*AIR_CRASH_STRIDE+ENTITY_CAPACITY*4+16
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
