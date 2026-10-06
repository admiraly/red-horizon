; Read-only legacy gameplay eye transformed by unsmoothed terrain support.
default rel
%include "schemas/ground_eye.inc"
%include "schemas/ground_support.inc"
extern ground_support,ground_contact
section .rodata
anchor: dd EYE_LOCAL_HEIGHT
zero: dd 0.0
maximum: dd 8000.0
y_maximum: dd 2000.0
y_minimum: dd -2000.0
section .text
global ground_eye
; SysV caller-saved GPR/SIMD scratch; all nonvolatile GPRs preserved.
ground_eye:
 test rdi,rdi
 jz .invalid_leaf
 cmp edx,EYE_STRIDE
 jb .invalid_leaf
 push rbx
 sub rsp,176
 mov [rsp+152],rdi
 mov [rsp+140],esi
 movss [rsp+128],xmm0
 movss [rsp+132],xmm1
 movss [rsp+136],xmm2
 mov rdi,rsp
 mov edx,SUPPORT_STRIDE
 call ground_support
 test eax,eax
 jnz .invalid
 lea rdi,[rsp+64]
 mov esi,[rsp+140]
 mov edx,SUPPORT_STRIDE
 movss xmm0,[rsp+128]
 movss xmm1,[rsp+132]
 movss xmm2,[rsp+136]
 movss xmm3,[rsp+SUPPORT_PITCH]
 movss xmm4,[rsp+SUPPORT_BANK]
 call ground_contact
 test eax,eax
 jnz .invalid
 movss xmm0,[rsp+SUPPORT_UP]
 mulss xmm0,[anchor]
 addss xmm0,[rsp+128]
 movss [rsp+160],xmm0
 movss xmm1,[rsp+SUPPORT_UP+4]
 mulss xmm1,[anchor]
 movss xmm2,[rsp+SUPPORT_Y]
 maxss xmm2,[rsp+64+SUPPORT_Y]
 addss xmm1,xmm2
 movss [rsp+164],xmm1
 movss xmm2,[rsp+SUPPORT_UP+8]
 mulss xmm2,[anchor]
 addss xmm2,[rsp+132]
 movss [rsp+168],xmm2
 ucomiss xmm0,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 ucomiss xmm2,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm2,[maximum]
 ja .invalid
 ucomiss xmm1,[y_minimum]
 jp .invalid
 jb .invalid
 ucomiss xmm1,[y_maximum]
 ja .invalid
 mov rdi,[rsp+152]
 movss [rdi],xmm0
 movss [rdi+4],xmm1
 movss [rdi+8],xmm2
 xor eax,eax
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,176
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
