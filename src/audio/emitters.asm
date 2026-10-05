; Frame-thread routing of validated authoritative remote rifle counters.
; Local weapon remains immediate via audio_shot; no firearm claim is inferred
; from cannon events. Static baselines prevent replay on joins/redeployment.
default rel
%include "schemas/player.inc"
extern sim_players,sim_player_vehicle,audio_listener,audio_emit
section .rodata
one: dd 1.0
section .bss align=16
seen_generation: resd PLAYER_CAPACITY
seen_shots: resd PLAYER_CAPACITY
local_id: resd 1
global audio_remote_shots
audio_remote_shots: resq 1
section .text
global audio_scene_update
; EDI local player id; XMM0..4 listener xyz,rightxz. No simulation writes.
; Preserves SysV nonvolatile registers. At most one emit per remote per frame;
; skipped snapshots collapse to the latest shot, rather than bursting history.
audio_scene_update:
 push rbx
 push r12
 push r13
 mov [local_id],edi
 call audio_listener
 test eax,eax
 jnz .done
 xor r12d,r12d
 lea rbx,[sim_players]
.players:
 lea rdx,[seen_generation]
 mov eax,[rbx+PLAYER_GENERATION]
 cmp [rdx+r12*4],eax
 jne .baseline
 cmp dword [rbx+PLAYER_CONNECTED],0
 je .baseline
 lea rdx,[seen_shots]
 mov eax,[rbx+PLAYER_SHOTS]
 cmp eax,[rdx+r12*4]
 jbe .baseline
 mov [rdx+r12*4],eax
 cmp r12d,[local_id]
 je .next
 lea rdx,[sim_player_vehicle]
 cmp dword [rdx+r12*4],-1
 jne .next
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Y]
 movss xmm2,[rbx+PLAYER_Z]
 movss xmm3,[one]
 call audio_emit
 test eax,eax
 jnz .next
 inc qword [audio_remote_shots]
 jmp .next
.baseline:
 lea rdx,[seen_generation]
 mov eax,[rbx+PLAYER_GENERATION]
 mov [rdx+r12*4],eax
 lea rdx,[seen_shots]
 mov eax,[rbx+PLAYER_SHOTS]
 mov [rdx+r12*4],eax
.next:
 add rbx,PLAYER_STRIDE
 inc r12d
 cmp r12d,PLAYER_CAPACITY
 jb .players
.done:
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
