default rel
extern hazard_choose_goal
section .text
global test_hazard_choose_goal
; (entity, centerX, centerZ, radius, outputPointer), output x,z,status,reason.
test_hazard_choose_goal:
 push rbx
 mov rbx,rsi
 call hazard_choose_goal
 movss [rbx],xmm0
 movss [rbx+4],xmm1
 mov [rbx+8],eax
 mov [rbx+12],edx
 pop rbx
 ret
global test_hazard_steering_abi
test_hazard_steering_abi:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov ebx,0x12345678
 mov ebp,0x23456789
 mov r12d,0x3456789a
 mov r13d,0x456789ab
 mov r14d,0x56789abc
 mov r15d,0x6789abcd
 call hazard_choose_goal
 xor eax,eax
 cmp rbx,0x12345678
 jne .done
 cmp rbp,0x23456789
 jne .done
 cmp r12,0x3456789a
 jne .done
 cmp r13,0x456789ab
 jne .done
 cmp r14,0x56789abc
 jne .done
 cmp r15,0x6789abcd
 jne .done
 mov eax,1
.done:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
