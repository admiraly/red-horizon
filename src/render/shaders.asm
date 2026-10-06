default rel
section .rodata
global battle_vertex_source,battle_fragment_source
; Vertex template keeps its 18-byte #version line first, followed by the
; generated canonical relief helper and the rest of the production source.
battle_vertex_source:
incbin "shaders/battle.vert",0,18
incbin "shaders/terrain_relief.glsl"
incbin "shaders/battle.vert",18
db 0
; Keep #version first: battle.frag is a GLSL template whose first line is 18 bytes.
; The generated canonical helper is embedded verbatim before the remaining body.
; incbin dependencies are tracked by the ordinary incremental assembler build.
battle_fragment_source:
incbin "shaders/battle.frag",0,18
incbin "shaders/terrain_roads.glsl"
incbin "shaders/battle.frag",18
db 0
section .note.GNU-stack noalloc noexec nowrite progbits
