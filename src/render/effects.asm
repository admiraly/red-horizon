; Allocation-free cosmetic pool. Reads authority; never modifies gameplay records.
default rel
%include "schemas/player.inc"
global effects_update,effects_records,effects_tracers,effects_active
extern sim_players,sinf,cosf
section .rodata
zero: dd 0.0
life: dd 0.14
reach: dd 100.0
forward: dd 3.0
right: dd 0.22
down: dd 0.25
section .bss
align 16
effects_records: resb 64*32 ; start xyz,remaining; end xyz,type1 tracer
seen_generation: resd 4
seen_shots: resd 4
next_slot: resd 1
effects_tracers: resd 1
effects_active: resd 1
dt: resd 1
sy: resd 1
cy: resd 1
pitch_sin: resd 1
cp: resd 1
section .text
; XMM0 elapsed render time. Counters observed exactly once despite repeated frames.
effects_update:
 push rbx
 push r12
 push r13
 movss [dt],xmm0
 lea rbx,[effects_records]
 mov ecx,64
 xor edx,edx
.decay:
 movss xmm1,[rbx+12]
 subss xmm1,xmm0
 maxss xmm1,[zero]
 movss [rbx+12],xmm1
 ucomiss xmm1,[zero]
 jbe .next
 inc edx
.next:
 add rbx,32
 loop .decay
 mov [effects_active],edx
 xor r12d,r12d
 lea r13,[sim_players]
.players:
 lea rdx,[seen_generation]
 lea rcx,[seen_shots]
 mov eax,[r13+PLAYER_GENERATION]
 cmp dword [r13+PLAYER_CONNECTED],0
 je .baseline
 cmp eax,[rdx+r12*4]
 jne .baseline
 mov eax,[r13+PLAYER_SHOTS]
 cmp eax,[rcx+r12*4]
 jbe .baseline
 mov ebx,eax
 xor edx,edx
 mov esi,3
 div esi
 mov esi,eax
 mov eax,[rcx+r12*4]
 xor edx,edx
 mov edi,3
 div edi
 mov [rcx+r12*4],ebx
 cmp esi,eax
 je .advance
 ; Collapse skipped snapshot intervals to at most one current cosmetic tracer.
 call .tracer
 jmp .advance
.baseline:
 mov eax,[r13+PLAYER_GENERATION]
 lea rdx,[seen_generation]
 mov [rdx+r12*4],eax
 mov eax,[r13+PLAYER_SHOTS]
 lea rcx,[seen_shots]
 mov [rcx+r12*4],eax
.advance:
 add r13,PLAYER_STRIDE
 inc r12d
 cmp r12d,4
 jb .players
 pop r13
 pop r12
 pop rbx
 ret
.tracer:
 push rbx
 movss xmm0,[r13+PLAYER_YAW]
 call sinf
 movss [sy],xmm0
 movss xmm0,[r13+PLAYER_YAW]
 call cosf
 movss [cy],xmm0
 movss xmm0,[r13+PLAYER_PITCH]
 call sinf
 movss [pitch_sin],xmm0
 movss xmm0,[r13+PLAYER_PITCH]
 call cosf
 movss [cp],xmm0
 mov eax,[next_slot]
 inc dword [next_slot]
 and dword [next_slot],63
 shl eax,5
 lea rbx,[effects_records]
 add rbx,rax
 movss xmm0,[sy]
 mulss xmm0,[cp]
 movss xmm1,[pitch_sin]
 movss xmm2,[cy]
 mulss xmm2,[cp]
 movaps xmm3,xmm0
 movaps xmm4,xmm1
 movaps xmm5,xmm2
 mulss xmm3,[reach]
 mulss xmm4,[reach]
 mulss xmm5,[reach]
 addss xmm3,[r13+PLAYER_X]
 addss xmm4,[r13+PLAYER_Y]
 addss xmm5,[r13+PLAYER_Z]
 movss [rbx+16],xmm3
 movss [rbx+20],xmm4
 movss [rbx+24],xmm5
 mulss xmm0,[forward]
 mulss xmm1,[forward]
 mulss xmm2,[forward]
 movss xmm3,[cy]
 mulss xmm3,[right]
 addss xmm0,xmm3
 movss xmm3,[sy]
 mulss xmm3,[right]
 subss xmm2,xmm3
 addss xmm0,[r13+PLAYER_X]
 addss xmm1,[r13+PLAYER_Y]
 subss xmm1,[down]
 addss xmm2,[r13+PLAYER_Z]
 movss [rbx],xmm0
 movss [rbx+4],xmm1
 movss [rbx+8],xmm2
 movss xmm0,[life]
 movss [rbx+12],xmm0
 mov dword [rbx+28],1
 inc dword [effects_tracers]
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
