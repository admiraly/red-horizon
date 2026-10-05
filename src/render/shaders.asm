default rel
section .rodata
global battle_vertex_source,battle_fragment_source
battle_vertex_source: incbin "shaders/battle.vert"
db 0
battle_fragment_source: incbin "shaders/battle.frag"
db 0
section .note.GNU-stack noalloc noexec nowrite progbits
