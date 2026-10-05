; SysV AMD64 profiler. CPU includes event/simulation/render/swap work.
; GPU timers cover draw submission, resolved from a bounded 8-query ring.
; All hooks require a current GL4.5 context and preserve nonvolatile registers.
default rel
extern clock_gettime,qsort,printf
extern glGenQueries,glBeginQuery,glEndQuery,glGetQueryObjectiv,glGetQueryObjectui64v
%define CAPACITY 10000
section .rodata
million: dq 1000000.0
format: db '{"client_metrics":true,"cpu_samples":%u,"gpu_samples":%u,"cpu_frame_mean_ms":%.6f,"cpu_frame_p95_ms":%.6f,"gpu_draw_mean_ms":%.6f,"gpu_draw_p95_ms":%.6f}',10,0
section .bss
ids: resd 8
pending: resd 8
cursor: resd 1
active: resd 1
available: resd 1
ready: resd 1
query_ns: resq 1
start: resq 2
finish: resq 2
cpu_count: resd 1
gpu_count: resd 1
cpu_sum: resq 1
gpu_sum: resq 1
cpu_mean: resq 1
gpu_mean: resq 1
cpu_p95: resq 1
gpu_p95: resq 1
cpu_samples: resq CAPACITY
gpu_samples: resq CAPACITY
section .text
global metrics_init,metrics_frame_begin,metrics_gpu_begin,metrics_gpu_end,metrics_frame_end,metrics_report
metrics_init:
 sub rsp,8
 mov edi,8
 lea rsi,[ids]
 call glGenQueries
 mov dword [ready],1
 add rsp,8
 ret
metrics_frame_begin:
 sub rsp,8
 mov edi,1
 lea rsi,[start]
 call clock_gettime
 add rsp,8
 ret
metrics_gpu_begin:
 push rbx
 mov dword [active],0
 mov ebx,[cursor]
 lea rcx,[pending]
 cmp dword [rcx+rbx*4],0
 je .begin
 lea rcx,[ids]
 mov edi,[rcx+rbx*4]
 mov esi,0x8867 ; GL_QUERY_RESULT_AVAILABLE
 lea rdx,[available]
 call glGetQueryObjectiv
 cmp dword [available],0
 je .skip
 lea rcx,[ids]
 mov edi,[rcx+rbx*4]
 mov esi,0x8866 ; GL_QUERY_RESULT
 lea rdx,[query_ns]
 call glGetQueryObjectui64v
 mov eax,[gpu_count]
 cmp eax,CAPACITY
 jae .discard
 cvtsi2sd xmm0,qword [query_ns]
 divsd xmm0,[million]
 lea rcx,[gpu_samples]
 movsd [rcx+rax*8],xmm0
 addsd xmm0,[gpu_sum]
 movsd [gpu_sum],xmm0
 inc dword [gpu_count]
.discard:
 lea rcx,[pending]
 mov dword [rcx+rbx*4],0
.begin:
 mov edi,0x88bf ; GL_TIME_ELAPSED
 lea rcx,[ids]
 mov esi,[rcx+rbx*4]
 call glBeginQuery
 mov dword [active],1
.skip:
 pop rbx
 ret
metrics_gpu_end:
 sub rsp,8
 cmp dword [active],0
 je .next
 mov edi,0x88bf
 call glEndQuery
 mov eax,[cursor]
 lea rcx,[pending]
 mov dword [rcx+rax*4],1
.next:
 inc dword [cursor]
 and dword [cursor],7
 add rsp,8
 ret
metrics_frame_end:
 sub rsp,8
 mov edi,1
 lea rsi,[finish]
 call clock_gettime
 test eax,eax
 jnz .end
 mov eax,[cpu_count]
 cmp eax,CAPACITY
 jae .end
 mov rdx,[finish]
 sub rdx,[start]
 imul rdx,1000000000
 add rdx,[finish+8]
 sub rdx,[start+8]
 cvtsi2sd xmm0,rdx
 divsd xmm0,[million]
 lea rcx,[cpu_samples]
 movsd [rcx+rax*8],xmm0
 addsd xmm0,[cpu_sum]
 movsd [cpu_sum],xmm0
 inc dword [cpu_count]
.end:
 add rsp,8
 ret
metrics_report:
 push rbx
 cmp dword [ready],0
 je .done
 mov ebx,[cpu_count]
 test ebx,ebx
 jz .gpu
 cvtsi2sd xmm0,ebx
 movsd xmm1,[cpu_sum]
 divsd xmm1,xmm0
 movsd [cpu_mean],xmm1
 lea rdi,[cpu_samples]
 mov esi,ebx
 mov edx,8
 lea rcx,[compare]
 call qsort
 mov eax,ebx
 imul eax,95
 xor edx,edx
 mov ecx,100
 div ecx
 lea rcx,[cpu_samples]
 movsd xmm0,[rcx+rax*8]
 movsd [cpu_p95],xmm0
.gpu:
 mov ebx,[gpu_count]
 test ebx,ebx
 jz .print
 cvtsi2sd xmm0,ebx
 movsd xmm1,[gpu_sum]
 divsd xmm1,xmm0
 movsd [gpu_mean],xmm1
 lea rdi,[gpu_samples]
 mov esi,ebx
 mov edx,8
 lea rcx,[compare]
 call qsort
 mov eax,ebx
 imul eax,95
 xor edx,edx
 mov ecx,100
 div ecx
 lea rcx,[gpu_samples]
 movsd xmm0,[rcx+rax*8]
 movsd [gpu_p95],xmm0
.print:
 lea rdi,[format]
 mov esi,[cpu_count]
 mov edx,[gpu_count]
 movsd xmm0,[cpu_mean]
 movsd xmm1,[cpu_p95]
 movsd xmm2,[gpu_mean]
 movsd xmm3,[gpu_p95]
 mov eax,4
 call printf
.done:
 pop rbx
 ret
compare:
 movsd xmm0,[rdi]
 comisd xmm0,[rsi]
 ja .greater
 jb .less
 xor eax,eax
 ret
.greater: mov eax,1
 ret
.less: mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
