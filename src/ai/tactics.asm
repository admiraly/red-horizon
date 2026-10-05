; Camera-independent bounded formation controller. Only acquired LOS targets
; become enemy observations; all own-state inspection is linear and permitted.
%include "schemas/entity.inc"
default rel
extern sim_count, sim_entities, sim_tick_count, sim_sites, sim_supply
extern sim_entity_height
extern terrain_height, terrain_los
section .bss align=64
global ai_fronts
ai_fronts: resb 6*64
seen: resd ENTITY_CAPACITY
section .rodata
weights: dd 1,4,2,2
retreat_goals: dd 1000.0,1300.0,1000.0,3900.0,1000.0,6500.0
               dd 7000.0,1300.0,7000.0,3900.0,7000.0,6500.0
zero: dd 0.0
maximum: dd 8000.0
flank_offset: dd 600.0
commit_distance: dd 500.0
survey_range2: dd 40000.0
eye: dd 2.0
air_eye: dd 90.0
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global ai_init, ai_tick, ai_entity_goal, ai_override, ai_hash
ai_init:
 lea rdi,[ai_fronts]
 xor eax,eax
 mov ecx,96
 rep stosd
 xor r8d,r8d
 lea rdi,[ai_fronts]
.init_front:
 mov eax,r8d
 xor edx,edx
 mov ecx,3
 div ecx
 imul edx,4
 mov ecx,2
 test eax,eax
 jz .init_site
 mov ecx,1
.init_site:
 add edx,ecx
 mov [rdi+20],edx
 shl edx,5
 lea rsi,[sim_sites]
 mov eax,[rsi+rdx]
 mov [rdi+44],eax
 mov eax,[rsi+rdx+4]
 mov [rdi+48],eax
 add rdi,64
 inc r8d
 cmp r8d,6
 jb .init_front
 ret
; EDI side, ESI front are already validated by world APIs.
ai_override:
 imul edi,3
 add edi,esi
 shl edi,6
 lea rax,[ai_fronts]
 mov dword [rax+rdi+24],1
 ret
ai_tick:
 mov eax,[sim_tick_count]
 xor edx,edx
 mov ecx,30
 div ecx
 test edx,edx
 jnz .return
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 lea rdi,[seen]
 xor eax,eax
 mov ecx,[sim_count]
 rep stosd
 lea rdi,[ai_fronts]
 mov ecx,6
.clear:
 mov dword [rdi],0
 mov dword [rdi+4],0
 add rdi,64
 loop .clear
 xor r12d,r12d
 lea rbx,[sim_entities]
.entity:
 cmp dword [rbx+ENTITY_HP],0
 je .next
 mov r13d,[rbx+ENTITY_SIDE]
 imul r13d,3
 add r13d,[rbx+ENTITY_FRONT]
 mov eax,r13d
 shl eax,6
 lea rbp,[ai_fronts]
 add rbp,rax
 mov eax,[rbx+ENTITY_KIND]
 lea rdx,[weights]
 mov eax,[rdx+rax*4]
 add [rbp],eax
 ; Enemy data comes exclusively from the last authoritative visible target.
 mov r14d,[rbx+ENTITY_TARGET]
 cmp r14d,-1
 je .survey
 cmp r14d,[sim_count]
 jae .survey
 mov eax,r14d
 imul rax,ENTITY_STRIDE
 lea r15,[sim_entities]
 add r15,rax
 cmp dword [r15+ENTITY_HP],0
 je .survey
 lea rdx,[seen]
 bts [rdx+r14*4],r13d
 jc .survey
 mov eax,[r15+ENTITY_KIND]
 lea rdx,[weights]
 mov eax,[rdx+rax*4]
 add [rbp+4],eax
 mov eax,[sim_tick_count]
 mov [rbp+8],eax
 mov dword [rbp+12],100
 mov eax,[r15+ENTITY_X]
 mov [rbp+32],eax
 mov eax,[r15+ENTITY_Z]
 mov [rbp+36],eax
.survey:
 ; Designated scouts physically inspect the selected site before commitment.
 test r12d,15
 jz .scout_survey
 cmp dword [rbx+ENTITY_KIND],3
 jne .next
.scout_survey:
 mov eax,[rbp+20]
 cmp eax,11
 ja .next
 shl eax,5
 lea r15,[sim_sites]
 add r15,rax
 movss xmm0,[rbx+ENTITY_X]
 subss xmm0,[r15]
 mulss xmm0,xmm0
 movss xmm1,[rbx+ENTITY_Z]
 subss xmm1,[r15+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[survey_range2]
 ja .next
 mov edi,r12d
 call sim_entity_height
 movss [rsp],xmm0
 movss xmm0,[r15]
 movss xmm1,[r15+4]
 call terrain_height
 addss xmm0,[eye]
 movaps xmm4,xmm0
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rsp]
 movss xmm2,[rbx+ENTITY_Z]
 movss xmm3,[r15]
 movss xmm5,[r15+4]
 call terrain_los
 test eax,eax
 jz .next
 mov dword [rbp+52],1
.next:
 add rbx,ENTITY_STRIDE
 inc r12d
 cmp r12d,[sim_count]
 jb .entity
 xor r12d,r12d
 lea rbx,[ai_fronts]
.front:
 cmp dword [rbx+24],0
 jne .front_next
 ; Pick the next hostile strategic site in this authored front.
 mov eax,r12d
 xor edx,edx
 mov ecx,3
 div ecx
 mov r13d,eax ; side
 imul edx,4
 mov r14d,edx ; first node in front
 mov r15d,2
 test r13d,r13d
 jz .choose
 mov r15d,1
.choose:
 mov eax,r14d
 add eax,r15d
 mov edx,eax
 shl edx,5
 lea rbp,[sim_sites]
 add rbp,rdx
 cmp [rbp+8],r13d
 jne .chosen
 mov r15d,3
 test r13d,r13d
 jz .last_site
 xor r15d,r15d
.last_site:
 mov eax,r14d
 add eax,r15d
 mov edx,eax
 shl edx,5
 lea rbp,[sim_sites]
 add rbp,rdx
.chosen:
 cmp [rbx+20],eax
 je .same_site
 mov [rbx+20],eax
 mov dword [rbx+52],0
 mov dword [rbx+16],0
.same_site:
 mov eax,[rbp]
 mov [rbx+44],eax
 mov eax,[rbp+4]
 mov [rbx+48],eax
 cmp dword [rbx+8],0
 je .stale
 mov eax,[sim_tick_count]
 sub eax,[rbx+8]
 cmp eax,300
 jae .stale
 xor edx,edx
 mov ecx,3
 div ecx
 mov edx,100
 sub edx,eax
 mov [rbx+12],edx
 jmp .evaluate
.stale: mov dword [rbx+12],0
.evaluate:
 cmp dword [rbx+16],2
 jne .threat
 cmp dword [rbx+56],0
 je .threat
 sub dword [rbx+56],30
 jmp .front_next
.threat:
 mov eax,[rbx]
 add eax,eax
 cmp [rbx+4],eax
 ja .withdraw
 lea rdx,[sim_supply]
 cmp dword [rdx+r13*4],100
 jb .withdraw
 ; Survey records reconnaissance completion, never a movement permission.
 cmp dword [rbx+52],0
 je .scout
 mov dword [rbx+16],1
 jmp .front_next
.scout:
 mov dword [rbx+16],0
 jmp .front_next
.withdraw:
 mov dword [rbx+16],2
 mov dword [rbx+56],90
.front_next:
 add rbx,64
 inc r12d
 cmp r12d,6
 jb .front
 add rsp,40
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
.return: ret
; EDI entity ID. EAX -1 means manual formation: world uses explicit order/goal.
; Otherwise EAX 0advance/1hold, and XMM0/XMM1 provide an autonomous goal.
ai_entity_goal:
 mov eax,edi
 imul rax,ENTITY_STRIDE
 lea rsi,[sim_entities]
 add rsi,rax
 mov eax,[rsi+ENTITY_SIDE]
 imul eax,3
 add eax,[rsi+ENTITY_FRONT]
 mov r8d,eax
 shl eax,6
 lea rdx,[ai_fronts]
 add rdx,rax
 cmp dword [rdx+24],0
 jne .manual
 movss xmm0,[rdx+44]
 movss xmm1,[rdx+48]
 cmp dword [rdx+16],2
 je .retreat
 ; Scouts lead directly; support approaches even before the remote site is
 ; surveyed. Enemy coordinates never supply these authored movement goals.
 cmp dword [rsi+ENTITY_KIND],3
 je .move
 test edi,15
 jz .move
.advance:
 mov r10d,edi
 shr r10d,4
 and r10d,1
 ; Short, staggered firing dwells only when this actor acquired a LOS target.
 ; Twelve ticks out of120 per squad replace indefinite scout-stage holding.
 cmp dword [rsi+ENTITY_TARGET],-1
 je .flank
 mov eax,[sim_tick_count]
 mov ecx,r10d
 imul ecx,60
 add eax,ecx
 xor edx,edx
 mov r9d,120
 div r9d
 cmp edx,12
 jb .hold
.flank:
 mov ecx,r10d
 movss xmm2,[rsi+ENTITY_X]
 subss xmm2,xmm0
 andps xmm2,[abs_mask]
 comiss xmm2,[commit_distance]
 jbe .move
 test ecx,ecx
 jnz .upper
 subss xmm1,[flank_offset]
 jmp .clamp
.upper: addss xmm1,[flank_offset]
.clamp:
 maxss xmm1,[zero]
 minss xmm1,[maximum]
.move: xor eax,eax
 ret
.retreat:
 lea rdx,[retreat_goals]
 movss xmm0,[rdx+r8*8]
 movss xmm1,[rdx+r8*8+4]
 xor eax,eax
 ret
.hold: mov eax,1
 ret
.manual: mov eax,-1
 ret
ai_hash:
 lea rsi,[ai_fronts]
 mov ecx,384
.loop:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 loop .loop
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
