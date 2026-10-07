; Fixed friendly-radio snapshot and finite right-turn convergence avoidance.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_separation.inc"
%include "schemas/air_flight.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,sim_tick_count
section .bss align=64
global sim_air_separation,air_separation_metrics
sim_air_separation: resb ENTITY_CAPACITY*16
poses: resb ENTITY_CAPACITY*32
heads: resd 2048
links: resd ENTITY_CAPACITY
ready: resd 1
clock: resd 1
air_separation_metrics: resq 5 ; builds,queries,cells,candidates,warnings
section .rodata
zero: dd 0.0
range2: dd AIR_SEPARATION_RANGE_SQ
miss2: dd AIR_SEPARATION_MISS_SQ
horizon: dd AIR_SEPARATION_PREDICT_TICKS
scale: dd 0.004
negative: dd -1.0
min_speed2: dd AIR_FLIGHT_MIN_SPEED_SQ
max_speed2: dd AIR_FLIGHT_MAX_SPEED_SQ
section .text
global air_separation_init,air_separation_build,air_separation_query,air_separation_step,air_separation_hash
air_separation_init:
 lea rdi,[sim_air_separation]
 xor eax,eax
 mov ecx,(ENTITY_CAPACITY*16+ENTITY_CAPACITY*32+2048*4+ENTITY_CAPACITY*4+8+40)/4
 rep stosd
 ret
; EDIphysical owner; EAX0invalid/1valid,R9 air,R10entity, preserves nonvolatile.
valid:
 cmp edi,[sim_count]
 jae .bad
 cmp edi,ENTITY_CAPACITY
 jae .bad
 mov eax,edi
 shl eax,5
 lea r10,[sim_entities]
 add r10,rax
 shl eax,1
 lea r9,[sim_aircraft]
 add r9,rax
 cmp dword [r10+ENTITY_HP],0
 je .bad
 cmp dword [r10+ENTITY_KIND],3
 jne .bad
 cmp dword [r10+ENTITY_SIDE],1
 ja .bad
 cmp dword [r10+ENTITY_FRONT],2
 ja .bad
 mov eax,[r10+ENTITY_GENERATION]
 test eax,eax
 jz .bad
 cmp eax,[r9+AIR_GENERATION]
 jne .bad
 test dword [r9+AIR_FLAGS],AIR_ACTIVE
 jz .bad
 cmp dword [r9+AIR_ROLE],1
 ja .bad
%macro coord 1
 mov eax,[r10+%1]
 test eax,eax
 js .bad
 cmp eax,__float32__(8000.0)
 ja .bad
%endmacro
 coord ENTITY_X
 coord ENTITY_Z
%unmacro coord 1
 mov eax,[r9+AIR_Y]
 and eax,0x7fffffff
 cmp eax,__float32__(1000.0)
 ja .bad
 xorps xmm2,xmm2
%macro velocity 1
 mov eax,[r9+%1]
 and eax,0x7fffffff
 cmp eax,__float32__(AIR_FLIGHT_MAX_SPEED)
 ja .bad
 movss xmm0,[r9+%1]
 mulss xmm0,xmm0
 addss xmm2,xmm0
%endmacro
 velocity AIR_VX
 velocity AIR_VY
 velocity AIR_VZ
%unmacro velocity 1
 ucomiss xmm2,[min_speed2]
 jb .bad
 ucomiss xmm2,[max_speed2]
 ja .bad
 mov eax,1
 ret
.bad:
 xor eax,eax
 ret
air_separation_build:
 push rbx
 push r12
 sub rsp,8
 mov dword [ready],0
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .done
 lea rdi,[heads]
 mov eax,-1
 mov ecx,2048
 rep stosd
 xor r12d,r12d
.loop:
 mov eax,r12d
 shl eax,5
 lea rbx,[poses]
 add rbx,rax
 mov dword [rbx+24],0
 mov edi,r12d
 call valid
 test eax,eax
 jz .next
 movss xmm0,[r10+ENTITY_X]
 movss [rbx],xmm0
 mulss xmm0,[scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .x
 mov eax,31
.x:
 mov edx,eax
 movss xmm0,[r10+ENTITY_Z]
 movss [rbx+8],xmm0
 mulss xmm0,[scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .z
 mov eax,31
.z:
 shl eax,5
 add eax,edx
 mov ecx,[r10+ENTITY_SIDE]
 shl ecx,10
 add eax,ecx
 lea rcx,[heads]
 mov edx,[rcx+rax*4]
 mov [rcx+rax*4],r12d
 lea rcx,[links]
 mov [rcx+r12*4],edx
 movss xmm0,[r9+AIR_Y]
 movss [rbx+4],xmm0
 movups xmm0,[r9+AIR_VX]
 movups [rbx+12],xmm0
 mov eax,[r10+ENTITY_GENERATION]
 mov [rbx+24],eax
 mov eax,[r10+ENTITY_SIDE]
 mov [rbx+28],eax
.next:
 inc r12d
 cmp r12d,[sim_count]
 jb .loop
 mov eax,[sim_tick_count]
 mov [clock],eax
 mov dword [ready],1
 inc qword [air_separation_metrics]
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
; EDIowner -> EAX nearest predicted converging friendly ID/-1.
; Snapshot-only query, no enemy/living records read; derived metrics only.
air_separation_query:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 mov r12d,edi
 cmp edi,[sim_count]
 jae .none
 cmp edi,ENTITY_CAPACITY
 jae .none
 cmp dword [ready],1
 jne .none
 mov eax,[sim_tick_count]
 cmp eax,[clock]
 jne .none
 mov eax,edi
 shl eax,5
 lea rbx,[poses]
 add rbx,rax
 cmp dword [rbx+24],0
 je .none
 inc qword [air_separation_metrics+8]
 movss xmm0,[rbx]
 mulss xmm0,[scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .cx
 mov eax,31
.cx:
 mov [rsp],eax
 movss xmm0,[rbx+8]
 mulss xmm0,[scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .cz
 mov eax,31
.cz:
 mov [rsp+4],eax
 mov eax,[clock]
 add eax,r12d
 xor edx,edx
 mov ecx,25
 div ecx
 mov [rsp+8],edx
 mov dword [rsp+12],0
 movss xmm0,[miss2]
 movss [rsp+16],xmm0
 mov ebp,-1
 xor r13d,r13d
.cells:
 mov eax,[rsp+8]
 add eax,r13d
 cmp eax,25
 jb .mod
 sub eax,25
.mod:
 xor edx,edx
 mov ecx,5
 div ecx
 sub eax,2
 add eax,[rsp+4]
 cmp eax,31
 ja .next_cell
 sub edx,2
 add edx,[rsp]
 cmp edx,31
 ja .next_cell
 shl eax,5
 add eax,edx
 mov ecx,[rbx+28]
 shl ecx,10
 add eax,ecx
 inc qword [air_separation_metrics+16]
 lea rcx,[heads]
 mov r14d,[rcx+rax*4]
.chain:
 cmp r14d,-1
 je .next_cell
 cmp dword [rsp+12],AIR_SEPARATION_CANDIDATES
 jae .answer
 inc dword [rsp+12]
 inc qword [air_separation_metrics+24]
 cmp r14d,r12d
 je .next_link
 mov eax,r14d
 shl eax,5
 lea r15,[poses]
 add r15,rax
 mov eax,[r15+28]
 cmp eax,[rbx+28]
 jne .next_link
 ; Relative displacement in XMM0..2 and relative velocity in3..5.
 movss xmm0,[r15]
 subss xmm0,[rbx]
 movss xmm1,[r15+4]
 subss xmm1,[rbx+4]
 movss xmm2,[r15+8]
 subss xmm2,[rbx+8]
 movaps xmm6,xmm0
 mulss xmm6,xmm0
 movaps xmm7,xmm1
 mulss xmm7,xmm1
 addss xmm6,xmm7
 movaps xmm7,xmm2
 mulss xmm7,xmm2
 addss xmm6,xmm7
 ucomiss xmm6,[range2]
 ja .next_link
 movss xmm3,[r15+12]
 subss xmm3,[rbx+12]
 movss xmm4,[r15+16]
 subss xmm4,[rbx+16]
 movss xmm5,[r15+20]
 subss xmm5,[rbx+20]
 movaps xmm6,xmm0
 mulss xmm6,xmm3
 movaps xmm7,xmm1
 mulss xmm7,xmm4
 addss xmm6,xmm7
 movaps xmm7,xmm2
 mulss xmm7,xmm5
 addss xmm6,xmm7
 ucomiss xmm6,[zero]
 jae .next_link ; no separating/parallel/overlapping-birth warning
 mulss xmm6,[negative]
 movaps xmm7,xmm3
 mulss xmm7,xmm3
 movaps xmm8,xmm4
 mulss xmm8,xmm4
 addss xmm7,xmm8
 movaps xmm8,xmm5
 mulss xmm8,xmm5
 addss xmm7,xmm8
 divss xmm6,xmm7
 ucomiss xmm6,[horizon]
 ja .next_link
 mulss xmm3,xmm6
 addss xmm0,xmm3
 mulss xmm4,xmm6
 addss xmm1,xmm4
 mulss xmm5,xmm6
 addss xmm2,xmm5
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 mulss xmm2,xmm2
 addss xmm0,xmm1
 addss xmm0,xmm2
 ucomiss xmm0,[rsp+16]
 ja .next_link
 jb .choose
 cmp ebp,-1
 je .choose
 cmp r14d,ebp
 jae .next_link
.choose:
 movss [rsp+16],xmm0
 mov ebp,r14d
.next_link:
 lea rcx,[links]
 mov r14d,[rcx+r14*4]
 jmp .chain
.next_cell:
 inc r13d
 cmp r13d,25
 jb .cells
.answer:
 mov eax,ebp
 jmp .done
.none:
 mov eax,-1
.done:
 add rsp,40
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
; EDIowner,ESIblocked by urgent defence ->EAX remaining finite avoidance.
air_separation_step:
 push rbx
 push r12
 sub rsp,8
 mov r12d,edi
 mov ebx,esi
 call valid
 test eax,eax
 jz .none
 mov eax,r12d
 shl eax,4
 lea r11,[sim_air_separation]
 add r11,rax
 mov eax,[r10+ENTITY_GENERATION]
 cmp eax,[r11]
 je .generation
 mov [r11],eax
 mov qword [r11+4],0
 mov dword [r11+12],-1
.generation:
 mov eax,[sim_tick_count]
 cmp eax,[r11+12]
 je .answer
 mov [r11+12],eax
 cmp dword [r11+4],0
 je .cooldown
 dec dword [r11+4]
.cooldown:
 cmp dword [r11+8],0
 je .query
 dec dword [r11+8]
 jmp .answer
.query:
 test ebx,ebx
 jnz .answer
 mov edi,r12d
 call air_separation_query
 cmp eax,-1
 je .none
 mov eax,r12d
 shl eax,6
 lea r9,[sim_aircraft]
 add r9,rax
 mov eax,r12d
 shl eax,4
 lea r11,[sim_air_separation]
 add r11,rax
 mov eax,AIR_SEPARATION_FIGHTER_TICKS
 mov edx,AIR_SEPARATION_FIGHTER_REFRACTORY
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 je .commit
 mov eax,AIR_SEPARATION_BOMBER_TICKS
 mov edx,AIR_SEPARATION_BOMBER_REFRACTORY
.commit:
 mov [r11+4],eax
 mov [r11+8],edx
 inc qword [air_separation_metrics+32]
.answer:
 mov eax,[r11+4]
 jmp .done
.none:
 xor eax,eax
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
air_separation_hash:
 lea rsi,[sim_air_separation]
 mov ecx,[sim_count]
 shl ecx,4
 test ecx,ecx
 jz .done
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .loop
.done:
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
