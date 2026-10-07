; Optional real-wall-clock frame cap, outside work/swap profiling. SysV AMD64.
; Absolute CLOCK_MONOTONIC deadlines; no busy wait/authority/clock substitution.
; Late by a full period rebases the next deadline, avoiding a catch-up burst.
default rel
extern client_frame_cap,clock_gettime,clock_nanosleep,printf
section .rodata
format: db '{"client_pacing":true,"frame_cap_requested":%u,"waits":%u,"late_rebases":%u,"clock_errors":%u,"work_metrics_exclude_cap_wait":true}',10,0
section .bss
deadline: resq 2
now: resq 2
period: resq 1
ready: resd 1
global client_pacing_waits,client_pacing_rebases,client_pacing_errors
client_pacing_waits:
waits: resd 1
client_pacing_rebases:
late: resd 1
client_pacing_errors:
errors: resd 1
section .text
global client_pacing_init,client_frame_pace,client_pacing_report
client_pacing_init:
 sub rsp,8
 mov dword [ready],0
 mov dword [waits],0
 mov dword [late],0
 mov dword [errors],0
 mov ecx,[client_frame_cap]
 test ecx,ecx
 jz .done
 cmp ecx,30
 jb .error
 cmp ecx,240
 ja .error
 mov eax,1000000000
 xor edx,edx
 div ecx
 mov [period],rax
 mov edi,1
 lea rsi,[deadline]
 call clock_gettime wrt ..plt
 test eax,eax
 jnz .error
 call advance
 mov dword [ready],1
 jmp .done
.error:
 inc dword [errors]
.done:
 add rsp,8
 ret
client_frame_pace:
 sub rsp,8
 cmp dword [ready],1
 jne .done
 mov edi,1
 lea rsi,[now]
 call clock_gettime wrt ..plt
 test eax,eax
 jnz .error
 call difference
 test rax,rax
 jns .advance
.retry:
 mov edi,1 ; CLOCK_MONOTONIC
 mov esi,1 ; TIMER_ABSTIME
 lea rdx,[deadline]
 xor ecx,ecx
 call clock_nanosleep wrt ..plt
 cmp eax,4 ; EINTR: retry the same absolute deadline
 je .retry
 test eax,eax
 jnz .error
 inc dword [waits]
 mov edi,1
 lea rsi,[now]
 call clock_gettime wrt ..plt
 test eax,eax
 jnz .error
 call difference
.advance:
 cmp rax,[period]
 jl .normal
 mov rax,[now]
 mov [deadline],rax
 mov rax,[now+8]
 mov [deadline+8],rax
 inc dword [late]
.normal:
 call advance
 jmp .done
.error:
 inc dword [errors]
 mov dword [ready],0
.done:
 add rsp,8
 ret
; Signed elapsed nanoseconds relative to this frame's target.
difference:
 mov rax,[now]
 sub rax,[deadline]
 imul rax,1000000000
 add rax,[now+8]
 sub rax,[deadline+8]
 ret
advance:
 mov rax,[deadline+8]
 add rax,[period]
 cmp rax,1000000000
 jb .store
 sub rax,1000000000
 inc qword [deadline]
.store:
 mov [deadline+8],rax
 ret
client_pacing_report:
 sub rsp,8
 lea rdi,[format]
 mov esi,[client_frame_cap]
 mov edx,[waits]
 mov ecx,[late]
 mov r8d,[errors]
 xor eax,eax
 call printf wrt ..plt
 add rsp,8
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
