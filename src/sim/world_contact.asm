%include "schemas/entity.inc"
%include "schemas/world_contact.inc"
default rel
extern terrain_ground_query,terrain_solid_query,wreck_query,sim_shell_contact
extern sim_entities,sim_count
section .rodata
abs_mask: dd 0x7fffffff
limit: dd 16000.0
map_limit: dd 8000.0
zero: dd 0.0
section .text
global world_contact_query
%macro endpoints 0
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
%endmacro
world_contact_query:
 push rbx
 push r12
 push r13
 sub rsp,128
 mov rbx,rdi
 mov r12d,edx
 test rdi,rdi
 jz .caller
 cmp esi,WORLD_CONTACT_BYTES
 jb .caller
 cmp edx,1
 ja .caller
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 xor ecx,ecx
.validate:
 movss xmm0,[rsp+rcx*4]
 movd eax,xmm0
 and eax,0x7fffffff
 cmp eax,0x467a0000 ; abs<=16000 rejects NaN/Inf
 ja .caller
 cmp ecx,1
 je .validated_coord
 cmp ecx,4
 je .validated_coord
 ucomiss xmm0,[zero]
 jb .caller
 ucomiss xmm0,[map_limit]
 ja .caller
.validated_coord:
 inc ecx
 cmp ecx,6
 jb .validate
 mov dword [rsp+68],0 ; no best hit
 endpoints
 lea rdi,[rsp+32]
 mov esi,24
 call terrain_ground_query
 test eax,eax
 js .source
 jz .solid
 mov r13d,WORLD_CONTACT_GROUND
 mov dword [rsp+36],0
 mov dword [rsp+40],0
 mov dword [rsp+44],0
 call .select
.solid:
 endpoints
 lea rdi,[rsp+32]
 mov esi,24
 call terrain_solid_query
 test eax,eax
 js .source
 jz .wreck
 mov r13d,WORLD_CONTACT_SOLID
 mov dword [rsp+40],0
 mov dword [rsp+44],0
 call .select
.wreck:
 endpoints
 lea rdi,[rsp+32]
 mov esi,24
 call wreck_query
 test eax,eax
 js .source
 jz .actor
 mov r13d,WORLD_CONTACT_WRECK
 ; Translate query slot/entity/gen/seq to typed physical identity/gen/seq.
 mov eax,[rsp+40]
 mov [rsp+36],eax
 mov eax,[rsp+44]
 mov [rsp+40],eax
 mov eax,[rsp+48]
 mov [rsp+44],eax
 call .select
.actor:
 endpoints
 mov edi,r12d
 call sim_shell_contact
 cmp eax,-1
 je .finish
 cmp eax,[sim_count]
 jae .source
 cmp eax,ENTITY_CAPACITY
 jae .source
 mov [rsp+36],eax
 shl eax,5
 lea rdx,[sim_entities]
 cmp dword [rdx+rax+ENTITY_HP],0
 je .source
 mov ecx,[rdx+rax+ENTITY_GENERATION]
 mov [rsp+40],ecx
 movss [rsp+32],xmm3
 mov dword [rsp+44],0
 mov r13d,WORLD_CONTACT_ACTOR
 call .select
.finish:
 xor eax,eax
 cmp dword [rsp+68],0
 je .out
 movdqu xmm0,[rsp+64]
 movdqu [rbx],xmm0
 mov rax,[rsp+80]
 mov [rbx+16],rax
 mov eax,1
 jmp .out
.caller:
 mov eax,-1
 jmp .out
.source:
 mov eax,-2
.out:
 add rsp,128
 pop r13
 pop r12
 pop rbx
 ret
; Internal no-call helper; caller scratch addressed after return-address bias.
.select:
 cmp dword [rsp+76],0
 je .take
 movss xmm0,[rsp+40]
 ucomiss xmm0,[rsp+72]
 jae .keep ; callers visit ascending kind, so equal keeps prior type
.take:
 mov eax,[rsp+40]
 mov [rsp+72],eax
 mov [rsp+76],r13d
 mov eax,[rsp+44]
 mov [rsp+80],eax
 mov eax,[rsp+48]
 mov [rsp+84],eax
 mov eax,[rsp+52]
 mov [rsp+88],eax
 mov dword [rsp+92],0
.keep:
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
