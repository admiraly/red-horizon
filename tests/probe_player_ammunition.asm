default rel
extern player_ammunition_reserve,player_ammunition_fire,player_ammunition_reload_finish
extern player_ammunition_resupply,player_ammunition_equip,player_ammunition_report,net_player_ammunition_report
section .text
global probe_player_ammunition
; EDI id,ESI entry0..6,RDX40-byte output,RCX7-qword GPR/stack observations.
probe_player_ammunition:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 mov [rsp],edi
 mov [rsp+4],esi
 mov [rsp+8],rdx
 mov [rsp+16],rcx
 mov rbx,0x123401
 mov rbp,0x123402
 mov r12,0x123403
 mov r13,0x123404
 mov r14,0x123405
 mov r15,0x123406
 cmp esi,0
 je .reserve
 cmp esi,1
 je .fire
 cmp esi,2
 je .reload
 cmp esi,3
 je .resupply
 cmp esi,4
 je .equip
 mov rsi,[rsp+8]
 mov edx,40
 cmp dword [rsp+4],5
 je .report
 call net_player_ammunition_report wrt ..plt
 jmp .observe
.report:
 call player_ammunition_report wrt ..plt
 jmp .observe
.reserve:
 call player_ammunition_reserve wrt ..plt
 jmp .observe
.fire:
 call player_ammunition_fire wrt ..plt
 jmp .observe
.reload:
 call player_ammunition_reload_finish wrt ..plt
 jmp .observe
.resupply:
 call player_ammunition_resupply wrt ..plt
 jmp .observe
.equip:
 call player_ammunition_equip wrt ..plt
.observe:
 mov [rsp+24],eax
 mov rcx,[rsp+16]
 mov [rcx],rbx
 mov [rcx+8],rbp
 mov [rcx+16],r12
 mov [rcx+24],r13
 mov [rcx+32],r14
 mov [rcx+40],r15
 mov rax,rsp
 and eax,15
 mov [rcx+48],rax
 mov eax,[rsp+24]
 add rsp,40
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
