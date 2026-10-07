; Return to an interior own-side recovery area on critical damage/empty stores.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_recovery.inc"
default rel
extern air_fuel_status
extern sim_entities,sim_aircraft,sim_count
section .bss align=64
global sim_air_holding
sim_air_holding: resb ENTITY_CAPACITY*8 ; generation, acquired recovery area
section .rodata
home: dd AIR_RECOVERY_HOME_X
world_edge: dd 8000.0
front_spacing: dd AIR_RECOVERY_FRONT_SPACING
arrival2: dd AIR_RECOVERY_ARRIVAL_SQ
radius: dd AIR_RECOVERY_BOMBER_HOLD_RADIUS,AIR_RECOVERY_FIGHTER_HOLD_RADIUS
lookahead: dd AIR_RECOVERY_HOLD_LOOKAHEAD
radial_gain: dd AIR_RECOVERY_HOLD_RADIAL_GAIN
one: dd 1.0
negative: dd -1.0
section .text
global air_recovery_goal
; EDI owned physical aircraft ID. EAX1/XMM0X/XMM1Z goal; EAX0 preservesXMM0/1.
; Read-only: current own condition, never another body or private target cache.
air_recovery_goal:
 cmp edi,[sim_count]
 jae .none
 cmp edi,ENTITY_CAPACITY
 jae .none
 mov eax,edi
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 cmp dword [r8+ENTITY_HP],0
 je .none
 cmp dword [r8+ENTITY_KIND],3
 jne .none
 cmp dword [r8+ENTITY_SIDE],1
 ja .none
 cmp dword [r8+ENTITY_FRONT],2
 ja .none
 mov eax,edi
 shl eax,6
 lea r9,[sim_aircraft]
 add r9,rax
 mov eax,[r8+ENTITY_GENERATION]
 test eax,eax
 jz .none
 cmp eax,[r9+AIR_GENERATION]
 jne .none
 test dword [r9+AIR_FLAGS],AIR_ACTIVE
 jz .none
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 ja .none
 cmp dword [r8+ENTITY_HP],AIR_RECOVERY_CRITICAL_HP
 jbe .goal
 cmp dword [r9+AIR_AMMO],0
 je .goal
 sub rsp,8
 call air_fuel_status
 add rsp,8
 cmp eax,1
 je .goal
 cmp eax,2
 jne .none
.goal:
 movss xmm0,[home]
 cmp dword [r8+ENTITY_SIDE],0
 je .front
 movss xmm0,[world_edge]
 subss xmm0,[home]
.front:
 mov eax,[r8+ENTITY_FRONT]
 inc eax
 cvtsi2ss xmm1,eax
 mulss xmm1,[front_spacing]
 mov eax,1
 ret
.none:
 xor eax,eax
 ret
; Arrival is persistent until a new generation or recovery condition clears.
; Holding guidance never changes physical records; air_tick owns actuators.
global air_holding_init,air_holding_goal,air_holding_hash
air_holding_init:
 lea rdi,[sim_air_holding]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*2
 rep stosd
 ret
air_holding_goal:
 push rbx
 sub rsp,16
 mov ebx,edi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 call air_recovery_goal
 test eax,eax
 jz .clear
 ; Reject malformed own positions before any guidance or private state update.
 mov edx,[r8+ENTITY_X]
 test edx,edx
 js .none
 cmp edx,__float32__(8000.0)
 ja .none
 mov edx,[r8+ENTITY_Z]
 test edx,edx
 js .none
 cmp edx,__float32__(8000.0)
 ja .none
 xorps xmm7,xmm7
%macro hold_velocity 1
 mov edx,[r9+%1]
 and edx,0x7fffffff
 cmp edx,__float32__(7.0)
 ja .none
 movss xmm6,[r9+%1]
 mulss xmm6,xmm6
 addss xmm7,xmm6
%endmacro
 hold_velocity AIR_VX
 hold_velocity AIR_VY
 hold_velocity AIR_VZ
%unmacro hold_velocity 1
 mov edx,__float32__(24.9)
 movd xmm6,edx
 ucomiss xmm7,xmm6
 jb .none
 mov edx,__float32__(49.1)
 movd xmm6,edx
 ucomiss xmm7,xmm6
 ja .none
 lea r10,[sim_air_holding]
 mov edx,[r8+ENTITY_GENERATION]
 cmp edx,[r10+rbx*8]
 je .same
 mov [r10+rbx*8],edx
 mov dword [r10+rbx*8+4],0
.same:
 movss xmm2,[r8+ENTITY_X]
 subss xmm2,xmm0
 movss xmm3,[r8+ENTITY_Z]
 subss xmm3,xmm1
 movaps xmm4,xmm2
 mulss xmm4,xmm2
 movaps xmm5,xmm3
 mulss xmm5,xmm3
 addss xmm4,xmm5
 cmp dword [r10+rbx*8+4],0
 jne .orbit
 ucomiss xmm4,[arrival2]
 ja .done
 mov dword [r10+rbx*8+4],1
.orbit:
 ; At exactly the centre choose the current physical forward radial axis.
 ; No hidden target/body is read, and division is guarded against zero.
 ucomiss xmm4,[one]
 jae .normalize
 movss xmm2,[r9+AIR_VX]
 movss xmm3,[r9+AIR_VZ]
 movaps xmm4,xmm2
 mulss xmm4,xmm2
 movaps xmm5,xmm3
 mulss xmm5,xmm3
 addss xmm4,xmm5
 ucomiss xmm4,[one]
 jp .none
 jb .none
 mov edx,__float32__(49.1)
 movd xmm5,edx
 ucomiss xmm4,xmm5
 ja .none
.normalize:
 sqrtss xmm4,xmm4
 divss xmm2,xmm4
 divss xmm3,xmm4
 mov edx,[r9+AIR_ROLE]
 lea rcx,[radius]
 movss xmm5,[rcx+rdx*4]
 ; Relative radial correction (R-r)/R, bounded to one tangent magnitude.
 movaps xmm6,xmm5
 subss xmm6,xmm4
 divss xmm6,xmm5
 mulss xmm6,[radial_gain]
 minss xmm6,[one]
 maxss xmm6,[negative]
 ; Clockwise tangent (nz,-nx) plus radial correction.
 movaps xmm0,xmm2
 mulss xmm0,xmm6
 addss xmm0,xmm3
 movaps xmm1,xmm3
 mulss xmm1,xmm6
 subss xmm1,xmm2
 mulss xmm0,[lookahead]
 mulss xmm1,[lookahead]
 addss xmm0,[r8+ENTITY_X]
 addss xmm1,[r8+ENTITY_Z]
.done:
 mov eax,1
 jmp .return
.clear:
 cmp ebx,[sim_count]
 jae .return
 cmp ebx,ENTITY_CAPACITY
 jae .return
 lea r10,[sim_air_holding]
 mov qword [r10+rbx*8],0
 jmp .return
.none:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 xor eax,eax
.return:
 add rsp,16
 pop rbx
 ret
air_holding_hash:
 lea rsi,[sim_air_holding]
 mov ecx,[sim_count]
 shl ecx,3
 test ecx,ecx
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
