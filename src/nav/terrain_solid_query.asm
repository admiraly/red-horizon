%include "schemas/terrain_solid_query.inc"
default rel
extern terrain_obstacles,terrain_obstacle_count,segment_box
section .rodata
zero: dd 0.0
section .text
global terrain_solid_query
terrain_solid_query:
 test rdi,rdi
 jz .invalid_leaf
 cmp esi,TERRAIN_SOLID_QUERY_BYTES
 jb .invalid_leaf
 push rbx
 push r12
 push r13
 sub rsp,80
 mov r13,rdi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 xor ecx,ecx
.validate_caller:
 mov eax,[rsp+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .invalid
 inc ecx
 cmp ecx,6
 jb .validate_caller
 mov eax,[terrain_obstacle_count]
 cmp eax,TERRAIN_SOLID_QUERY_LIMIT
 ja .bad_source
 test eax,eax
 jz .clear
 mov [rsp+64],eax
 mov dword [rsp+52],-1
 lea rbx,[terrain_obstacles]
 xor r12d,r12d
.record:
 xor ecx,ecx
.validate_source:
 mov eax,[rbx+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .bad_source
 inc ecx
 cmp ecx,6
 jb .validate_source
 cmp dword [rbx+24],1
 ja .bad_source
 cmp dword [rbx+28],0
 jne .bad_source
 movss xmm0,[rbx+20]
 ucomiss xmm0,[zero]
 jb .bad_source
 movss xmm0,[rbx]
 movss [rsp+24],xmm0
 movss xmm0,[rbx+16]
 movss [rsp+28],xmm0
 addss xmm0,[rbx+20]
 movss [rsp+40],xmm0
 movss xmm0,[rbx+4]
 movss [rsp+32],xmm0
 movss xmm0,[rbx+8]
 movss [rsp+36],xmm0
 movss xmm0,[rbx+12]
 movss [rsp+44],xmm0
 lea rdi,[rsp+24]
 mov esi,24
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
 call segment_box
 cmp eax,-1
 je .bad_source
 test eax,eax
 jz .next
 cmp dword [rsp+52],-1
 je .select
 ucomiss xmm0,[rsp+48]
 jae .next
.select:
 movss [rsp+48],xmm0
 mov [rsp+52],r12d
 mov eax,[rbx+24]
 mov [rsp+56],eax
.next:
 add rbx,32
 inc r12d
 cmp r12d,[rsp+64]
 jb .record
 cmp dword [rsp+52],-1
 je .clear
 mov eax,[rsp+48]
 mov [r13],eax
 mov eax,[rsp+52]
 mov [r13+4],eax
 mov eax,[rsp+56]
 mov [r13+8],eax
 mov dword [r13+12],0
 mov eax,1
 jmp .done
.clear:
 xor eax,eax
 jmp .done
.bad_source:
 mov eax,-2
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,80
 pop r13
 pop r12
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
