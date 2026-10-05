; Fixed twelve-node authored operation graph, evaluated once per second.
%include "schemas/entity.inc"
default rel
extern sim_count, sim_entities, sim_tick_count
section .bss align=32
global sim_sites, sim_requisition, sim_supply, sim_operation_state
sim_sites: resb 12*32
sim_requisition: resd 2
sim_supply: resd 2
sim_operation_state: resd 1
defense_seconds: resd 1
section .rodata
site_x: dd 1000.0,3000.0,5000.0,7000.0
site_z: dd 1300.0,3900.0,6500.0
; Each row is a front, with lateral roads connecting matching columns.
adjacency: dw 0x012,0x025,0x04a,0x084,0x121,0x252,0x4a4,0x848,0x210,0x520,0xa40,0x480
radius2: dd 40000.0
section .text
global operation_init, operation_tick, operation_hash, sim_spend
operation_init:
 lea rdi,[sim_sites]
 xor eax,eax
 mov ecx,102
 rep stosd
 mov dword [sim_requisition],100
 mov dword [sim_requisition+4],100
 xor r8d,r8d
 lea rdi,[sim_sites]
.loop:
 mov eax,r8d
 and eax,3
 lea rsi,[site_x]
 mov edx,[rsi+rax*4]
 mov [rdi],edx
 mov ecx,eax
 mov eax,r8d
 xor edx,edx
 mov esi,4
 div esi
 lea rsi,[site_z]
 mov eax,[rsi+rax*4]
 mov [rdi+4],eax
 xor eax,eax
 cmp ecx,2
 jb .owner
 inc eax
.owner:
 mov [rdi+8],eax
 mov edx,-10
 test eax,eax
 jz .progress
 mov edx,10
.progress:
 mov [rdi+12],edx
 mov dword [rdi+16],1
 cmp ecx,1
 jne .not_production
 mov dword [rdi+16],2
.not_production:
 cmp ecx,2
 jne .not_deployment
 mov dword [rdi+16],3
.not_deployment:
 mov dword [rdi+24],1000
 cmp r8d,0
 jne .enemy_root
 mov dword [rdi+16],0
 mov dword [rdi+28],1
.enemy_root:
 cmp r8d,3
 jne .next
 mov dword [rdi+16],0
 mov dword [rdi+28],2
.next:
 add rdi,32
 inc r8d
 cmp r8d,12
 jb .loop
 jmp connectivity
; Every capture scan is O(12*N), with N bounded by the entity capacity.
operation_tick:
 mov eax,[sim_tick_count]
 xor edx,edx
 mov ecx,30
 div ecx
 test edx,edx
 jnz .return
 push rbx
 push r12
 sub rsp,8
 xor r12d,r12d
 lea rbx,[sim_sites]
.site:
 and dword [rbx+28],3
 cmp dword [rbx+24],0
 je .next_site
 xor r8d,r8d
 xor r9d,r9d
 xor ecx,ecx
 lea rsi,[sim_entities]
.scan:
 cmp ecx,[sim_count]
 jae .capture
 cmp dword [rsi+ENTITY_HP],0
 je .next_entity
 ; Airborne passes cannot occupy, contest or capture ground sites.
 cmp dword [rsi+ENTITY_KIND],3
 je .next_entity
 movss xmm0,[rsi+ENTITY_X]
 subss xmm0,[rbx]
 mulss xmm0,xmm0
 movss xmm1,[rsi+ENTITY_Z]
 subss xmm1,[rbx+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[radius2]
 ja .next_entity
 cmp dword [rsi+ENTITY_SIDE],0
 jne .enemy
 mov r8d,1
 jmp .next_entity
.enemy: mov r9d,1
.next_entity:
 add rsi,ENTITY_STRIDE
 inc ecx
 jmp .scan
.capture:
 test r8d,r8d
 jz .enemy_capture
 test r9d,r9d
 jnz .contest
 cmp dword [rbx+12],-10
 jle .next_site
 dec dword [rbx+12]
 cmp dword [rbx+12],-10
 jne .next_site
 mov dword [rbx+8],0
 jmp .next_site
.enemy_capture:
 test r9d,r9d
 jz .next_site
 cmp dword [rbx+12],10
 jge .next_site
 inc dword [rbx+12]
 cmp dword [rbx+12],10
 jne .next_site
 mov dword [rbx+8],1
 jmp .next_site
.contest: or dword [rbx+28],4
.next_site:
 add rbx,32
 inc r12d
 cmp r12d,12
 jb .site
 call connectivity
 ; Regenerate requisition only from connected, healthy captured sites.
 lea rbx,[sim_sites]
 mov ecx,12
.regen:
 cmp dword [rbx+20],0
 je .regen_next
 mov edx,[rbx+8]
 lea rsi,[sim_requisition]
 mov eax,3
 cmp dword [rbx+16],2
 jne .income
 mov eax,10
.income:
 add [rsi+rdx*4],eax
 jnc .regen_next
 mov dword [rsi+rdx*4],0xffffffff
.regen_next:
 add rbx,32
 loop .regen
 mov eax,[sim_operation_state]
 cmp eax,1
 je .done
 cmp eax,2
 je .done
 cmp dword [sim_sites+8],0
 jne .final_defense
 mov dword [defense_seconds],0
 mov dword [sim_operation_state],0
 cmp dword [sim_sites+3*32+8],0
 jne .done
 mov dword [sim_operation_state],1
 jmp .done
.final_defense:
 mov dword [sim_operation_state],3
 inc dword [defense_seconds]
 cmp dword [defense_seconds],30
 jb .done
 mov dword [sim_operation_state],2
.done:
 add rsp,8
 pop r12
 pop rbx
.return: ret
; Bounded reachability relaxation from roots 0 (allied) and 3 (enemy).
connectivity:
 lea rdi,[sim_sites]
 mov ecx,12
.clear:
 mov dword [rdi+20],0
 add rdi,32
 loop .clear
 mov qword [sim_supply],0
 cmp dword [sim_sites+8],0
 jne .enemy_root
 cmp dword [sim_sites+24],0
 je .enemy_root
 mov dword [sim_sites+20],1
.enemy_root:
 cmp dword [sim_sites+3*32+8],1
 jne .expand
 cmp dword [sim_sites+3*32+24],0
 je .expand
 mov dword [sim_sites+3*32+20],1
.expand:
 mov r11d,12
.pass:
 lea rdi,[sim_sites]
 xor r8d,r8d
.node:
 cmp dword [rdi+20],0
 jne .next
 cmp dword [rdi+24],0
 je .next
 mov eax,[rdi+8]
 cmp eax,1
 ja .next
 lea rsi,[adjacency]
 movzx r9d,word [rsi+r8*2]
 lea rsi,[sim_sites]
 xor r10d,r10d
.neighbor:
 bt r9d,r10d
 jnc .neighbor_next
 cmp dword [rsi+20],0
 je .neighbor_next
 cmp [rsi+8],eax
 jne .neighbor_next
 mov dword [rdi+20],1
 jmp .next
.neighbor_next:
 add rsi,32
 inc r10d
 cmp r10d,12
 jb .neighbor
.next:
 add rdi,32
 inc r8d
 cmp r8d,12
 jb .node
 dec r11d
 jnz .pass
 lea rdi,[sim_sites]
 mov ecx,12
.capacity:
 cmp dword [rdi+20],0
 je .capacity_next
 mov eax,[rdi+8]
 lea rsi,[sim_supply]
 add dword [rsi+rax*4],100
.capacity_next:
 add rdi,32
 loop .capacity
 ret
; Single-threaded authoritative transaction, no additions or wraparound.
sim_spend:
 cmp edi,1
 ja .bad
 test esi,esi
 jz .bad
 lea rdx,[sim_requisition]
 cmp [rdx+rdi*4],esi
 jb .bad
 sub [rdx+rdi*4],esi
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
; Extend world's hash (RAX hash, R8 multiplier) with operation state.
operation_hash:
 lea rsi,[sim_sites]
 mov ecx,408
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
