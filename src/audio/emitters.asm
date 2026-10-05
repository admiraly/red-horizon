; Frame-thread routing of validated authoritative remote rifle counters.
; Local weapon remains immediate via audio_shot; no firearm claim is inferred
; from cannon events. Static baselines prevent replay on joins/redeployment.
default rel
%include "schemas/player.inc"
%include "schemas/combat.inc"
extern sim_players,sim_player_vehicle,audio_listener,audio_emit,audio_emit_kind
extern sim_events,sim_event_sequence,sim_tick_count
section .rodata
one: dd 1.0
section .bss align=16
seen_generation: resd PLAYER_CAPACITY
seen_shots: resd PLAYER_CAPACITY
local_id: resd 1
global audio_remote_shots
audio_remote_shots: resq 1
global audio_event_cursor,audio_battle_events,audio_airgun_events
audio_event_cursor: resd 1
audio_battle_events: resq 1
audio_airgun_events: resq 1
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
 call .events
.done:
 pop r13
 pop r12
 pop rbx
 ret
; Bounded ring consumption, exact sequence matching, <=15-tick age (0.5s).
; Actual impacts/destruction only. Air gun uses recorded rifle surrogate.
.events:
 mov r12d,[sim_event_sequence]
 mov r13d,[audio_event_cursor]
 cmp r12d,r13d
 jb .reset
 mov eax,r12d
 sub eax,r13d
 cmp eax,EVENT_CAPACITY
 jbe .eventloop
 mov r13d,r12d
 sub r13d,EVENT_CAPACITY
.eventloop:
 cmp r13d,r12d
 jae .eventdone
 inc r13d
 mov eax,r13d
 and eax,EVENT_CAPACITY-1
 shl eax,5
 lea rbx,[sim_events]
 add rbx,rax
 cmp [rbx+EVENT_SEQUENCE],r13d
 jne .eventloop
 mov eax,[sim_tick_count]
 sub eax,[rbx+EVENT_TICK]
 cmp eax,15
 ja .eventloop ; stale and future ticks both rejected
 mov eax,[rbx+EVENT_KIND]
 mov edi,1
 cmp eax,3
 jb .eventloop
 cmp eax,5
 jbe .emit_event
 cmp eax,7
 je .emit_event
 cmp eax,9
 je .emit_event
 cmp eax,8
 jne .eventloop
 xor edi,edi
.emit_event:
 movss xmm0,[rbx+EVENT_X]
 movss xmm1,[rbx+EVENT_Y]
 movss xmm2,[rbx+EVENT_Z]
 movss xmm3,[one]
 call audio_emit_kind
 test eax,eax
 jnz .eventloop
 cmp dword [rbx+EVENT_KIND],8
 je .airgun
 inc qword [audio_battle_events]
 jmp .eventloop
.airgun:
 inc qword [audio_airgun_events]
 jmp .eventloop
.reset:
 mov r13d,r12d
.eventdone:
 mov [audio_event_cursor],r12d
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
