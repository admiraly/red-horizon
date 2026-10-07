; Bounded complete-packet validation and immutable remote air_crash lifecycle.
%include "schemas/air_crash.inc"
%include "schemas/air_crash_remote.inc"
default rel
section .bss align=64
global net_air_crashes,net_air_crash_count
net_air_crashes: resb AIR_CRASH_CAPACITY*AIR_CRASH_STRIDE
net_air_crash_count: resd 1
slot_tick: resd AIR_CRASH_CAPACITY
slot_valid: resb AIR_CRASH_CAPACITY

section .text
global air_crash_receive,air_crash_remote_expire,air_crash_remote_reset
air_crash_remote_reset:
 lea rdi,[net_air_crashes]
 xor eax,eax
 mov ecx,(AIR_CRASH_CAPACITY*AIR_CRASH_STRIDE+4+AIR_CRASH_CAPACITY*5)/4
 rep stosd
 ret
air_crash_receive:
 test rdi,rdi
 jz .invalid_leaf
 test esi,esi
 jz .invalid_leaf
 cmp esi,AIR_CRASH_WIRE_MAX*AIR_CRASH_WIRE_STRIDE
 ja .invalid_leaf
 mov eax,esi
 mov r8d,edx
 xor edx,edx
 mov ecx,AIR_CRASH_WIRE_STRIDE
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
 cmp eax,AIR_CRASH_CAPACITY
 jae .invalid
 mov rdx,r12
.duplicate:
 cmp rdx,r15
 je .unique
 cmp eax,[rdx]
 je .invalid
 add rdx,AIR_CRASH_WIRE_STRIDE
 jmp .duplicate
.unique:
 cmp dword [r15+4+AIR_CRASH_ROLE],1
 ja .invalid
 cmp dword [r15+4+AIR_CRASH_SIDE],1
 ja .invalid
 cmp dword [r15+4+AIR_CRASH_ENTITY],32768
 jae .invalid
 cmp dword [r15+4+AIR_CRASH_GENERATION],0
 je .invalid
 cmp dword [r15+4+AIR_CRASH_SEQUENCE],0
 je .invalid
 cmp dword [r15+4+AIR_CRASH_STATE],2
 ja .invalid
 xor ecx,ecx
.reserved:
 cmp qword [r15+4+64+rcx*8],0
 jne .invalid
 inc ecx
 cmp ecx,4
 jb .reserved
 mov eax,r14d
 sub eax,[r15+4+AIR_CRASH_BIRTH]
 js .invalid
 cmp dword [r15+4+AIR_CRASH_STATE],0
 je .inactive_age
 cmp eax,AIR_CRASH_LIFETIME
 jae .invalid
 jmp .pose
.inactive_age:
 cmp eax,AIR_CRASH_LIFETIME
 jb .invalid
.pose:
 xor ecx,ecx
.finite:
 mov eax,[r15+4+rcx*4]
 and eax,0x7fffffff
 mov edx,__float32__(16.0)
 cmp ecx,6
 jae .bounded
 mov edx,__float32__(32.0)
 cmp ecx,3
 jae .bounded
 mov edx,__float32__(1000.0)
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
 cmp ecx,9
 jb .finite
 cmp dword [r15+4+AIR_CRASH_STATE],2
 jne .identity
 cmp qword [r15+4+AIR_CRASH_VX],0
 jne .invalid
 cmp dword [r15+4+AIR_CRASH_VZ],0
 jne .invalid
 cmp qword [r15+4+AIR_CRASH_PITCH],0
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
 imul eax,AIR_CRASH_STRIDE
 lea rdx,[net_air_crashes]
 add rdx,rax
 mov ecx,[r15+4+AIR_CRASH_SEQUENCE]
 cmp ecx,[rdx+AIR_CRASH_SEQUENCE]
 jne .valid_record
 ; Captured role/faction/source identity/generation/birth/sequence are immutable.
 mov ecx,AIR_CRASH_ROLE/4
.immutable:
 mov eax,[r15+4+rcx*4]
 cmp eax,[rdx+rcx*4]
 jne .invalid
 inc ecx
 cmp ecx,AIR_CRASH_SEQUENCE/4+1
 jb .immutable
 ; Equal source tick must repeat exact bytes. Landed pose stays frozen.
 mov eax,[r15]
 lea rcx,[slot_tick]
 cmp r14d,[rcx+rax*4]
 je .exact
 cmp dword [rdx+AIR_CRASH_STATE],2
 jne .valid_record
 cmp dword [r15+4+AIR_CRASH_STATE],1
 je .invalid
.exact:
 xor ecx,ecx
.exact_loop:
 mov eax,[r15+4+rcx*4]
 cmp eax,[rdx+rcx*4]
 jne .invalid
 inc ecx
 cmp ecx,9
 jb .exact_loop
 mov eax,[r15]
 lea rcx,[slot_tick]
 cmp r14d,[rcx+rax*4]
 jne .valid_record
 mov eax,[r15+4+AIR_CRASH_STATE]
 cmp eax,[rdx+AIR_CRASH_STATE]
 jne .invalid
.valid_record:
 add r15,AIR_CRASH_WIRE_STRIDE
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
 imul edx,AIR_CRASH_STRIDE
 lea rdi,[net_air_crashes]
 add rdi,rdx
 cmp byte [r9+rax],0
 je .commit
 mov ecx,r14d
 sub ecx,[r8+rax*4]
 js .next
 mov ecx,[r15+4+AIR_CRASH_SEQUENCE]
 sub ecx,[rdi+AIR_CRASH_SEQUENCE]
 js .next
 jnz .commit
 test dword [rdi+AIR_CRASH_STATE],3
 jnz .commit
 test dword [r15+4+AIR_CRASH_STATE],3
 jnz .next
.commit:
 mov [r8+rax*4],r14d
 mov byte [r9+rax],1
 lea rsi,[r15+4]
 mov ecx,12
 rep movsq
 inc r12d
.next:
 add r15,AIR_CRASH_WIRE_STRIDE
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
air_crash_remote_expire:
 lea rsi,[net_air_crashes]
 mov ecx,AIR_CRASH_CAPACITY
.loop:
 test dword [rsi+AIR_CRASH_STATE],3
 jz .next
 mov eax,edi
 sub eax,[rsi+AIR_CRASH_BIRTH]
 js .next
 cmp eax,AIR_CRASH_LIFETIME
 jb .next
 mov dword [rsi+AIR_CRASH_STATE],0
.next:
 add rsi,AIR_CRASH_STRIDE
 loop .loop
recount:
 lea rsi,[net_air_crashes+AIR_CRASH_STATE]
 mov ecx,AIR_CRASH_CAPACITY
 xor eax,eax
.loop:
 cmp dword [rsi],0
 setne dl
 movzx edx,dl
 add eax,edx
 add rsi,AIR_CRASH_STRIDE
 loop .loop
 mov [net_air_crash_count],eax
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
