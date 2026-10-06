default rel
extern infantry_weapon_init,infantry_weapon_tick,infantry_weapon_fire
section .text
global probe_infantry_weapon
; EDI selector0init/1tick/2fire,ESI actorID,RDX7qword register output.
probe_infantry_weapon:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],edi
 mov [rsp+4],esi
 mov [rsp+8],rdx
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 cmp dword [rsp],0
 je .init
 cmp dword [rsp],1
 je .tick
 mov edi,[rsp+4]
 call infantry_weapon_fire
 jmp .output
.init:
 call infantry_weapon_init
 jmp .output
.tick:
 call infantry_weapon_tick
.output:
 mov [rsp+16],eax
 mov rdx,[rsp+8]
 mov [rdx],rbx
 mov [rdx+8],rbp
 mov [rdx+16],r12
 mov [rdx+24],r13
 mov [rdx+32],r14
 mov [rdx+40],r15
 mov rax,rsp
 and eax,15
 mov [rdx+48],rax
 mov eax,[rsp+16]
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
