; Read-only authority-derived cosmetic emitters; no render-clock accumulation.
%include "schemas/air_crash.inc"
default rel
extern air_crash_instance,sim_air_crashes,net_air_crashes
section .rodata
seconds: dd 30.0
range2: dd 2250000.0
section .bss align=16
global air_crash_plume_records,air_crash_plume_count
air_crash_plume_records: resb 32*64
air_crash_plume_count: resd 1
section .text
global air_crash_plume,air_crash_plumes_update
; RDI output64,ESI capacity,RDX source96,ECX bytes,R8D source tick.
; EAX0 packed,1 expired cosmetic envelope,-1 invalid; failures are atomic.
air_crash_plume:
 test rdi,rdi
 jz .bad_leaf
 test rdx,rdx
 jz .bad_leaf
 cmp esi,64
 jb .bad_leaf
 cmp ecx,96
 jb .bad_leaf
 sub rsp,200
 mov [rsp+160],rdi
 mov [rsp+168],r8d
 mov rsi,rdx
 lea rdi,[rsp]
 mov ecx,12
 rep movsq
 lea rdi,[rsp+96]
 mov esi,64
 lea rdx,[rsp]
 mov ecx,96
 call air_crash_instance
 test eax,eax
 jnz .bad
 mov eax,[rsp+168]
 sub eax,[rsp+AIR_CRASH_BIRTH]
 js .bad
 cmp eax,600
 jae .expired
 cvtsi2ss xmm1,eax
 divss xmm1,[seconds]
 cmp dword [rsp+AIR_CRASH_STATE],2
 jne .pack
 cmp qword [rsp+AIR_CRASH_VX],0
 jne .bad
 cmp dword [rsp+AIR_CRASH_VZ],0
 jne .bad
.pack:
 mov rdi,[rsp+160]
 movups xmm0,[rsp]
 movups [rdi],xmm0
 movss [rdi+12],xmm1
 movups xmm0,[rsp+AIR_CRASH_VX]
 movups [rdi+16],xmm0
 mov eax,[rsp+AIR_CRASH_SEQUENCE]
 mov [rdi+28],eax
 mov eax,[rsp+AIR_CRASH_STATE]
 mov [rdi+32],eax
 mov dword [rdi+36],0
 mov qword [rdi+40],0
 mov qword [rdi+48],0
 mov qword [rdi+56],0
 xor eax,eax
 jmp .done
.expired:
 mov eax,1
 jmp .done
.bad:
 mov eax,-1
.done:
 add rsp,200
 ret
.bad_leaf:
 mov eax,-1
 ret
; EDI0local/1remote,ESI source tick,XMM0..2 camera XYZ. Fixed128 scan/32 emitters.
air_crash_plumes_update:
 push rbx
 push r12
 push r13
 push r14
 sub rsp,24
 mov r12d,edi
 mov r13d,esi
 movss [rsp],xmm0
 movss [rsp+4],xmm2
 lea rdi,[air_crash_plume_records]
 xor eax,eax
 mov ecx,256
 rep stosq
 mov dword [air_crash_plume_count],0
 cmp r12d,1
 ja .done
 lea rbx,[sim_air_crashes]
 test r12d,r12d
 jz .source
 lea rbx,[net_air_crashes]
.source:
 xor r14d,r14d
.record:
 movss xmm0,[rbx+AIR_CRASH_X]
 subss xmm0,[rsp]
 mulss xmm0,xmm0
 movss xmm1,[rbx+AIR_CRASH_Z]
 subss xmm1,[rsp+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[range2]
 jp .next
 ja .next
 mov eax,[air_crash_plume_count]
 shl eax,6
 lea rdi,[air_crash_plume_records]
 add rdi,rax
 mov esi,64
 mov rdx,rbx
 mov ecx,96
 mov r8d,r13d
 call air_crash_plume
 test eax,eax
 jnz .next
 inc dword [air_crash_plume_count]
 cmp dword [air_crash_plume_count],32
 jae .done
.next:
 add rbx,AIR_CRASH_STRIDE
 inc r14d
 cmp r14d,AIR_CRASH_CAPACITY
 jb .record
.done:
 add rsp,24
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
