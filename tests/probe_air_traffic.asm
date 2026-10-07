default rel
extern air_traffic_request
section .rodata align=16
vectors: dd 0x3f000001,0x3f000002,0x3f000003,0x3f000004,0x3f000005,0x3f000006,0x3f000007,0x3f000008,0x3f000009,0x3f00000a,0x3f00000b,0x3f00000c,0x3f00000d,0x3f00000e,0x3f00000f,0x3f000010,0x3f000011,0x3f000012,0x3f000013,0x3f000014,0x3f000015,0x3f000016,0x3f000017,0x3f000018,0x3f000019,0x3f00001a,0x3f00001b,0x3f00001c,0x3f00001d,0x3f00001e,0x3f00001f,0x3f000020
section .text
global probe_air_traffic_request
; EDI/ESI source/base, RDX128-byte vector out, RCX56-byte ABI out.
probe_air_traffic_request:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov [rsp],rdx
 mov [rsp+8],rcx
 mov [rsp+16],rsp
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 movdqu xmm0,[vectors+0]
 movdqu xmm1,[vectors+16]
 movdqu xmm2,[vectors+32]
 movdqu xmm3,[vectors+48]
 movdqu xmm4,[vectors+64]
 movdqu xmm5,[vectors+80]
 movdqu xmm6,[vectors+96]
 movdqu xmm7,[vectors+112]
 call air_traffic_request
 mov r8d,eax
 mov rdx,[rsp]
 movdqu [rdx+0],xmm0
 movdqu [rdx+16],xmm1
 movdqu [rdx+32],xmm2
 movdqu [rdx+48],xmm3
 movdqu [rdx+64],xmm4
 movdqu [rdx+80],xmm5
 movdqu [rdx+96],xmm6
 movdqu [rdx+112],xmm7
 mov rcx,[rsp+8]
 mov [rcx],rbx
 mov [rcx+8],rbp
 mov [rcx+16],r12
 mov [rcx+24],r13
 mov [rcx+32],r14
 mov [rcx+40],r15
 mov rax,rsp
 sub rax,[rsp+16]
 mov [rcx+48],rax
 mov eax,r8d
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
