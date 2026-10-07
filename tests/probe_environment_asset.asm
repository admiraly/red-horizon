; Development-only state for the standalone non-GL asset/weather probe.
; The production client links the real HDR owner; these checks never render.
default rel
section .bss
global hdr_world_linear
hdr_world_linear: resd 1
section .note.GNU-stack noalloc noexec nowrite progbits
