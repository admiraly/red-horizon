; Build with -DMULTIPLIER=1 or 2, optionally -DINCOMPATIBLE=1.
; update(RDI=host-owned state*) -> void; clobbers RAX, flags.
; No allocation, callbacks, module-owned persistent pointers or platform calls.
default rel
%include "abi.inc"
%ifndef MULTIPLIER
%define MULTIPLIER 1
%endif
section .rodata align=8
global rh_module_table
rh_module_table:
    dq RH_ABI
%ifdef INCOMPATIBLE
    dq RH_SCHEMA + 1
%else
    dq RH_SCHEMA
%endif
    dq update - rh_module_table
section .text
update:
    mov rax, [rdi + STATE_STEP]
    imul rax, MULTIPLIER
    add [rdi + STATE_VALUE], rax
    inc qword [rdi + STATE_TICKS]
    ret
section .note.GNU-stack noalloc noexec nowrite progbits
