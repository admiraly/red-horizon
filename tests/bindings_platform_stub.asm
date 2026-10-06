; Development-only platform call recorder; never linked into game executables.
default rel
section .bss
global probe_binding_device,probe_binding_code,probe_binding_window
probe_binding_device: resd 1
probe_binding_code: resd 1
probe_binding_window: resq 1
section .text
global glfwGetKey,glfwGetMouseButton
glfwGetKey:
 mov dword [probe_binding_device],0
 jmp record
glfwGetMouseButton:
 mov dword [probe_binding_device],1
record:
 mov [probe_binding_code],esi
 mov [probe_binding_window],rdi
 mov eax,1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
