; Conservative circular-body enclosure against static ground solids.
default rel
%include "terrain_body.inc"
extern terrain_obstacles, terrain_obstacle_count
extern terrain_blocked, terrain_path_clear, terrain_move
section .data
global terrain_body_enabled
terrain_body_enabled: dd 1
section .rodata align=16
; One millimetre safety inflation prevents float round-down at map/wall tangency.
radii: dd 0.551,3.551,4.491,0.0
zero: dd 0.0
one: dd 1.0
half: dd 0.5
maximum: dd 8000.0
corner_near: dd 0.1
clearance: dd 0.5
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global terrain_body_init, terrain_body_blocked, terrain_body_path_clear
global terrain_body_move, terrain_body_hash
terrain_body_init:
 mov dword [terrain_body_enabled],1
 ret
terrain_body_hash:
 lea rsi,[terrain_body_enabled]
 mov ecx,4
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .loop
 ret
; Validate role and finite bounded XZ. Returns carry on invalid, radius XMM5.
validate:
 cmp edi,3
 ja .bad
 lea rax,[radii]
 movss xmm5,[rax+rdi*4]
 ucomiss xmm0,[zero]
 jp .bad
 jb .bad
 ucomiss xmm0,[maximum]
 ja .bad
 ucomiss xmm1,[zero]
 jp .bad
 jb .bad
 ucomiss xmm1,[maximum]
 ja .bad
 clc
 ret
.bad: stc
 ret
; RSI immutable box, radius XMM5 -> expanded bounds XMM10..13.
bounds:
 movss xmm10,[rsi]
 subss xmm10,xmm5
 movss xmm11,[rsi+8]
 addss xmm11,xmm5
 movss xmm12,[rsi+4]
 subss xmm12,xmm5
 movss xmm13,[rsi+12]
 addss xmm13,xmm5
 ret
terrain_body_blocked:
 call validate
 jc .blocked
 cmp dword [terrain_body_enabled],0
 je terrain_blocked
 cmp edi,3
 je .clear
 ucomiss xmm0,xmm5
 jb .blocked
 ucomiss xmm1,xmm5
 jb .blocked
 movss xmm6,[maximum]
 subss xmm6,xmm5
 ucomiss xmm0,xmm6
 ja .blocked
 ucomiss xmm1,xmm6
 ja .blocked
 lea rsi,[terrain_obstacles]
 mov ecx,[terrain_obstacle_count]
 test ecx,ecx
 jz .clear
.loop:
 test dword [rsi+24],1
 jz .next
 call bounds
 ucomiss xmm0,xmm10
 jb .next
 ucomiss xmm0,xmm11
 ja .next
 ucomiss xmm1,xmm12
 jb .next
 ucomiss xmm1,xmm13
 jbe .blocked
.next:
 add rsi,32
 dec ecx
 jnz .loop
.clear: xor eax,eax
 ret
.blocked: mov eax,1
 ret
; Segment record RDX x,z,endx,endz. XMM5 radius, RSI box.
; EAX hit, XMM6 entry fraction; pure derived scratch.
slab:
 call bounds
 movss xmm6,[zero]
 movss xmm7,[one]
 movss xmm8,[rdx]
 movss xmm9,[rdx+8]
 subss xmm9,xmm8
 call axis
 test eax,eax
 jz .miss
 movss xmm8,[rdx+4]
 movss xmm9,[rdx+12]
 subss xmm9,xmm8
 movaps xmm10,xmm12
 movaps xmm11,xmm13
 call axis
 ret
.miss: xor eax,eax
 ret
axis:
 ucomiss xmm9,[zero]
 jne .moving
 ucomiss xmm8,xmm10
 jb .miss
 ucomiss xmm8,xmm11
 ja .miss
 mov eax,1
 ret
.moving:
 subss xmm10,xmm8
 subss xmm11,xmm8
 divss xmm10,xmm9
 divss xmm11,xmm9
 movaps xmm14,xmm10
 minss xmm10,xmm11
 maxss xmm11,xmm14
 maxss xmm6,xmm10
 minss xmm7,xmm11
 ucomiss xmm6,xmm7
 ja .miss
 mov eax,1
 ret
.miss: xor eax,eax
 ret
terrain_body_path_clear:
 push rbx
 sub rsp,32
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 mov [rsp+16],edi
 call terrain_body_blocked
 test eax,eax
 jnz .blocked
 movss xmm0,[rsp+8]
 movss xmm1,[rsp+12]
 mov edi,[rsp+16]
 call terrain_body_blocked
 test eax,eax
 jnz .blocked
 cmp dword [terrain_body_enabled],0
 je .legacy
 cmp dword [rsp+16],3
 je .clear
 lea rbx,[terrain_obstacles]
 mov dword [rsp+20],0
.loop:
 mov eax,[rsp+20]
 cmp eax,[terrain_obstacle_count]
 jae .clear
 test dword [rbx+24],1
 jz .next
 mov rsi,rbx
 mov rdx,rsp
 call slab
 test eax,eax
 jnz .blocked
.next:
 add rbx,32
 inc dword [rsp+20]
 jmp .loop
.legacy:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 call terrain_path_clear
 jmp .out
.clear: mov eax,1
 jmp .out
.blocked: xor eax,eax
.out:
 add rsp,32
 pop rbx
 ret
terrain_body_move:
 push rbx
 sub rsp,80
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 mov [rsp+20],edi
 call validate
 jc .stay
 movss [rsp+24],xmm5
 movaps xmm0,xmm2
 movaps xmm1,xmm3
 call validate
 jc .stay
 movss xmm4,[rsp+16]
 ucomiss xmm4,[zero]
 jp .stay
 jbe .stay
 movaps xmm0,xmm4
 andps xmm0,[abs_mask]
 ucomiss xmm0,[maximum]
 ja .stay
 cmp dword [terrain_body_enabled],0
 je .legacy
 cmp dword [rsp+20],3
 je .legacy
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 call terrain_body_blocked
 test eax,eax
 jnz .stay
 ; Clamp goal to body map inset. A blocked obstacle goal is approached safely.
 movss xmm5,[rsp+24]
 movss xmm6,[maximum]
 subss xmm6,xmm5
 movss xmm0,[rsp+8]
 maxss xmm0,xmm5
 minss xmm0,xmm6
 movss [rsp+8],xmm0
 movss xmm0,[rsp+12]
 maxss xmm0,xmm5
 minss xmm0,xmm6
 movss [rsp+12],xmm0
 mov qword [rsp+32],0
 movss xmm0,[one]
 movss [rsp+40],xmm0
 lea rbx,[terrain_obstacles]
 mov dword [rsp+28],0
.search:
 mov eax,[rsp+28]
 cmp eax,[terrain_obstacle_count]
 jae .route
 test dword [rbx+24],1
 jz .next
 mov rsi,rbx
 mov rdx,rsp
 call slab
 test eax,eax
 jz .next
 ucomiss xmm6,[rsp+40]
 ja .next
 movss [rsp+40],xmm6
 mov [rsp+32],rbx
.next:
 add rbx,32
 inc dword [rsp+28]
 jmp .search
.route:
 mov rbx,[rsp+32]
 test rbx,rbx
 jz .step
 mov rsi,rbx
 call bounds
 movss xmm0,[rbx+4]
 addss xmm0,[rbx+12]
 mulss xmm0,[half]
 movss xmm1,[rsp+12]
 ucomiss xmm1,xmm0
 jae .upper
 movaps xmm1,xmm12
 subss xmm1,[clearance]
 jmp .edge
.upper:
 movaps xmm1,xmm13
 addss xmm1,[clearance]
.edge:
 movss xmm0,[rsp+4]
 subss xmm0,xmm1
 andps xmm0,[abs_mask]
 movss xmm2,[rsp+8]
 subss xmm2,[rsp]
 ucomiss xmm2,[zero]
 jb .left
 movaps xmm2,xmm10
 subss xmm2,[clearance]
 ucomiss xmm0,[corner_near]
 ja .corner
 movaps xmm2,xmm11
 addss xmm2,[clearance]
 jmp .corner
.left:
 movaps xmm2,xmm11
 addss xmm2,[clearance]
 ucomiss xmm0,[corner_near]
 ja .corner
 movaps xmm2,xmm10
 subss xmm2,[clearance]
.corner:
 movss [rsp+8],xmm2
 movss [rsp+12],xmm1
.step:
 movss xmm2,[rsp+8]
 subss xmm2,[rsp]
 movss xmm3,[rsp+12]
 subss xmm3,[rsp+4]
 movaps xmm0,xmm2
 mulss xmm0,xmm0
 movaps xmm1,xmm3
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[zero]
 je .stay
 sqrtss xmm0,xmm0
 movss xmm4,[rsp+16]
 minss xmm4,xmm0
 divss xmm4,xmm0
 mulss xmm2,xmm4
 mulss xmm3,xmm4
 addss xmm2,[rsp]
 addss xmm3,[rsp+4]
 movss [rsp+48],xmm2
 movss [rsp+52],xmm3
 call .check
 test eax,eax
 jnz .accept
 movss xmm2,[rsp+48]
 movss xmm3,[rsp+4]
 call .check
 test eax,eax
 jnz .accept
 movss xmm2,[rsp]
 movss xmm3,[rsp+52]
 call .check
 test eax,eax
 jz .stay
.accept:
 movss xmm0,[rsp+56]
 movss xmm1,[rsp+60]
 jmp .out
.legacy:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 mov edi,[rsp+20]
 call terrain_move
 jmp .out
.stay:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
.out:
 add rsp,80
 pop rbx
 ret
.check:
 ; Internal call shifts stack by8; compensate record addresses.
 movss [rsp+64],xmm2
 movss [rsp+68],xmm3
 movss xmm0,[rsp+8]
 movss xmm1,[rsp+12]
 mov edi,[rsp+28]
 sub rsp,8
 call terrain_body_path_clear
 add rsp,8
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
