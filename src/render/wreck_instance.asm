%include "schemas/wreck.inc"
%include "schemas/wreck_instance.inc"
default rel
section .text
global wreck_instance
wreck_instance:
 test rdi,rdi
 jz .invalid_leaf
 test rdx,rdx
 jz .invalid_leaf
 cmp esi,64
 jb .invalid_leaf
 cmp ecx,64
 jb .invalid_leaf
 sub rsp,64
 movups xmm0,[rdx]
 movups xmm1,[rdx+16]
 movups xmm2,[rdx+32]
 movups xmm3,[rdx+48]
 movups [rsp],xmm0
 movups [rsp+16],xmm1
 movups [rsp+32],xmm2
 movups [rsp+48],xmm3
 cmp dword [rsp+WRECK_FLAGS],3
 ja .invalid
 test dword [rsp+WRECK_FLAGS],WRECK_ACTIVE
 jz .inactive
 mov eax,[rsp+WRECK_KIND]
 sub eax,1
 cmp eax,1
 ja .invalid
 cmp dword [rsp+WRECK_SIDE],1
 ja .invalid
 cmp dword [rsp+WRECK_ENTITY],32768
 jae .invalid
 cmp dword [rsp+WRECK_GENERATION],0
 je .invalid
 cmp dword [rsp+WRECK_SEQUENCE],0
 je .invalid
 cmp qword [rsp+56],0
 jne .invalid
 xor ecx,ecx
.validate:
 mov eax,[rsp+rcx*4]
 and eax,0x7fffffff
 mov edx,__float32__(16.0)
 cmp ecx,3
 jae .bounded
 mov edx,__float32__(2000.0)
 cmp ecx,1
 je .bounded
 mov edx,__float32__(8000.0)
 test eax,eax
 jz .bounded
 test dword [rsp+rcx*4],0x80000000
 jnz .invalid
.bounded:
 cmp eax,edx
 ja .invalid
 inc ecx
 cmp ecx,6
 jb .validate
 ; All validation precedes every caller write; copy-before-write supports aliasing.
 movups xmm0,[rsp]
 movups [rdi],xmm0
 mov qword [rdi+16],0
 mov dword [rdi+24],0
 mov eax,[rsp+WRECK_PITCH]
 mov [rdi+28],eax
 mov dword [rdi+32],__float32__(1.0)
 mov dword [rdi+36],__float32__(1.0)
 mov dword [rdi+40],__float32__(1.0)
 mov eax,[rsp+WRECK_BANK]
 mov [rdi+44],eax
 mov dword [rdi+48],__float32__(-1.0)
 mov dword [rdi+52],__float32__(3.0)
 cvtsi2ss xmm0,[rsp+WRECK_KIND]
 movss [rdi+56],xmm0
 mov dword [rdi+60],__float32__(1.0)
 xor eax,eax
 jmp .done
.inactive:
 mov eax,-2
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,64
 ret
.invalid_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
