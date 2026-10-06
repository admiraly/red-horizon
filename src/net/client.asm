; Actual gameplay network adapter. SysV x86-64; fixed bounded buffers.
default rel
%include "schemas/player.inc"
%include "schemas/aircraft.inc"
%include "schemas/ground_motion.inc"
%include "schemas/combat.inc"
%include "schemas/wreck_remote.inc"
%include "schemas/company_remote.inc"
extern net_company_reset,net_company_receive
extern wreck_receive,wreck_remote_reset,wreck_remote_expire
%include "src/net/protocol.inc"
extern sim_ground_motion
extern sim_aircraft
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
air_min_y: dd -100.0
air_max_y: dd 1200.0
air_heading: dd 6.4
air_angle: dd 1.6
air_speed: dd 10.0
ground_speed: dd 0.61
ground_turn: dd 0.1
ground_velocity2: dd 0.373321
projectile_velocity: dd 1000.0
projectile_horizon: dd 120.0
fixed_rate: dd 30.0
projectile_gravity: dd 0.0109
half: dd 0.5
tick_one: dd 1.0
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
air_tick: resd 32768
ground_tick: resd 32768
ground_dead_generation: resd 32768
global net_projectiles, net_projectile_count
net_projectiles: resb PROJECTILE_CAPACITY*PROJECTILE_STRIDE
net_projectile_count: resd 1
projectile_tick: resd PROJECTILE_CAPACITY
projectile_age: resd PROJECTILE_CAPACITY
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
 lea rdi,[air_tick]
 mov ecx,32768
 rep stosd
 call wreck_remote_reset
 call net_company_reset
 call reset_ground
 lea rdi,[sim_aircraft]
 mov ecx,32768*AIR_STRIDE/8
 rep stosq
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
 test esi,~127
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
 cmp dword [incoming+16],NET_COMPANIES
 je .companies
 cmp dword [incoming+16],NET_ENTITIES
 je .entities
 cmp dword [incoming+16],NET_WRECKS
 je .wrecks
 cmp dword [incoming+16],NET_GROUND
 je .ground
 cmp dword [incoming+16],NET_AIRCRAFT
 je .aircraft
 cmp dword [incoming+16],NET_PROJECTILES
 je .projectiles
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
.companies:
 cmp dword [incoming+32],COMPANY_REMOTE_PAYLOAD
 jne .next
 cmp dword [incoming+40],COMPANY_REMOTE_COUNT
 jne .next
 lea rdi,[incoming+44]
 mov esi,COMPANY_REMOTE_COUNT
 mov edx,[incoming+28]
 call net_company_receive
 test eax,eax
 jnz .next
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
 cmp dword [r15+12],0
 je .sparsegroundalive
 cmp dword [r15+20],1
 jb .sparsegroundalive
 cmp dword [r15+20],2
 ja .sparsegroundalive
 mov eax,[r15]
 lea rdx,[ground_dead_generation]
 mov ecx,[r15+32]
 cmp ecx,[rdx+rax*4]
 je .nextrecord
.sparsegroundalive:
 ; Same/older sparse chunks cannot undo a self-contained hull pose/XZ.
 mov eax,[r15]
 mov edx,eax
 shl edx,5
 lea r9,[sim_ground_motion]
 cmp dword [r9+rdx+GROUND_GENERATION],0
 je .checkairpriority
 lea rdx,[ground_tick]
 mov ecx,[rdx+rax*4]
 cmp ecx,[incoming+28]
 jb .checkairpriority
 mov ecx,[r15+32]
 cmp ecx,[rdi+28]
 jbe .nextrecord
.checkairpriority:
 ; An air64 refresh wins against same/older-tick sparse entity chunks.
 mov eax,[r15]
 lea rdx,[air_tick]
 mov ecx,[rdx+rax*4]
 test ecx,ecx
 jz .entitystamp
 cmp ecx,[incoming+28]
 jb .entitystamp
 mov ecx,[r15+32]
 cmp ecx,[rdi+28]
 jbe .nextrecord
.entitystamp:
 lea rdx,[entity_tick]
 mov ecx,[incoming+28]
 mov [rdx+rax*4],ecx
 ; Clear obsolete poses when a newer generation or ground kind replaces it.
 mov ecx,[r15+32]
 cmp ecx,[rdi+28]
 jne .clearpose
 cmp dword [r15+20],3
 jne .clearpose
 cmp dword [r15+12],0
 jne .copyentity
.clearpose:
 shl eax,6
 lea rdx,[sim_aircraft]
 mov dword [rdx+rax+AIR_FLAGS],0
.copyentity:
 mov eax,[r15]
 shl eax,5
 lea rdx,[sim_ground_motion]
 add rdx,rax
 mov ecx,[r15+32]
 cmp ecx,[rdx+GROUND_GENERATION]
 jne .clearground
 mov ecx,[r15+20]
 cmp ecx,[rdx+GROUND_KIND]
 jne .clearground
 cmp dword [r15+12],0
 jne .copygroundentity
.clearground:
 mov dword [rdx+GROUND_FLAGS],0
.copygroundentity:
 mov eax,[r15]
 lea rdx,[ground_dead_generation]
 xor ecx,ecx
 cmp dword [r15+20],1
 jb .sparsedeathstamp
 cmp dword [r15+20],2
 ja .sparsedeathstamp
 cmp dword [r15+12],0
 jne .sparsedeathstamp
 mov ecx,[r15+32]
.sparsedeathstamp:
 mov [rdx+rax*4],ecx
 lea rsi,[r15+4]
 mov ecx,4
 rep movsq
.nextrecord:
 add r15,36
 dec r14d
 jmp .records
; Self-contained ground64: validate the complete batch before any mutation.
.wrecks:
 lea rdi,[incoming+NET_HEADER]
 mov esi,[incoming+32]
 mov edx,[incoming+28]
 call wreck_receive
 test eax,eax
 js .next
 jmp .accepted
.ground:
 cmp dword [incoming+32],4
 jb .next
 mov r14d,[incoming+40]
 cmp r14d,18
 ja .next
 imul eax,r14d,64
 add eax,4
 cmp eax,[incoming+32]
 jne .next
 lea r15,[incoming+44]
.validateground:
 test r14d,r14d
 jz .groundvalid
 mov eax,[r15]
 cmp eax,[sim_count]
 jae .next
 lea rsi,[incoming+44]
.groundduplicates:
 cmp rsi,r15
 jae .groundunique
 cmp eax,[rsi]
 je .next
 add rsi,64
 jmp .groundduplicates
.groundunique:
 cmp dword [r15+32],0
 je .next
 cmp dword [r15+16],1
 ja .next
 mov eax,[r15+20]
 cmp eax,1
 jb .next
 cmp eax,2
 ja .next
 mov ecx,400
 cmp eax,1
 je .groundhp
 mov ecx,160
.groundhp:
 cmp [r15+12],ecx
 ja .next
 cmp dword [r15+24],2
 ja .next
 mov eax,[r15+28]
 cmp eax,-1
 je .groundtarget
 cmp eax,[sim_count]
 jae .next
.groundtarget:
 cmp dword [r15+60],0
 jne .next
 xor eax,eax
 cmp dword [r15+12],0
 setne al
 cmp eax,[r15+56]
 jne .next
 lea rsi,[r15+4]
 mov ecx,2
.groundxz:
 mov eax,[rsi]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .next
 movss xmm0,[rsi]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[maximum]
 ja .next
 add rsi,4
 loop .groundxz
 lea rsi,[r15+36]
 mov ecx,5
.groundfinite:
 mov eax,[rsi]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .next
 add rsi,4
 loop .groundfinite
 mov eax,[r15+36]
 and eax,0x7fffffff
 movd xmm0,eax
 ucomiss xmm0,[air_heading]
 ja .next
 mov eax,[r15+40]
 and eax,0x7fffffff
 movd xmm0,eax
 ucomiss xmm0,[ground_speed]
 ja .next
 mov eax,[r15+44]
 and eax,0x7fffffff
 movd xmm0,eax
 ucomiss xmm0,[ground_turn]
 ja .next
 movss xmm0,[r15+48]
 mulss xmm0,xmm0
 movss xmm1,[r15+52]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[ground_velocity2]
 ja .next
 add r15,64
 dec r14d
 jmp .validateground
.groundvalid:
 mov r14d,[incoming+40]
 lea r15,[incoming+44]
.applyground:
 test r14d,r14d
 jz .accepted
 mov eax,[r15]
 lea rdx,[entity_tick]
 lea r8,[ground_tick]
 mov ecx,[incoming+28]
 cmp ecx,[rdx+rax*4]
 jb .nextground
 cmp ecx,[r8+rax*4]
 jb .nextground
 mov edi,eax
 shl edi,5
 lea r9,[sim_entities]
 add rdi,r9
 mov esi,[r15+32]
 cmp esi,[rdi+28]
 jb .nextground
 ja .groundgeneration
 ; Explicit wire tombstones, rather than interest-hidden HP, establish death.
 cmp dword [r15+12],0
 je .groundkindvalid
 lea r9,[ground_dead_generation]
 mov esi,[r15+32]
 cmp esi,[r9+rax*4]
 je .nextground
.groundkindvalid:
 cmp dword [rdx+rax*4],0
 je .groundgeneration
 mov esi,[r15+20]
 cmp esi,[rdi+16]
 jne .nextground
.groundgeneration:
 lea r9,[ground_dead_generation]
 xor esi,esi
 cmp dword [r15+12],0
 jne .grounddeathstamp
 mov esi,[r15+32]
.grounddeathstamp:
 mov [r9+rax*4],esi
 mov [rdx+rax*4],ecx
 mov [r8+rax*4],ecx
 mov r10d,eax
 lea rsi,[r15+4]
 mov ecx,4
 rep movsq
 shl r10d,5
 lea rdi,[sim_ground_motion]
 add rdi,r10
 lea rsi,[r15+36]
 mov ecx,5
 rep movsd
 mov eax,[r15+32]
 stosd
 mov eax,[r15+20]
 stosd
 mov eax,[r15+56]
 stosd
.nextground:
 add r15,64
 dec r14d
 jmp .applyground

; Self-contained air64 records warm up and refresh independently of sparse
; ground chunks. Validate all entity/pose fields before writing either array.
.aircraft:
 cmp dword [incoming+32],4
 jb .next
 mov r14d,[incoming+40]
 cmp r14d,18
 ja .next
 imul eax,r14d,64
 add eax,4
 cmp eax,[incoming+32]
 jne .next
 lea r15,[incoming+44]
.validateair:
 test r14d,r14d
 jz .airvalid
 mov eax,[r15]
 cmp eax,[sim_count]
 jae .next
 cmp dword [r15+32],0
 je .next
 cmp dword [r15+12],200
 ja .next
 cmp dword [r15+16],1
 ja .next
 cmp dword [r15+20],3
 jne .next
 cmp dword [r15+24],2
 ja .next
 mov eax,[r15+28]
 cmp eax,-1
 je .targetvalid
 cmp eax,[sim_count]
 jae .next
.targetvalid:
 lea rsi,[r15+4]
 mov ecx,2
.validatexz:
 mov eax,[rsi]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .next
 movss xmm0,[rsi]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[maximum]
 ja .next
 add rsi,4
 loop .validatexz
 lea rsi,[r15+36]
 mov ecx,5
.finiteair:
 mov eax,[rsi]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .next
 add rsi,4
 loop .finiteair
 movss xmm0,[r15+36]
 ucomiss xmm0,[air_min_y]
 jb .next
 ucomiss xmm0,[air_max_y]
 ja .next
 mov eax,[r15+40]
 and eax,0x7fffffff
 movd xmm0,eax
 ucomiss xmm0,[air_heading]
 ja .next
 mov eax,[r15+44]
 and eax,0x7fffffff
 movd xmm0,eax
 ucomiss xmm0,[air_angle]
 ja .next
 mov eax,[r15+48]
 and eax,0x7fffffff
 movd xmm0,eax
 ucomiss xmm0,[air_angle]
 ja .next
 movss xmm0,[r15+52]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[air_speed]
 ja .next
 cmp dword [r15+56],AIR_FIGHTER
 ja .next
 cmp dword [r15+60],AIR_RETURN
 ja .next
 add r15,64
 dec r14d
 jmp .validateair
.airvalid:
 mov r14d,[incoming+40]
 lea r15,[incoming+44]
.applyair:
 test r14d,r14d
 jz .accepted
 mov eax,[r15]
 lea rdx,[entity_tick]
 mov ecx,[incoming+28]
 cmp ecx,[rdx+rax*4]
 jb .nextair
 lea r8,[air_tick]
 cmp ecx,[r8+rax*4]
 jb .nextair
 mov edi,eax
 shl edi,5
 lea r9,[sim_entities]
 add rdi,r9
 mov esi,[r15+32]
 cmp esi,[rdi+28]
 jb .nextair
 ja .generationvalid
 cmp dword [rdx+rax*4],0
 je .generationvalid
 cmp dword [rdi+16],3
 jne .nextair
.generationvalid:
 mov [rdx+rax*4],ecx
 mov [r8+rax*4],ecx
 mov r10d,eax
 lea rsi,[r15+4]
 mov ecx,4
 rep movsq
 shl r10d,6
 lea rdi,[sim_aircraft]
 add rdi,r10
 mov eax,[r15+32]
 mov [rdi+AIR_GENERATION],eax
 xor eax,eax
 cmp dword [r15+12],0
 je .airflags
 mov eax,AIR_ACTIVE
.airflags:
 mov [rdi+AIR_FLAGS],eax
 lea rsi,[r15+36]
 mov ecx,7
 rep movsd
.nextair:
 add r15,64
 dec r14d
 jmp .applyair
 ; Whole trajectory packet validates before any slot or tick changes.
.projectiles:
 cmp dword [incoming+32],4
 jb .next
 mov r14d,[incoming+40]
 cmp r14d,18
 ja .next
 imul eax,r14d,64
 add eax,4
 cmp eax,[incoming+32]
 jne .next
 lea r15,[incoming+44]
 xor r9d,r9d
.validateprojectile:
 test r14d,r14d
 jz .projectilesvalid
 mov eax,[r15]
 cmp eax,PROJECTILE_CAPACITY
 jae .next
 ; Fair cursor wrap is legal; duplicate indices in one batch are not.
 lea rdx,[incoming+44]
.checkduplicate:
 cmp rdx,r15
 je .uniqueprojectile
 cmp eax,[rdx]
 je .next
 add rdx,64
 jmp .checkduplicate
.uniqueprojectile:
 cmp dword [r15+52],0
 je .next
 cmp dword [r15+56],1
 ja .next
 cmp dword [r15+32],1
 ja .next
 mov eax,[r15+36]
 dec eax
 cmp eax,3
 ja .next
 cmp dword [r15+28],240
 ja .next
 cmp dword [r15+56],0
 je .ttlvalid
 cmp dword [r15+28],0
 je .next
.ttlvalid:
 cmp dword [r15+60],0
 je .next
 mov eax,[r15+48]
 cmp eax,[sim_count]
 jae .next
 lea rsi,[r15+4]
 mov ecx,6
.finiteprojectile:
 mov eax,[rsi]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .next
 add rsi,4
 loop .finiteprojectile
 movss xmm0,[r15+4]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[maximum]
 ja .next
 movss xmm0,[r15+12]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[maximum]
 ja .next
 movss xmm0,[r15+8]
 ucomiss xmm0,[minimum_y]
 jb .next
 ucomiss xmm0,[maximum_y]
 ja .next
 lea rsi,[r15+16]
 mov ecx,3
.velocityprojectile:
 mov eax,[rsi]
 and eax,0x7fffffff
 movd xmm0,eax
 ucomiss xmm0,[projectile_velocity]
 ja .next
 add rsi,4
 loop .velocityprojectile
 mov eax,[r15+44]
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .next
 movss xmm0,[r15+44]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[maximum_radius]
 ja .next
 add r15,64
 dec r14d
 jmp .validateprojectile
.projectilesvalid:
 mov r14d,[incoming+40]
 lea r15,[incoming+44]
.applyprojectile:
 test r14d,r14d
 jz .accepted
 mov eax,[r15]
 lea rdx,[projectile_tick]
 mov ecx,[incoming+28]
 cmp ecx,[rdx+rax*4]
 jbe .nextprojectile
 ; Refuse delayed samples beyond the bounded prediction horizon.
 mov r8d,[net_server_tick]
 sub r8d,ecx
 jbe .projectiletime
 cmp r8d,120
 ja .nextprojectile
.projectiletime:
 mov r8d,eax
 shl r8d,6
 lea rdi,[net_projectiles]
 add rdi,r8
 mov esi,[r15+52]
 cmp esi,[rdi+PROJECTILE_GENERATION]
 jb .nextprojectile
 ; Once dead/expired, equal generation cannot resurrect from late alive data.
 ja .newprojectilegeneration
 cmp dword [rdi+PROJECTILE_ACTIVE],0
 je .nextprojectile
.newprojectilegeneration:
 mov [rdx+rax*4],ecx
 lea rdx,[projectile_age]
 mov dword [rdx+rax*4],0
 lea rsi,[r15+4]
 mov ecx,15
 rep movsd
 mov dword [rdi],0
.nextprojectile:
 add r15,64
 dec r14d
 jmp .applyprojectile
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
 cmp eax,8
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
 call reset_projectiles
 call wreck_remote_reset
 call net_company_reset
 call reset_ground
.retry:
 cmp dword [pending_len],0
 je .expire
 mov rax,r14
 sub rax,[last_send]
 cmp rax,100
 jb .expire
 call transmit
.expire:
 mov edi,[net_server_tick]
 call wreck_remote_expire
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
 call wreck_remote_reset
 call net_company_reset
 call reset_ground
 call reset_projectiles
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
; Cosmetic-only render update. Velocities are metres per authoritative 30Hz tick.
; Lifetimes expire even when no packets arrive; no damage/contact authority here.
global net_projectiles_update
net_projectiles_update:
 mov eax,[net_connected]
 test eax,eax
 jz reset_projectiles
 movd eax,xmm0
 and eax,0x7fffffff
 cmp eax,0x7f800000
 jae .done
 ucomiss xmm0,[zero]
 jb .done
 mulss xmm0,[fixed_rate]
 movaps xmm6,xmm0
 lea rdi,[net_projectiles]
 lea rsi,[projectile_age]
 lea rdx,[projectile_tick]
 xor r8d,r8d
 mov ecx,PROJECTILE_CAPACITY
.loop:
 cmp dword [rdi+PROJECTILE_ACTIVE],0
 je .next
 movss xmm3,[rsi]
 movaps xmm0,xmm3
 addss xmm0,xmm6
 ; Catch up delayed samples to the most recent received authority tick.
 mov eax,[net_server_tick]
 sub eax,[rdx]
 cvtsi2ss xmm1,eax
 maxss xmm0,xmm1
 movss [rsi],xmm0
 ucomiss xmm0,[projectile_horizon]
 jae .expire
 cvtsi2ss xmm1,dword [rdi+PROJECTILE_TTL]
 ucomiss xmm0,xmm1
 jae .expire
 movaps xmm7,xmm0
 subss xmm7,xmm3
 movss xmm0,[rdi+PROJECTILE_VX]
 mulss xmm0,xmm7
 addss xmm0,[rdi+PROJECTILE_X]
 movss [rdi+PROJECTILE_X],xmm0
 movss xmm0,[rdi+PROJECTILE_VZ]
 mulss xmm0,xmm7
 addss xmm0,[rdi+PROJECTILE_Z]
 movss [rdi+PROJECTILE_Z],xmm0
 movss xmm0,[rdi+PROJECTILE_VY]
 mulss xmm0,xmm7
 cmp dword [rdi+PROJECTILE_KIND],2
 je .gravity
 cmp dword [rdi+PROJECTILE_KIND],3
 jne .linear
.gravity:
 movaps xmm1,xmm7
 mulss xmm1,[projectile_gravity]
 movss xmm2,[rdi+PROJECTILE_VY]
 subss xmm2,xmm1
 movss [rdi+PROJECTILE_VY],xmm2
 ; Authoritative tick advances position before subtracting gravity.
 movaps xmm2,xmm7
 subss xmm2,[tick_one]
 mulss xmm1,xmm2
 mulss xmm1,[half]
 subss xmm0,xmm1
.linear:
 addss xmm0,[rdi+PROJECTILE_Y]
 movss [rdi+PROJECTILE_Y],xmm0
 inc r8d
 jmp .next
.expire:
 mov dword [rdi+PROJECTILE_ACTIVE],0
.next:
 add rdi,PROJECTILE_STRIDE
 add rsi,4
 add rdx,4
 dec ecx
 jnz .loop
 mov [net_projectile_count],r8d
.done:
 ret
reset_projectiles:
 lea rdi,[net_projectiles]
 xor eax,eax
 mov ecx,PROJECTILE_CAPACITY*PROJECTILE_STRIDE/8
 rep stosq
 lea rdi,[projectile_tick]
 mov ecx,PROJECTILE_CAPACITY*2
 rep stosd
 mov dword [net_projectile_count],0
 ret
reset_ground:
 lea rdi,[ground_tick]
 xor eax,eax
 mov ecx,32768
 rep stosd
 lea rdi,[ground_dead_generation]
 mov ecx,32768
 rep stosd
 lea rdi,[sim_ground_motion]
 mov ecx,32768*GROUND_STRIDE/8
 rep stosq
 ret

section .note.GNU-stack noalloc noexec nowrite progbits
