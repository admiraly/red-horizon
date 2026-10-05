; Read-only, bounded physical escape/shelter goal selection. SysV ABI.
default rel
%include "schemas/entity.inc"
extern sim_entities,sim_count,terrain_obstacles,terrain_obstacle_count
extern terrain_blocked,terrain_path_clear,terrain_height,terrain_los
global hazard_choose_goal
section .rodata align=16
zero: dd 0.0
one: dd 1.0
two: dd 2.0
twelve: dd 12.0
maximum: dd 8000.0
max_radius: dd 512.0
max_step: dd 36.0
shelter_sq: dd 576.0
step_sq: dd 1296.0
huge: dd 1.0e20
epsilon: dd 0.0001
halfroot: dd 0.7071067812
health_limit: dd 100,400,160
align 16
abs_mask: dd 0x7fffffff,0,0,0
; Eight compass choices distribute co-located IDs deterministically.
directions: dd 1.0,0.0, 0.7071067812,0.7071067812, 0.0,1.0, -0.7071067812,0.7071067812
 dd -1.0,0.0, -0.7071067812,-0.7071067812, 0.0,-1.0, 0.7071067812,-0.7071067812
; Rotation cos/sin: straight, +/-45, +/-90 (no backwards escape).
rotations: dd 1.0,0.0, 0.7071067812,0.7071067812, 0.7071067812,-0.7071067812, 0.0,1.0, 0.0,-1.0
section .text
hazard_choose_goal:
 push rbx
 push r12
 push r13
 sub rsp,96
 ; Stack: center0/4 radius8,actor12/16,kind20,candidate24/28,
 ; best32/36 distance40, direction44/48,step52,old radialSq56,blastY60.
 mov r12d,edi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 cmp edi,[sim_count]
 jae .none
 cmp edi,ENTITY_CAPACITY
 jae .none
 shl edi,5
 lea rbx,[sim_entities]
 add rbx,rdi
 cmp dword [rbx+ENTITY_HP],0
 je .none
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,2
 ja .none
 lea rcx,[health_limit]
 mov edx,[rbx+ENTITY_HP]
 cmp edx,[rcx+rax*4]
 ja .none
 mov [rsp+20],eax
 ; Validate all coordinates and finite positive blast radius.
 xor ecx,ecx
.validate_center:
 movss xmm0,[rsp+rcx*4]
 ucomiss xmm0,[zero]
 jp .none
 jb .none
 ucomiss xmm0,[maximum]
 ja .none
 inc ecx
 cmp ecx,2
 jb .validate_center
 movss xmm0,[rsp+8]
 ucomiss xmm0,[zero]
 jp .none
 jbe .none
 ucomiss xmm0,[max_radius]
 ja .none
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 movss [rsp+12],xmm0
 movss [rsp+16],xmm1
 mov edi,[rsp+20]
 call terrain_blocked
 test eax,eax
 jnz .none
 movss xmm0,[rsp+12]
 subss xmm0,[rsp]
 movss xmm1,[rsp+16]
 subss xmm1,[rsp+4]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 mulss xmm2,xmm2
 mulss xmm3,xmm3
 addss xmm2,xmm3
 movss [rsp+56],xmm2
 sqrtss xmm3,xmm2
 ucomiss xmm3,[epsilon]
 jbe .center
 divss xmm0,xmm3
 divss xmm1,xmm3
 jmp .direction
.center:
 and r12d,7
 lea rax,[directions]
 movss xmm0,[rax+r12*8]
 movss xmm1,[rax+r12*8+4]
.direction:
 movss [rsp+44],xmm0
 movss [rsp+48],xmm1
 movss xmm0,[rsp+8]
 addss xmm0,[twelve]
 subss xmm0,xmm3
 ucomiss xmm0,[zero]
 jbe .none
 minss xmm0,[max_step]
 movss [rsp+52],xmm0
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 call terrain_height
 addss xmm0,[one]
 movss [rsp+60],xmm0
 movss xmm0,[huge]
 movss [rsp+40],xmm0
 xor r12d,r12d
 ; Static obstacle count is bounded in current terrain; clamp to16 defensively.
 mov r13d,[terrain_obstacle_count]
 cmp r13d,16
 jbe .obstacles
 mov r13d,16
.obstacles:
 cmp r12d,r13d
 jae .shelter_done
 mov eax,r12d
 shl eax,5
 lea rbx,[terrain_obstacles]
 add rbx,rax
 test dword [rbx+24],1
 jz .next_obstacle
 mov dword [rsp+64],0
.face:
 mov eax,[rsp+64]
 cmp eax,2
 jae .zface
 movss xmm0,[rbx]
 test eax,eax
 jz .xmin
 movss xmm0,[rbx+8]
 addss xmm0,[two]
 jmp .xface_z
.xmin:
 subss xmm0,[two]
.xface_z:
 movss xmm1,[rsp+16]
 maxss xmm1,[rbx+4]
 minss xmm1,[rbx+12]
 jmp .shelter_candidate
.zface:
 movss xmm1,[rbx+4]
 cmp eax,2
 je .zmin
 movss xmm1,[rbx+12]
 addss xmm1,[two]
 jmp .zface_x
.zmin:
 subss xmm1,[two]
.zface_x:
 movss xmm0,[rsp+12]
 maxss xmm0,[rbx]
 minss xmm0,[rbx+8]
.shelter_candidate:
 movss [rsp+24],xmm0
 movss [rsp+28],xmm1
 call .travel_squared
 ucomiss xmm0,[shelter_sq]
 ja .next_face
 ucomiss xmm0,[rsp+40]
 jae .next_face
 movss [rsp+68],xmm0
 call .clear_path
 test eax,eax
 jz .next_face
 movss xmm0,[rsp+24]
 movss xmm1,[rsp+28]
 call terrain_height
 addss xmm0,[two]
 movaps xmm4,xmm0
 movss xmm0,[rsp]
 movss xmm1,[rsp+60]
 movss xmm2,[rsp+4]
 movss xmm3,[rsp+24]
 movss xmm5,[rsp+28]
 call terrain_los
 test eax,eax
 jnz .next_face
 movss xmm0,[rsp+24]
 movss xmm1,[rsp+28]
 movss [rsp+32],xmm0
 movss [rsp+36],xmm1
 movss xmm0,[rsp+68]
 movss [rsp+40],xmm0
.next_face:
 inc dword [rsp+64]
 cmp dword [rsp+64],4
 jb .face
.next_obstacle:
 inc r12d
 jmp .obstacles
.shelter_done:
 movss xmm0,[rsp+40]
 ucomiss xmm0,[huge]
 jae .escape
 movss xmm0,[rsp+32]
 movss xmm1,[rsp+36]
 mov edx,2
 jmp .success
.escape:
 xor r12d,r12d
.rotation:
 lea rbx,[rotations]
 movss xmm2,[rbx+r12*8]
 movss xmm3,[rbx+r12*8+4]
 movss xmm0,[rsp+44]
 mulss xmm0,xmm2
 movss xmm1,[rsp+48]
 mulss xmm1,xmm3
 subss xmm0,xmm1
 movss xmm1,[rsp+44]
 mulss xmm1,xmm3
 mulss xmm2,[rsp+48]
 addss xmm1,xmm2
 mulss xmm0,[rsp+52]
 mulss xmm1,[rsp+52]
 addss xmm0,[rsp+12]
 addss xmm1,[rsp+16]
 movss [rsp+24],xmm0
 movss [rsp+28],xmm1
 subss xmm0,[rsp]
 subss xmm1,[rsp+4]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 subss xmm0,[rsp+56]
 ucomiss xmm0,[epsilon]
 jbe .next_rotation
 call .clear_path
 test eax,eax
 jnz .dispersion
.next_rotation:
 inc r12d
 cmp r12d,5
 jb .rotation
.none:
 mov eax,-1
 xor edx,edx
 jmp .done
.dispersion:
 movss xmm0,[rsp+24]
 movss xmm1,[rsp+28]
 mov edx,1
.success:
 xor eax,eax
.done:
 add rsp,96
 pop r13
 pop r12
 pop rbx
 ret
; Internal calls have return-address-adjusted stack positions.
.travel_squared:
 movss xmm0,[rsp+32]
 subss xmm0,[rsp+20]
 movss xmm1,[rsp+36]
 subss xmm1,[rsp+24]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ret
.clear_path:
 sub rsp,8
 movss xmm0,[rsp+28]
 movss xmm1,[rsp+32]
 movss xmm2,[rsp+40]
 movss xmm3,[rsp+44]
 call terrain_path_clear
 add rsp,8
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
