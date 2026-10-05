; ABI v1. All routines preserve SysV nonvolatile registers. Fixed 30 Hz steps.
%include "schemas/entity.inc"
default rel
extern operation_init, operation_tick, operation_hash
extern terrain_move, terrain_height, terrain_los
extern ai_init, ai_tick, ai_entity_goal, ai_override, ai_hash
extern player_init, player_tick, player_hash
section .bss align=64
global sim_count, sim_tick_count, sim_alive, sim_engaged, sim_entities
sim_count: resd 1
sim_tick_count: resd 1
sim_alive: resd 2
sim_engaged: resd 1
sim_entities: resb ENTITY_CAPACITY*ENTITY_STRIDE
cell_counts: resd 1024
cell_samples: resd 1024*24
damage: resd ENTITY_CAPACITY
orders: resd 6
rng: resd 1
global sim_waypoints
sim_waypoints: resq 6
section .rodata
health: dd 100,400,160,200
speed: dd 0.12,0.5,0.2,5.0
default_goals: dd 5000.0,1300.0,5000.0,3900.0,5000.0,6500.0
               dd 3000.0,1300.0,3000.0,3900.0,3000.0,6500.0
range2: dd 57600.0,202500.0,422500.0,202500.0
power: dd 3,10,15,6
zero: dd 0.0
maximum: dd 8000.0
cell_scale: dd 0.004
eye_height: dd 2.0
air_height: dd 90.0
retreat_distance: dd 100.0
section .text
global sim_init, sim_tick, sim_checksum, sim_order
; Accept even counts 2..32768; invalid calls leave state unchanged.
sim_init:
 cmp edi,2
 jb .bad
 cmp edi,ENTITY_CAPACITY
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
 lea rsi,[default_goals]
 lea rdi,[sim_waypoints]
 mov ecx,6
 rep movsq
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
 movss [rbx+ENTITY_X],xmm0
 mov [rbx+ENTITY_SIDE],esi
 mov eax,r12d
 xor edx,edx
 mov ecx,3
 div ecx
 mov [rbx+ENTITY_FRONT],edx
 imul edx,2600
 add edx,700
 mov eax,[rng]
 shr eax,16
 and eax,1023
 add edx,eax
 cvtsi2ss xmm0,edx
 movss [rbx+ENTITY_Z],xmm0
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
 mov [rbx+ENTITY_KIND],edx
 lea rcx,[health]
 mov eax,[rcx+rdx*4]
 mov [rbx+ENTITY_HP],eax
 mov dword [rbx+ENTITY_TARGET],-1
 mov dword [rbx+ENTITY_GENERATION],1
 add rbx,ENTITY_STRIDE
 inc r12d
 cmp r12d,[sim_count]
 jb .loop
 sub rsp,8
 call operation_init
 call player_init
 call ai_init
 add rsp,8
 pop r12
 pop rbx
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
sim_order:
 mov r8d,edi
 mov r9d,esi
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
 mov edi,r8d
 mov esi,r9d
 sub rsp,8
 call ai_override
 add rsp,8
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
global sim_waypoint
; Set a host-owned goal; the caller separately selects advance/hold/retreat.
sim_waypoint:
 mov r8d,edi
 mov r9d,esi
 cmp edi,1
 ja .bad
 cmp esi,2
 ja .bad
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
 imul edi,3
 add edi,esi
 lea rax,[sim_waypoints]
 movss [rax+rdi*8],xmm0
 movss [rax+rdi*8+4],xmm1
 mov edi,r8d
 mov esi,r9d
 sub rsp,8
 call ai_override
 add rsp,8
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
 sub rsp,96
 inc dword [sim_tick_count]
 sub rsp,8
 call ai_tick
 add rsp,8
 mov dword [sim_engaged],0
 lea rdi,[cell_counts]
 xor eax,eax
 mov ecx,1024
 rep stosd
 lea rdi,[damage]
 xor eax,eax
 mov ecx,[sim_count]
 rep stosd
 xor r12d,r12d
 lea rbx,[sim_entities]
.move:
 cmp dword [rbx+ENTITY_HP],0
 je .move_next
 mov edi,r12d
 sub rsp,8
 call ai_entity_goal
 add rsp,8
 cmp eax,-1
 je .manual_move
 test eax,eax
 jnz .insert
 movss [rsp+64],xmm0
 movss [rsp+68],xmm1
 mov eax,[rbx+ENTITY_KIND]
 lea rcx,[speed]
 movss xmm4,[rcx+rax*4]
 movss xmm2,[rsp+64]
 movss xmm3,[rsp+68]
 jmp .terrain_step
.manual_move:
 mov eax,[rbx+ENTITY_KIND]
 lea rcx,[speed]
 movss xmm1,[rcx+rax*4]
 mov eax,[rbx+ENTITY_SIDE]
 imul eax,3
 add eax,[rbx+ENTITY_FRONT]
 mov edi,eax
 lea rcx,[orders]
 mov eax,[rcx+rax*4]
 cmp eax,1
 je .insert
 cmp eax,2
 je .retreat
 ; Advance holds a firing position while its last target is alive.
 mov edx,[rbx+ENTITY_TARGET]
 cmp edx,-1
 je .toward_goal
 mov ecx,edx
 imul rcx,ENTITY_STRIDE
 lea rsi,[sim_entities]
 cmp dword [rsi+rcx+ENTITY_HP],0
 jne .insert
.toward_goal:
 lea rsi,[sim_waypoints]
 movss xmm2,[rsi+rdi*8]
 movss xmm3,[rsi+rdi*8+4]
 movaps xmm4,xmm1
 jmp .terrain_step
.retreat:
 movss xmm2,[rbx+ENTITY_X]
 cmp dword [rbx+ENTITY_SIDE],0
 jne .retreat_right
 subss xmm2,[retreat_distance]
 jmp .retreat_z
.retreat_right:
 addss xmm2,[retreat_distance]
.retreat_z:
 movss xmm3,[rbx+ENTITY_Z]
 movaps xmm4,xmm1
.terrain_step:
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 mov edi,[rbx+ENTITY_KIND]
 sub rsp,8
 call terrain_move
 add rsp,8
 movss [rbx+ENTITY_X],xmm0
 movss [rbx+ENTITY_Z],xmm1
.insert:
 movss xmm0,[rbx+ENTITY_X]
 mulss xmm0,[cell_scale]
 cvttss2si eax,xmm0
 cmp eax,31
 jbe .xok
 mov eax,31
.xok:
 movss xmm0,[rbx+ENTITY_Z]
 mulss xmm0,[cell_scale]
 cvttss2si edx,xmm0
 cmp edx,31
 jbe .zok
 mov edx,31
.zok:
 shl edx,5
 add eax,edx
 ; Deterministic reservoir: each dense cell retains 24 distributed IDs.
 lea rcx,[cell_counts]
 inc dword [rcx+rax*4]
 mov edi,[rcx+rax*4]
 mov esi,eax
 dec edi
 cmp edi,24
 jb .sample_slot
 ; Hash tick and stable entity ID, then select a reservoir replacement.
 mov eax,[sim_tick_count]
 imul eax,0x9e3779b9
 add eax,r12d
 mov edx,eax
 shr edx,16
 xor eax,edx
 imul eax,0x7feb352d
 mov edx,eax
 shr edx,15
 xor eax,edx
 imul eax,0x846ca68b
 mov edx,eax
 shr edx,16
 xor eax,edx
 lea ecx,[rdi+1]
 xor edx,edx
 div ecx
 mov edi,edx
 cmp edi,24
 jae .move_next
.sample_slot:
 imul esi,24
 add esi,edi
 lea rcx,[cell_samples]
 mov [rcx+rsi*4],r12d
.move_next:
 add rbx,ENTITY_STRIDE
 inc r12d
 cmp r12d,[sim_count]
 jb .move
 xor r12d,r12d
 lea rbx,[sim_entities]
.attack:
 mov dword [rbx+ENTITY_TARGET],-1
 cmp dword [rbx+ENTITY_HP],0
 je .attack_next
 movss xmm4,[rbx+ENTITY_X]
 movss xmm5,[rbx+ENTITY_Z]
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
 mov eax,[rbx+ENTITY_KIND]
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
 lea rcx,[cell_counts]
 mov edi,[rcx+rax*4]
 test edi,edi
 jz .xnext
 cmp edi,24
 jbe .sample_count
 mov edi,24
.sample_count:
 imul eax,24
 mov [rsp+12],eax
 mov dword [rsp+16],0
.candidate:
 mov eax,[rsp+12]
 add eax,[rsp+16]
 lea rcx,[cell_samples]
 mov ebp,[rcx+rax*4]
 mov eax,ebp
 imul rax,ENTITY_STRIDE
 lea rdx,[sim_entities]
 add rdx,rax
 mov eax,[rdx+ENTITY_SIDE]
 cmp eax,[rbx+ENTITY_SIDE]
 je .chain
 movss xmm0,[rdx+ENTITY_X]
 subss xmm0,xmm4
 mulss xmm0,xmm0
 movss xmm1,[rdx+ENTITY_Z]
 subss xmm1,xmm5
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,xmm6
 ja .chain
 ; Only physically visible candidates can become authoritative targets.
 movss [rsp+32],xmm4
 movss [rsp+36],xmm5
 movss [rsp+40],xmm6
 movss [rsp+44],xmm0
 mov [rsp+48],edi
 movaps xmm0,xmm4
 movaps xmm1,xmm5
 sub rsp,8
 call terrain_height
 add rsp,8
 addss xmm0,[eye_height]
 cmp dword [rbx+ENTITY_KIND],3
 jne .own_ground
 addss xmm0,[air_height]
.own_ground:
 movss [rsp+52],xmm0
 mov eax,ebp
 imul rax,ENTITY_STRIDE
 lea rdx,[sim_entities]
 add rdx,rax
 movss xmm0,[rdx+ENTITY_X]
 movss xmm1,[rdx+ENTITY_Z]
 sub rsp,8
 call terrain_height
 add rsp,8
 addss xmm0,[eye_height]
 mov eax,ebp
 imul rax,ENTITY_STRIDE
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_KIND],3
 jne .target_ground
 addss xmm0,[air_height]
.target_ground:
 movaps xmm4,xmm0
 movss xmm0,[rsp+32]
 movss xmm1,[rsp+52]
 movss xmm2,[rsp+36]
 movss xmm3,[rdx+ENTITY_X]
 movss xmm5,[rdx+ENTITY_Z]
 sub rsp,8
 call terrain_los
 add rsp,8
 movss xmm4,[rsp+32]
 movss xmm5,[rsp+36]
 movss xmm6,[rsp+40]
 mov edi,[rsp+48]
 test eax,eax
 jz .chain
 movss xmm6,[rsp+44]
 mov r15d,ebp
.chain:
 inc dword [rsp+16]
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
 mov [rbx+ENTITY_TARGET],r15d
 inc dword [sim_engaged]
 ; Fire every 8 ticks with staggered phases, avoiding one giant damage spike.
 mov eax,[sim_tick_count]
 add eax,r12d
 test eax,7
 jnz .attack_next
 mov eax,[rbx+ENTITY_KIND]
 lea rcx,[power]
 mov eax,[rcx+rax*4]
 lea rcx,[damage]
 add [rcx+r15*4],eax
.attack_next:
 add rbx,ENTITY_STRIDE
 inc r12d
 cmp r12d,[sim_count]
 jb .attack
 xor r12d,r12d
 lea rbx,[sim_entities]
.apply:
 cmp dword [rbx+ENTITY_HP],0
 je .apply_next
 lea rcx,[damage]
 mov eax,[rcx+r12*4]
 cmp [rbx+ENTITY_HP],eax
 ja .survive
 mov dword [rbx+ENTITY_HP],0
 mov eax,[rbx+ENTITY_SIDE]
 lea rcx,[sim_alive]
 dec dword [rcx+rax*4]
 jmp .apply_next
.survive:
 sub [rbx+ENTITY_HP],eax
.apply_next:
 add rbx,ENTITY_STRIDE
 inc r12d
 cmp r12d,[sim_count]
 jb .apply
 sub rsp,8
 call operation_tick
 call player_tick
 add rsp,8
 add rsp,96
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
 imul ecx,ENTITY_STRIDE
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
 lea rsi,[sim_waypoints]
 mov ecx,48
.goals:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .goals
 sub rsp,8
 call ai_hash
 add rsp,8
 sub rsp,8
 call operation_hash
 add rsp,8
 jmp player_hash
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
 imul rax,ENTITY_STRIDE
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_SIDE],1
 jne .bad
 cmp dword [rdx+ENTITY_HP],0
 je .bad
 cmp [rdx+ENTITY_HP],esi
 ja .hit
 mov dword [rdx+ENTITY_HP],0
 dec dword [sim_alive+4]
 xor eax,eax
 ret
.hit: sub [rdx+ENTITY_HP],esi
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
