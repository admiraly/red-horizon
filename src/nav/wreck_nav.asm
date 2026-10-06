; Local dynamic-cover routes. All actual displacement remains independently swept.
%include "schemas/entity.inc"
%include "schemas/terrain_body.inc"
%include "schemas/wreck.inc"
%include "schemas/wreck_nav.inc"
default rel
%define STRIDE 256
%define NODES WRECK_NAV_MAX_NODES
extern sim_entities,sim_count,sim_wrecks,sim_wreck_count
extern wreck_body_query,wreck_query_bounds,world_body_path_clear,world_body_blocked
extern terrain_obstacles,terrain_obstacle_count
section .bss align=64
global wreck_nav_metrics
; pending, completed, queue overflow, cache proposals, graph failures,
; local-cover overflow, builds last tick, maximum builds per tick.
wreck_nav_metrics: resd 8
head: resd 1
tail: resd 1
queue: resd WRECK_NAV_QUEUE
; state0 empty/1queued/2ready; generation,role,path count, ultimate goal,
; request start, then reverse path(goal first). One stable commitment per actor.
cache: resb ENTITY_CAPACITY*STRIDE
; Build scratch is neither persistent policy nor authoritative identity.
nodes: resq NODES
distance: resd NODES
previous: resd NODES
visited: resd NODES
node_count: resd 1
section .rodata
zero: dd 0.0
one: dd WRECK_NAV_CORNER_MARGIN
mapmax: dd 8000.0
look: dd WRECK_NAV_LOOKAHEAD
plan: dd WRECK_NAV_PLAN_DISTANCE
endpoint_step: dd WRECK_NAV_ENDPOINT_INCREMENT
endpoint_max: dd WRECK_NAV_ENDPOINT_MAX_DISTANCE
window: dd WRECK_NAV_WINDOW_MARGIN
look2: dd WRECK_NAV_LOOKAHEAD_SQUARED
plan2: dd WRECK_NAV_PLAN_DISTANCE_SQUARED
leg2: dd WRECK_NAV_MAX_LEG_SQUARED
changed2: dd WRECK_NAV_GOAL_CHANGE_SQUARED
reached2: dd WRECK_NAV_REACHED_SQUARED
infinity: dd 1.0e30
radii: dd BODY_INF_SWEEP_RADIUS,BODY_TANK_SWEEP_RADIUS,BODY_ARTY_SWEEP_RADIUS
section .text
global wreck_nav_init,wreck_nav_tick,wreck_nav_goal,wreck_nav_hash
wreck_nav_init:
 lea rdi,[wreck_nav_metrics]
 xor eax,eax
 mov ecx,(8*4+8+WRECK_NAV_QUEUE*4+ENTITY_CAPACITY*STRIDE)/4
 rep stosd
 ret
; RBP commitment pointer. Updating a pending request never duplicates its FIFO ID.
enqueue:
 cmp dword [rbp],1
 je .done
 cmp dword [wreck_nav_metrics],WRECK_NAV_QUEUE
 jae .full
 mov eax,[tail]
 lea rdx,[queue]
 mov rcx,rbp
 lea rsi,[cache]
 sub rcx,rsi
 shr rcx,8
 mov [rdx+rax*4],ecx
 inc eax
 and eax,WRECK_NAV_QUEUE-1
 mov [tail],eax
 inc dword [wreck_nav_metrics]
 mov dword [rbp],1
 ret
.full:
 inc dword [wreck_nav_metrics+8]
 mov dword [rbp],0
.done:
 ret
wreck_nav_tick:
 push rbp
 push r12
 sub rsp,8
 xor r12d,r12d
 mov dword [wreck_nav_metrics+24],0
.next:
 cmp dword [wreck_nav_metrics],0
 je .out
 cmp r12d,WRECK_NAV_BUILDS_PER_TICK
 jae .out
 mov eax,[head]
 lea rdx,[queue]
 mov edi,[rdx+rax*4]
 inc eax
 and eax,WRECK_NAV_QUEUE-1
 mov [head],eax
 dec dword [wreck_nav_metrics]
 mov eax,edi
 shl eax,8
 lea rbp,[cache]
 add rbp,rax
 call build
 inc dword [wreck_nav_metrics+4]
 inc r12d
 jmp .next
.out:
 mov [wreck_nav_metrics+24],r12d
 cmp r12d,[wreck_nav_metrics+28]
 jbe .return
 mov [wreck_nav_metrics+28],r12d
.return:
 add rsp,8
 pop r12
 pop rbp
 ret
wreck_nav_goal:
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .raw
 cmp edi,ENTITY_CAPACITY
 jae .raw
 ucomiss xmm0,[zero]
 jp .raw
 jb .raw
 ucomiss xmm0,[mapmax]
 ja .raw
 ucomiss xmm1,[zero]
 jp .raw
 jb .raw
 ucomiss xmm1,[mapmax]
 ja .raw
 cmp edi,[sim_count]
 jae .raw
 push rbx
 push rbp
 push r12
 push r13
 sub rsp,88
 mov r12d,edi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .original
 cmp dword [rbx+ENTITY_GENERATION],0
 je .original
 movss xmm2,[rbx]
 ucomiss xmm2,[zero]
 jp .original
 jb .original
 ucomiss xmm2,[mapmax]
 ja .original
 movss xmm2,[rbx+4]
 ucomiss xmm2,[zero]
 jp .original
 jb .original
 ucomiss xmm2,[mapmax]
 ja .original
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,2
 ja .original
 mov eax,r12d
 shl eax,8
 lea rbp,[cache]
 add rbp,rax
 cmp dword [sim_wreck_count],0
 je .cancel
 mov eax,[rbx+ENTITY_GENERATION]
 cmp eax,[rbp+4]
 jne .new_key
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,[rbp+8]
 jne .new_key
 movss xmm0,[rsp]
 subss xmm0,[rbp+16]
 movss xmm1,[rsp+4]
 subss xmm1,[rbp+20]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[changed2]
 ja .new_key
 cmp dword [rbp],2
 jne .probe
 ; Completed local segment releases its commitment; it cannot become a new stop.
 movss xmm0,[rbx]
 subss xmm0,[rbp+32]
 movss xmm1,[rbx+4]
 subss xmm1,[rbp+36]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[reached2]
 jbe .finished
 xor r13d,r13d
.path:
 cmp r13d,[rbp+12]
 jae .request
 movss xmm0,[rbp+32+r13*8]
 subss xmm0,[rbx]
 movss xmm1,[rbp+36+r13*8]
 subss xmm1,[rbx+4]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[reached2]
 jbe .request
 ucomiss xmm0,[leg2]
 ja .next_path
 movss xmm0,[rbx]
 movss xmm1,[rbx+4]
 movss xmm2,[rbp+32+r13*8]
 movss xmm3,[rbp+36+r13*8]
 mov edi,[rbx+ENTITY_KIND]
 call world_body_path_clear
 cmp eax,1
 je .routed
.next_path:
 inc r13d
 jmp .path
.routed:
 inc dword [wreck_nav_metrics+12]
 movss xmm0,[rbp+32+r13*8]
 movss xmm1,[rbp+36+r13*8]
 jmp .out
.new_key:
 ; Preserve pending FIFO identity across a goal/generation replacement.
 cmp dword [rbp],1
 je .request
 mov dword [rbp],0
 jmp .probe
.finished:
 mov dword [rbp],0
.probe:
 movss xmm0,[rsp]
 subss xmm0,[rbx]
 movss xmm1,[rsp+4]
 subss xmm1,[rbx+4]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 mulss xmm2,xmm2
 mulss xmm3,xmm3
 addss xmm2,xmm3
 ucomiss xmm2,[reached2]
 jbe .original
 ucomiss xmm2,[look2]
 jbe .probe_end
 sqrtss xmm2,xmm2
 movss xmm3,[look]
 divss xmm3,xmm2
 mulss xmm0,xmm3
 mulss xmm1,xmm3
.probe_end:
 addss xmm0,[rbx]
 addss xmm1,[rbx+4]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 movss xmm0,[rbx]
 movss xmm1,[rbx+4]
 mov eax,[rbx+ENTITY_KIND]
 lea rdx,[radii]
 movss xmm4,[rdx+rax*4]
 lea rdi,[rsp+64]
 mov esi,24
 call wreck_body_query
 cmp eax,1
 jne .original
.request:
 mov eax,[rbx+ENTITY_GENERATION]
 mov [rbp+4],eax
 mov eax,[rbx+ENTITY_KIND]
 mov [rbp+8],eax
 mov rax,[rsp]
 mov [rbp+16],rax
 mov rax,[rbx]
 mov [rbp+24],rax
 call enqueue
 jmp .original
.cancel:
 ; A pending queue ID must remain marked until popped, even after last expiry.
 cmp dword [rbp],1
 je .original
 mov dword [rbp],0
.original:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
.out:
 add rsp,88
 pop r13
 pop r12
 pop rbp
 pop rbx
.raw:
 ret
; EDI queued actor, RBP commitment. At most8 relevant wrecks +5 authored solids.
; Source is validated once before reading its cached bounds. All edges then use
; original-role terrain/grade/body/cover checks within a finite local window.
build:
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,64
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .fail
 cmp edi,ENTITY_CAPACITY
 jae .fail
 cmp edi,[sim_count]
 jae .fail
 mov eax,edi
 shl eax,5
 lea rbx,[sim_entities]
 add rbx,rax
 cmp dword [rbx+ENTITY_HP],0
 je .fail
 mov eax,[rbx+ENTITY_GENERATION]
 cmp eax,[rbp+4]
 jne .fail
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,[rbp+8]
 jne .fail
 cmp eax,2
 ja .fail
 lea rdx,[radii]
 movss xmm0,[rdx+rax*4]
 addss xmm0,[one]
 movss [rsp+32],xmm0
 lea r15,[nodes]
 mov rax,[rbp+24]
 mov [r15],rax
 mov dword [rsp+36],0
 movss xmm0,[rbp+16]
 subss xmm0,[rbp+24]
 movss xmm1,[rbp+20]
 subss xmm1,[rbp+28]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 mulss xmm2,xmm2
 mulss xmm3,xmm3
 addss xmm2,xmm3
 ucomiss xmm2,[plan2]
 jbe .plan_end
 sqrtss xmm2,xmm2
 movss [rsp+16],xmm2
 divss xmm0,xmm2
 divss xmm1,xmm2
 movss [rsp+20],xmm0
 movss [rsp+24],xmm1
 mov dword [rsp+36],1
 movss xmm3,[plan]
 movss [rsp+28],xmm3
 mulss xmm0,xmm3
 mulss xmm1,xmm3
.plan_end:
 addss xmm0,[rbp+24]
 addss xmm1,[rbp+28]
 movss [r15+8],xmm0
 movss [r15+12],xmm1
.endpoint:
 ; A clipped local goal may lie inside later cover. Extend along the chosen
 ; corridor in bounded increments, never beyond its actual ultimate endpoint.
 mov edi,[rbp+8]
 call world_body_blocked
 test eax,eax
 jz .endpoint_clear
 cmp dword [rsp+36],0
 je .fail
 movss xmm3,[rsp+28]
 ucomiss xmm3,[rsp+16]
 jae .fail
 addss xmm3,[endpoint_step]
 minss xmm3,[rsp+16]
 ucomiss xmm3,[endpoint_max]
 ja .fail
 movss [rsp+28],xmm3
 movss xmm0,[rsp+20]
 movss xmm1,[rsp+24]
 mulss xmm0,xmm3
 mulss xmm1,xmm3
 addss xmm0,[rbp+24]
 addss xmm1,[rbp+28]
 movss [r15+8],xmm0
 movss [r15+12],xmm1
 jmp .endpoint
.endpoint_clear:
 movss xmm0,[r15+8]
 movss xmm1,[r15+12]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 movss xmm0,[r15]
 movss xmm1,[r15+4]
 mov eax,[rbp+8]
 lea rdx,[radii]
 movss xmm4,[rdx+rax*4]
 lea rdi,[rsp+40]
 mov esi,24
 call wreck_body_query
 test eax,eax
 js .fail
 ; Axis-aligned local window includes tangent corners and neighboring cover.
 movss xmm0,[r15]
 minss xmm0,[r15+8]
 subss xmm0,[window]
 movss [rsp],xmm0
 movss xmm0,[r15+4]
 minss xmm0,[r15+12]
 subss xmm0,[window]
 movss [rsp+4],xmm0
 movss xmm0,[r15]
 maxss xmm0,[r15+8]
 addss xmm0,[window]
 movss [rsp+8],xmm0
 movss xmm0,[r15+4]
 maxss xmm0,[r15+12]
 addss xmm0,[window]
 movss [rsp+12],xmm0
 mov dword [node_count],2
 xor r12d,r12d
 xor r13d,r13d
.wreck:
 mov eax,r12d
 shl eax,6
 lea rdx,[sim_wrecks]
 test dword [rdx+rax+WRECK_FLAGS],WRECK_ACTIVE
 jz .next_wreck
 imul eax,r12d,24
 lea rdx,[wreck_query_bounds]
 add rdx,rax
 movss xmm0,[rdx]
 movss xmm1,[rdx+8]
 movss xmm2,[rdx+12]
 movss xmm3,[rdx+20]
 call relevant
 test eax,eax
 jz .next_wreck
 cmp r13d,WRECK_NAV_MAX_WRECKS
 jae .cover_full
 inc r13d
 call corners
.next_wreck:
 inc r12d
 cmp r12d,WRECK_CAPACITY
 jb .wreck
 cmp dword [terrain_obstacle_count],5
 ja .fail
 xor r12d,r12d
.solid:
 cmp r12d,[terrain_obstacle_count]
 jae .graph
 mov eax,r12d
 shl eax,5
 lea rdx,[terrain_obstacles]
 add rdx,rax
 movss xmm0,[rdx]
 movss xmm1,[rdx+4]
 movss xmm2,[rdx+8]
 movss xmm3,[rdx+12]
 call relevant
 test eax,eax
 jz .next_solid
 call corners
.next_solid:
 inc r12d
 jmp .solid
.graph:
 lea rdi,[distance]
 mov eax,[infinity]
 mov ecx,NODES
 rep stosd
 lea rdi,[visited]
 xor eax,eax
 mov ecx,NODES
 rep stosd
 lea rdi,[previous]
 mov eax,-1
 mov ecx,NODES
 rep stosd
 mov dword [distance],0
.select:
 movss xmm0,[infinity]
 mov r12d,-1
 xor ecx,ecx
 lea rdx,[distance]
 lea rsi,[visited]
.minimum:
 cmp ecx,[node_count]
 jae .selected
 cmp dword [rsi+rcx*4],0
 jne .minimum_next
 ucomiss xmm0,[rdx+rcx*4]
 jbe .minimum_next
 movss xmm0,[rdx+rcx*4]
 mov r12d,ecx
.minimum_next:
 inc ecx
 jmp .minimum
.selected:
 cmp r12d,-1
 je .fail
 cmp r12d,1
 je .path
 lea rdx,[visited]
 mov dword [rdx+r12*4],1
 xor r13d,r13d
.edge:
 cmp r13d,[node_count]
 jae .select
 lea rdx,[visited]
 cmp dword [rdx+r13*4],0
 jne .edge_next
 movss xmm0,[r15+r12*8]
 movss xmm1,[r15+r12*8+4]
 movss xmm2,[r15+r13*8]
 movss xmm3,[r15+r13*8+4]
 mov edi,[rbp+8]
 call world_body_path_clear
 cmp eax,1
 jne .edge_next
 movss xmm0,[r15+r12*8]
 subss xmm0,[r15+r13*8]
 movss xmm1,[r15+r12*8+4]
 subss xmm1,[r15+r13*8+4]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 addss xmm0,xmm1
 sqrtss xmm0,xmm0
 lea rdx,[distance]
 addss xmm0,[rdx+r12*4]
 ucomiss xmm0,[rdx+r13*4]
 jae .edge_next
 movss [rdx+r13*4],xmm0
 lea rdx,[previous]
 mov [rdx+r13*4],r12d
.edge_next:
 inc r13d
 jmp .edge
.path:
 mov eax,1
 xor ecx,ecx
 lea rdx,[previous]
.path_node:
 cmp ecx,WRECK_NAV_MAX_PATH
 jae .fail
 mov rsi,[r15+rax*8]
 mov [rbp+32+rcx*8],rsi
 inc ecx
 mov eax,[rdx+rax*4]
 test eax,eax
 jg .path_node
 cmp eax,0
 jne .fail
 mov [rbp+12],ecx
 mov dword [rbp],2
 jmp .done
.cover_full:
 inc dword [wreck_nav_metrics+20]
.fail:
 mov dword [rbp],0
 mov dword [rbp+12],0
 inc dword [wreck_nav_metrics+16]
.done:
 add rsp,64
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
; Internal helpers called with return address: parent's scratch offsets +8.
relevant:
 ucomiss xmm0,[rsp+16]
 ja .no
 ucomiss xmm1,[rsp+20]
 ja .no
 ucomiss xmm2,[rsp+8]
 jb .no
 ucomiss xmm3,[rsp+12]
 jb .no
 mov eax,1
 ret
.no:
 xor eax,eax
 ret
corners:
 subss xmm0,[rsp+40]
 subss xmm1,[rsp+40]
 addss xmm2,[rsp+40]
 addss xmm3,[rsp+40]
 mov eax,[node_count]
 movss [r15+rax*8],xmm0
 movss [r15+rax*8+4],xmm1
 inc eax
 movss [r15+rax*8],xmm2
 movss [r15+rax*8+4],xmm1
 inc eax
 movss [r15+rax*8],xmm2
 movss [r15+rax*8+4],xmm3
 inc eax
 movss [r15+rax*8],xmm0
 movss [r15+rax*8+4],xmm3
 inc eax
 mov [node_count],eax
 ret
wreck_nav_hash:
 lea rsi,[wreck_nav_metrics]
 mov ecx,(8*4+8+WRECK_NAV_QUEUE*4+ENTITY_CAPACITY*STRIDE)/4
.loop:
 mov edx,[rsi]
 xor rax,rdx
 imul rax,r8
 add rsi,4
 dec ecx
 jnz .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
