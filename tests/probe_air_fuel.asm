default rel
extern air_fuel_step,air_fuel_status
section .text
global probe_air_fuel_step,probe_air_fuel_status
; EDI owned physical ID, RSI seven-qword ABI observer.
probe_air_fuel_status:
 mov eax,1
 jmp fuel_probe
probe_air_fuel_step:
 xor eax,eax
fuel_probe:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp+8],rsi
 mov [rsp],eax
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 mov [rsp+16],rsp
 cmp dword [rsp],0
 jne .status
 call air_fuel_step
 jmp .returned
.status:
 call air_fuel_status
.returned:
 mov r8d,eax
 mov rcx,[rsp+8]
 mov [rcx],rbx
 mov [rcx+8],rbp
 mov [rcx+16],r12
 mov [rcx+24],r13
 mov [rcx+32],r14
 mov [rcx+40],r15
 mov rax,rsp
 sub rax,[rsp+16]
 mov [rcx+48],rax
 mov eax,r8d
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
