; Derived presentation only; no simulation writes.
default rel
%include "schemas/ground_visual.inc"
%include "schemas/ground_support.inc"
extern ground_support,ground_contact,suspension_step
section .rodata
zero: dd 0.0
max_dt: dd VISUAL_MAX_DT
jump_sq: dd VISUAL_JUMP_SQ
section .text
global ground_visual
ground_visual:
 test rdi,rdi
 jz .bad_leaf
 test rsi,rsi
 jz .bad_cache
 test edx,edx
 jz .bad_cache
 test r8d,r8d
 jz .bad_cache
 ucomiss xmm3,[zero]
 jp .bad_cache
 jb .bad_cache
 movd eax,xmm3
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .bad_cache
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,176
 mov r12,rdi
 mov r13,rsi
 mov r14d,edx
 mov r15d,ecx
 mov ebx,r8d
 movss [rsp+128],xmm0
 movss [rsp+132],xmm1
 movss [rsp+136],xmm2
 movss [rsp+140],xmm3
 mov esi,r15d
 mov edx,SUPPORT_STRIDE
 mov rdi,rsp
 call ground_support
 test eax,eax
 jnz .failed
 ; Only a continuous observed pose may carry a spring response forward.
 mov eax,ebx
 sub eax,[r12+VISUAL_FRAME]
 cmp eax,1
 ja .reset
 movss xmm0,[rsp+128]
 subss xmm0,[r12+VISUAL_X]
 mulss xmm0,xmm0
 movss xmm1,[rsp+132]
 subss xmm1,[r12+VISUAL_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[jump_sq]
 jp .reset
 ja .reset
 movss xmm1,[rsp+140]
 ucomiss xmm1,[max_dt]
 ja .reset
 ; Repeated same-frame draws reuse only matching, unchanged cached poses.
 test eax,eax
 jnz .step
 ucomiss xmm0,[zero]
 jne .reset
 mov dword [rsp+140],0 ; validate live cache without advancing spring
 jmp .step
.reset:
 mov dword [r12+SUSPENSION_FLAGS],0
.step:
 mov rdi,r12
 mov rsi,rsp
 mov edx,r14d
 mov ecx,r15d
 mov r8d,SUSPENSION_STRIDE
 movss xmm0,[rsp+140]
 minss xmm0,[max_dt]
 call suspension_step
 test eax,eax
 jnz .failed
.contact:
 lea rdi,[rsp+64]
 mov esi,r15d
 mov edx,SUPPORT_STRIDE
 movss xmm0,[rsp+128]
 movss xmm1,[rsp+132]
 movss xmm2,[rsp+136]
 movss xmm3,[r12+4]
 movss xmm4,[r12+8]
 call ground_contact
 test eax,eax
 jnz .failed
 movss xmm0,[r12]
 ucomiss xmm0,[rsp+64+SUPPORT_Y]
 jae .height_done
 movss xmm0,[rsp+64+SUPPORT_Y]
 movss [r12],xmm0
 movss xmm1,[r12+SUSPENSION_VELOCITY]
 maxss xmm1,[zero]
 movss [r12+SUSPENSION_VELOCITY],xmm1
.height_done:
 movss [rsp+64+SUPPORT_Y],xmm0
 mov [r12+VISUAL_FRAME],ebx
 mov eax,[rsp+128]
 mov [r12+VISUAL_X],eax
 mov eax,[rsp+132]
 mov [r12+VISUAL_Z],eax
 mov dword [r12+60],0
 movups xmm0,[rsp+64]
 movups xmm1,[rsp+80]
 movups xmm2,[rsp+96]
 movups xmm3,[rsp+112]
 movups [r13],xmm0
 movups [r13+16],xmm1
 movups [r13+32],xmm2
 movups [r13+48],xmm3
 xor eax,eax
 jmp .done
.failed:
 mov dword [r12+SUSPENSION_FLAGS],0
 mov eax,-1
.done:
 add rsp,176
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
.bad_cache:
 mov dword [rdi+SUSPENSION_FLAGS],0
.bad_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
