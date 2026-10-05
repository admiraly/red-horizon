; Actual gameplay network adapter. SysV x86-64; fixed bounded buffers.
default rel
%include "schemas/player.inc"
%include "src/net/protocol.inc"
extern inet_pton, sim_init, player_init, reset_event_ring
extern sim_count, sim_tick_count, sim_entities, sim_players, sim_sites
extern sim_requisition, sim_supply, sim_operation_state
extern sim_vehicles, sim_player_vehicle, sim_events, sim_event_sequence, sim_event_count
section .rodata
interest2: dd 1440000.0
maximum: dd 8000.0
zero: dd 0.0
minimum_y: dd -1000.0
maximum_y: dd 2000.0
maximum_radius: dd 2000.0
section .data
global net_connected, net_player_id, net_front, net_server_tick, net_last_status
net_connected: dd 0
net_player_id: dd -1
net_front: dd 0
net_server_tick: dd 0
net_last_status: dd 0
fd: dq -1
address: dw 2,0
 dd 0
 dq 0
section .bss align=16
outgoing: resb NET_MTU
incoming: resb NET_MTU
global net_pending
net_pending:
pending_len: resd 1
sequence: resd 1
generation: resd 1
clock_now: resq 2
last_send: resq 1
last_receive: resq 1
state_tick: resd 1
entity_tick: resd 32768
section .text
global net_client_open, net_client_poll, net_client_input, net_client_order, net_client_close
; open(RDI=IPv4 text,ESI=port)->0 queued join/-1. Connected set only on ACK.
net_client_open:
 push rbp
 mov rbp,rsp
 push r12
 push r13
 mov r12,rdi
 mov r13d,esi
 call net_client_close
 cmp r13d,65535
 ja .bad
 test r13d,r13d
 jz .bad
 mov eax,r13d
 rol ax,8
 mov [address+2],ax
 mov edi,2
 mov rsi,r12
 lea rdx,[address+4]
 call inet_pton wrt ..plt
 cmp eax,1
 jne .bad
 mov eax,41
 mov edi,2
 mov esi,2050
 xor edx,edx
 syscall
 test rax,rax
 js .bad
 mov [fd],rax
 mov rdi,rax
 lea rsi,[address]
 mov edx,16
 mov eax,42
 syscall
 test rax,rax
 js .closebad
 mov edi,8192
 mov esi,42
 call sim_init
 call player_init
 call reset_event_ring
 lea rdi,[sim_entities+8]
 mov ecx,8192
.zero:
 mov dword [rdi],0
 add rdi,32
 loop .zero
 lea rdi,[entity_tick]
 xor eax,eax
 mov ecx,32768
 rep stosd
 mov dword [sequence],1
 mov dword [generation],0
 mov dword [state_tick],0
 mov dword [net_server_tick],0
 mov dword [net_player_id],-1
 mov edi,NET_JOIN
 xor esi,esi
 call command_header
 mov dword [pending_len],NET_HEADER
 call now_ms
 mov [last_receive],rax
 call transmit
 xor eax,eax
 jmp .done
.closebad:
 call net_client_close
.bad:
 mov eax,-1
.done:
 pop r13
 pop r12
 pop rbp
 ret
; command_header(EDI=type,ESI=payloadbytes), doesn't alter XMM input values.
command_header:
 mov dword [outgoing],NET_MAGIC
 mov dword [outgoing+4],NET_VERSION
 mov dword [outgoing+8],NET_SCHEMA
 mov dword [outgoing+12],NET_CONTENT
 mov [outgoing+16],edi
 mov eax,[net_player_id]
 mov [outgoing+20],eax
 mov eax,[sequence]
 mov [outgoing+24],eax
 mov dword [outgoing+28],0
 mov [outgoing+32],esi
 mov eax,[generation]
 mov [outgoing+36],eax
 ret
; clock monotonically in milliseconds; no libc allocation.
now_ms:
 mov eax,228
 mov edi,1
 lea rsi,[clock_now]
 syscall
 imul r8,qword [clock_now],1000
 mov rax,[clock_now+8]
 xor edx,edx
 mov ecx,1000000
 div rcx
 add rax,r8
 ret
transmit:
 push rbp
 mov rbp,rsp
 mov rdi,[fd]
 lea rsi,[outgoing]
 mov edx,[pending_len]
 xor r10d,r10d
 xor r8d,r8d
 xor r9d,r9d
 mov eax,44
 syscall
 call now_ms
 mov [last_send],rax
 pop rbp
 ret
net_client_input:
 cmp dword [net_connected],1
 jne input_bad
 cmp dword [pending_len],0
 jne input_bad
 test esi,~31
 jnz input_bad
 mov [outgoing+40],esi
 movss [outgoing+44],xmm0
 movss [outgoing+48],xmm1
 movss [outgoing+52],xmm2
 movss [outgoing+56],xmm3
 push rbp
 mov rbp,rsp
 inc dword [sequence]
 mov edi,NET_INPUT
 mov esi,20
 call command_header
 mov dword [pending_len],60
 call transmit
 xor eax,eax
 pop rbp
 ret
input_bad:
 mov eax,-1
 ret
net_client_order:
 cmp dword [net_connected],1
 jne input_bad
 cmp dword [pending_len],0
 jne input_bad
 cmp edi,[net_front]
 jne input_bad
 cmp dword [net_player_id],3
 je input_bad
 cmp esi,2
 ja input_bad
 mov [outgoing+40],edi
 mov [outgoing+44],esi
 movss [outgoing+48],xmm0
 movss [outgoing+52],xmm1
 push rbp
 mov rbp,rsp
 inc dword [sequence]
 mov edi,NET_ORDER
 mov esi,16
 call command_header
 mov dword [pending_len],56
 call transmit
 xor eax,eax
 pop rbp
 ret
; poll->accepted packet count. Never ticks local simulation.
net_client_poll:
 push rbp
 mov rbp,rsp
 push r12
 push r13
 push r14
 push r15
 xor r12d,r12d
 mov r13d,32
 cmp qword [fd],0
 jl .done
.receive:
 mov rdi,[fd]
 lea rsi,[incoming]
 mov edx,NET_MTU
 mov r10d,32
 xor r8d,r8d
 xor r9d,r9d
 mov eax,45
 syscall
 test rax,rax
 js .after
 cmp rax,NET_HEADER
 jb .next
 cmp rax,NET_MTU
 ja .next
 mov edx,[incoming+32]
 add rdx,NET_HEADER
 cmp rax,rdx
 jne .next
 cmp dword [incoming],NET_MAGIC
 jne .next
 cmp dword [incoming+4],NET_VERSION
 jne .next
 cmp dword [incoming+8],NET_SCHEMA
 jne .next
 cmp dword [incoming+12],NET_CONTENT
 jne .next
 cmp dword [incoming+16],NET_ACK
 je .ack
 cmp dword [net_connected],1
 jne .next
 mov eax,[incoming+20]
 cmp eax,[net_player_id]
 jne .next
 mov eax,[incoming+36]
 cmp eax,[generation]
 jne .next
 cmp dword [incoming+16],NET_STATE
 je .state
 cmp dword [incoming+16],NET_ENTITIES
 je .entities
 cmp dword [incoming+16],NET_EVENTS
 je .events
 jmp .next
.ack:
 cmp dword [incoming+32],16
 jne .next
 cmp dword [pending_len],0
 je .next
 mov eax,[incoming+24]
 cmp eax,[sequence]
 jne .next
 cmp dword [incoming+20],4
 jae .next
 cmp dword [outgoing+16],NET_JOIN
 je .joinack
 mov eax,[incoming+20]
 cmp eax,[net_player_id]
 jne .next
 mov eax,[incoming+36]
 cmp eax,[generation]
 jne .next
 jmp .ackdone
.joinack:
 cmp dword [incoming+40],0
 jne .next
 cmp dword [incoming+36],0
 je .next
 cmp dword [incoming+44],3
 jae .next
 cmp dword [incoming+48],2
 jb .next
 cmp dword [incoming+48],32768
 ja .next
 mov eax,[incoming+48]
 mov [sim_count],eax
 ; Clear all capacity HP so no fabricated records beyond default init.
 lea rdi,[sim_entities+8]
 mov ecx,32768
.clear:
 mov dword [rdi],0
 add rdi,32
 loop .clear
 mov eax,[incoming+20]
 mov [net_player_id],eax
 mov eax,[incoming+44]
 mov [net_front],eax
 mov eax,[incoming+36]
 mov [generation],eax
 mov dword [net_connected],1
.ackdone:
 mov eax,[incoming+40]
 mov [net_last_status],eax
 mov dword [pending_len],0
 jmp .accepted
.state:
 cmp dword [incoming+32],NET_STATE_SIZE-NET_HEADER
 jne .next
 mov eax,[incoming+28]
 cmp eax,[state_tick]
 jb .next
 mov ecx,[incoming+40]
 cmp ecx,2
 jb .next
 cmp ecx,32768
 ja .next
 ; Validate all new ownership records before applying any snapshot fields.
 xor edx,edx
 lea rsi,[incoming+704]
.vehiclecheck:
 cmp dword [rsi+12],1
 ja .next
 cmp [rsi+8],edx
 jne .next
 mov eax,[rsi+12]
 test eax,eax
 jz .detached
 mov eax,[rsi]
 cmp eax,ecx
 jae .next
 lea rdi,[incoming+832]
 cmp [rdi+rdx*4],eax
 jne .next
 ; No two human ownership records may claim the same live entity.
 xor r8d,r8d
 lea rdi,[incoming+704]
.exclusive:
 cmp r8d,edx
 jae .vehiclevalid
 cmp dword [rdi+12],1
 jne .exclusive_next
 cmp [rdi],eax
 je .next
.exclusive_next:
 add rdi,32
 inc r8d
 jmp .exclusive
.detached:
 lea rdi,[incoming+832]
 cmp dword [rdi+rdx*4],-1
 jne .next
.vehiclevalid:
 add rsi,32
 inc edx
 cmp edx,4
 jb .vehiclecheck
 mov eax,[incoming+44]
 cmp eax,3
 ja .next
 mov [sim_operation_state],eax
 mov eax,[incoming+28]
 mov [state_tick],eax
 mov [sim_count],ecx
 lea rsi,[incoming+48]
 lea rdi,[sim_requisition]
 mov ecx,2
 rep movsd
 lea rdi,[sim_supply]
 mov ecx,2
 rep movsd
 lea rdi,[sim_players]
 mov ecx,64
 rep movsd
 lea rdi,[sim_sites]
 mov ecx,96
 rep movsd
 lea rdi,[sim_vehicles]
 mov ecx,32
 rep movsd
 lea rdi,[sim_player_vehicle]
 mov ecx,4
 rep movsd
 jmp .accepted
.entities:
 cmp dword [incoming+32],4
 jb .next
 mov r14d,[incoming+40]
 cmp r14d,32
 ja .next
 imul eax,r14d,36
 add eax,4
 cmp eax,[incoming+32]
 jne .next
 lea r15,[incoming+44]
.records:
 test r14d,r14d
 jz .accepted
 mov eax,[r15]
 cmp eax,[sim_count]
 jae .nextrecord
 lea rdx,[entity_tick]
 mov ecx,[incoming+28]
 cmp ecx,[rdx+rax*4]
 jb .nextrecord
 mov [rdx+rax*4],ecx
 shl eax,5
 lea rdi,[sim_entities]
 add rdi,rax
 mov ecx,[r15+32] ; entity generation at indexprefix+28
 cmp ecx,[rdi+28]
 jb .nextrecord
 ; Server records still undergo finite x/z and enum bounds validation.
 mov ecx,[r15+4]
 and ecx,0x7fffffff
 cmp ecx,0x7f800000
 jae .nextrecord
 mov ecx,[r15+8]
 and ecx,0x7fffffff
 cmp ecx,0x7f800000
 jae .nextrecord
 movss xmm0,[r15+4]
 ucomiss xmm0,[zero]
 jb .nextrecord
 ucomiss xmm0,[maximum]
 ja .nextrecord
 movss xmm1,[r15+8]
 ucomiss xmm1,[zero]
 jb .nextrecord
 ucomiss xmm1,[maximum]
 ja .nextrecord
 cmp dword [r15+16],1
 ja .nextrecord
 cmp dword [r15+20],3
 ja .nextrecord
 cmp dword [r15+24],2
 ja .nextrecord
 lea rsi,[r15+4]
 mov ecx,4
 rep movsq
.nextrecord:
 add r15,36
 dec r14d
 jmp .records
; Validate the complete bounded event packet before publishing any ring slot.
.events:
 cmp dword [incoming+32],4
 jb .next
 mov r14d,[incoming+40]
 cmp r14d,32
 ja .next
 mov eax,r14d
 shl eax,5
 add eax,4
 cmp eax,[incoming+32]
 jne .next
 lea r15,[incoming+44]
 xor r9d,r9d
.validateevent:
 test r14d,r14d
 jz .eventsvalid
 mov ecx,3
 lea rsi,[r15]
.finiteevent:
 mov eax,[rsi]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .next
 add rsi,4
 loop .finiteevent
 movss xmm0,[r15]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[maximum]
 ja .next
 movss xmm0,[r15+8]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[maximum]
 ja .next
 movss xmm0,[r15+4]
 ucomiss xmm0,[minimum_y]
 jb .next
 ucomiss xmm0,[maximum_y]
 ja .next
 mov eax,[r15+12]
 dec eax
 cmp eax,4
 ja .next
 cmp dword [r15+16],1
 ja .next
 mov eax,[r15+20]
 cmp eax,[incoming+28]
 ja .next
 mov eax,[r15+24]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .next
 movss xmm0,[r15+24]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[maximum_radius]
 ja .next
 mov eax,[r15+28]
 cmp eax,r9d
 jbe .next
 mov r9d,eax
 add r15,32
 dec r14d
 jmp .validateevent
.eventsvalid:
 mov r14d,[incoming+40]
 lea r15,[incoming+44]
.applyevent:
 test r14d,r14d
 jz .eventcensus
 mov eax,[r15+28]
 cmp eax,[sim_event_sequence]
 jbe .nextevent
 mov [sim_event_sequence],eax
 and eax,255
 shl eax,5
 lea rdi,[sim_events]
 add rdi,rax
 mov rsi,r15
 mov ecx,4
 rep movsq
.nextevent:
 add r15,32
 dec r14d
 jmp .applyevent
.eventcensus:
 ; Count actual retained records inside the latest256-sequence window.
 ; Sparse interest and loss leave holes; sequence extent is not event count.
 mov r8d,[sim_event_sequence]
 mov r9d,r8d
 sub r9d,255
 jnc .eventwindow
 xor r9d,r9d
.eventwindow:
 lea rsi,[sim_events+28]
 mov ecx,256
 xor edx,edx
.count_events:
 mov eax,[rsi]
 test eax,eax
 jz .count_next
 cmp eax,r9d
 jb .count_next
 cmp eax,r8d
 ja .count_next
 inc edx
.count_next:
 add rsi,32
 loop .count_events
 mov [sim_event_count],edx
.accepted:
 inc r12d
 mov eax,[incoming+28]
 cmp eax,[net_server_tick]
 jb .stamp
 mov [net_server_tick],eax
 mov [sim_tick_count],eax
.stamp:
 call now_ms
 mov [last_receive],rax
.next:
 dec r13d
 jnz .receive
.after:
 call now_ms
 mov r14,rax
 sub rax,[last_receive]
 cmp rax,3000
 jb .retry
 mov dword [net_connected],0
 mov dword [pending_len],0
.retry:
 cmp dword [pending_len],0
 je .expire
 mov rax,r14
 sub rax,[last_send]
 cmp rax,100
 jb .expire
 call transmit
.expire:
 ; Old unrefreshed entities cannot remain authoritative ghosts indefinitely.
 mov ecx,[sim_count]
 imul r9d,ecx,3
 add r9d,63
 shr r9d,6
 add r9d,90 ; full count worst-case cycle plus 3s margin
 mov r8d,[net_player_id]
 cmp r8d,4
 jae .done
 shl r8d,6
 lea rdx,[sim_players]
 add r8,rdx
 lea rdi,[sim_entities+8]
 lea rsi,[entity_tick]
 mov eax,[net_server_tick]
.loop:
 mov edx,eax
 sub edx,[rsi]
 cmp edx,r9d
 ja .hide
 movss xmm0,[rdi-8]
 subss xmm0,[r8+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[rdi-4]
 subss xmm1,[r8+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[interest2]
 jbe .keep
.hide:
 mov dword [rdi],0
.keep:
 add rdi,32
 add rsi,4
 dec ecx
 jnz .loop
.done:
 mov eax,r12d
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 ret
net_client_close:
 mov rdi,[fd]
 test rdi,rdi
 js .done
 ; Best-effort disconnect is followed by server timeout if this datagram drops.
 cmp dword [net_connected],1
 jne .close
 inc dword [sequence]
 mov edi,NET_LEAVE
 xor esi,esi
 call command_header
 mov rdi,[fd]
 lea rsi,[outgoing]
 mov edx,NET_HEADER
 xor r10d,r10d
 xor r8d,r8d
 xor r9d,r9d
 mov eax,44
 syscall
.close:
 mov rdi,[fd]
 mov eax,3
 syscall
.done:
 mov qword [fd],-1
 mov dword [net_connected],0
 mov dword [net_player_id],-1
 mov dword [pending_len],0
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
