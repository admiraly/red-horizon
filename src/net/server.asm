; Bounded Linux UDP transport proof. NASM/SysV, platform via Linux syscalls.
; CLI: udp-proof --port 0..65535 --packets 1..10000. Loopback only.
default rel
%define MAGIC 0x52484e31
%define SIZE 32
extern strcmp, printf, fflush
section .rodata
port_flag: db '--port',0
packet_flag: db '--packets',0
ready_fmt: db '{"port":%u,"protocol":1}',10,0
end_fmt: db '{"received":%u,"rejected":%u}',10,0
usage: db 'usage: udp-proof --port 0..65535 --packets 1..10000',10,0
section .data align=8
bind_addr: dw 2,0
    dd 0x0100007f
    dq 0
section .bss align=16
fd: resq 1
limit: resd 1
seen: resd 1
rejected: resd 1
address_len: resd 1
peer: resb 16
packet: resb 1200
response: resd 8
pollfd: resb 8
endptr: resq 1
; Four server records: endpoint qword, lastseq u32, balance u32, attempts u32.
clients: resb 4*24
section .text
global main
main:
    push rbp
    mov rbp,rsp
    push r12
    push r13
    cmp edi,5
    jne .usage
    mov r12,rsi
    mov rdi,[r12+8]
    lea rsi,[port_flag]
    call strcmp wrt ..plt
    test eax,eax
    jnz .usage
    mov rdi,[r12+24]
    lea rsi,[packet_flag]
    call strcmp wrt ..plt
    test eax,eax
    jnz .usage
    mov rdi,[r12+16]
    call parse_uint
    jc .usage
    cmp rax,65535
    ja .usage
    xchg al,ah
    mov [bind_addr+2],ax
    mov rdi,[r12+32]
    call parse_uint
    jc .usage
    test rax,rax
    jz .usage
    cmp rax,10000
    ja .usage
    mov [limit],eax
    mov eax,41 ; socket(AF_INET,SOCK_DGRAM,0)
    mov edi,2
    mov esi,2
    xor edx,edx
    syscall
    test rax,rax
    js .failed
    mov [fd],rax
    mov rdi,rax
    lea rsi,[bind_addr]
    mov edx,16
    mov eax,49
    syscall
    test eax,eax
    js .close_failed
    mov dword [address_len],16
    mov rdi,[fd]
    lea rsi,[bind_addr]
    lea rdx,[address_len]
    mov eax,51
    syscall
    test eax,eax
    js .close_failed
    movzx esi,word [bind_addr+2]
    rol si,8
    lea rdi,[ready_fmt]
    xor eax,eax
    call printf wrt ..plt
    xor edi,edi
    call fflush wrt ..plt
    mov rax,[fd]
    mov [pollfd],eax
    mov word [pollfd+4],1 ; POLLIN
.loop:
    lea rdi,[pollfd]
    mov esi,1
    mov edx,2000 ; finite inactivity timeout
    mov eax,7
    syscall
    test eax,eax
    jle .timeout
    mov dword [address_len],16
    mov rdi,[fd]
    lea rsi,[packet]
    mov edx,1200
    mov r10d,32 ; MSG_TRUNC returns full original datagram length
    lea r8,[peer]
    lea r9,[address_len]
    mov eax,45
    syscall
    test rax,rax
    js .close_failed
    inc dword [seen]
    cmp rax,SIZE
    jne .malformed
    call process
    jmp .send
.malformed:
    ; No reading fields in short or oversized messages.
    lea rdi,[response]
    xor eax,eax
    mov ecx,8
    rep stosd
    mov dword [response],MAGIC
    mov dword [response+4],1
    mov dword [response+16],0x80000000
    mov dword [response+20],1
    inc dword [rejected]
.send:
    mov rdi,[fd]
    lea rsi,[response]
    mov edx,SIZE
    xor r10d,r10d
    lea r8,[peer]
    mov r9d,16
    mov eax,44
    syscall
    mov eax,[seen]
    cmp eax,[limit]
    jb .loop
    xor r13d,r13d
    jmp .finish
.timeout:
    mov r13d,3
.finish:
    lea rdi,[end_fmt]
    mov esi,[seen]
    mov edx,[rejected]
    xor eax,eax
    call printf wrt ..plt
    mov rdi,[fd]
    mov eax,3
    syscall
    mov eax,r13d
    jmp .done
.close_failed:
    mov rdi,[fd]
    mov eax,3
    syscall
.failed:
    mov eax,1
    jmp .done
.usage:
    lea rdi,[usage]
    xor eax,eax
    call printf wrt ..plt
    mov eax,2
.done:
    pop r13
    pop r12
    pop rbp
    ret
; parse_uint(RDI=decimal string) -> RAX / carry invalid. No signed/space forms.
parse_uint:
    xor eax,eax
    xor ecx,ecx
.loop:
    movzx edx,byte [rdi+rcx]
    test edx,edx
    jz .end
    sub edx,'0'
    cmp edx,9
    ja .bad
    imul rax,10
    add rax,rdx
    cmp rax,10000*65536
    ja .bad
    inc rcx
    jmp .loop
.end:
    test rcx,rcx
    jz .bad
    clc
    ret
.bad:
    stc
    ret
; process validated-size packet. No calls, no unbounded state/allocation.
; Response words magic,version,clientId,sequence,op|highbit,status,company,balance.
process:
    lea rdi,[response]
    lea rsi,[packet]
    mov ecx,5
    rep movsd
    mov dword [response],MAGIC
    mov dword [response+4],1
    or dword [response+16],0x80000000
    mov dword [response+20],0
    mov qword [response+24],0
    cmp dword [packet],MAGIC
    jne .invalid
    cmp dword [packet+4],1
    jne .invalid
    mov r8,[peer]
    lea r9,[clients]
    xor ecx,ecx
.search:
    cmp [r9],r8
    je .known
    add r9,24
    inc ecx
    cmp ecx,4
    jb .search
    cmp dword [packet+16],1
    jne .unauthorized
    cmp dword [packet+8],0
    jne .unauthorized
    cmp dword [packet+12],1
    jne .sequence
    cmp qword [packet+20],0
    jne .invalid
    cmp dword [packet+28],0
    jne .invalid
    lea r9,[clients]
    xor ecx,ecx
.free:
    cmp qword [r9],0
    je .allocate
    add r9,24
    inc ecx
    cmp ecx,4
    jb .free
    mov eax,8 ; client capacity
    jmp .reject
.allocate:
    mov [r9],r8
    mov dword [r9+8],1
    mov dword [r9+12],100
    jmp .state
.known:
    lea edx,[rcx+1]
    mov [response+8],edx
    cmp dword [packet+16],1
    jne .auth
    cmp dword [packet+8],0
    jne .unauthorized
    jmp .seqcheck
.auth:
    cmp [packet+8],edx
    jne .unauthorized
.seqcheck:
    mov eax,[packet+12]
    cmp eax,[r9+8]
    je .duplicate
    mov edx,[r9+8]
    inc edx
    cmp eax,edx
    jne .sequence
    mov [r9+8],eax ; consumed and acked even when command rejected
    cmp dword [packet+16],3
    je .snapshot
    cmp dword [packet+16],2
    jne .invalid
    inc dword [r9+16]
    cmp dword [r9+16],16
    ja .rate
    lea eax,[rcx+1]
    cmp [packet+20],eax
    jne .ownership
    mov eax,[packet+24]
    test eax,eax
    jz .invalid
    cmp eax,100
    ja .invalid
    cmp dword [packet+28],8000
    ja .invalid
    cmp eax,[r9+12]
    ja .funds
    sub [r9+12],eax
    jmp .state
.snapshot:
    cmp qword [packet+20],0
    jne .invalid
    cmp dword [packet+28],0
    jne .invalid
.state:
    lea eax,[rcx+1]
    mov [response+8],eax
    mov [response+24],eax
    mov eax,[r9+12]
    mov [response+28],eax
    ret
.duplicate:
    mov eax,2
    jmp .reject_state
.sequence:
    mov eax,3
    jmp .reject
.unauthorized:
    mov eax,4
    jmp .reject
.ownership:
    mov eax,5
    jmp .reject_state
.funds:
    mov eax,6
    jmp .reject_state
.rate:
    mov eax,7
    jmp .reject_state
.invalid:
    mov eax,1
    jmp .reject
.reject_state:
    mov [response+20],eax
    inc dword [rejected]
    jmp .state
.reject:
    mov [response+20],eax
    inc dword [rejected]
    ret
section .note.GNU-stack noalloc noexec nowrite progbits
