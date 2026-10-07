; Generation-safe cosmetic aim from the actual physically visible decision.
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/infantry_aim.inc"
default rel
extern sim_entities,sim_players,sim_player_vehicle,sim_count,sim_tick_count
extern sim_entity_height,atan2f
section .bss align=64
global infantry_aims
infantry_aims: resb ENTITY_CAPACITY*INFANTRY_AIM_STRIDE
section .rodata
zero: dd 0.0
maximum: dd 8000.0
min_y: dd -2000.0
max_y: dd 2000.0
range_sq: dd 57600.0
pi: dd 3.141593
pitch_max: dd 1.570797
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global infantry_aim_init,infantry_aim_mark,infantry_aim_shot,infantry_aim_pose
infantry_aim_init:
 lea rdi,[infantry_aims]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*INFANTRY_AIM_STRIDE/8
 rep stosq
 ret
; EDI source,ESI known visible target ID,EDX0 army/1 human. Caller owns LOS.
; Returns0 publication/-1invalid; read-only gates before complete publication.
infantry_aim_mark:
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,32
 cmp edx,1
 ja .bad
 mov r14d,edx
 mov r13d,esi
 call aim_source
 test eax,eax
 jnz .bad
 mov r12d,edi
 mov rbx,r8
 mov eax,edi
 shl eax,5
 lea r15,[infantry_aims]
 add r15,rax
 test r14d,r14d
 jnz .human
 cmp r13d,[sim_count]
 jae .bad
 mov eax,r13d
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .bad
 mov eax,[rbx+ENTITY_SIDE]
 xor eax,1
 cmp [rdx+ENTITY_SIDE],eax
 jne .bad
 cmp dword [rdx+ENTITY_KIND],2
 ja .bad
 cmp dword [rdx+ENTITY_GENERATION],0
 je .bad
 movss xmm0,[rdx+ENTITY_X]
 movss xmm1,[rdx+ENTITY_Z]
 call aim_xz
 test eax,eax
 jnz .bad
 movss [rsp],xmm0
 movss [rsp+8],xmm1
 mov edi,r13d
 call sim_entity_height
 movss [rsp+4],xmm0
 jmp .compute
.human:
 cmp dword [rbx+ENTITY_SIDE],1
 jne .bad
 cmp r13d,PLAYER_CAPACITY
 jae .bad
 mov eax,r13d
 shl eax,6
 lea rdx,[sim_players]
 add rdx,rax
 cmp dword [rdx+PLAYER_CONNECTED],1
 jne .bad
 cmp dword [rdx+PLAYER_HP],0
 je .bad
 cmp dword [rdx+PLAYER_HP],100
 ja .bad
 cmp dword [rdx+PLAYER_GENERATION],0
 je .bad
 lea rcx,[sim_player_vehicle]
 cmp dword [rcx+r13*4],-1
 jne .bad
 movss xmm0,[rdx+PLAYER_X]
 movss xmm1,[rdx+PLAYER_Z]
 call aim_xz
 test eax,eax
 jnz .bad
 movss [rsp],xmm0
 movss [rsp+8],xmm1
 mov eax,[rdx+PLAYER_Y]
 mov [rsp+4],eax
.compute:
 movss xmm0,[rsp+4]
 ucomiss xmm0,[min_y]
 jp .bad
 jb .bad
 ucomiss xmm0,[max_y]
 ja .bad
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 call aim_xz
 test eax,eax
 jnz .bad
 movss xmm2,[rsp]
 subss xmm2,xmm0
 movss [rsp+12],xmm2
 movss xmm3,[rsp+8]
 subss xmm3,xmm1
 movss [rsp+16],xmm3
 mulss xmm2,xmm2
 mulss xmm3,xmm3
 addss xmm2,xmm3
 ucomiss xmm2,[range_sq]
 ja .bad
 sqrtss xmm2,xmm2
 movss [rsp+20],xmm2
 mov edi,r12d
 call sim_entity_height
 ucomiss xmm0,[min_y]
 jp .bad
 jb .bad
 ucomiss xmm0,[max_y]
 ja .bad
 movss xmm1,[rsp+4]
 subss xmm1,xmm0
 movss [rsp+24],xmm1
 movss xmm0,[rsp+12]
 movss xmm1,[rsp+16]
 call atan2f wrt ..plt
 movss [rsp+28],xmm0
 movss xmm0,[rsp+24]
 movss xmm1,[rsp+20]
 call atan2f wrt ..plt
 movss [r15+INFANTRY_AIM_PITCH],xmm0
 mov eax,[rsp+28]
 mov [r15+INFANTRY_AIM_HEADING],eax
 mov eax,[rbx+ENTITY_GENERATION]
 mov [r15+INFANTRY_AIM_GENERATION],eax
 mov eax,[sim_tick_count]
 mov [r15+INFANTRY_AIM_TICK],eax
 mov eax,[rsp]
 mov [r15+INFANTRY_AIM_X],eax
 mov eax,[rsp+4]
 mov [r15+INFANTRY_AIM_Y],eax
 mov eax,[rsp+8]
 mov [r15+INFANTRY_AIM_Z],eax
 lea eax,[r14*2+INFANTRY_AIM_ACTIVE]
 mov [r15+INFANTRY_AIM_FLAGS],eax
 xor eax,eax
 jmp .done
.bad:mov eax,-1
.done:
 add rsp,32
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
; Sole successful shot gate calls this; absent/stale observations stay absent.
infantry_aim_shot:
 sub rsp,8
 call aim_source
 add rsp,8
 test eax,eax
 jnz .return
 mov eax,edi
 shl eax,5
 lea rdx,[infantry_aims]
 add rdx,rax
 mov eax,[r8+ENTITY_GENERATION]
 cmp eax,[rdx+INFANTRY_AIM_GENERATION]
 jne .return
 mov eax,[sim_tick_count]
 cmp eax,[rdx+INFANTRY_AIM_TICK]
 jne .return
 test dword [rdx+INFANTRY_AIM_FLAGS],INFANTRY_AIM_ACTIVE
 jz .return
 or dword [rdx+INFANTRY_AIM_FLAGS],INFANTRY_AIM_SHOT
.return:ret
; EDI actor,ESI presentation tick ->EAXflags0inactive,EDXage,XMM0heading,XMM1pitch.
; Every validity failure returns inactive; no array/body/authority mutation.
infantry_aim_pose:
 mov ecx,edx
 test ecx,ecx
 jz .inactive
 cmp ecx,INFANTRY_AIM_REMOTE_MAX_AGE
 ja .inactive
 sub rsp,8
 call aim_source
 add rsp,8
 test eax,eax
 jnz .inactive
 mov eax,edi
 shl eax,5
 lea r9,[infantry_aims]
 add r9,rax
 mov eax,[r8+ENTITY_GENERATION]
 cmp eax,[r9+INFANTRY_AIM_GENERATION]
 jne .inactive
 mov eax,[r9+INFANTRY_AIM_FLAGS]
 test eax,INFANTRY_AIM_ACTIVE
 jz .inactive
 cmp eax,7
 ja .inactive
 mov edx,esi
 sub edx,[r9+INFANTRY_AIM_TICK]
 cmp edx,ecx
 jae .inactive
 movss xmm0,[r9+INFANTRY_AIM_HEADING]
 movaps xmm2,xmm0
 andps xmm2,[abs_mask]
 ucomiss xmm2,[pi]
 jp .inactive
 ja .inactive
 movss xmm1,[r9+INFANTRY_AIM_PITCH]
 movaps xmm2,xmm1
 andps xmm2,[abs_mask]
 ucomiss xmm2,[pitch_max]
 jp .inactive
 ja .inactive
 ret
.inactive:
 xor eax,eax
 xor edx,edx
 xorps xmm0,xmm0
 xorps xmm1,xmm1
 ret
aim_source:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .bad
 cmp edi,[sim_count]
 jae .bad
 mov eax,edi
 shl eax,5
 lea r8,[sim_entities]
 add r8,rax
 cmp dword [r8+ENTITY_KIND],0
 jne .bad
 cmp dword [r8+ENTITY_HP],0
 je .bad
 cmp dword [r8+ENTITY_SIDE],1
 ja .bad
 cmp dword [r8+ENTITY_GENERATION],0
 je .bad
 xor eax,eax
 ret
.bad:mov eax,-1
 ret
aim_xz:
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 ucomiss xmm1,[zero]
 jp .bad
 jb .bad
 ucomiss xmm1,[maximum]
 ja .bad
 xor eax,eax
 ret
.bad:mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
