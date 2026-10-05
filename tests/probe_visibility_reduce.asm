default rel
section .data
global view_width,view_height,sim_count,sim_tick_count
view_width: dd 320
view_height: dd 240
sim_count: dd 32768
sim_tick_count: dd 0
section .bss
global sim_entities
sim_entities: resb 32768*32
section .text
global sim_checksum
sim_checksum: xor eax,eax
ret
section .note.GNU-stack noalloc noexec nowrite progbits
