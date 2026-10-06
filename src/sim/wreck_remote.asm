; Bounded complete-packet validation and immutable remote wreck lifecycle.
%include "schemas/wreck.inc"
%include "schemas/wreck_remote.inc"
default rel
section .bss align=64
global net_wrecks,net_wreck_count
net_wrecks: resb WRECK_CAPACITY*WRECK_STRIDE
net_wreck_count: resd 1
slot_tick: resd WRECK_CAPACITY
slot_valid: resb WRECK_CAPACITY
section .text
global wreck_receive,wreck_remote_expire,wreck_remote_reset
wreck_remote_reset:
 lea rdi,[net_wrecks]
 xor eax,eax
 mov ecx,(WRECK_CAPACITY*WRECK_STRIDE+4+WRECK_CAPACITY*5)/4
 rep stosd
 ret
wreck_receive:
 test rdi,rdi
 jz .invalid_leaf
 test esi,esi
 jz .invalid_leaf
 cmp esi,WRECK_WIRE_MAX*WRECK_WIRE_STRIDE
 ja .invalid_leaf
 mov eax,esi
 mov r8d,edx
 xor edx,edx
 mov ecx,WRECK_WIRE_STRIDE
 div ecx
 test edx,edx
 jnz .invalid_leaf
 push rbx
 push r12
 push r13
 push r14
 push r15
 mov r12,rdi
 mov r13d,eax
 mov r14d,r8d
 mov r15,rdi
 mov ebx,eax
.validate:
 mov eax,[r15]
 cmp eax,WRECK_CAPACITY
 jae .invalid
 mov rdx,r12
.duplicate:
 cmp rdx,r15
 je .unique
 cmp eax,[rdx]
 je .invalid
 add rdx,WRECK_WIRE_STRIDE
 jmp .duplicate
.unique:
 mov eax,[r15+4+WRECK_KIND]
 sub eax,1
 cmp eax,1
 ja .invalid
 cmp dword [r15+4+WRECK_SIDE],1
 ja .invalid
 cmp dword [r15+4+WRECK_ENTITY],32768
 jae .invalid
 cmp dword [r15+4+WRECK_GENERATION],0
 je .invalid
 cmp dword [r15+4+WRECK_SEQUENCE],0
 je .invalid
 cmp dword [r15+4+WRECK_FLAGS],3
 ja .invalid
 cmp qword [r15+4+56],0
 jne .invalid
 mov eax,[r15+4+WRECK_BIRTH]
 add eax,WRECK_LIFETIME_TICKS
 cmp eax,[r15+4+WRECK_EXPIRY]
 jne .invalid
 mov eax,r14d
 sub eax,[r15+4+WRECK_BIRTH]
 js .invalid
 test dword [r15+4+WRECK_FLAGS],WRECK_ACTIVE
 jz .inactive_age
 cmp eax,WRECK_LIFETIME_TICKS
 jae .invalid
 jmp .pose
.inactive_age:
 cmp eax,WRECK_LIFETIME_TICKS
 jb .invalid
.pose:
 xor ecx,ecx
.finite:
 mov eax,[r15+4+rcx*4]
 and eax,0x7fffffff
 mov edx,__float32__(16.0)
 cmp ecx,3
 jae .bounded
 mov edx,__float32__(2000.0)
 cmp ecx,1
 je .bounded
 mov edx,__float32__(8000.0)
 test eax,eax
 jz .bounded
 test dword [r15+4+rcx*4],0x80000000
 jnz .invalid
.bounded:
 cmp eax,edx
 ja .invalid
 inc ecx
 cmp ecx,6
 jb .finite
 test dword [r15+4+WRECK_FLAGS],WRECK_UPRIGHT
 jz .identity
 cmp dword [r15+4+WRECK_HEADING],0
 jne .invalid
 cmp qword [r15+4+WRECK_PITCH],0
 jne .invalid
.identity:
 ; A reused same sequence cannot change captured immutable pose or identity.
 ; Check only nonstale updates, so old historical slots remain harmless drops.
 mov eax,[r15]
 lea rdx,[slot_valid]
 cmp byte [rdx+rax],0
 je .valid_record
 lea rdx,[slot_tick]
 mov ecx,r14d
 sub ecx,[rdx+rax*4]
 js .valid_record
 shl eax,6
 lea rdx,[net_wrecks]
 add rdx,rax
 mov ecx,[r15+4+WRECK_SEQUENCE]
 cmp ecx,[rdx+WRECK_SEQUENCE]
 jne .valid_record
 xor ecx,ecx
.immutable:
 cmp ecx,WRECK_FLAGS/4
 je .flags
 mov eax,[r15+4+rcx*4]
 cmp eax,[rdx+rcx*4]
 jne .invalid
 jmp .immutable_next
.flags:
 mov eax,[r15+4+WRECK_FLAGS]
 xor eax,[rdx+WRECK_FLAGS]
 test eax,WRECK_UPRIGHT
 jnz .invalid
.immutable_next:
 inc ecx
 cmp ecx,16
 jb .immutable
.valid_record:
 add r15,WRECK_WIRE_STRIDE
 dec ebx
 jnz .validate
 mov r15,r12
 mov ebx,r13d
 xor r12d,r12d
.apply:
 mov eax,[r15]
 lea r8,[slot_tick]
 lea r9,[slot_valid]
 mov edx,eax
 shl edx,6
 lea rdi,[net_wrecks]
 add rdi,rdx
 cmp byte [r9+rax],0
 je .commit
 mov ecx,r14d
 sub ecx,[r8+rax*4]
 js .next
 mov ecx,[r15+4+WRECK_SEQUENCE]
 sub ecx,[rdi+WRECK_SEQUENCE]
 js .next
 jnz .commit
 test dword [rdi+WRECK_FLAGS],WRECK_ACTIVE
 jnz .commit
 test dword [r15+4+WRECK_FLAGS],WRECK_ACTIVE
 jnz .next
.commit:
 mov [r8+rax*4],r14d
 mov byte [r9+rax],1
 lea rsi,[r15+4]
 mov ecx,8
 rep movsq
 inc r12d
.next:
 add r15,WRECK_WIRE_STRIDE
 dec ebx
 jnz .apply
 call recount
 mov eax,r12d
 jmp .done
.invalid:
 mov eax,-1
.done:
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
.invalid_leaf:
 mov eax,-1
 ret
wreck_remote_expire:
 lea rsi,[net_wrecks]
 mov ecx,WRECK_CAPACITY
.loop:
 test dword [rsi+WRECK_FLAGS],WRECK_ACTIVE
 jz .next
 mov eax,edi
 sub eax,[rsi+WRECK_BIRTH]
 js .next
 cmp eax,WRECK_LIFETIME_TICKS
 jb .next
 and dword [rsi+WRECK_FLAGS],~WRECK_ACTIVE
.next:
 add rsi,WRECK_STRIDE
 loop .loop
recount:
 lea rsi,[net_wrecks+WRECK_FLAGS]
 mov ecx,WRECK_CAPACITY
 xor eax,eax
.loop:
 mov edx,[rsi]
 and edx,WRECK_ACTIVE
 add eax,edx
 add rsi,WRECK_STRIDE
 loop .loop
 mov [net_wreck_count],eax
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
