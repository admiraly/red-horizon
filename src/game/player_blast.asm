; Hostile explosion damage against current on-foot human bodies.
; No ammunition source, projectile creation, movement or local client damage.
%include "schemas/player.inc"
default rel
extern sim_players,sim_player_vehicle,player_deaths,vehicle_detach,player_motion_reset
extern world_los
section .rodata
zero: dd 0.0
maximum: dd 8000.0
min_y: dd -2000.0
max_y: dd 2000.0
maximum_radius: dd 256.0
section .text
global player_apply_damage,player_blast
; EDI body slot,ESI positive damage<=1000,EDX source side0/1.
; 1applied,0dead/disconnected/friendly,-1invalid. Cooperative humans are side0.
player_apply_damage:
 push rbx
 push r12
 push r13
 mov r12d,edi
 mov r13d,esi
 cmp edi,PLAYER_CAPACITY
 jae .bad
 cmp edx,1
 ja .bad
 test esi,esi
 jz .bad
 cmp esi,1000
 ja .bad
 test edx,edx
 jz .none
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .none
 cmp dword [rbx+PLAYER_HP],0
 je .none
 cmp dword [rbx+PLAYER_HP],100
 ja .bad
 cmp dword [rbx+PLAYER_FRONT],2
 ja .bad
 cmp dword [rbx+PLAYER_GENERATION],0
 je .bad
 add dword [rbx+PLAYER_SUPPRESSION],25
 cmp dword [rbx+PLAYER_SUPPRESSION],100
 jbe .damage
 mov dword [rbx+PLAYER_SUPPRESSION],100
.damage:
 cmp [rbx+PLAYER_HP],r13d
 jbe .dead
 sub [rbx+PLAYER_HP],r13d
 jmp .applied
.dead:
 mov dword [rbx+PLAYER_HP],0
 mov dword [rbx+PLAYER_RESPAWN],30
 mov dword [rbx+PLAYER_RELOAD],0
 inc dword [player_deaths]
 mov edi,r12d
 call vehicle_detach
 mov edi,r12d
 call player_motion_reset
.applied: mov eax,1
 jmp .return
.none: xor eax,eax
 jmp .return
.bad: mov eax,-1
.return:
 pop r13
 pop r12
 pop rbx
 ret
; Finite XZ0..8000,Yabs<=2000. Private leaf; preserves XMM0..2.
position:
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
 ucomiss xmm2,[min_y]
 jp .bad
 jb .bad
 ucomiss xmm2,[max_y]
 ja .bad
 xor eax,eax
 ret
.bad: mov eax,-1
 ret
; EDI source side,ESI damage; XMM0x,XMM1z,XMM2radius,XMM3y.
; Returns number of on-foot humans damaged,or-1invalid. Public eye point sphere
; and physical world LOS; armour crew consequences stay with vehicle authority.
; Stage all four eligibility decisions before damage/death can alter the world.
player_blast:
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,48
 cmp edi,1
 ja .bad
 mov r15d,edi
 test esi,esi
 jz .bad
 cmp esi,1000
 ja .bad
 mov [rsp+16],esi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm3
 ucomiss xmm2,[zero]
 jp .bad
 jbe .bad
 ucomiss xmm2,[maximum_radius]
 ja .bad
 mulss xmm2,xmm2
 movss [rsp+12],xmm2
 movaps xmm2,xmm3
 call position
 test eax,eax
 jnz .bad
 xor r14d,r14d
 test r15d,r15d
 jz .done
 xor r12d,r12d
 xor r13d,r13d
 lea rbx,[sim_players]
.scan:
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .next
 cmp dword [rbx+PLAYER_HP],0
 je .next
 cmp dword [rbx+PLAYER_HP],100
 ja .next
 cmp dword [rbx+PLAYER_FRONT],2
 ja .next
 cmp dword [rbx+PLAYER_GENERATION],0
 je .next
 lea rdx,[sim_player_vehicle]
 cmp dword [rdx+r12*4],-1
 jne .next
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 movss xmm2,[rbx+PLAYER_Y]
 call position
 test eax,eax
 jnz .next
 subss xmm0,[rsp]
 subss xmm1,[rsp+4]
 subss xmm2,[rsp+8]
 mulss xmm0,xmm0
 mulss xmm1,xmm1
 mulss xmm2,xmm2
 addss xmm0,xmm1
 addss xmm0,xmm2
 comiss xmm0,[rsp+12]
 ja .next
 movss xmm0,[rsp]
 movss xmm1,[rsp+8]
 movss xmm2,[rsp+4]
 movss xmm3,[rbx+PLAYER_X]
 movss xmm4,[rbx+PLAYER_Y]
 movss xmm5,[rbx+PLAYER_Z]
 call world_los
 test eax,eax
 jz .next
 bts r13d,r12d
.next:
 inc r12d
 add rbx,PLAYER_STRIDE
 cmp r12d,PLAYER_CAPACITY
 jb .scan
 xor r12d,r12d
.apply:
 bt r13d,r12d
 jnc .apply_next
 mov edi,r12d
 mov esi,[rsp+16]
 mov edx,r15d
 call player_apply_damage
 cmp eax,1
 jne .apply_next
 inc r14d
.apply_next:
 inc r12d
 cmp r12d,PLAYER_CAPACITY
 jb .apply
.done: mov eax,r14d
 jmp .return
.bad: mov eax,-1
.return:
 add rsp,48
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
