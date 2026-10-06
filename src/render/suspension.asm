; Caller-owned, bounded cosmetic critical-damping response; no authority writes.
default rel
%include "schemas/suspension.inc"
extern expf
section .rodata align=16
zero: dd 0.0
max_dt: dd 0.1
max_time: dd 86400.0
position_limits: dd SUSPENSION_Y_LIMIT,SUSPENSION_ANGLE_LIMIT,SUSPENSION_ANGLE_LIMIT
velocity_limits: dd SUSPENSION_Y_VELOCITY_LIMIT,SUSPENSION_ANGLE_VELOCITY_LIMIT,SUSPENSION_ANGLE_VELOCITY_LIMIT
omegas: dd SUSPENSION_Y_OMEGA,SUSPENSION_PITCH_OMEGA,SUSPENSION_BANK_OMEGA
signbit: dd 0x80000000,0,0,0
absmask: dd 0x7fffffff,0,0,0
section .text
global suspension_step
suspension_step:
 test rdi,rdi
 jz .invalid_leaf
 test rsi,rsi
 jz .invalid_leaf
 test edx,edx
 jz .invalid_leaf
 cmp ecx,1
 jb .invalid_leaf
 cmp ecx,2
 ja .invalid_leaf
 cmp r8d,SUSPENSION_STRIDE
 jb .invalid_leaf
 ucomiss xmm0,[zero]
 jp .invalid_leaf
 jb .invalid_leaf
 ucomiss xmm0,[max_dt]
 ja .invalid_leaf
 cmp dword [rdi+SUSPENSION_FLAGS],1
 ja .invalid_leaf
 push rbx
 sub rsp,112
 mov [rsp+96],rdi
 mov [rsp+104],edx
 mov [rsp+108],ecx
 movss [rsp+80],xmm0
 ; Snapshot targets before any possible publishing, including overlapping memory.
 movss xmm1,[rsi]
 movss [rsp+48],xmm1
 movss xmm1,[rsi+4]
 movss [rsp+52],xmm1
 movss xmm1,[rsi+8]
 movss [rsp+56],xmm1
 xor ebx,ebx
.target_validate:
 movss xmm1,[rsp+48+rbx*4]
 andps xmm1,[absmask]
 lea rax,[position_limits]
 ucomiss xmm1,[rax+rbx*4]
 jp .invalid
 ja .invalid
 inc ebx
 cmp ebx,3
 jb .target_validate
 cmp dword [rdi+SUSPENSION_FLAGS],0
 je .initialize
 cmp [rdi+SUSPENSION_GENERATION],edx
 jne .initialize
 cmp [rdi+SUSPENSION_KIND],ecx
 jne .initialize
 ; Only matching active stamps may read live positions, velocities and time.
 xor ebx,ebx
.state_validate:
 movss xmm1,[rdi+rbx*4]
 andps xmm1,[absmask]
 lea rax,[position_limits]
 ucomiss xmm1,[rax+rbx*4]
 jp .invalid
 ja .invalid
 movss xmm1,[rdi+12+rbx*4]
 andps xmm1,[absmask]
 lea rax,[velocity_limits]
 ucomiss xmm1,[rax+rbx*4]
 jp .invalid
 ja .invalid
 inc ebx
 cmp ebx,3
 jb .state_validate
 movss xmm1,[rdi+SUSPENSION_TIME]
 ucomiss xmm1,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[max_time]
 ja .invalid
 ucomiss xmm0,[zero]
 je .unchanged
 movups xmm1,[rdi]
 movups [rsp],xmm1
 movups xmm1,[rdi+16]
 movups [rsp+16],xmm1
 movups xmm1,[rdi+32]
 movups [rsp+32],xmm1
 xor ebx,ebx
.axis:
 lea rax,[omegas]
 movss xmm0,[rax+rbx*4]
 movss [rsp+60],xmm0
 mulss xmm0,[rsp+80]
 xorps xmm0,[signbit]
 call expf wrt ..plt
 movss [rsp+64],xmm0
 movss xmm1,[rsp+rbx*4]
 subss xmm1,[rsp+48+rbx*4] ; q
 movss xmm2,[rsp+60]
 mulss xmm2,xmm1
 addss xmm2,[rsp+12+rbx*4] ; k
 movss xmm3,[rsp+80]
 mulss xmm3,xmm2
 addss xmm1,xmm3
 mulss xmm1,xmm0
 addss xmm1,[rsp+48+rbx*4]
 lea rax,[position_limits]
 movss xmm3,[rax+rbx*4]
 minss xmm1,xmm3
 xorps xmm3,[signbit]
 maxss xmm1,xmm3
 movss [rsp+rbx*4],xmm1
 mulss xmm2,[rsp+60]
 mulss xmm2,[rsp+80]
 movss xmm1,[rsp+12+rbx*4]
 subss xmm1,xmm2
 mulss xmm1,xmm0
 lea rax,[velocity_limits]
 movss xmm3,[rax+rbx*4]
 minss xmm1,xmm3
 xorps xmm3,[signbit]
 maxss xmm1,xmm3
 movss [rsp+12+rbx*4],xmm1
 inc ebx
 cmp ebx,3
 jb .axis
 movss xmm0,[rsp+32]
 addss xmm0,[rsp+80]
 minss xmm0,[max_time]
 movss [rsp+32],xmm0
 mov qword [rsp+40],0
 jmp .publish
.initialize:
 movss xmm0,[rsp+48]
 movss [rsp],xmm0
 movss xmm0,[rsp+52]
 movss [rsp+4],xmm0
 movss xmm0,[rsp+56]
 movss [rsp+8],xmm0
 mov dword [rsp+12],0
 mov qword [rsp+16],0
 mov eax,[rsp+104]
 mov [rsp+24],eax
 mov eax,[rsp+108]
 mov [rsp+28],eax
 mov dword [rsp+32],0
 mov dword [rsp+36],SUSPENSION_ACTIVE
 mov qword [rsp+40],0
.publish:
 mov rdi,[rsp+96]
 movups xmm0,[rsp]
 movups xmm1,[rsp+16]
 movups xmm2,[rsp+32]
 movups [rdi],xmm0
 movups [rdi+16],xmm1
 movups [rdi+32],xmm2
.unchanged:
 xor eax,eax
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,112
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
