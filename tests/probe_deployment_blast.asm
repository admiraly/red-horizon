default rel
extern deployment_blast_clear
section .text
global deployment_blast_abi
deployment_blast_abi:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rsp
 mov ebx,0x11223344
 mov ebp,0x22334455
 mov r12d,0x33445566
 mov r13d,0x44556677
 mov r14d,0x55667788
 mov r15d,0x66778899
 call deployment_blast_clear wrt ..plt
 mov [rsp+8],eax
 cmp [rsp],rsp
 jne .bad
 cmp rbx,0x11223344
 jne .bad
 cmp rbp,0x22334455
 jne .bad
 cmp r12,0x33445566
 jne .bad
 cmp r13,0x44556677
 jne .bad
 cmp r14,0x55667788
 jne .bad
 cmp r15,0x66778899
 jne .bad
 mov eax,[rsp+8]
 jmp .done
.bad: mov eax,-777
.done:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
