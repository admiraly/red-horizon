; Owned Linux listen authority. Called before GLFW/audio/thread creation.
; Fork child uses syscalls only before execve; no shell and no PATH lookup.
; Startup bounded by eight 625ms readiness polls. No authoritative state here.
default rel
%include "src/net/protocol.inc"
extern environ,sscanf,printf,fflush
section .rodata
self_path: db '/proc/self/exe',0
server_name: db 'red-horizon-coop-server',0
server_name_len equ $-server_name
arg_port: db '--port',0
arg_zero: db '0',0
arg_ticks: db '--ticks',0
arg_units: db '--units',0
arg_army: db '8192',0
ready_format: db '{"port":%u,"protocol":%u,"units":%u}%n',0
listen_ready_format: db '{"listen_ready":true,"port":%u,"child_pid":%u,"units":8192}',10,0
report_format: db '{"listen_host":true,"port":%u,"child_pid":%u,"child_exited":%u,"startup_failed":%u}',10,0
section .data
pipe_fds: dd -1,-1
section .bss
global listen_host_port,listen_host_pid
listen_host_port: resd 1
listen_host_pid: resd 1
owned_pid: resd 1
child_exited: resd 1
startup_failed: resd 1
poll_fd: resd 1
poll_events: resw 1
poll_return: resw 1
ready_port: resd 1
ready_protocol: resd 1
ready_units: resd 1
ready_length: resd 1
ready_bytes: resd 1
exe_path: resb 4096
ready_buffer: resb 256
server_argv: resq 8
section .text
global listen_host_start,listen_host_check,listen_host_stop,listen_host_report
listen_host_start:
 push rbx
 push r12
 sub rsp,8
 cmp dword [owned_pid],0
 jne .busy
 mov dword [pipe_fds],-1
 mov dword [pipe_fds+4],-1
 mov eax,89 ; readlink bounded, reserve room for sibling filename
 lea rdi,[self_path]
 lea rsi,[exe_path]
 mov edx,4000
 syscall
 test rax,rax
 jle .failed
 cmp eax,4000
 jae .failed
 mov rcx,rax
.findslash:
 dec rcx
 js .failed
 lea rdx,[exe_path]
 cmp byte [rdx+rcx],'/'
 jne .findslash
 lea rdi,[rdx+rcx+1]
 lea rsi,[server_name]
 mov ecx,server_name_len
 rep movsb
 lea rax,[exe_path]
 mov [server_argv],rax
 lea rax,[arg_port]
 mov [server_argv+8],rax
 lea rax,[arg_zero]
 mov [server_argv+16],rax
 lea rax,[arg_ticks]
 mov [server_argv+24],rax
 lea rax,[arg_zero]
 mov [server_argv+32],rax
 lea rax,[arg_units]
 mov [server_argv+40],rax
 lea rax,[arg_army]
 mov [server_argv+48],rax
 mov qword [server_argv+56],0
 mov eax,293 ; pipe2: nonblocking and exec-clean descriptors
 lea rdi,[pipe_fds]
 mov esi,0x80800
 syscall
 test eax,eax
 jnz .failed
 mov eax,57 ; fork before platform creates any threads
 syscall
 test rax,rax
 js .failed
 jz .child
 mov [owned_pid],eax
 mov [listen_host_pid],eax
 mov edi,[pipe_fds+4]
 mov eax,3
 syscall
 mov dword [pipe_fds+4],-1
 mov eax,[pipe_fds]
 mov [poll_fd],eax
 mov word [poll_events],1
 mov dword [ready_bytes],0
 mov r12d,8
.poll:
 mov edi,[owned_pid]
 lea rsi,[child_exited] ; separate wait status; nonzero is overwritten below
 mov edx,1
 mov eax,61
 syscall
 test eax,eax
 jz .wait
 cmp eax,-4
 je .wait
 mov dword [owned_pid],0
 mov dword [child_exited],1
 jmp .failed
.wait:
 mov eax,7
 lea rdi,[poll_fd]
 mov esi,1
 mov edx,625
 syscall
 test eax,eax
 jle .nextpoll
 mov ecx,[ready_bytes]
 mov edx,255
 sub edx,ecx
 jbe .failed
 lea rsi,[ready_buffer]
 add rsi,rcx
 mov edi,[pipe_fds]
 xor eax,eax
 syscall
 test eax,eax
 jz .failed
 js .nextpoll
 add [ready_bytes],eax
 lea rdx,[ready_buffer]
 mov ecx,[ready_bytes]
 mov byte [rdx+rcx],0
 xor ebx,ebx
.newline:
 cmp byte [rdx+rbx],10
 je .parse
 inc ebx
 cmp ebx,ecx
 jb .newline
 jmp .nextpoll
.parse:
 lea rdi,[ready_buffer]
 lea rsi,[ready_format]
 lea rdx,[ready_port]
 lea rcx,[ready_protocol]
 lea r8,[ready_units]
 lea r9,[ready_length]
 xor eax,eax
 call sscanf wrt ..plt
 cmp eax,3
 jne .failed
 cmp [ready_length],ebx
 jne .failed
 cmp dword [ready_protocol],NET_VERSION
 jne .failed
 cmp dword [ready_units],8192
 jne .failed
 mov eax,[ready_port]
 dec eax
 cmp eax,65534
 ja .failed
 inc eax
 mov [listen_host_port],eax
 lea rdi,[listen_ready_format]
 mov esi,eax
 mov edx,[listen_host_pid]
 xor eax,eax
 call printf wrt ..plt
 xor edi,edi
 call fflush wrt ..plt
 xor eax,eax
 jmp .return
.busy:
 mov eax,-1
 jmp .return
.nextpoll:
 dec r12d
 jnz .poll
.failed:
 mov dword [startup_failed],1
 call listen_host_stop
 mov eax,-1
.return:
 add rsp,8
 pop r12
 pop rbx
 ret
.child:
 ; Parent death cannot leave the army running. Check the race after prctl.
 mov eax,110
 syscall
 mov r12,rax
 mov eax,157
 mov edi,1 ; PR_SET_PDEATHSIG
 mov esi,15
 xor edx,edx
 xor r10d,r10d
 xor r8d,r8d
 syscall
 test eax,eax
 js .childexit
 mov eax,110
 syscall
 cmp rax,r12
 jne .childexit
 cmp eax,1
 je .childexit
 mov eax,3
 mov edi,[pipe_fds]
 syscall
 mov eax,33
 mov edi,[pipe_fds+4]
 mov esi,1
 syscall
 test eax,eax
 js .childexit
 mov eax,3
 mov edi,[pipe_fds+4]
 cmp edi,1
 je .exec
 syscall
.exec:
 mov eax,59
 lea rdi,[exe_path]
 lea rsi,[server_argv]
 mov rdx,[environ]
 syscall
.childexit:
 mov eax,60
 mov edi,127
 syscall
 ud2
; Return0 alive/no host, -1 terminated (reaps only our own PID).
listen_host_check:
 mov edi,[owned_pid]
 test edi,edi
 jz .done
 mov eax,61
 xor esi,esi
 mov edx,1
 syscall
 test eax,eax
 jz .done
 cmp eax,-4
 je .done
 mov dword [owned_pid],0
 mov dword [child_exited],1
 mov eax,-1
 ret
.done:
 xor eax,eax
 ret
listen_host_stop:
 push rbx
 mov ebx,[owned_pid]
 test ebx,ebx
 jz .pipes
.retrycheck:
 mov eax,61
 mov edi,ebx
 xor esi,esi
 mov edx,1
 syscall
 cmp eax,-4
 je .retrycheck
 test eax,eax
 jnz .reaped
 mov eax,62
 mov edi,ebx
 mov esi,15
 syscall
.wait:
 mov eax,61
 mov edi,ebx
 xor esi,esi
 xor edx,edx
 syscall
 cmp eax,-4
 je .wait
.reaped:
 mov dword [owned_pid],0
 mov dword [child_exited],1
.pipes:
 mov edi,[pipe_fds]
 cmp edi,0
 jl .writepipe
 mov eax,3
 syscall
 mov dword [pipe_fds],-1
.writepipe:
 mov edi,[pipe_fds+4]
 cmp edi,0
 jl .done
 mov eax,3
 syscall
 mov dword [pipe_fds+4],-1
.done:
 pop rbx
 ret
listen_host_report:
 lea rdi,[report_format]
 mov esi,[listen_host_port]
 mov edx,[listen_host_pid]
 mov ecx,[child_exited]
 mov r8d,[startup_failed]
 xor eax,eax
 jmp printf wrt ..plt
section .note.GNU-stack noalloc noexec nowrite progbits
