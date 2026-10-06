; Bounded squad visibility corridors followed by existing local swept steering.
%include "schemas/entity.inc"
%include "schemas/terrain_relief.inc"
default rel
%define SQUAD_SLOTS 12288
%define SLOTS (SQUAD_SLOTS+2048)
%define STRIDE 256
%define QCAP 512
%define NODES 27
extern sim_count,sim_entities,sim_tick_count,ai_fronts
extern terrain_obstacles,terrain_obstacle_count,terrain_body_path_clear,terrain_height,world_los
extern terrain_relief_fields
extern wreck_nav_init,wreck_nav_tick,wreck_nav_goal,wreck_nav_hash
section .bss align=64
global nav_metrics
; pending, completed, overflow, cache_hits, stuck_replans, cover_choices,
; last_tick_requests, max_tick_requests
nav_metrics: resd 8
head: resd 1
tail: resd 1
queue: resd QCAP
; state0 invalid/1queued/2ready, count, goalXZ, startXZ, path reversed goal->start
cache: resb SLOTS*STRIDE
; Last actual position, nonprogress ticks, packed shelter expiry/face per actor.
progress: resb ENTITY_CAPACITY*16
nodes: resq NODES
distance: resd NODES
previous: resd NODES
visited: resd NODES
section .rodata
zero: dd 0.0
one: dd 1.0
route_margin: dd 6.0
margin: dd 4.0
infinity: dd 1.0e30
changed2: dd 4096.0
progress2: dd 0.0001
cover_range2: dd 1600.0
eye: dd 2.0
section .text
global nav_init,nav_tick,nav_entity_goal,nav_hash
nav_init:
 lea rdi,[nav_metrics]
 xor eax,eax
 mov ecx,(8*4+8+QCAP*4+SLOTS*STRIDE+ENTITY_CAPACITY*16+NODES*20)/4
 rep stosd
 jmp wreck_nav_init
; Internal RBP entry. Enqueue only once; saturated queue retains local steering.
enqueue:
 cmp dword [rbp],1
 je .done
 cmp dword [nav_metrics],QCAP
 jae .full
 mov eax,[tail]
 lea rdx,[queue]
 mov rcx,rbp
 lea rsi,[cache]
 sub rcx,rsi
 shr rcx,8
 mov [rdx+rax*4],ecx
 inc eax
 and eax,QCAP-1
 mov [tail],eax
 inc dword [nav_metrics]
 mov dword [rbp],1
 ret
.full:
 inc dword [nav_metrics+8]
 mov dword [rbp],0
.done: ret
nav_tick:
 push rbp
 push r12
 sub rsp,8
 call wreck_nav_tick
 xor r12d,r12d
 mov dword [nav_metrics+24],0
.next:
 cmp dword [nav_metrics],0
 je .out
 cmp r12d,8
 jae .out
 mov eax,[head]
 lea rdx,[queue]
 mov eax,[rdx+rax*4]
 shl eax,8
 lea rbp,[cache]
 add rbp,rax
 mov eax,[head]
 inc eax
 and eax,QCAP-1
 mov [head],eax
 dec dword [nav_metrics]
 call build_route
 inc dword [nav_metrics+4]
 inc r12d
 jmp .next
.out:
 mov [nav_metrics+24],r12d
 cmp r12d,[nav_metrics+28]
 jbe .return
 mov [nav_metrics+28],r12d
.return:
 add rsp,8
 pop r12
 pop rbp
 ret
; Dijkstra over start, goal and four padded corners per physical static box.
; At most27 nodes: start/goal,20 box corners,5 canonical hill bypasses.
; Shared graph stays artillery-conservative; live queries retain actual roles.
build_route:
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,16
 mov dword [rbp+4],0
 cmp dword [terrain_obstacle_count],5
 ja .fail
 lea rbx,[nodes]
 mov rax,[rbp+16]
 mov [rbx],rax
 mov rax,[rbp+8]
 mov [rbx+8],rax
 lea rsi,[terrain_obstacles]
 mov r12d,2
 xor r13d,r13d
.corners:
 cmp r13d,[terrain_obstacle_count]
 jae .relief_nodes
 movss xmm0,[rsi]
 subss xmm0,[route_margin]
 movss xmm1,[rsi+4]
 subss xmm1,[route_margin]
 movss [rbx+r12*8],xmm0
 movss [rbx+r12*8+4],xmm1
 inc r12d
 movss xmm0,[rsi+8]
 addss xmm0,[route_margin]
 movss [rbx+r12*8],xmm0
 movss [rbx+r12*8+4],xmm1
 inc r12d
 movss xmm1,[rsi+12]
 addss xmm1,[route_margin]
 movss [rbx+r12*8],xmm0
 movss [rbx+r12*8+4],xmm1
 inc r12d
 movss xmm0,[rsi]
 subss xmm0,[route_margin]
 movss [rbx+r12*8],xmm0
 movss [rbx+r12*8+4],xmm1
 inc r12d
 add rsi,32
 inc r13d
 jmp .corners
.relief_nodes:
 lea rsi,[terrain_relief_fields]
 test dword [rsi+RELIEF_FLAGS],RELIEF_ACTIVE
 jz .init
 ; Retain the original graph outside the start/goal rectangle near relief.
 movss xmm0,[rbx]
 maxss xmm0,[rbx+8]
 addss xmm0,[route_margin]
 ucomiss xmm0,[rsi+RELIEF_X0]
 jb .init
 movss xmm0,[rbx]
 minss xmm0,[rbx+8]
 subss xmm0,[route_margin]
 ucomiss xmm0,[rsi+RELIEF_X3]
 ja .init
 movss xmm0,[rbx+4]
 maxss xmm0,[rbx+12]
 addss xmm0,[route_margin]
 ucomiss xmm0,[rsi+RELIEF_Z0]
 jb .init
 movss xmm0,[rbx+4]
 minss xmm0,[rbx+12]
 subss xmm0,[route_margin]
 ucomiss xmm0,[rsi+RELIEF_Z3]
 ja .init
 movss xmm0,[rsi+RELIEF_X0]
 subss xmm0,[route_margin]
 movss xmm1,[rsi+RELIEF_Z0]
 subss xmm1,[route_margin]
 movss [rbx+r12*8],xmm0
 movss [rbx+r12*8+4],xmm1
 inc r12d
 movss xmm0,[rsi+RELIEF_X3]
 addss xmm0,[route_margin]
 movss [rbx+r12*8],xmm0
 movss [rbx+r12*8+4],xmm1
 inc r12d
 movss xmm1,[rsi+RELIEF_Z3]
 addss xmm1,[route_margin]
 movss [rbx+r12*8],xmm0
 movss [rbx+r12*8+4],xmm1
 inc r12d
 movss xmm2,[rsi+RELIEF_X0]
 subss xmm2,[route_margin]
 movss [rbx+r12*8],xmm2
 movss [rbx+r12*8+4],xmm1
 inc r12d
 ; Explicit east gentle entrance prevents conservative diagonal boxes forcing
 ; a needless second circuit around the hill to reach the plateau.
 movss xmm1,[rsi+RELIEF_Z1]
 addss xmm1,[rsi+RELIEF_Z2]
 mulss xmm1,[half]
 movss [rbx+r12*8],xmm0
 movss [rbx+r12*8+4],xmm1
 inc r12d
.init:
 mov [rsp],r12d
 lea rdi,[distance]
 lea rsi,[previous]
 lea rdx,[visited]
 xor eax,eax
.init_loop:
 mov ecx,[infinity]
 mov [rdi+rax*4],ecx
 mov dword [rsi+rax*4],-1
 mov dword [rdx+rax*4],0
 inc eax
 cmp eax,r12d
 jb .init_loop
 mov dword [distance],0
.search:
 movss xmm0,[infinity]
 mov r13d,-1
 xor eax,eax
 lea rsi,[visited]
 lea rdi,[distance]
.minimum:
 cmp dword [rsi+rax*4],0
 jne .minimum_next
 comiss xmm0,[rdi+rax*4]
 jbe .minimum_next
 movss xmm0,[rdi+rax*4]
 mov r13d,eax
.minimum_next:
 inc eax
 cmp eax,[rsp]
 jb .minimum
 cmp r13d,-1
 je .fail
 cmp r13d,1
 je .reconstruct
 mov dword [rsi+r13*4],1
 xor r14d,r14d
.edges:
 lea rsi,[visited]
 cmp dword [rsi+r14*4],0
 jne .edge_next
 movss xmm0,[rbx+r13*8]
 movss xmm1,[rbx+r13*8+4]
 movss xmm2,[rbx+r14*8]
 movss xmm3,[rbx+r14*8+4]
 mov edi,2
 call terrain_body_path_clear
 test eax,eax
 jz .edge_next
 movss xmm0,[rbx+r13*8]
 subss xmm0,[rbx+r14*8]
 mulss xmm0,xmm0
 movss xmm1,[rbx+r13*8+4]
 subss xmm1,[rbx+r14*8+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 sqrtss xmm0,xmm0
 lea rsi,[distance]
 addss xmm0,[rsi+r13*4]
 comiss xmm0,[rsi+r14*4]
 jae .edge_next
 movss [rsi+r14*4],xmm0
 lea rsi,[previous]
 mov [rsi+r14*4],r13d
.edge_next:
 inc r14d
 cmp r14d,[rsp]
 jb .edges
 jmp .search
.reconstruct:
 mov eax,1
 xor ecx,ecx
 lea rsi,[previous]
.path:
 cmp ecx,NODES
 jae .fail
 mov rdx,[rbx+rax*8]
 mov [rbp+24+rcx*8],rdx
 inc ecx
 mov eax,[rsi+rax*4]
 test eax,eax
 jg .path
 cmp eax,0
 jne .fail
 mov [rbp+4],ecx
 mov dword [rbp],2
 jmp .done
.fail:
 mov dword [rbp],0
.done:
 add rsp,16
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
nav_entity_goal:
 cmp edi,[sim_count]
 jae .raw
 push rbx
 push rbp
 push r12
 push r13
 sub rsp,40
 mov r12d,edi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_KIND],3
 je .bypass
 mov eax,[rbx+ENTITY_SIDE]
 cmp eax,1
 ja .bypass
 imul eax,3
 add eax,[rbx+ENTITY_FRONT]
 cmp dword [rbx+ENTITY_FRONT],3
 jae .bypass
 mov [rsp+8],eax
 shl eax,11
 mov edx,r12d
 shr edx,4
 add eax,edx
 ; Designated scouts have direct goals while their support squad flanks.
 ; One scout per stable 16-ID group needs its own corridor, otherwise these
 ; two goals continually invalidate each other and saturate the FIFO.
 test r12d,15
 jnz .slot
 lea eax,[rdx+SQUAD_SLOTS]
.slot:
 shl eax,8
 lea rbp,[cache]
 add rbp,rax
 cmp dword [rbp],0
 je .request
 movss xmm0,[rsp]
 subss xmm0,[rbp+8]
 mulss xmm0,xmm0
 movss xmm1,[rsp+4]
 subss xmm1,[rbp+12]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[changed2]
 ja .request
 jmp .progress
.request:
 mov rax,[rsp]
 mov [rbp+8],rax
 mov rax,[rbx]
 mov [rbp+16],rax
 call enqueue
.progress:
 mov eax,r12d
 shl eax,4
 lea r13,[progress]
 add r13,rax
 movss xmm0,[rbx]
 subss xmm0,[r13]
 mulss xmm0,xmm0
 movss xmm1,[rbx+4]
 subss xmm1,[r13+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[progress2]
 ja .moving
 inc dword [r13+8]
 cmp dword [r13+8],240
 jb .route
 mov dword [r13+8],0
 movss xmm0,[rbx]
 subss xmm0,[rsp]
 mulss xmm0,xmm0
 movss xmm1,[rbx+4]
 subss xmm1,[rsp+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[one]
 jbe .route
 mov rax,[rbx]
 mov [rbp+16],rax
 call enqueue
 inc dword [nav_metrics+16]
 jmp .route
.moving:
 mov rax,[rbx]
 mov [r13],rax
 mov dword [r13+8],0
.route:
 movss xmm0,[rbx]
 movss xmm1,[rbx+4]
 movss xmm2,[rsp]
 movss xmm3,[rsp+4]
 mov edi,[rbx+ENTITY_KIND]
 call terrain_body_path_clear
 test eax,eax
 jnz .original
 cmp dword [rbp],2
 jne .original
 xor r13d,r13d
.corridor:
 cmp r13d,[rbp+4]
 jae .original
 movss xmm0,[rbx]
 movss xmm1,[rbx+4]
 movss xmm2,[rbp+24+r13*8]
 movss xmm3,[rbp+28+r13*8]
 mov edi,[rbx+ENTITY_KIND]
 call terrain_body_path_clear
 test eax,eax
 jnz .routed
 inc r13d
 jmp .corridor
.routed:
 inc dword [nav_metrics+12]
 movss xmm0,[rbp+24+r13*8]
 movss xmm1,[rbp+28+r13*8]
 jmp .cover
.original:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 jmp .cover
.bypass:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 jmp .return
.cover:
 movss [rsp+16],xmm0
 movss [rsp+20],xmm1
 call choose_cover
 mov edi,r12d
 call wreck_nav_goal
.return:
 add rsp,40
 pop r13
 pop r12
 pop rbp
 pop rbx
.raw: ret
; Short staggered shelter only for autonomous infantry with an acquired target.
; Physical candidates lie on the opposite X face from that observed target.
choose_cover:
 cmp dword [rbx+ENTITY_KIND],0
 jne .none
 mov eax,[rsp+8+8] ; caller frame + return address
 shl eax,6
 lea rdx,[ai_fronts]
 cmp dword [rdx+rax+24],0
 jne .cancel
 mov eax,r12d
 shl eax,4
 lea rdx,[progress]
 add rdx,rax
 mov eax,[rdx+12]
 test eax,eax
 jz .acquire
 mov ecx,eax
 shr ecx,4
 cmp [sim_tick_count],ecx
 jae .expired
 and eax,15
 dec eax
 mov ecx,eax
 shr eax,1
 shl eax,5
 lea rdx,[terrain_obstacles]
 add rdx,rax
 test ecx,1
 jnz .shelter_right
 movss xmm0,[rdx]
 subss xmm0,[margin]
 jmp .shelter_z
.shelter_right:
 movss xmm0,[rdx+8]
 addss xmm0,[margin]
.shelter_z:
 movss xmm1,[rdx+4]
 addss xmm1,[rdx+12]
 mulss xmm1,[half]
 ret
.expired:
 mov dword [rdx+12],0
.acquire:
 mov eax,[rbx+ENTITY_TARGET]
 cmp eax,[sim_count]
 jae .none
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .none
 mov eax,[rdx+ENTITY_SIDE]
 cmp eax,[rbx+ENTITY_SIDE]
 je .none
 mov eax,[sim_tick_count]
 mov ecx,r12d
 shr ecx,4
 imul ecx,31
 add eax,ecx
 xor edx,edx
 mov ecx,1080
 div ecx
 cmp edx,30
 jae .none
 ; Preserve parent's frame; select a reachable candidate with blocked physical LOS.
 push r14
 push r15
 sub rsp,40
 mov eax,[rbx+ENTITY_TARGET]
 shl eax,5
 lea r15,[sim_entities]
 add r15,rax
 lea r14,[terrain_obstacles]
 mov dword [rsp],0
.scan:
 movss xmm0,[r14]
 addss xmm0,[r14+8]
 addss xmm0,xmm0
 ; Half midpoint computed without extra constant.
 mulss xmm0,[quarter]
 comiss xmm0,[r15]
 jb .left
 movss xmm0,[r14+8]
 addss xmm0,[margin]
 mov dword [rsp+4],1
 jmp .point
.left:
 movss xmm0,[r14]
 subss xmm0,[margin]
 mov dword [rsp+4],0
.point:
 movss xmm1,[r14+4]
 addss xmm1,[r14+12]
 mulss xmm1,[half]
 movss [rsp+8],xmm0
 movss [rsp+12],xmm1
 movaps xmm2,xmm0
 subss xmm2,[rbx]
 mulss xmm2,xmm2
 movaps xmm3,xmm1
 subss xmm3,[rbx+4]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 comiss xmm2,[cover_range2]
 ja .next
 movss xmm0,[rbx]
 movss xmm1,[rbx+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 mov edi,[rbx+ENTITY_KIND]
 call terrain_body_path_clear
 test eax,eax
 jz .next
 movss xmm0,[rsp+8]
 movss xmm1,[rsp+12]
 call terrain_height
 addss xmm0,[eye]
 movss [rsp+16],xmm0
 movss xmm0,[r15]
 movss xmm1,[r15+4]
 call terrain_height
 addss xmm0,[eye]
 movaps xmm4,xmm0
 movss xmm0,[rsp+8]
 movss xmm1,[rsp+16]
 movss xmm2,[rsp+12]
 movss xmm3,[r15]
 movss xmm5,[r15+4]
 call world_los
 test eax,eax
 jnz .next
 movss xmm0,[rsp+8]
 movss xmm1,[rsp+12]
 inc dword [nav_metrics+20]
 mov eax,[sim_tick_count]
 add eax,360
 shl eax,4
 mov ecx,[rsp]
 add ecx,ecx
 add ecx,[rsp+4]
 inc ecx
 or eax,ecx
 mov ecx,r12d
 shl ecx,4
 lea rdx,[progress]
 mov [rdx+rcx+12],eax
 jmp .found
.next:
 add r14,32
 inc dword [rsp]
 mov eax,[rsp]
 cmp eax,[terrain_obstacle_count]
 jb .scan
 movss xmm0,[rsp+40+16+8+16]
 movss xmm1,[rsp+40+16+8+20]
.found:
 add rsp,40
 pop r15
 pop r14
 ret
.cancel:
 mov eax,r12d
 shl eax,4
 lea rdx,[progress]
 mov dword [rdx+rax+12],0
.none: ret
nav_hash:
 lea rsi,[nav_metrics]
 mov ecx,(8*4+8+QCAP*4+SLOTS*STRIDE+ENTITY_CAPACITY*16)/4
.loop:
 mov edx,[rsi]
 xor rax,rdx
 imul rax,r8
 add rsi,4
 dec ecx
 jnz .loop
 jmp wreck_nav_hash
section .rodata
half: dd 0.5
quarter: dd 0.25
section .note.GNU-stack noalloc noexec nowrite progbits
