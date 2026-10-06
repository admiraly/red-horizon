default rel
%include "schemas/entity.inc"
%include "schemas/ground_motion.inc"
%ifdef WRECK_STANDALONE
section .bss align=64
global sim_entities,sim_count,sim_tick_count,sim_ground_motion
sim_entities: resb ENTITY_CAPACITY*ENTITY_STRIDE
sim_count: resd 1
sim_tick_count: resd 1
sim_ground_motion: resb ENTITY_CAPACITY*GROUND_STRIDE
%endif
section .text
extern wreck_register,wreck_hash
global probe_wreck_register
; EDI ID, RSI six-qword register observation pointer.
probe_wreck_register:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rsi
 mov [rsp+8],rsp
 mov ebx,0x123401
 mov ebp,0x123402
 mov r12d,0x123403
 mov r13d,0x123404
 mov r14d,0x123405
 mov r15d,0x123406
 call wreck_register
 mov rsi,[rsp]
 mov [rsi],rbx
 mov [rsi+8],rbp
 mov [rsi+16],r12
 mov [rsi+24],r13
 mov [rsi+32],r14
 mov [rsi+40],r15
 cmp rsp,[rsp+8]
 je .done
 mov eax,-99
.done:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
global probe_wreck_hash
probe_wreck_hash:
 mov rax,14695981039346656037
 mov r8,1099511628211
 jmp wreck_hash
section .bss align=8
global wreck_probe_alignment_errors
wreck_probe_alignment_errors: resq 1
section .text
%macro WRAPPER 1
extern __real_%1
global __wrap_%1
__wrap_%1:
 mov rax,rsp
 and eax,15
 cmp eax,8
 je %%aligned
 inc qword [wreck_probe_alignment_errors]
%%aligned:
 jmp __real_%1 wrt ..plt
%endmacro
WRAPPER ground_support
WRAPPER ground_contact
WRAPPER terrain_height
WRAPPER sinf
WRAPPER cosf
WRAPPER atan2f
section .note.GNU-stack noalloc noexec nowrite progbits
