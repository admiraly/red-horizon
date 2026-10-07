; Private per-frame CPU phase timings. No simulation or render-state writes.
; EDI0 simulation loop,1 sync/routes/render submission,2 PCM pump. SysV AMD64.
default rel
extern clock_gettime,qsort,printf
%define CAPACITY 10000
section .rodata
million: dq 1000000.0
names: dq simulation,rendering,audio
simulation: db 'simulation',0
rendering: db 'render_routes',0
audio: db 'audio_pump',0
format: db '{"client_phase_metrics":true,"phase":"%s","samples":%u,"mean_ms":%.6f,"p95_ms":%.6f,"p99_ms":%.6f,"clock_errors":%u}',10,0
section .bss
starts: resq 6
finish: resq 2
valid: resd 3
counts: resd 3
errors: resd 3
sums: resq 3
samples: resq (3*CAPACITY)
stats: resq 3
section .text
global metrics_phase_begin,metrics_phase_end,metrics_phases_report
metrics_phase_begin:
 cmp edi,2
 ja .return
 push rbx
 mov ebx,edi
 lea rax,[valid]
 mov dword [rax+rbx*4],0
 mov eax,ebx
 shl eax,4
 lea rsi,[starts]
 add rsi,rax
 mov edi,1
 call clock_gettime wrt ..plt
 test eax,eax
 jnz .error
 lea rax,[valid]
 mov dword [rax+rbx*4],1
 jmp .done
.error:
 lea rax,[errors]
 inc dword [rax+rbx*4]
.done:
 pop rbx
.return:
 ret
metrics_phase_end:
 cmp edi,2
 ja .return
 push rbx
 mov ebx,edi
 lea rax,[valid]
 cmp dword [rax+rbx*4],1
 jne .done
 mov dword [rax+rbx*4],0
 mov edi,1
 lea rsi,[finish]
 call clock_gettime wrt ..plt
 test eax,eax
 jnz .error
 lea rdx,[counts]
 mov ecx,[rdx+rbx*4]
 cmp ecx,CAPACITY
 jae .done
 mov eax,ebx
 shl eax,4
 lea rsi,[starts]
 add rsi,rax
 mov rax,[finish]
 sub rax,[rsi]
 imul rax,1000000000
 add rax,[finish+8]
 sub rax,[rsi+8]
 test rax,rax
 js .error
 cvtsi2sd xmm0,rax
 divsd xmm0,[million]
 imul eax,ebx,CAPACITY
 add eax,ecx
 lea rsi,[samples]
 movsd [rsi+rax*8],xmm0
 lea rsi,[sums]
 addsd xmm0,[rsi+rbx*8]
 movsd [rsi+rbx*8],xmm0
 inc dword [rdx+rbx*4]
 jmp .done
.error:
 lea rax,[errors]
 inc dword [rax+rbx*4]
.done:
 pop rbx
.return:
 ret
metrics_phases_report:
 push rbx
 push r12
 push r13
 xor ebx,ebx
.phase:
 lea rax,[counts]
 mov r12d,[rax+rbx*4]
 test r12d,r12d
 jz .next
 imul eax,ebx,CAPACITY*8
 lea r13,[samples]
 add r13,rax
 lea rax,[sums]
 movsd xmm0,[rax+rbx*8]
 cvtsi2sd xmm1,r12d
 divsd xmm0,xmm1
 movsd [stats],xmm0
 mov rdi,r13
 mov esi,r12d
 mov edx,8
 lea rcx,[compare]
 call qsort wrt ..plt
 mov eax,r12d
 imul eax,95
 add eax,99
 xor edx,edx
 mov ecx,100
 div ecx
 dec eax
 movsd xmm0,[r13+rax*8]
 movsd [stats+8],xmm0
 mov eax,r12d
 imul eax,99
 add eax,99
 xor edx,edx
 mov ecx,100
 div ecx
 dec eax
 movsd xmm0,[r13+rax*8]
 movsd [stats+16],xmm0
 lea rdi,[format]
 lea rax,[names]
 mov rsi,[rax+rbx*8]
 mov edx,r12d
 lea rax,[errors]
 mov ecx,[rax+rbx*4]
 movsd xmm0,[stats]
 movsd xmm1,[stats+8]
 movsd xmm2,[stats+16]
 mov eax,3
 call printf wrt ..plt
.next:
 inc ebx
 cmp ebx,3
 jb .phase
 pop r13
 pop r12
 pop rbx
 ret
compare:
 movsd xmm0,[rdi]
 comisd xmm0,[rsi]
 seta al
 setb dl
 movzx eax,al
 movzx edx,dl
 sub eax,edx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
