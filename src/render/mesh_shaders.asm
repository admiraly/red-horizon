default rel
section .rodata
global mesh_vertex_source,mesh_fragment_source
mesh_vertex_source: incbin "shaders/mesh.vert"
db 0
mesh_fragment_source: incbin "shaders/mesh.frag"
db 0
section .note.GNU-stack noalloc noexec nowrite progbits
