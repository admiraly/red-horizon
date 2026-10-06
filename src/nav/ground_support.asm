; Stateless five-height cosmetic support. No global writes or collision changes.
default rel
%include "schemas/ground_support.inc"
extern terrain_height,sinf,cosf,atan2f
section .rodata align=16
zero: dd 0.0
one: dd 1.0
four: dd 4.0
quarter: dd 0.25
maximum: dd 8000.0
pi: dd 3.14159265358979323846
negative_pi: dd -3.14159265358979323846
sizes: dd SUPPORT_TANK_HALF_WIDTH,SUPPORT_TANK_HALF_LENGTH,SUPPORT_TANK_CENTER_Z
 dd SUPPORT_ARTY_HALF_WIDTH,SUPPORT_ARTY_HALF_LENGTH,SUPPORT_ARTY_CENTER_Z
signs: dd 1.0,1.0, 1.0,-1.0, -1.0,1.0, -1.0,-1.0
section .text
global ground_support
ground_support:
 test rdi,rdi
 jz .invalid_leaf
 cmp edx,SUPPORT_STRIDE
 jb .invalid_leaf
 cmp esi,1
 jb .invalid_leaf
 cmp esi,2
 ja .invalid_leaf
 ucomiss xmm0,[zero]
 jp .invalid_leaf
 jb .invalid_leaf
 ucomiss xmm0,[maximum]
 ja .invalid_leaf
 ucomiss xmm1,[zero]
 jp .invalid_leaf
 jb .invalid_leaf
 ucomiss xmm1,[maximum]
 ja .invalid_leaf
 ucomiss xmm2,[negative_pi]
 jp .invalid_leaf
 jb .invalid_leaf
 ucomiss xmm2,[pi]
 ja .invalid_leaf
 push rbx
 sub rsp,256
 mov [rsp+240],rdi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 dec esi
 imul esi,12
 lea rax,[sizes]
 movss xmm3,[rax+rsi]
 movss [rsp+12],xmm3
 movss xmm3,[rax+rsi+4]
 movss [rsp+16],xmm3
 movss xmm3,[rax+rsi+8]
 movss [rsp+20],xmm3
 movaps xmm0,xmm2
 call sinf wrt ..plt
 movss [rsp+24],xmm0
 movss xmm0,[rsp+8]
 call cosf wrt ..plt
 movss [rsp+28],xmm0
 xor ebx,ebx
.corner:
 lea rax,[signs]
 movss xmm2,[rax+rbx*8]
 mulss xmm2,[rsp+12]
 movss xmm3,[rax+rbx*8+4]
 mulss xmm3,[rsp+16]
 addss xmm3,[rsp+20]
 movaps xmm0,xmm2
 mulss xmm0,[rsp+28]
 movaps xmm1,xmm3
 mulss xmm1,[rsp+24]
 addss xmm0,xmm1
 addss xmm0,[rsp]
 movaps xmm1,xmm3
 mulss xmm1,[rsp+28]
 mulss xmm2,[rsp+24]
 subss xmm1,xmm2
 addss xmm1,[rsp+4]
 ucomiss xmm0,[zero]
 jb .invalid
 ucomiss xmm0,[maximum]
 ja .invalid
 ucomiss xmm1,[zero]
 jb .invalid
 ucomiss xmm1,[maximum]
 ja .invalid
 movss [rsp+32+rbx*8],xmm0
 movss [rsp+36+rbx*8],xmm1
 inc ebx
 cmp ebx,4
 jb .corner
 xor ebx,ebx
.sample:
 movss xmm0,[rsp+32+rbx*8]
 movss xmm1,[rsp+36+rbx*8]
 call terrain_height
 movss [rsp+64+rbx*4],xmm0
 inc ebx
 cmp ebx,4
 jb .sample
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 call terrain_height
 movss [rsp+116],xmm0
 movss xmm0,[rsp+64]
 addss xmm0,[rsp+68]
 subss xmm0,[rsp+72]
 subss xmm0,[rsp+76]
 movss xmm1,[rsp+12]
 mulss xmm1,[four]
 divss xmm0,xmm1
 movss [rsp+80],xmm0
 movss xmm0,[rsp+64]
 addss xmm0,[rsp+72]
 subss xmm0,[rsp+68]
 subss xmm0,[rsp+76]
 movss xmm1,[rsp+16]
 mulss xmm1,[four]
 divss xmm0,xmm1
 movss [rsp+84],xmm0
 movss xmm1,[rsp+64]
 addss xmm1,[rsp+68]
 addss xmm1,[rsp+72]
 addss xmm1,[rsp+76]
 mulss xmm1,[quarter]
 mulss xmm0,[rsp+20]
 subss xmm1,xmm0
 movss [rsp+88],xmm1
 ; Raise fitted plane to each of the four actual sampled heights.
 xor ebx,ebx
.residual:
 lea rax,[signs]
 movss xmm0,[rax+rbx*8]
 mulss xmm0,[rsp+12]
 mulss xmm0,[rsp+80]
 movss xmm1,[rax+rbx*8+4]
 mulss xmm1,[rsp+16]
 addss xmm1,[rsp+20]
 mulss xmm1,[rsp+84]
 addss xmm0,xmm1
 movss xmm1,[rsp+64+rbx*4]
 subss xmm1,xmm0
 maxss xmm1,[rsp+88]
 movss [rsp+88],xmm1
 inc ebx
 cmp ebx,4
 jb .residual
 movss xmm0,[rsp+88]
 maxss xmm0,[rsp+116]
 movss [rsp+128],xmm0
 movss xmm0,[rsp+84]
 movss xmm1,[one]
 call atan2f wrt ..plt
 movss [rsp+132],xmm0
 movss xmm1,[rsp+84]
 mulss xmm1,xmm1
 addss xmm1,[one]
 sqrtss xmm1,xmm1
 movss xmm0,[rsp+80]
 call atan2f wrt ..plt
 movss [rsp+136],xmm0
 mov dword [rsp+140],SUPPORT_VALID
 movss xmm0,[rsp+132]
 call sinf wrt ..plt
 movss [rsp+100],xmm0
 movss xmm0,[rsp+132]
 call cosf wrt ..plt
 movss [rsp+104],xmm0
 movss xmm0,[rsp+136]
 call sinf wrt ..plt
 movss [rsp+108],xmm0
 movss xmm0,[rsp+136]
 call cosf wrt ..plt
 movss [rsp+112],xmm0
 ; Frame = yaw * pitch * bank, as in mesh.vert (column vectors).
 movss xmm0,[rsp+28]
 mulss xmm0,[rsp+112]
 movss xmm1,[rsp+24]
 mulss xmm1,[rsp+100]
 mulss xmm1,[rsp+108]
 subss xmm0,xmm1
 movss [rsp+144],xmm0
 movss xmm0,[rsp+104]
 mulss xmm0,[rsp+108]
 movss [rsp+148],xmm0
 xorps xmm0,xmm0
 subss xmm0,[rsp+24]
 mulss xmm0,[rsp+112]
 movss xmm1,[rsp+28]
 mulss xmm1,[rsp+100]
 mulss xmm1,[rsp+108]
 subss xmm0,xmm1
 movss [rsp+152],xmm0
 mov dword [rsp+156],0
 xorps xmm0,xmm0
 subss xmm0,[rsp+28]
 mulss xmm0,[rsp+108]
 movss xmm1,[rsp+24]
 mulss xmm1,[rsp+100]
 mulss xmm1,[rsp+112]
 subss xmm0,xmm1
 movss [rsp+160],xmm0
 movss xmm0,[rsp+104]
 mulss xmm0,[rsp+112]
 movss [rsp+164],xmm0
 movss xmm0,[rsp+24]
 mulss xmm0,[rsp+108]
 movss xmm1,[rsp+28]
 mulss xmm1,[rsp+100]
 mulss xmm1,[rsp+112]
 subss xmm0,xmm1
 movss [rsp+168],xmm0
 mov dword [rsp+172],0
 movss xmm0,[rsp+24]
 mulss xmm0,[rsp+104]
 movss [rsp+176],xmm0
 movss xmm0,[rsp+100]
 movss [rsp+180],xmm0
 movss xmm0,[rsp+28]
 mulss xmm0,[rsp+104]
 movss [rsp+184],xmm0
 mov dword [rsp+188],0
 ; Finite gate before the single publish phase (flags excluded).
 xor ebx,ebx
.finite:
 mov eax,[rsp+128+rbx*4]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .invalid
 inc ebx
 cmp ebx,3
 jne .check_end
 inc ebx
.check_end:
 cmp ebx,16
 jb .finite
 mov rdi,[rsp+240]
 movups xmm0,[rsp+128]
 movups xmm1,[rsp+144]
 movups xmm2,[rsp+160]
 movups xmm3,[rsp+176]
 movups [rdi],xmm0
 movups [rdi+16],xmm1
 movups [rdi+32],xmm2
 movups [rdi+48],xmm3
 xor eax,eax
 jmp .done
.invalid: mov eax,-1
.done:
 add rsp,256
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
