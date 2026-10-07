; Fresh physical fighter observations and bounded last-seen extrapolation.
; Recall reads only the owner and its private record, never the enemy body.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_observation.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,sim_tick_count,world_los
section .bss align=64
global sim_air_observations
sim_air_observations: resb ENTITY_CAPACITY*AIR_OBSERVATION_STRIDE
section .rodata
zero: dd 0.0
one: dd 1.0
maximum: dd 8000.0
max_y: dd 1000.0
min_speed: dd 5.0
max_speed: dd 7.0
min_speed_sq: dd 24.9
max_speed_sq: dd 49.1
range_sq: dd AIR_OBSERVATION_RANGE_SQ
rear_cos_sq: dd AIR_OBSERVATION_REAR_COS_SQ
memory_ticks: dd AIR_OBSERVATION_MAX_AGE
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global air_observation_init,air_observation_capture,air_observation_goal,air_observation_hash
air_observation_init:
 lea rdi,[sim_air_observations]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*AIR_OBSERVATION_STRIDE/4
 rep stosd
 ret
; EDI physical ID; EAX1 valid, R8 entity/R9 aircraft, XMM2 speed squared.
valid_air:
 cmp edi,[sim_count]
 jae .bad
 cmp edi,ENTITY_CAPACITY
 jae .bad
 mov eax,edi
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 cmp dword [r8+ENTITY_HP],0
 je .bad
 cmp dword [r8+ENTITY_KIND],3
 jne .bad
 cmp dword [r8+ENTITY_SIDE],1
 ja .bad
 cmp dword [r8+ENTITY_FRONT],2
 ja .bad
 mov eax,edi
 shl eax,6
 lea r9,[sim_aircraft]
 add r9,rax
 mov eax,[r8+ENTITY_GENERATION]
 test eax,eax
 jz .bad
 cmp eax,[r9+AIR_GENERATION]
 jne .bad
 test dword [r9+AIR_FLAGS],AIR_ACTIVE
 jz .bad
 cmp dword [r9+AIR_ROLE],1
 ja .bad
 movss xmm0,[r9+AIR_SPEED]
 ucomiss xmm0,[min_speed]
 jp .bad
 jb .bad
 ucomiss xmm0,[max_speed]
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
 ucomiss xmm0,[max_y]
 jp .bad
 ja .bad
 xorps xmm2,xmm2
%macro velocity 1
 movss xmm0,[r9+%1]
 mulss xmm0,xmm0
 addss xmm2,xmm0
%endmacro
 velocity AIR_VX
 velocity AIR_VY
 velocity AIR_VZ
%unmacro velocity 1
 ucomiss xmm2,[min_speed_sq]
 jp .bad
 jb .bad
 ucomiss xmm2,[max_speed_sq]
 ja .bad
 mov eax,1
 ret
.bad:
 xor eax,eax
 ret
; EDI fighter, ESI candidate. EAX1 fresh visible capture,0 rejected atomically.
; Single actual world LOS after metadata,750m range and forward240degree cone.
air_observation_capture:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov r12d,edi
 mov r13d,esi
 call valid_air
 test eax,eax
 jz .none
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 jne .none
 cmp dword [r9+AIR_AMMO],0
 je .none
 mov rbx,r8
 mov rbp,r9
 movss [rsp],xmm2
 mov edi,r13d
 call valid_air
 test eax,eax
 jz .none
 mov r14,r8
 mov r15,r9
 mov eax,[rbx+ENTITY_SIDE]
 cmp eax,[r14+ENTITY_SIDE]
 je .none
 movss xmm0,[r14+ENTITY_X]
 subss xmm0,[rbx+ENTITY_X]
 movss xmm1,[r15+AIR_Y]
 subss xmm1,[rbp+AIR_Y]
 movss xmm2,[r14+ENTITY_Z]
 subss xmm2,[rbx+ENTITY_Z]
 movaps xmm3,xmm0
 mulss xmm3,xmm3
 movaps xmm4,xmm1
 mulss xmm4,xmm4
 addss xmm3,xmm4
 movaps xmm4,xmm2
 mulss xmm4,xmm4
 addss xmm3,xmm4
 ucomiss xmm3,[range_sq]
 ja .none
 ; Rear120degree sector is blind. Positive forward half always qualifies.
 mulss xmm0,[rbp+AIR_VX]
 mulss xmm1,[rbp+AIR_VY]
 addss xmm0,xmm1
 mulss xmm2,[rbp+AIR_VZ]
 addss xmm0,xmm2
 ucomiss xmm0,[zero]
 jae .los
 mulss xmm0,xmm0
 mulss xmm3,[rsp]
 mulss xmm3,[rear_cos_sq]
 ucomiss xmm0,xmm3
 ja .none
.los:
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbp+AIR_Y]
 movss xmm2,[rbx+ENTITY_Z]
 movss xmm3,[r14+ENTITY_X]
 movss xmm4,[r15+AIR_Y]
 movss xmm5,[r14+ENTITY_Z]
 call world_los
 test eax,eax
 jz .none
 mov eax,r12d
 shl eax,6
 lea rdi,[sim_air_observations]
 add rdi,rax
 mov eax,[r14+ENTITY_X]
 mov [rdi],eax
 mov eax,[r15+AIR_Y]
 mov [rdi+4],eax
 mov eax,[r14+ENTITY_Z]
 mov [rdi+8],eax
 mov eax,[r15+AIR_VX]
 mov [rdi+12],eax
 mov eax,[r15+AIR_VY]
 mov [rdi+16],eax
 mov eax,[r15+AIR_VZ]
 mov [rdi+20],eax
 mov eax,[rbx+ENTITY_GENERATION]
 mov [rdi+24],eax
 mov [rdi+28],r13d
 mov eax,[r14+ENTITY_GENERATION]
 mov [rdi+32],eax
 mov eax,[sim_tick_count]
 mov [rdi+36],eax
 mov dword [rdi+40],1
 mov eax,1
 jmp .done
.none:
 xor eax,eax
.done:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
; EDI owner. EAX1 goal, XMM0..2 estimated XYZ,XMM3..5 observed velocity,
; XMM6 linearly decaying confidence. EAX0/all zero on no valid observation.
; Pure recall: no target lookup, no cache mutation, at most one-second prediction.
air_observation_goal:
 push rbx
 mov ebx,edi
 call valid_air
 test eax,eax
 jz .none
 cmp dword [r9+AIR_ROLE],AIR_FIGHTER
 jne .none
 cmp dword [r9+AIR_AMMO],0
 je .none
 mov eax,ebx
 shl eax,6
 lea rsi,[sim_air_observations]
 add rsi,rax
 cmp dword [rsi+40],1
 jne .none
 mov eax,[r8+ENTITY_GENERATION]
 cmp eax,[rsi+24]
 jne .none
 cmp dword [rsi+28],ENTITY_CAPACITY
 jae .none
 cmp dword [rsi+32],0
 je .none
 mov eax,[sim_tick_count]
 sub eax,[rsi+36]
 cmp eax,AIR_OBSERVATION_MAX_AGE
 jae .none
 mov edx,eax
 cvtsi2ss xmm6,eax
 cvtsi2ss xmm8,dword [memory_ticks]
 divss xmm6,xmm8
 movss xmm7,[one]
 subss xmm7,xmm6
 movaps xmm6,xmm7
 cmp edx,AIR_OBSERVATION_PREDICT_TICKS
 jbe .prediction
 mov edx,AIR_OBSERVATION_PREDICT_TICKS
.prediction:
 cvtsi2ss xmm7,edx
 movss xmm0,[rsi]
 ucomiss xmm0,[zero]
 jp .none
 jb .none
 ucomiss xmm0,[maximum]
 ja .none
 movss xmm1,[rsi+4]
 movaps xmm8,xmm1
 andps xmm8,[abs_mask]
 ucomiss xmm8,[max_y]
 jp .none
 ja .none
 movss xmm2,[rsi+8]
 ucomiss xmm2,[zero]
 jp .none
 jb .none
 ucomiss xmm2,[maximum]
 ja .none
 movss xmm3,[rsi+12]
 movss xmm4,[rsi+16]
 movss xmm5,[rsi+20]
 movaps xmm8,xmm3
 mulss xmm8,xmm8
 movaps xmm9,xmm4
 mulss xmm9,xmm9
 addss xmm8,xmm9
 movaps xmm9,xmm5
 mulss xmm9,xmm9
 addss xmm8,xmm9
 ucomiss xmm8,[min_speed_sq]
 jp .none
 jb .none
 ucomiss xmm8,[max_speed_sq]
 ja .none
 movaps xmm8,xmm3
 mulss xmm8,xmm7
 addss xmm0,xmm8
 minss xmm0,[maximum]
 maxss xmm0,[zero]
 movaps xmm8,xmm4
 mulss xmm8,xmm7
 addss xmm1,xmm8
 minss xmm1,[max_y]
 maxss xmm1,[zero]
 mulss xmm7,xmm5
 addss xmm2,xmm7
 minss xmm2,[maximum]
 maxss xmm2,[zero]
 mov eax,1
 pop rbx
 ret
.none:
 xor eax,eax
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 xorps xmm2,xmm2
 xorps xmm3,xmm3
 xorps xmm4,xmm4
 xorps xmm5,xmm5
 xorps xmm6,xmm6
 pop rbx
 ret
air_observation_hash:
 lea rsi,[sim_air_observations]
 mov ecx,[sim_count]
 shl ecx,6
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
