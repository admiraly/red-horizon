; Read-only prospective stopping path on the selected facility's runway.
%include "schemas/aircraft.inc"
%include "schemas/air_rollout.inc"
default rel
extern air_base_goal,air_bases,sim_aircraft,terrain_height
extern air_ground_speed_step,air_world_sweep
section .rodata
one: dd 1.0
minus: dd -1.0
maximum: dd AIR_ROLLOUT_MAX_SPEED
grade_limit: dd AIR_ROLLOUT_MAX_GRADE
height: dd AIR_ROLLOUT_CENTER_HEIGHT
margin: dd AIR_ROLLOUT_EDGE_MARGIN
align 16
absolute_mask: dd 0x7fffffff,0,0,0
section .text
global air_rollout_clear
; EDI own aircraft ID, ESI selected base, XMM0 planned touchdown speed.
; -> 1clear,0unsafe,-1invalid/source. No writes outside private stack.
; One-metre forward terrain grade sample, semi-implicit braking, actual
; ground-height endpoints and production swept4m hull. At most300 steps.
; This admission forecast does not put aircraft onto their wheels.
air_rollout_clear:
 push rbx
 push r12
 push r13
 sub rsp,96
 mov ebx,edi
 mov r12d,esi
 cmp esi,6
 jae .invalid
 xorps xmm1,xmm1
 ucomiss xmm0,xmm1
 jp .invalid
 jbe .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 movss [rsp+12],xmm0
 call air_base_goal
 cmp eax,r12d
 jne .invalid
 movss [rsp+8],xmm1 ; runway Z
 movss [rsp+36],xmm0 ; centre X
 mov eax,ebx
 shl eax,6
 lea rdx,[sim_aircraft]
 mov eax,[rdx+rax+AIR_ROLE]
 mov [rsp+32],eax
 movss xmm2,[minus]
 cmp r12d,3
 jb .direction
 movss xmm2,[one]
.direction:
 movss [rsp+40],xmm2
 mov eax,r12d
 shl eax,5
 lea rdx,[air_bases]
 movss xmm1,[rdx+rax+8]
 subss xmm1,[margin]
 movss [rsp+44],xmm1 ; usable half length
 mulss xmm1,xmm2
 subss xmm0,xmm1 ; start upstream, five metres inside runway
 movss [rsp],xmm0
 movss xmm1,[rsp+8]
 call terrain_height
 movss [rsp+48],xmm0 ; old terrain height
 addss xmm0,[height]
 movss [rsp+4],xmm0
 mov r13d,AIR_ROLLOUT_MAX_TICKS
.tick:
 ; Signed grade sampled one metre in flight direction.
 movss xmm0,[rsp]
 addss xmm0,[rsp+40]
 movss xmm1,[rsp+8]
 call terrain_height
 subss xmm0,[rsp+48]
 movss [rsp+52],xmm0
 movaps xmm1,xmm0
 andps xmm1,[absolute_mask]
 ucomiss xmm1,[grade_limit]
 jp .invalid
 ja .unsafe
 movaps xmm1,xmm0
 movss xmm0,[rsp+12]
 mov edi,[rsp+32]
 call air_ground_speed_step
 test eax,eax
 js .invalid
 movss [rsp+12],xmm0
 ; Convert total speed into horizontal distance at sampled ground grade.
 movss xmm1,[rsp+52]
 mulss xmm1,xmm1
 addss xmm1,[one]
 sqrtss xmm1,xmm1
 divss xmm0,xmm1
 mulss xmm0,[rsp+40]
 addss xmm0,[rsp]
 movss [rsp+16],xmm0
 subss xmm0,[rsp+36]
 andps xmm0,[absolute_mask]
 ucomiss xmm0,[rsp+44]
 ja .unsafe
 movss xmm0,[rsp+16]
 movss xmm1,[rsp+8]
 call terrain_height
 movss [rsp+56],xmm0
 addss xmm0,[height]
 movss [rsp+20],xmm0
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+16]
 movss xmm4,[rsp+20]
 movaps xmm5,xmm2
 lea rdi,[rsp+64]
 mov esi,16
 call air_world_sweep
 test eax,eax
 js .invalid
 jnz .unsafe
 mov eax,[rsp+16]
 mov [rsp],eax
 mov eax,[rsp+20]
 mov [rsp+4],eax
 mov eax,[rsp+56]
 mov [rsp+48],eax
 xorps xmm0,xmm0
 ucomiss xmm0,[rsp+12]
 je .clear
 dec r13d
 jnz .tick
.unsafe:
 xor eax,eax
 jmp .done
.invalid:
 mov eax,-1
 jmp .done
.clear:
 mov eax,1
.done:
 add rsp,96
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
