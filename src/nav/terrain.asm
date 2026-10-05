; Authoritative SSE2 analytic terrain and bounded static-solid queries.
default rel
section .rodata align=16
global terrain_obstacle_count, terrain_obstacles
terrain_obstacle_count: dd 5
; xmin,zmin,xmax,zmax,base,height,flags,reserved. Flag1 = ground solid.
terrain_obstacles:
 dd 3988.0,1100.0,4012.0,1500.0,20.0,28.0,1,0
 dd 3988.0,3700.0,4012.0,4100.0,20.0,28.0,1,0
 dd 3988.0,6300.0,4012.0,6700.0,20.0,28.0,1,0
 dd 5170.0,1540.0,5230.0,1600.0,12.0,20.0,1,0
 dd 2770.0,3540.0,2830.0,3600.0,12.0,20.0,1,0
center: dd 4000.0
xscale: dd 0.000001
zscale: dd 0.0000005
ridge_scale: dd 0.00125
ridge_height: dd 18.0
base: dd 12.0
one: dd 1.0
zero: dd 0.0
maximum: dd 8000.0
align 16
abs_mask: dd 0x7fffffff,0,0,0
margin: dd 4.0
corner_near: dd 2.0
ray_eighth: dd 0.125
section .text
global terrain_height, terrain_blocked, terrain_los, terrain_move
terrain_height:
 subss xmm0,[center]
 subss xmm1,[center]
 movaps xmm2,xmm0
 andps xmm2,[abs_mask]
 mulss xmm2,[ridge_scale]
 movss xmm3,[one]
 subss xmm3,xmm2
 maxss xmm3,[zero]
 mulss xmm3,[ridge_height]
 mulss xmm0,xmm0
 mulss xmm0,[xscale]
 mulss xmm1,xmm1
 mulss xmm1,[zscale]
 addss xmm0,xmm1
 addss xmm0,[base]
 addss xmm0,xmm3
 ret
terrain_blocked:
 xor eax,eax
 cmp edi,3
 je .return
 ucomiss xmm0,[zero]
 jp .blocked
 jb .blocked
 ucomiss xmm0,[maximum]
 ja .blocked
 ucomiss xmm1,[zero]
 jp .blocked
 jb .blocked
 ucomiss xmm1,[maximum]
 ja .blocked
 lea rsi,[terrain_obstacles]
 mov ecx,[terrain_obstacle_count]
.loop:
 comiss xmm0,[rsi]
 jb .next
 comiss xmm0,[rsi+8]
 ja .next
 comiss xmm1,[rsi+4]
 jb .next
 comiss xmm1,[rsi+12]
 jbe .blocked
.next:
 add rsi,32
 loop .loop
.return: ret
.blocked: mov eax,1
 ret
; Segment/AABB slab test. Inputs start/end xyz packed in stack record RDI:
; x1,y1,z1,x2,y2,z2. RSI obstacle. EAX1 hits, 0 misses. No calls.
slab:
 movss xmm6,[zero]
 movss xmm7,[one]
 xor ecx,ecx
.axis:
 movss xmm8,[rdi+rcx*4]
 movss xmm9,[rdi+rcx*4+12]
 subss xmm9,xmm8
 cmp ecx,0
 jne .not_x
 movss xmm10,[rsi]
 movss xmm11,[rsi+8]
 jmp .bounds
.not_x:
 cmp ecx,1
 jne .z
 movss xmm10,[rsi+16]
 movaps xmm11,xmm10
 addss xmm11,[rsi+20]
 jmp .bounds
.z:
 movss xmm10,[rsi+4]
 movss xmm11,[rsi+12]
.bounds:
 ucomiss xmm9,[zero]
 jne .nonzero
 comiss xmm8,xmm10
 jb .miss
 comiss xmm8,xmm11
 ja .miss
 jmp .next
.nonzero:
 subss xmm10,xmm8
 subss xmm11,xmm8
 divss xmm10,xmm9
 divss xmm11,xmm9
 movaps xmm12,xmm10
 minss xmm10,xmm11
 maxss xmm11,xmm12
 maxss xmm6,xmm10
 minss xmm7,xmm11
 comiss xmm6,xmm7
 ja .miss
.next:
 inc ecx
 cmp ecx,3
 jb .axis
 mov eax,1
 ret
.miss: xor eax,eax
 ret
terrain_los:
 push rbx
 sub rsp,64
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 lea rbx,[terrain_obstacles]
 mov dword [rsp+24],0
.obstacle:
 mov rdi,rsp
 mov rsi,rbx
 call slab
 test eax,eax
 jnz .blocked
 add rbx,32
 inc dword [rsp+24]
 mov eax,[rsp+24]
 cmp eax,[terrain_obstacle_count]
 jb .obstacle
 ; Seven interior ground samples; solid obstacles were swept exactly above.
 mov ebx,1
.ground:
 cvtsi2ss xmm4,ebx
 mulss xmm4,[ray_eighth]
 movss [rsp+28],xmm4
 movss xmm0,[rsp+12]
 subss xmm0,[rsp]
 mulss xmm0,xmm4
 addss xmm0,[rsp]
 movss xmm1,[rsp+20]
 subss xmm1,[rsp+8]
 mulss xmm1,xmm4
 addss xmm1,[rsp+8]
 call terrain_height
 movss xmm4,[rsp+28]
 movss xmm1,[rsp+16]
 subss xmm1,[rsp+4]
 mulss xmm1,xmm4
 addss xmm1,[rsp+4]
 comiss xmm1,xmm0
 jb .blocked
 inc ebx
 cmp ebx,8
 jb .ground
 mov eax,1
 jmp .out
.blocked: xor eax,eax
.out:
 add rsp,64
 pop rbx
 ret
terrain_move:
 push rbx
 sub rsp,64
 movss [rsp],xmm0
 movss [rsp+8],xmm1
 movss [rsp+12],xmm2
 movss [rsp+20],xmm3
 movss [rsp+24],xmm4
 mov [rsp+28],edi
 mov dword [rsp+4],0x41f00000 ; y30 forces overlap with wall vertical slabs
 mov dword [rsp+16],0x41f00000
 cmp edi,3
 je .step
 lea rbx,[terrain_obstacles]
 mov dword [rsp+32],0
.corridor:
 mov rdi,rsp
 mov rsi,rbx
 call slab
 test eax,eax
 jz .next_obstacle
 ; Go around a consistent upper/lower edge, then across its far corner.
 movss xmm0,[rsp+8]
 movss xmm1,[rbx+4]
 addss xmm1,[rbx+12]
 mulss xmm1,[ray_eighth] ; midpoint compare below uses multiply4 = half
 addss xmm1,xmm1
 addss xmm1,xmm1
 comiss xmm0,xmm1
 jae .upper
 movss xmm1,[rbx+4]
 subss xmm1,[margin]
 jmp .edge
.upper:
 movss xmm1,[rbx+12]
 addss xmm1,[margin]
.edge:
 movss [rsp+20],xmm1
 subss xmm0,xmm1
 andps xmm0,[abs_mask]
 movss xmm2,[rsp+12]
 subss xmm2,[rsp]
 ucomiss xmm2,[zero]
 jb .leftward
 movss xmm2,[rbx]
 subss xmm2,[margin]
 comiss xmm0,[corner_near]
 ja .corner
 movss xmm2,[rbx+8]
 addss xmm2,[margin]
 jmp .corner
.leftward:
 movss xmm2,[rbx+8]
 addss xmm2,[margin]
 comiss xmm0,[corner_near]
 ja .corner
 movss xmm2,[rbx]
 subss xmm2,[margin]
.corner:
 movss [rsp+12],xmm2
 jmp .step
.next_obstacle:
 add rbx,32
 inc dword [rsp+32]
 mov eax,[rsp+32]
 cmp eax,[terrain_obstacle_count]
 jb .corridor
.step:
 movss xmm2,[rsp+12]
 subss xmm2,[rsp]
 movss xmm3,[rsp+20]
 subss xmm3,[rsp+8]
 movaps xmm0,xmm2
 mulss xmm0,xmm0
 movaps xmm1,xmm3
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[zero]
 je .stay
 sqrtss xmm0,xmm0
 movss xmm4,[rsp+24]
 minss xmm4,xmm0
 divss xmm4,xmm0
 mulss xmm2,xmm4
 mulss xmm3,xmm4
 addss xmm2,[rsp]
 addss xmm3,[rsp+8]
 maxss xmm2,[zero]
 minss xmm2,[maximum]
 maxss xmm3,[zero]
 minss xmm3,[maximum]
 movss [rsp+40],xmm2
 movss [rsp+44],xmm3
 movaps xmm0,xmm2
 movaps xmm1,xmm3
 mov edi,[rsp+28]
 call terrain_blocked
 test eax,eax
 jnz .stay
 movss xmm0,[rsp+40]
 movss xmm1,[rsp+44]
 jmp .out
.stay:
 movss xmm0,[rsp]
 movss xmm1,[rsp+8]
.out:
 add rsp,64
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
