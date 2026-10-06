default rel
section .rodata
global mesh_vertex_source,mesh_fragment_source
; Vertex template keeps its 18-byte #version line first, followed by the
; generated canonical relief helper and the rest of the production source.
mesh_vertex_source:
incbin "shaders/mesh.vert",0,18
incbin "shaders/terrain_relief.glsl"
incbin "shaders/mesh.vert",18
db 0
mesh_fragment_source: incbin "shaders/mesh.frag"
db 0
section .note.GNU-stack noalloc noexec nowrite progbits
