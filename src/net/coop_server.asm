default rel
%include "schemas/player.inc"
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/ground_motion.inc"
%include "schemas/combat.inc"
%include "schemas/projectile_remote.inc"
%include "schemas/wreck.inc"
%include "schemas/wreck_remote.inc"
%include "schemas/company_remote.inc"
extern sim_wrecks
extern sim_projectiles
%include "src/net/protocol.inc"
extern vehicle_driver_generation
extern vehicle_entity_driver
extern sim_ground_motion
extern sim_aircraft
extern strcmp, printf, fflush
extern company_transfer,company_transfers
extern company_for_player,company_control_order,company_controls,player_companies
extern sim_init, sim_tick, sim_order, sim_waypoint, sim_spend
extern sim_count, sim_tick_count, sim_entities, sim_players, sim_sites
extern sim_requisition, sim_supply, sim_operation_state
extern sim_vehicles, sim_player_vehicle, sim_events, sim_event_sequence, sim_event_count
extern player_init, player_join, player_leave, player_input
extern terrain_blocked
section .rodata
f_port: db '--port',0
f_ticks: db '--ticks',0
f_units: db '--units',0
ready_fmt: db '{"port":%u,"protocol":%u,"units":%u}',10,0
report_fmt: db '{"ticks":%u,"simulated":%u,"bytes_in":%lu,"bytes_out":%lu,"entity_records":%lu,"rejected":%u,"disconnects":%u,"distinct_client_entity_pairs":%lu,"nearby_interest":%u,"unseen_interest":%u,"aircraft_records":%lu}',10,0
interest2: dd 1440000.0
maximum: dd 8000.0
zero: dd 0.0
section .data
port: dd 7777
ticks: dd 0
units: dd 8192
sockaddr: dw 2,0
 dd 0
 dq 0
section .bss align=16
sock: resq 1
peer: resb 16
peerlen: resd 1
packet: resb NET_MTU
output: resb NET_MTU
slots: resb 4*NET_RECORD
bytes_in: resq 1
bytes_out: resq 1
entity_records: resq 1
aircraft_records: resq 1
rejections: resd 1
disconnects: resd 1
budget: resd 1
event_cursors: resd 4
air_cursors: resd 4
ground_cursors: resd 4
projectile_cursors: resd 4
wreck_cursors: resd 4
replicated: resb 4*32768
distinct_pairs: resq 1
interest_counts: resd 4
unseen_counts: resd 4
clock_target: resq 2
section .text
global main
main:
 push rbp
 mov rbp,rsp
 push r12
 push r13
 push r14
 push r15
 mov r12,rsi
 mov r13d,edi
 mov r14d,1
.args:
 cmp r14d,r13d
 jae .parsed
 lea eax,[r14+1]
 cmp eax,r13d
 jae .bad
 mov rdi,[r12+r14*8]
 lea rsi,[f_port]
 call strcmp wrt ..plt
 test eax,eax
 jz .port
 mov rdi,[r12+r14*8]
 lea rsi,[f_ticks]
 call strcmp wrt ..plt
 test eax,eax
 jz .ticks
 mov rdi,[r12+r14*8]
 lea rsi,[f_units]
 call strcmp wrt ..plt
 test eax,eax
 jnz .bad
 lea r15,[units]
 jmp .value
.port:
 lea r15,[port]
 jmp .value
.ticks:
 lea r15,[ticks]
.value:
 mov rdi,[r12+r14*8+8]
 call parse_number
 jc .bad
 mov [r15],eax
 add r14d,2
 jmp .args
.parsed:
 cmp dword [port],65535
 ja .bad
 cmp dword [ticks],18000
 ja .bad
 mov edi,[units]
 mov esi,42
 call sim_init
 test eax,eax
 jnz .bad
 call player_init
 mov eax,41
 mov edi,2
 mov esi,2050
 xor edx,edx
 syscall
 test rax,rax
 js .bad
 mov [sock],rax
 mov edx,[port]
 rol dx,8
 mov [sockaddr+2],dx
 mov rdi,rax
 lea rsi,[sockaddr]
 mov edx,16
 mov eax,49
 syscall
 test rax,rax
 js .closebad
 mov dword [peerlen],16
 mov rdi,[sock]
 lea rsi,[sockaddr]
 lea rdx,[peerlen]
 mov eax,51
 syscall
 movzx esi,word [sockaddr+2]
 rol si,8
 mov ecx,[units]
 mov edx,NET_VERSION
 lea rdi,[ready_fmt]
 xor eax,eax
 call printf wrt ..plt
 xor edi,edi
 call fflush wrt ..plt
 mov eax,228
 mov edi,1
 lea rsi,[clock_target]
 syscall
.loop:
 mov dword [budget],64
.receive:
 mov dword [peerlen],16
 mov rdi,[sock]
 lea rsi,[packet]
 mov edx,NET_MTU
 mov r10d,32
 lea r8,[peer]
 lea r9,[peerlen]
 mov eax,45
 syscall
 test rax,rax
 js .advance
 add [bytes_in],rax
 cmp rax,NET_HEADER
 jb .reject
 cmp rax,NET_MTU
 ja .reject
 mov ecx,[packet+32]
 add rcx,NET_HEADER
 cmp rcx,rax
 jne .reject
 cmp dword [packet],NET_MAGIC
 jne .reject
 cmp dword [packet+4],NET_VERSION
 jne .reject
 cmp dword [packet+8],NET_SCHEMA
 jne .reject
 cmp dword [packet+12],NET_CONTENT
 jne .reject
 call handle_packet
 jmp .nextpacket
.reject:
 inc dword [rejections]
.nextpacket:
 dec dword [budget]
 jnz .receive
.advance:
 call expire_slots
 call sim_tick
 mov eax,[sim_tick_count]
 xor edx,edx
 mov ecx,3
 div ecx
 test edx,edx
 jnz .sleep
 call snapshots
.sleep:
 add qword [clock_target+8],33333333
 cmp qword [clock_target+8],1000000000
 jb .wait
 sub qword [clock_target+8],1000000000
 inc qword [clock_target]
.wait:
 mov eax,230
 mov edi,1
 mov esi,1
 lea rdx,[clock_target]
 xor r10d,r10d
 syscall
 mov eax,[sim_tick_count]
 cmp dword [ticks],0
 je .loop
 cmp eax,[ticks]
 jb .loop
 lea rdi,[report_fmt]
 mov esi,[sim_tick_count]
 mov edx,[sim_count]
 mov rcx,[bytes_in]
 mov r8,[bytes_out]
 mov r9,[entity_records]
 sub rsp,48
 mov rax,[distinct_pairs]
 mov [rsp+16],rax
 mov eax,[interest_counts]
 add eax,[interest_counts+4]
 add eax,[interest_counts+8]
 add eax,[interest_counts+12]
 mov [rsp+24],rax
 mov eax,[unseen_counts]
 add eax,[unseen_counts+4]
 add eax,[unseen_counts+8]
 add eax,[unseen_counts+12]
 mov [rsp+32],rax
 mov rax,[aircraft_records]
 mov [rsp+40],rax
 mov eax,[rejections]
 mov [rsp],rax
 mov eax,[disconnects]
 mov [rsp+8],rax
 xor eax,eax
 call printf wrt ..plt
 add rsp,48
 mov rdi,[sock]
 mov eax,3
 syscall
 xor eax,eax
 jmp .done
.closebad:
 mov rdi,[sock]
 mov eax,3
 syscall
.bad:
 mov eax,2
.done:
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 ret
parse_number:
 xor eax,eax
 xor ecx,ecx
.loop:
 movzx edx,byte [rdi+rcx]
 test edx,edx
 jz .end
 sub edx,'0'
 cmp edx,9
 ja .bad
 imul eax,10
 add eax,edx
 cmp eax,65535
 ja .bad
 inc ecx
 jmp .loop
.end:
 test ecx,ecx
 jz .bad
 clc
 ret
.bad:
 stc
 ret
; Fill response/snapshot header EDI=type,ESI=slot,EDX=payloadlen.
header:
 mov dword [output],NET_MAGIC
 mov dword [output+4],NET_VERSION
 mov dword [output+8],NET_SCHEMA
 mov dword [output+12],NET_CONTENT
 mov [output+16],edi
 mov [output+20],esi
 mov dword [output+24],0
 mov eax,[sim_tick_count]
 mov [output+28],eax
 mov [output+32],edx
 imul eax,esi,NET_RECORD
 lea rcx,[slots]
 mov eax,[rcx+rax+SLOT_GENERATION]
 mov [output+36],eax
 ret
; ESI length, RDI address.
send_packet:
 mov edx,esi
 mov r8,rdi
 mov r9d,16
 mov rdi,[sock]
 lea rsi,[output]
 xor r10d,r10d
 mov eax,44
 syscall
 test rax,rax
 jle .done
 add [bytes_out],rax
.done:
 ret
; All input work runs before authoritative sim_tick. Callee-saved slot/index.
handle_packet:
 push rbp
 mov rbp,rsp
 push r12
 push r13
 push r14
 push r15
 xor r12d,r12d
 lea r13,[slots]
 mov rax,[peer]
.search:
 cmp [r13],rax
 je .found
 add r13,NET_RECORD
 inc r12d
 cmp r12d,4
 jb .search
 cmp dword [packet+16],NET_JOIN
 jne .silent
 cmp dword [packet+32],0
 jne .silent
 cmp dword [packet+20],-1
 jne .silent
 cmp dword [packet+24],1
 jne .silent
 cmp dword [packet+36],0
 jne .silent
 xor r12d,r12d
 lea r13,[slots]
.free:
 cmp qword [r13],0
 je .join
 add r13,NET_RECORD
 inc r12d
 cmp r12d,4
 jb .free
 jmp .silent
.join:
 mov edi,r12d
 mov esi,r12d
 cmp esi,3
 jb .front
 xor esi,esi
.front:
 call player_join
 test eax,eax
 jnz .silent
 mov rax,[peer]
 mov [r13],rax
 mov qword [r13+8],0
 lea rdx,[event_cursors]
 mov eax,[sim_event_sequence]
 mov [rdx+r12*4],eax
 mov dword [r13+SLOT_SEQUENCE],1
 inc dword [r13+SLOT_GENERATION]
 mov eax,r12d
 shl eax,15
 lea rdi,[replicated]
 add rdi,rax
 xor eax,eax
 mov ecx,32768
 rep stosb
 lea rdx,[air_cursors]
 mov dword [rdx+r12*4],0
 lea rdx,[ground_cursors]
 mov dword [rdx+r12*4],0
 lea rdx,[projectile_cursors]
 mov dword [rdx+r12*4],0
 mov dword [r13+SLOT_CURSOR],0
 mov dword [r13+SLOT_INPUTTICK],-1
 mov dword [r13+SLOT_ORDERTICK],-15
 mov dword [r13+SLOT_ACKSTATUS],0
 jmp .ack
.found:
 cmp dword [packet+16],NET_JOIN
 je .joinretry
 cmp [packet+20],r12d
 jne .silent
 mov eax,[packet+36]
 cmp eax,[r13+SLOT_GENERATION]
 jne .silent
 jmp .sequence
.joinretry:
 cmp dword [packet+20],-1
 jne .silent
 cmp dword [packet+24],1
 jne .silent
 cmp dword [packet+32],0
 jne .silent
 jmp .ack
.sequence:
 mov eax,[packet+24]
 cmp eax,[r13+SLOT_SEQUENCE]
 je .ack
 mov edx,[r13+SLOT_SEQUENCE]
 inc edx
 cmp eax,edx
 jne .silent
 mov [r13+SLOT_SEQUENCE],eax
 mov dword [r13+SLOT_ACKSTATUS],1
 cmp dword [packet+16],NET_INPUT
 je .input
 cmp dword [packet+16],NET_ORDER
 je .order
 cmp dword [packet+16],NET_TRANSFER
 je .transfer
 cmp dword [packet+16],NET_LEAVE
 je .leave
 jmp .ack
.input:
 cmp dword [packet+32],20
 jne .ack
 mov eax,[sim_tick_count]
 cmp eax,[r13+SLOT_INPUTTICK]
 je .rate
 mov [r13+SLOT_INPUTTICK],eax
 mov edi,r12d
 mov esi,[packet+40]
 test esi,~127
 jnz .ack
 movss xmm0,[packet+44]
 movss xmm1,[packet+48]
 movss xmm2,[packet+52]
 movss xmm3,[packet+56]
 call player_input
 test eax,eax
 jnz .ack
 mov dword [r13+SLOT_ACKSTATUS],0
 jmp .ack
.transfer:
 cmp dword [packet+32],12
 jne .ack
 mov edi,r12d
 mov esi,[packet+44]
 mov edx,[packet+40]
 mov ecx,[packet+48]
 call company_transfer
 cmp eax,-2
 je .ownership
 test eax,eax
 jnz .ack
 mov dword [r13+SLOT_ACKSTATUS],0
 jmp .ack
.order:
 cmp dword [packet+32],16
 jne .ack
 mov eax,r12d
 shl eax,6
 lea rcx,[sim_players]
 mov eax,[rcx+rax+PLAYER_FRONT]
 cmp [packet+40],eax
 jne .ownership
 cmp dword [packet+44],4
 ja .ack
 mov eax,[sim_tick_count]
 sub eax,[r13+SLOT_ORDERTICK]
 cmp eax,15
 jb .rate
 mov eax,[packet+48]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .ack
 mov eax,[packet+52]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .ack
 movss xmm0,[packet+48]
 movss xmm1,[packet+52]
 ucomiss xmm0,[zero]
 jb .ack
 ucomiss xmm1,[zero]
 jb .ack
 ucomiss xmm0,[maximum]
 ja .ack
 ucomiss xmm1,[maximum]
 ja .ack
 ; Reject ground-solid destinations before charging or mutating orders.
 xor edi,edi
 call terrain_blocked
 test eax,eax
 jnz .ack
 mov edi,r12d
 call company_for_player
 cmp eax,-1
 je .ownership
 mov esi,eax
 mov edi,r12d
 mov edx,[packet+44]
 movss xmm0,[packet+48]
 movss xmm1,[packet+52]
 call company_control_order
 cmp eax,-2
 je .ownership
 cmp eax,-3
 je .funds
 test eax,eax
 jnz .ack
 mov eax,[sim_tick_count]
 mov [r13+SLOT_ORDERTICK],eax
 mov dword [r13+SLOT_ACKSTATUS],0
 jmp .ack
.ownership:
 mov dword [r13+SLOT_ACKSTATUS],5
 jmp .ack
.funds:
 mov dword [r13+SLOT_ACKSTATUS],6
 jmp .ack
.rate:
 mov dword [r13+SLOT_ACKSTATUS],7
 jmp .ack
.leave:
 cmp dword [packet+32],0
 jne .ack
 mov edi,r12d
 call player_leave
 mov qword [r13],0
 lea rax,[interest_counts]
 mov dword [rax+r12*4],0
 lea rax,[unseen_counts]
 mov dword [rax+r12*4],0
 mov dword [r13+SLOT_ACKSTATUS],0
.ack:
 mov eax,[sim_tick_count]
 mov [r13+SLOT_LASTSEEN],eax
 mov edi,NET_ACK
 mov esi,r12d
 mov edx,16
 call header
 mov eax,[packet+24]
 mov [output+24],eax
 mov eax,[r13+SLOT_ACKSTATUS]
 mov [output+40],eax
 cmp eax,0
 je .ok
 inc dword [rejections]
.ok:
 mov eax,r12d
 shl eax,6
 lea rdx,[sim_players]
 mov eax,[rdx+rax+PLAYER_FRONT]
 mov [output+44],eax
 mov eax,[sim_count]
 mov [output+48],eax
 mov eax,[sim_requisition]
 mov [output+52],eax
 lea rdi,[peer]
 mov esi,56
 call send_packet
 jmp .done
.silent:
 inc dword [rejections]
.done:
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 ret
expire_slots:
 push rbp
 mov rbp,rsp
 push r12
 push r13
 xor r12d,r12d
 lea r13,[slots]
.loop:
 cmp qword [r13],0
 je .next
 mov eax,[sim_tick_count]
 sub eax,[r13+SLOT_LASTSEEN]
 cmp eax,NET_TIMEOUT
 jb .next
 mov edi,r12d
 call player_leave
 mov qword [r13],0
 lea rax,[interest_counts]
 mov dword [rax+r12*4],0
 lea rax,[unseen_counts]
 mov dword [rax+r12*4],0
 inc dword [disconnects]
.next:
 add r13,NET_RECORD
 inc r12d
 cmp r12d,4
 jb .loop
 pop r13
 pop r12
 pop rbp
 ret
snapshots:
 push rbp
 mov rbp,rsp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 xor r12d,r12d
 lea r13,[slots]
.slot:
 cmp qword [r13],0
 je .nextslot
 mov edi,NET_STATE
 mov esi,r12d
 mov edx,NET_STATE_SIZE-NET_HEADER
 call header
 mov eax,[sim_count]
 mov [output+40],eax
 mov eax,[sim_operation_state]
 mov [output+44],eax
 lea rsi,[sim_requisition]
 lea rdi,[output+48]
 mov ecx,2
 rep movsd
 lea rsi,[sim_supply]
 mov ecx,2
 rep movsd
 lea rsi,[sim_players]
 mov ecx,64
 rep movsd
 lea rsi,[sim_sites]
 mov ecx,96
 rep movsd
 lea rsi,[sim_vehicles]
 mov ecx,32
 rep movsd
 lea rsi,[sim_player_vehicle]
 mov ecx,4
 rep movsd
 mov rdi,r13
 mov esi,NET_STATE_SIZE
 call send_packet
 ; Bounded full-region census for measured interest/backlog; simulation is unchanged.
 mov eax,r12d
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 mov eax,r12d
 shl eax,15
 lea r8,[replicated]
 add r8,rax
 xor ecx,ecx
 xor edx,edx
 xor r9d,r9d
 lea rsi,[sim_entities]
.census:
 movss xmm0,[rsi]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[rsi+4]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[interest2]
 ja .censusnext
 inc edx
 cmp byte [r8+rcx],0
 jne .censusnext
 inc r9d
.censusnext:
 add rsi,32
 inc ecx
 cmp ecx,[sim_count]
 jb .census
 lea rax,[interest_counts]
 mov [rax+r12*4],edx
 lea rax,[unseen_counts]
 mov [rax+r12*4],r9d
 mov edi,r12d
 call company_for_player
 mov [rsp+4],eax ; own allied cohort also remains visible outside local region
 mov dword [rsp],2 ; chunks
.chunk:
 mov edi,NET_ENTITIES
 mov esi,r12d
 mov edx,0
 call header
 xor r14d,r14d ; included
 xor r15d,r15d ; examined
 lea rbx,[sim_players] ; RBX must preserve! use stack scratch for player pointer
 mov eax,r12d
 shl eax,6
 add rbx,rax
.scan:
 mov eax,[r13+SLOT_CURSOR]
 cmp eax,[sim_count]
 jb .index
 xor eax,eax
.index:
 lea rdx,[sim_entities]
 mov ecx,eax
 shl ecx,5
 add rdx,rcx
 inc eax
 mov [r13+SLOT_CURSOR],eax
 inc r15d
 movss xmm0,[rdx]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[rdx+4]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[interest2]
 jbe .include_entity
 ; Bounded own-company exception only; no remote enemy ground truth.
 cmp dword [rsp+4],768
 jae .skip
 cmp dword [rdx+ENTITY_SIDE],0
 jne .skip
 cmp dword [rdx+ENTITY_KIND],2
 ja .skip
 cmp dword [rdx+ENTITY_GENERATION],0
 je .skip
 mov ecx,[rdx+ENTITY_FRONT]
 cmp ecx,2
 ja .skip
 shl ecx,8
 mov eax,[r13+SLOT_CURSOR]
 dec eax
 shr eax,7
 add ecx,eax
 cmp ecx,[rsp+4]
 jne .skip
.include_entity:
 mov eax,r14d
 imul eax,36
 lea rdi,[output+44]
 add rdi,rax
 mov eax,[r13+SLOT_CURSOR]
 dec eax
 mov [rdi],eax
 mov ecx,r12d
 shl ecx,15
 add ecx,eax
 lea rsi,[replicated]
 cmp byte [rsi+rcx],0
 jne .counted
 mov byte [rsi+rcx],1
 inc qword [distinct_pairs]
.counted:
 add rdi,4
 mov rsi,rdx
 mov ecx,4
 rep movsq
 inc r14d
.skip:
 cmp r14d,32
 jae .sendchunk
 cmp r15d,[sim_count]
 jb .scan
.sendchunk:
 mov [output+40],r14d
 imul esi,r14d,36
 add esi,44
 lea eax,[rsi-NET_HEADER]
 mov [output+32],eax
 add [entity_records],r14
 mov rdi,r13
 call send_packet
 dec dword [rsp]
 jnz .chunk
 mov edi,r12d
 mov rsi,r13
 call send_events
 mov edi,r12d
 mov rsi,r13
 call send_aircraft
 mov edi,r12d
 mov rsi,r13
 call send_ground
 mov edi,r12d
 mov rsi,r13
 call send_projectiles
 mov edi,r12d
 mov rsi,r13
 call send_wrecks
 mov edi,r12d
 mov rsi,r13
 call send_companies
.nextslot:
 add r13,NET_RECORD
 inc r12d
 cmp r12d,4
 jb .slot
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
; Cosmetic-only ring replication: at most one 1068-byte packet per snapshot.
; Cursor advances through filtered events too; at most256 slots examined.
; Late join begins at latest sequence and never replays old battlefield flashes.
send_events:
 push rbp
 mov rbp,rsp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov r12d,edi
 mov r13,rsi
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 lea rdx,[event_cursors]
 mov r14d,[rdx+r12*4]
 mov eax,[sim_event_sequence]
 sub eax,r14d
 cmp eax,256
 jbe .bounded
 mov r14d,[sim_event_sequence]
 sub r14d,256
.bounded:
 xor r15d,r15d
 mov edi,NET_EVENTS
 mov esi,r12d
 mov edx,4
 call header
.scan:
 cmp r14d,[sim_event_sequence]
 je .finish
 inc r14d
 mov eax,r14d
 and eax,255
 shl eax,5
 lea rsi,[sim_events]
 add rsi,rax
 cmp [rsi+28],r14d
 jne .scan
 movss xmm0,[rsi]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[rsi+8]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[interest2]
 ja .scan
 mov eax,r15d
 shl eax,5
 lea rdi,[output+44]
 add rdi,rax
 mov ecx,4
 rep movsq
 inc r15d
 cmp r15d,32
 jb .scan
.finish:
 lea rdx,[event_cursors]
 mov [rdx+r12*4],r14d
 test r15d,r15d
 jz .done
 mov [output+40],r15d
 mov esi,r15d
 shl esi,5
 add esi,44
 lea eax,[rsi-NET_HEADER]
 mov [output+32],eax
 mov rdi,r13
 call send_packet
.done:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
; Bounded independent ground64 interest, with the legitimate owned hull first.
send_ground:
 push rbp
 mov rbp,rsp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov r12d,edi
 mov r13,rsi
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 mov edi,NET_GROUND
 mov esi,r12d
 mov edx,4
 call header
 xor r14d,r14d
 xor r15d,r15d
 mov dword [rsp],-1
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .scan
 cmp dword [rbx+PLAYER_HP],0
 je .scan
 cmp dword [rbx+PLAYER_GENERATION],0
 je .scan
 lea rdx,[sim_player_vehicle]
 mov eax,[rdx+r12*4]
 cmp eax,[sim_count]
 jae .scan
 mov r9d,eax
 mov eax,r12d
 shl eax,5
 lea r8,[sim_vehicles]
 add r8,rax
 cmp dword [r8+VEHICLE_ACTIVE],1
 jne .scan
 cmp [r8+VEHICLE_ENTITY],r9d
 jne .scan
 cmp [r8+VEHICLE_DRIVER],r12d
 jne .scan
 lea rdx,[vehicle_driver_generation]
 mov eax,[rbx+PLAYER_GENERATION]
 cmp eax,[rdx+r12*4]
 jne .scan
 lea rdx,[vehicle_entity_driver]
 cmp [rdx+r9*4],r12d
 jne .scan
 mov eax,r9d
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+12],0
 jne .scan
 cmp dword [rdx+16],1
 jne .scan
 cmp dword [rdx+8],0
 je .scan
 mov eax,[rdx+28]
 cmp eax,[r8+VEHICLE_ENTITY_GENERATION]
 jne .scan
 mov [rsp],r9d
 jmp .candidate
.scan:
 lea r8,[ground_cursors]
 mov eax,[r8+r12*4]
 cmp eax,[sim_count]
 jb .index
 xor eax,eax
.index:
 mov r9d,eax
 inc eax
 mov [r8+r12*4],eax
 inc r15d
 cmp r9d,[rsp]
 je .skip
 mov eax,r9d
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 movss xmm0,[rdx]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[rdx+4]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[interest2]
 ja .skip
.candidate:
 mov eax,[rdx+16]
 cmp eax,1
 jb .skip
 cmp eax,2
 ja .skip
 mov ecx,r9d
 shl ecx,5
 lea rsi,[sim_ground_motion]
 add rsi,rcx
 cmp eax,[rsi+GROUND_KIND]
 jne .skip
 mov eax,[rdx+28]
 cmp eax,[rsi+GROUND_GENERATION]
 jne .skip
 cmp dword [rdx+8],0
 je .append
 test dword [rsi+GROUND_FLAGS],GROUND_ACTIVE
 jz .skip
.append:
 mov eax,r12d
 shl eax,15
 add eax,r9d
 lea r8,[replicated]
 cmp byte [r8+rax],0
 jne .counted
 mov byte [r8+rax],1
 inc qword [distinct_pairs]
.counted:
 imul edi,r14d,64
 lea r8,[output+44]
 add rdi,r8
 mov [rdi],r9d
 add rdi,4
 mov r8,rsi
 mov rsi,rdx
 mov ecx,4
 rep movsq
 mov rsi,r8
 mov ecx,5
 rep movsd
 xor eax,eax
 cmp dword [rdx+8],0
 je .dead
 mov eax,GROUND_ACTIVE
 jmp .flags
.dead:
 mov dword [rdi-16],0
 mov dword [rdi-12],0
 mov dword [rdi-8],0
 mov dword [rdi-4],0
.flags:
 stosd
 xor eax,eax
 stosd
 inc r14d
.skip:
 cmp r14d,18
 jae .finish
 cmp r15d,[sim_count]
 jb .scan
.finish:
 test r14d,r14d
 jz .done
 mov [output+40],r14d
 imul esi,r14d,64
 add esi,44
 lea eax,[rsi-NET_HEADER]
 mov [output+32],eax
 mov rdi,r13
 call send_packet
.done:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret

; One bounded independent aircraft packet per client snapshot:
; nearby live aircraft; full entity32 plus pose makes air warmup independent.
send_aircraft:
 push rbp
 mov rbp,rsp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov r12d,edi
 mov r13,rsi
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 mov edi,NET_AIRCRAFT
 mov esi,r12d
 mov edx,4
 call header
 xor r14d,r14d
 xor r15d,r15d
.scan:
 lea r8,[air_cursors]
 mov eax,[r8+r12*4]
 cmp eax,[sim_count]
 jb .index
 xor eax,eax
.index:
 mov r9d,eax
 inc eax
 mov [r8+r12*4],eax
 inc r15d
 lea rdx,[sim_entities]
 mov eax,r9d
 shl eax,5
 add rdx,rax
 cmp dword [rdx+16],3
 jne .skip
 movss xmm0,[rdx]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[rdx+4]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[interest2]
 ja .skip
 mov eax,r9d
 shl eax,6
 lea rsi,[sim_aircraft]
 add rsi,rax
 test dword [rsi+AIR_FLAGS],AIR_ACTIVE
 jz .skip
 mov eax,[rdx+28]
 cmp eax,[rsi+AIR_GENERATION]
 jne .skip
 ; Air64 itself replicates a full entity, so include it in interest evidence.
 mov eax,r12d
 shl eax,15
 add eax,r9d
 lea r8,[replicated]
 cmp byte [r8+rax],0
 jne .aircounted
 mov byte [r8+rax],1
 inc qword [distinct_pairs]
.aircounted:
 imul edi,r14d,64
 lea r8,[output+44]
 add rdi,r8
 mov [rdi],r9d
 add rdi,4
 mov r8,rsi
 mov rsi,rdx
 mov ecx,4
 rep movsq
 mov rsi,r8
 mov ecx,7
 rep movsd
 inc r14d
.skip:
 cmp r14d,18
 jae .finish
 cmp r15d,[sim_count]
 jb .scan
.finish:
 test r14d,r14d
 jz .done
 add [aircraft_records],r14
 mov [output+40],r14d
 imul esi,r14d,64
 add esi,44
 lea eax,[rsi-NET_HEADER]
 mov [output+32],eax
 mov rdi,r13
 call send_packet
.done:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
; Up to18 authentic pool records including generation-stamped tombstones.
; Fair cursor scans at most512 slots, independently of sparse entity/air packets.
send_projectiles:
 push rbp
 mov rbp,rsp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,24
 mov r12d,edi
 mov r13,rsi
 mov eax,edi
 shl eax,6
 lea rbx,[sim_players]
 add rbx,rax
 mov edi,NET_PROJECTILES
 mov esi,r12d
 mov edx,4
 call header
 xor r14d,r14d
 mov dword [rsp],-1
 cmp dword [rbx+PLAYER_CONNECTED],1
 jne .fair_begin
 cmp dword [rbx+PLAYER_HP],0
 je .fair_begin
 cmp dword [rbx+PLAYER_GENERATION],0
 je .fair_begin
 lea rdx,[sim_player_vehicle]
 mov eax,[rdx+r12*4]
 cmp eax,[sim_count]
 jae .fair_begin
 mov r9d,eax
 mov eax,r12d
 shl eax,5
 lea r8,[sim_vehicles]
 add r8,rax
 cmp dword [r8+VEHICLE_ACTIVE],1
 jne .fair_begin
 cmp [r8+VEHICLE_ENTITY],r9d
 jne .fair_begin
 cmp [r8+VEHICLE_DRIVER],r12d
 jne .fair_begin
 lea rdx,[vehicle_driver_generation]
 mov eax,[rbx+PLAYER_GENERATION]
 cmp eax,[rdx+r12*4]
 jne .fair_begin
 lea rdx,[vehicle_entity_driver]
 cmp [rdx+r9*4],r12d
 jne .fair_begin
 mov eax,r9d
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_SIDE],0
 jne .fair_begin
 cmp dword [rdx+ENTITY_KIND],1
 jne .fair_begin
 cmp dword [rdx+ENTITY_HP],0
 je .fair_begin
 mov eax,[rdx+ENTITY_GENERATION]
 cmp eax,[r8+VEHICLE_ENTITY_GENERATION]
 jne .fair_begin
 mov [rsp],r9d
 ; Reserve at most four entries for freshest actual moving owned cannon rounds.
 ; The remaining >=14 entries retain the original fair ring/tombstone stream.
.priority:
 mov dword [rsp+4],-1
 mov dword [rsp+8],0
 xor r15d,r15d
.priority_scan:
 mov eax,r15d
 shl eax,6
 lea rsi,[sim_projectiles]
 add rsi,rax
 cmp dword [rsi+PROJECTILE_ACTIVE],1
 jne .priority_next
 cmp dword [rsi+PROJECTILE_KIND],1
 jne .priority_next
 mov eax,[rsp]
 cmp [rsi+PROJECTILE_SOURCE],eax
 jne .priority_next
 shl eax,5
 lea rdx,[sim_entities]
 mov eax,[rdx+rax+ENTITY_GENERATION]
 cmp [rsi+PROJECTILE_SOURCE_GENERATION],eax
 jne .priority_next
 xor ecx,ecx
.priority_duplicate:
 cmp ecx,r14d
 jae .priority_interest
 mov eax,ecx
 shl eax,6
 lea rdx,[output+44]
 cmp [rdx+rax],r15d
 je .priority_next
 inc ecx
 jmp .priority_duplicate
.priority_interest:
 movss xmm0,[rsi+PROJECTILE_X]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[rsi+PROJECTILE_Z]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[interest2]
 ja .priority_next
 mov eax,[rsi+PROJECTILE_TTL]
 cmp eax,[rsp+8]
 jbe .priority_next
 mov [rsp+8],eax
 mov [rsp+4],r15d
.priority_next:
 inc r15d
 cmp r15d,PROJECTILE_CAPACITY
 jb .priority_scan
 mov eax,[rsp+4]
 cmp eax,-1
 je .fair_begin
 mov edx,r14d
 shl edx,6
 lea rdi,[output+44]
 add rdi,rdx
 mov [rdi],eax
 add rdi,4
 shl eax,6
 lea rsi,[sim_projectiles]
 add rsi,rax
 mov ecx,15
 rep movsd
 inc r14d
 cmp r14d,PROJECTILE_OWNED_PRIORITY_MAX
 jb .priority
.fair_begin:
 xor r15d,r15d
.scan:
 lea r8,[projectile_cursors]
 mov eax,[r8+r12*4]
 and eax,511
 mov r9d,eax
 inc eax
 mov [r8+r12*4],eax
 inc r15d
 shl r9d,6
 lea rsi,[sim_projectiles]
 add rsi,r9
 cmp dword [rsi+PROJECTILE_GENERATION],0
 je .skip
 ; Already prioritised slots must not occur twice in an atomic batch.
 mov r10d,r9d
 shr r10d,6
 xor ecx,ecx
.fair_duplicate:
 cmp ecx,r14d
 jae .fair_interest
 mov eax,ecx
 shl eax,6
 lea rdx,[output+44]
 cmp [rdx+rax],r10d
 je .skip
 inc ecx
 jmp .fair_duplicate
.fair_interest:
 movss xmm0,[rsi+PROJECTILE_X]
 subss xmm0,[rbx+PLAYER_X]
 mulss xmm0,xmm0
 movss xmm1,[rsi+PROJECTILE_Z]
 subss xmm1,[rbx+PLAYER_Z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[interest2]
 ja .skip
 mov eax,r14d
 shl eax,6
 lea rdi,[output+44]
 add rdi,rax
 shr r9d,6
 mov [rdi],r9d
 add rdi,4
 mov ecx,15
 rep movsd
 inc r14d
.skip:
 cmp r14d,PROJECTILE_WIRE_MAX
 jae .finish
 cmp r15d,PROJECTILE_CAPACITY
 jb .scan
.finish:
 test r14d,r14d
 jz .done
 mov [output+40],r14d
 imul esi,r14d,64
 add esi,44
 lea eax,[rsi-NET_HEADER]
 mov [output+32],eax
 mov rdi,r13
 call send_packet
.done:
 add rsp,24
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
; Global source-independent fair wreck stream, includes expiry tombstones.
; At most17 records/1196bytes; absent virgin slots skipped, no distance filter
; that could conceal a distant death or prevent late-join/full registry recovery.
send_wrecks:
 push rbp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov r12d,edi
 mov r13,rsi
 mov edi,NET_WRECKS
 mov esi,r12d
 xor edx,edx
 call header
 xor r14d,r14d
 xor r15d,r15d
.scan:
 lea r8,[wreck_cursors]
 mov ebx,[r8+r12*4]
 and ebx,WRECK_CAPACITY-1
 lea eax,[rbx+1]
 mov [r8+r12*4],eax
 inc r15d
 mov eax,ebx
 shl eax,6
 lea rsi,[sim_wrecks]
 add rsi,rax
 cmp dword [rsi+WRECK_SEQUENCE],0
 je .next
 imul eax,r14d,WRECK_WIRE_STRIDE
 lea rdi,[output+NET_HEADER]
 add rdi,rax
 mov [rdi],ebx
 add rdi,4
 mov ecx,8
 rep movsq
 inc r14d
.next:
 cmp r14d,WRECK_WIRE_MAX
 jae .send
 cmp r15d,WRECK_CAPACITY
 jb .scan
.send:
 test r14d,r14d
 jz .done
 imul esi,r14d,WRECK_WIRE_STRIDE
 mov [output+32],esi
 add esi,NET_HEADER
 mov rdi,r13
 call send_packet
.done:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
section .note.GNU-stack noalloc noexec nowrite progbits

section .text
; Complete bounded own-allied company assignments/intents, no enemy truth.
send_companies:
 push rbx
 push r12
 push r13
 mov rbx,rsi
 mov esi,edi
 mov edi,NET_COMPANIES
 mov edx,COMPANY_REMOTE_PAYLOAD
 call header
 mov dword [output+40],COMPANY_REMOTE_COUNT
 xor r12d,r12d
 lea r13,[output+44]
.loop:
 mov rdi,r13
 xor eax,eax
 mov ecx,5
 rep stosq
 mov [r13],r12d
 mov dword [r13+4],-1
 mov eax,r12d
 shl eax,4
 lea rdx,[player_companies]
 mov eax,[rdx+rax+8]
 mov [r13+12],eax
 mov edi,r12d
 call company_for_player
 cmp eax,-1
 je .next
 mov [r13+4],eax
 shl eax,5
 lea rdx,[company_controls]
 add rdx,rax
 mov eax,[rdx+4]
 mov [r13+8],eax
 mov rax,[rdx+8]
 mov [r13+16],rax
 mov rax,[rdx+16]
 mov [r13+24],rax
 mov rax,[rdx+24]
 mov [r13+32],rax
.next:
 add r13,COMPANY_REMOTE_STRIDE
 inc r12d
 cmp r12d,COMPANY_REMOTE_COUNT
 jb .loop
 lea rsi,[company_transfers]
 mov rdi,r13
 mov ecx,COMPANY_TRANSFER_PLAYERS*COMPANY_TRANSFER_STRIDE/8
 rep movsq
 mov rdi,rbx
 mov esi,NET_HEADER+COMPANY_REMOTE_PAYLOAD
 call send_packet
 pop r13
 pop r12
 pop rbx
 ret

section .note.GNU-stack noalloc noexec nowrite progbits
