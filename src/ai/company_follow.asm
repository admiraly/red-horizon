; Read-only bounded destination projection for follow formation slots.
%include "schemas/company_control.inc"
default rel
extern terrain_body_blocked
section .rodata
project_step: dd COMPANY_FOLLOW_PROJECT_STEP
section .text
global company_follow_place
; EDI ground role, XMM0/1 desired slot ->0 valid XZ or1 hold.
; Uses the actual conservative role footprint, solids and ground grade.
; Try original slot then at most four positions further behind; no allocation,
; pose/order/store writes, clocks, shared scratch or infinite search.
company_follow_place:
 push rbx
 sub rsp,32
 mov ebx,edi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 mov dword [rsp+8],0
.try:
 mov edi,ebx
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 call terrain_body_blocked
 test eax,eax
 jz .clear
 inc dword [rsp+8]
 cmp dword [rsp+8],COMPANY_FOLLOW_PROJECT_TRIES
 jae .hold
 movss xmm0,[rsp]
 subss xmm0,[project_step]
 movss [rsp],xmm0
 jmp .try
.clear:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 xor eax,eax
 jmp .done
.hold:
 mov eax,1
.done:
 add rsp,32
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
