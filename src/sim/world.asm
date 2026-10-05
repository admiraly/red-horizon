; ABI v1. All routines preserve SysV nonvolatile registers. Fixed 30 Hz steps.
default rel
section .bss align=64
global sim_count, sim_tick_count, sim_alive, sim_engaged, sim_entities
sim_count: resd 1
sim_tick_count: resd 1
sim_alive: resd 2
sim_engaged: resd 1
sim_entities: resb 32768*32
heads: resd 1024
links: resd 32768
damage: resd 32768
orders: resd 6
rng: resd 1
section .rodata
health: dd 100,400,160,200
speed: dd 1.5,2.2,0.5,5.0
range2: dd 57600.0,202500.0,422500.0,202500.0
power: dd 3,10,15,6
zero: dd 0.0
maximum: dd 8000.0
cell_scale: dd 0.004
section .text
global sim_init, sim_tick, sim_checksum, sim_order
; Accept even counts 2..32768; invalid calls leave state unchanged.
sim_init:
 cmp edi,2
 jb .bad
 cmp edi,32768
 ja .bad
 test edi,1
 jnz .bad
 push rbx
 push r12
 mov [sim_count],edi
 mov [rng],esi
 mov dword [sim_tick_count],0
 mov dword [sim_engaged],0
 shr edi,1
 mov [sim_alive],edi
 mov [sim_alive+4],edi
 lea rdi,[orders]
 xor eax,eax
 mov ecx,6
 rep stosd
 xor r12d,r12d
 lea rbx,[sim_entities]
.loop:
 mov eax,[rng]
 imul eax,1664525
 add eax,1013904223
 mov [rng],eax
 mov edx,eax
 and edx,511
 add edx,3400
 mov ecx,[sim_count]
 shr ecx,1
 xor esi,esi
 cmp r12d,ecx
 jb .side
 mov esi,1
 add edx,650
.side:
 cvtsi2ss xmm0,edx
 movss [rbx],xmm0
 mov [rbx+12],esi
 mov eax,r12d
 xor edx,edx
 mov ecx,3
 div ecx
 mov [rbx+20],edx
 imul edx,2600
 add edx,700
 mov eax,[rng]
 shr eax,16
 and eax,1023
 add edx,eax
 cvtsi2ss xmm0,edx
 movss [rbx+4],xmm0
 ; 75% infantry, 12.5% armour, 6.25% artillery, 6.25% aircraft.
 mov eax,r12d
 and eax,15
 xor edx,edx
 cmp eax,12
 jb .kind
 mov edx,1
 cmp eax,14
 jb .kind
 mov edx,2
 je .kind
 mov edx,3
.kind:
 mov [rbx+16],edx
 lea rcx,[health]
 mov eax,[rcx+rdx*4]
 mov [rbx+8],eax
 mov dword [rbx+24],-1
 mov dword [rbx+28],1
 add rbx,32
 inc r12d
 cmp r12d,[sim_count]
 jb .loop
 pop r12
 pop rbx
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
sim_order:
 cmp edi,1
 ja .bad
 cmp esi,2
 ja .bad
 cmp edx,2
 ja .bad
 imul edi,3
 add edi,esi
 lea rax,[orders]
 mov [rax+rdi*4],edx
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
sim_tick:
 cmp dword [sim_count],0
 je .uninitialized
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,32
 inc dword [sim_tick_count]
 mov dword [sim_engaged],0
 lea rdi,[heads]
 mov eax,-1
 mov ecx,1024
 rep stosd
 lea rdi,[damage]
 xor eax,eax
 mov ecx,[sim_count]
 rep stosd
 xor r12d,r12d
 lea rbx,[sim_entities]
.move:
 cmp dword [rbx+8],0
 je .move_next
 mov eax,[rbx+16]
 lea rcx,[speed]
 movss xmm1,[rcx+rax*4]
 mov eax,[rbx+12]
 imul eax,3
 add eax,[rbx+20]
 lea rcx,[orders]
 mov eax,[rcx+rax*4]
 cmp eax,1
 je .insert
 cmp eax,2
 je .retreat
 ; Advance holds a firing position while its last target is alive.
 mov edx,[rbx+24]
 cmp edx,-1
 je .direction
 mov ecx,edx
 shl rcx,5
 lea rsi,[sim_entities]
 cmp dword [rsi+rcx+8],0
 jne .insert
 jmp .direction
.retreat:
 xorps xmm2,xmm2
 subss xmm2,xmm1
 movaps xmm1,xmm2
.direction:
 cmp dword [rbx+12],0
 je .advance
 xorps xmm2,xmm2
 subss xmm2,xmm1
 movaps xmm1,xmm2
.advance:
 movss xmm0,[rbx]
 addss xmm0,xmm1
 maxss xmm0,[zero]
 minss xmm0,[maximum]
 movss [rbx],xmm0
.insert:
 movss xmm0,[rbx]
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .xok
 mov eax,31
.xok:
 movss xmm0,[rbx+4]
 mulss xmm0,[cell_scale]
 cvttss2si edx,xmm0
 cmp edx,31
 jbe .zok
 mov edx,31
.zok:
 shl edx,5
 add eax,edx
 lea rcx,[heads]
 mov edx,[rcx+rax*4]
 lea rsi,[links]
 mov [rsi+r12*4],edx
 mov [rcx+rax*4],r12d
.move_next:
 add rbx,32
 inc r12d
 cmp r12d,[sim_count]
 jb .move
 xor r12d,r12d
 lea rbx,[sim_entities]
.attack:
 mov dword [rbx+24],-1
 cmp dword [rbx+8],0
 je .attack_next
 movss xmm4,[rbx]
 movss xmm5,[rbx+4]
 movaps xmm0,xmm4
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .ax
 mov eax,31
.ax: mov [rsp],eax
 movaps xmm0,xmm5
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .az
 mov eax,31
.az: mov [rsp+4],eax
 mov eax,[rbx+16]
 lea rcx,[range2]
 movss xmm6,[rcx+rax*4]
 mov r15d,-1
 mov r13d,-1
.zloop:
 mov eax,[rsp+4]
 add eax,r13d
 cmp eax,31
 ja .znext
 shl eax,5
 mov [rsp+8],eax
 mov r14d,-1
.xloop:
 mov eax,[rsp]
 add eax,r14d
 cmp eax,31
 ja .xnext
 add eax,[rsp+8]
 lea rcx,[heads]
 mov ebp,[rcx+rax*4]
 mov edi,24
.candidate:
 cmp ebp,-1
 je .xnext
 mov eax,ebp
 shl rax,5
 lea rdx,[sim_entities]
 add rdx,rax
 mov eax,[rdx+12]
 cmp eax,[rbx+12]
 je .chain
 movss xmm0,[rdx]
 subss xmm0,xmm4
 mulss xmm0,xmm0
 movss xmm1,[rdx+4]
 subss xmm1,xmm5
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,xmm6
 ja .chain
 movaps xmm6,xmm0
 mov r15d,ebp
.chain:
 lea rcx,[links]
 mov ebp,[rcx+rbp*4]
 dec edi
 jnz .candidate
.xnext:
 inc r14d
 cmp r14d,1
 jle .xloop
.znext:
 inc r13d
 cmp r13d,1
 jle .zloop
 cmp r15d,-1
 je .attack_next
 mov [rbx+24],r15d
 inc dword [sim_engaged]
 ; Fire every 8 ticks with staggered phases, avoiding one giant damage spike.
 mov eax,[sim_tick_count]
 add eax,r12d
 test eax,7
 jnz .attack_next
 mov eax,[rbx+16]
 lea rcx,[power]
 mov eax,[rcx+rax*4]
 lea rcx,[damage]
 add [rcx+r15*4],eax
.attack_next:
 add rbx,32
 inc r12d
 cmp r12d,[sim_count]
 jb .attack
 xor r12d,r12d
 lea rbx,[sim_entities]
.apply:
 cmp dword [rbx+8],0
 je .apply_next
 lea rcx,[damage]
 mov eax,[rcx+r12*4]
 cmp [rbx+8],eax
 ja .survive
 mov dword [rbx+8],0
 mov eax,[rbx+12]
 lea rcx,[sim_alive]
 dec dword [rcx+rax*4]
 jmp .apply_next
.survive:
 sub [rbx+8],eax
.apply_next:
 add rbx,32
 inc r12d
 cmp r12d,[sim_count]
 jb .apply
 add rsp,32
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
.uninitialized:
 ret
; FNV-1a over full active entity records, tick and front orders.
sim_checksum:
 mov rax,14695981039346656037
 mov r8,1099511628211
 lea rsi,[sim_entities]
 mov ecx,[sim_count]
 shl ecx,5
 test ecx,ecx
 jz .tick_hash
.bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .bytes
.tick_hash:
 mov edx,[sim_tick_count]
 xor rax,rdx
 imul rax,r8
 lea rsi,[orders]
 mov ecx,6
.orders:
 mov edx,[rsi]
 xor rax,rdx
 imul rax,r8
 add rsi,4
 loop .orders
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
section .text
global sim_fire
; Local solo prototype only: caller validates its aim; no network trust boundary.
sim_fire:
 cmp edi,[sim_count]
 jae .bad
 test esi,esi
 jz .bad
 cmp esi,100
 ja .bad
 mov eax,edi
 shl rax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+12],1
 jne .bad
 cmp dword [rdx+8],0
 je .bad
 cmp [rdx+8],esi
 ja .hit
 mov dword [rdx+8],0
 dec dword [sim_alive+4]
 xor eax,eax
 ret
.hit: sub [rdx+8],esi
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
