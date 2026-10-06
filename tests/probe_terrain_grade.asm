; Development-only C ABI wrapper: EDI role, RSI pointer to four floats.
default rel
extern terrain_grade_clear
section .text
global test_grade
test_grade:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov ebx,0x12345
 mov ebp,0x23456
 mov r12d,0x34567
 mov r13d,0x45678
 mov r14d,0x56789
 mov r15d,0x6789a
 movss xmm0,[rsi]
 movss xmm1,[rsi+4]
 movss xmm2,[rsi+8]
 movss xmm3,[rsi+12]
 call terrain_grade_clear
 cmp rbx,0x12345
 jne .abi_fail
 cmp rbp,0x23456
 jne .abi_fail
 cmp r12,0x34567
 jne .abi_fail
 cmp r13,0x45678
 jne .abi_fail
 cmp r14,0x56789
 jne .abi_fail
 cmp r15,0x6789a
 jne .abi_fail
 jmp .out
.abi_fail:
 mov eax,-2
.out:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
