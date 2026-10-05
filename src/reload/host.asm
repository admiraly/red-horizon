; Linux reload proof. main(argc,argv) follows SysV; exit 0 success, 2 usage.
; All swaps occur between synchronous update calls: no in-flight worker/callback.
default rel
%include "abi.inc"
extern dlopen, dlsym, dlclose, printf
section .rodata
symbol: db 'rh_module_table',0
usage: db 'usage: reload-proof initial.so compatible.so incompatible.so missing.so valid.params invalid.params',10,0
fmt: db '{"event":"%s","status":%d,"ticks":%lu,"value":%lu,"step":%lu}',10,0
e_initial: db 'initial',0
e_swap: db 'compatible',0
e_bad: db 'incompatible',0
e_missing: db 'missing',0
e_param: db 'parameter',0
e_invalid: db 'invalid_parameter',0
section .data align=8
state: dq 0,0,1
section .bss align=8
active: resq 1
update_fn: resq 1
parameter_buffer: resb 32
section .text
global main
main:
    push rbp
    mov rbp,rsp
    push r12
    push r13
    cmp edi,7
    jne .usage
    mov r12,rsi
    mov rdi,[r12+8]
    call load_candidate
    cmp eax,1
    jne .initial_failed
    call tick
    lea rdi,[e_initial]
    mov esi,1
    call report
    mov rdi,[r12+16]
    call load_candidate
    mov r13d,eax
    call tick
    lea rdi,[e_swap]
    mov esi,r13d
    call report
    mov rdi,[r12+24]
    call load_candidate
    mov r13d,eax
    call tick
    lea rdi,[e_bad]
    mov esi,r13d
    call report
    mov rdi,[r12+32]
    call load_candidate
    mov r13d,eax
    call tick
    lea rdi,[e_missing]
    mov esi,r13d
    call report
    mov rdi,[r12+40]
    call load_parameter
    mov r13d,eax
    call tick
    lea rdi,[e_param]
    mov esi,r13d
    call report
    mov rdi,[r12+48]
    call load_parameter
    mov r13d,eax
    call tick
    lea rdi,[e_invalid]
    mov esi,r13d
    call report
    mov rdi,[active]
    call dlclose wrt ..plt
    xor eax,eax
    jmp .done
.initial_failed:
    lea rdi,[e_initial]
    mov esi,eax
    call report
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
; load_candidate(RDI=path) -> EAX 1 swapped, 0 loader/symbol failure,
; -1 incompatible. Keeps old module callable on either failure.
; Trusted local DSOs only: dlopen executes ELF constructors before validation.
load_candidate:
    push rbp
    mov rbp,rsp
    push r12
    push r13
    mov esi,2 ; RTLD_NOW | RTLD_LOCAL
    call dlopen wrt ..plt
    test rax,rax
    jz .failed
    mov r12,rax
    mov rdi,rax
    lea rsi,[symbol]
    call dlsym wrt ..plt
    test rax,rax
    jz .symbol_failed
    cmp qword [rax+TABLE_ABI],RH_ABI
    jne .incompatible
    mov rdx,RH_SCHEMA
    cmp [rax+TABLE_SCHEMA],rdx
    jne .incompatible
    mov r13,[rax+TABLE_UPDATE_REL]
    add r13,rax
    ; Publish together at this single-thread safe boundary, then unload old.
    mov rdi,[active]
    mov [active],r12
    mov [update_fn],r13
    test rdi,rdi
    jz .success
    call dlclose wrt ..plt
.success:
    mov eax,1
    jmp .done
.incompatible:
    mov r13d,-1
    jmp .reject
.symbol_failed:
    xor r13d,r13d
.reject:
    mov rdi,r12
    call dlclose wrt ..plt
    mov eax,r13d
    jmp .done
.failed:
    xor eax,eax
.done:
    pop r13
    pop r12
    pop rbp
    ret
; load_parameter(RDI=path) -> EAX 1 published, 0 rejected.
; Strict unsigned decimal integer 1..100 with optional final LF. Max 31 bytes.
; Synchronous M0 validation; no match exists and no threads are running.
; Read into scratch, validate fully, publish one aligned u64 at safe boundary.
load_parameter:
    mov eax,2 ; Linux open
    xor esi,esi
    xor edx,edx
    syscall
    test rax,rax
    js .failed
    mov r8,rax
    mov rdi,rax
    xor eax,eax ; read
    lea rsi,[parameter_buffer]
    mov edx,32
    syscall
    mov r9,rax
    mov rdi,r8
    mov eax,3 ; close
    syscall
    cmp r9,1
    jl .failed
    cmp r9,32
    jge .failed
    lea rsi,[parameter_buffer]
    xor edx,edx ; accumulator
    xor ecx,ecx ; position
.parse:
    movzx eax,byte [rsi+rcx]
    cmp al,10
    je .newline
    sub eax,'0'
    cmp eax,9
    ja .failed
    imul edx,10
    add edx,eax
    cmp edx,100
    ja .failed
    inc rcx
    cmp rcx,r9
    jb .parse
    jmp .publish
.newline:
    test rcx,rcx
    jz .failed
    inc rcx
    cmp rcx,r9
    jne .failed
.publish:
    test edx,edx
    jz .failed
    mov [state+STATE_STEP],rdx
    mov eax,1
    ret
.failed:
    xor eax,eax
    ret
tick:
    lea rdi,[state]
    jmp [update_fn]
; report(RDI=event,ESI=status). Tail-call libc with caller-aligned stack.
report:
    mov rdx,rsi
    mov rsi,rdi
    lea rdi,[fmt]
    mov rcx,[state+STATE_TICKS]
    mov r8,[state+STATE_VALUE]
    mov r9,[state+STATE_STEP]
    xor eax,eax
    jmp printf wrt ..plt
section .note.GNU-stack noalloc noexec nowrite progbits
