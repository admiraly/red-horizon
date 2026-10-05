default rel
extern sim_init, sim_tick, sim_checksum, sim_count, sim_alive, sim_engaged
extern strcmp, strtoul, printf, puts, clock_gettime, qsort
section .rodata
arg_units: db '--units',0
arg_ticks: db '--ticks',0
arg_seed: db '--seed',0
usage: db 'Usage: red-horizon-headless [--units EVEN_2..32768] [--ticks 1..100000] [--seed 0..4294967295]',0
fmt: db '{"units":%u,"ticks":%u,"seed":%u,"alive":[%u,%u],"engaged":%u,"checksum":"%016lx","tick_mean_ms":%.6f,"tick_p95_ms":%.6f}',10,0
million: dq 1000000.0
section .bss
samples: resq 100000
section .text
global main
main:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,72
 mov r12d,edi
 mov r13,rsi
 mov r14d,8192
 mov r15d,600
 mov ebp,1
 mov ebx,1
 test r12d,1
 jz .bad
.parse:
 cmp ebx,r12d
 jae .init
 mov rdi,[r13+rbx*8]
 lea rsi,[arg_units]
 call strcmp
 test eax,eax
 jz .units
 mov rdi,[r13+rbx*8]
 lea rsi,[arg_ticks]
 call strcmp
 test eax,eax
 jz .ticks
 mov rdi,[r13+rbx*8]
 lea rsi,[arg_seed]
 call strcmp
 test eax,eax
 jnz .bad
 mov dword [rsp+48],2
 jmp .value
.units: mov dword [rsp+48],0
 jmp .value
.ticks: mov dword [rsp+48],1
.value:
 mov rdi,[r13+rbx*8+8]
 cmp byte [rdi],'0'
 jb .bad
 cmp byte [rdi],'9'
 ja .bad
 lea rsi,[rsp+56]
 mov edx,10
 call strtoul
 mov rcx,[rsp+56]
 cmp byte [rcx],0
 jne .bad
 mov ecx,0xffffffff
 cmp rax,rcx
 ja .bad
 cmp dword [rsp+48],0
 je .set_units
 cmp dword [rsp+48],1
 je .set_ticks
 mov ebp,eax
 jmp .parsed
.set_units: mov r14d,eax
 jmp .parsed
.set_ticks:
 test eax,eax
 jz .bad
 cmp eax,100000
 ja .bad
 mov r15d,eax
.parsed:
 add ebx,2
 jmp .parse
.init:
 mov edi,r14d
 mov esi,ebp
 call sim_init
 test eax,eax
 jnz .bad
 xor ebx,ebx
 mov qword [rsp+64],0
.tick:
 mov edi,1
 lea rsi,[rsp]
 call clock_gettime
 test eax,eax
 jnz .bad
 call sim_tick
 mov edi,1
 lea rsi,[rsp+16]
 call clock_gettime
 test eax,eax
 jnz .bad
 mov rax,[rsp+16]
 sub rax,[rsp]
 imul rax,1000000000
 add rax,[rsp+24]
 sub rax,[rsp+8]
 lea rcx,[samples]
 mov [rcx+rbx*8],rax
 add [rsp+64],rax
 inc ebx
 cmp ebx,r15d
 jb .tick
 lea rdi,[samples]
 mov esi,r15d
 mov edx,8
 lea rcx,[compare_ns]
 call qsort
 mov eax,r15d
 dec eax
 imul eax,95
 xor edx,edx
 mov ecx,100
 div ecx
 lea rcx,[samples]
 cvtsi2sd xmm1,qword [rcx+rax*8]
 divsd xmm1,[million]
 cvtsi2sd xmm0,qword [rsp+64]
 cvtsi2sd xmm2,r15d
 divsd xmm0,xmm2
 divsd xmm0,[million]
 movsd [rsp+32],xmm0
 movsd [rsp+40],xmm1
 call sim_checksum
 ; Seven integer args: checksum and engaged exceed register argument slots.
 mov [rsp+8],rax
 mov eax,[sim_engaged]
 mov [rsp],rax
 lea rdi,[fmt]
 mov esi,r14d
 mov edx,r15d
 mov ecx,ebp
 mov r8d,[sim_alive]
 mov r9d,[sim_alive+4]
 movsd xmm0,[rsp+32]
 movsd xmm1,[rsp+40]
 mov eax,2
 call printf
 xor eax,eax
 jmp .out
.bad:
 lea rdi,[usage]
 call puts
 mov eax,2
.out:
 add rsp,72
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
compare_ns:
 mov rax,[rdi]
 cmp rax,[rsi]
 mov eax,0
 je .done
 mov eax,1
 ja .done
 mov eax,-1
.done: ret
section .note.GNU-stack noalloc noexec nowrite progbits
