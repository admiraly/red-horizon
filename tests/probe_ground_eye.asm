default rel
extern ground_eye, __real_ground_support, __real_ground_contact
section .text
global probe_ground_eye
; Same ABI, RCX additional six-qword preserved-register observation output.
probe_ground_eye:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rcx
 mov [rsp+8],rsp
 mov ebx,0x123401
 mov ebp,0x123402
 mov r12d,0x123403
 mov r13d,0x123404
 mov r14d,0x123405
 mov r15d,0x123406
 call ground_eye
 mov rcx,[rsp]
 mov [rcx],rbx
 mov [rcx+8],rbp
 mov [rcx+16],r12
 mov [rcx+24],r13
 mov [rcx+32],r14
 mov [rcx+40],r15
 cmp rsp,[rsp+8]
 je .ok
 mov eax,-99
.ok:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
; Test-only link wrappers: inspect entry alignment before tail-calling real ABI.
extern __real_sinf,__real_cosf,__real_terrain_height
section .bss align=8
global eye_probe_alignment_errors,eye_probe_height_calls
eye_probe_alignment_errors: resq 1
eye_probe_height_calls: resq 1
section .text
%macro ALIGN_WRAPPER 2
global %1
%1:
 mov rax,rsp
 and eax,15
 cmp eax,8
 je %%aligned
 inc qword [eye_probe_alignment_errors]
%%aligned:
 jmp %2 wrt ..plt
%endmacro
ALIGN_WRAPPER __wrap_sinf,__real_sinf
ALIGN_WRAPPER __wrap_cosf,__real_cosf
global __wrap_terrain_height
__wrap_terrain_height:
 inc qword [eye_probe_height_calls]
 mov rax,rsp
 and eax,15
 cmp eax,8
 je .aligned
 inc qword [eye_probe_alignment_errors]
.aligned:
 jmp __real_terrain_height wrt ..plt

section .text
ALIGN_WRAPPER __wrap_ground_support,__real_ground_support
ALIGN_WRAPPER __wrap_ground_contact,__real_ground_contact
