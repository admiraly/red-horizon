default rel
extern terrain_move
section .text
global test_terrain_move
; Development probe packs the two SSE float return values into RAX.
test_terrain_move:
 sub rsp,8
 call terrain_move
 add rsp,8
 movd eax,xmm0
 movd edx,xmm1
 shl rdx,32
 or rax,rdx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
