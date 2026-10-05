default rel
%include "schemas/combat.inc"
%include "schemas/aircraft.inc"
extern hazard_metrics,ordnance_metrics,air_admission_metrics,crowd_metrics
extern sim_scenario
extern sim_init, sim_tick, sim_checksum, sim_count, sim_alive, sim_engaged
extern sim_requisition, sim_supply, sim_operation_state
extern sim_projectile_count, sim_projectile_dropped
extern sim_events,sim_event_sequence,nav_metrics
extern strcmp, strtoul, printf, puts, clock_gettime, clock_nanosleep, qsort
section .rodata
arg_scenario: db '--scenario',0
air_battle_name: db 'air-battle',0
scale_front_name: db 'scale-front',0
scale_hotspot_name: db 'scale-hotspot',0
scale_open_name: db 'scale-open',0
arg_realtime: db '--realtime',0
arg_units: db '--units',0
arg_ticks: db '--ticks',0
arg_seed: db '--seed',0
usage: db 'Usage: red-horizon-headless [--units EVEN_2..32768] [--ticks 1..100000] [--seed 0..4294967295] [--realtime] [--scenario scale-open|air-battle|scale-front|scale-hotspot]',0
fmt: db '{"units":%u,"ticks":%u,"seed":%u,"alive":[%u,%u],"engaged":%u,"checksum":"%016lx","tick_mean_ms":%.6f,"tick_p95_ms":%.6f,"operation_state":%u,"requisition":[%u,%u],"supply":[%u,%u],"projectiles":%u,"projectile_peak":%u,"projectile_dropped":%u,"navigation":{"pending":%u,"completed":%u,"overflow":%u,"cache_hits":%u,"stuck_replans":%u,"cover_choices":%u,"processed_last_tick":%u,"processed_max":%u},"air_events":{"bomb_launches":%u,"bomb_impacts":%u,"gun_bursts":%u,"aircraft_destroyed":%u,"overwritten_unobserved":%u},"hazards":{"predictions":%lu,"tile_overflow":%lu,"acquired":%lu,"dispersions":%lu,"shelters":%lu,"los_calls":%lu,"budget_skipped":%lu,"active_goals":%lu},"ordnance_admission":[{"submitted":%lu,"admitted":%lu,"capacity_denied":%lu,"invalidated":%lu},{"submitted":%lu,"admitted":%lu,"capacity_denied":%lu,"invalidated":%lu},{"submitted":%lu,"admitted":%lu,"capacity_denied":%lu,"invalidated":%lu},{"submitted":%lu,"admitted":%lu,"capacity_denied":%lu,"invalidated":%lu}],"air_admission":[{"submitted":%lu,"admitted":%lu,"capacity_denied":%lu,"invalidated":%lu},{"submitted":%lu,"admitted":%lu,"capacity_denied":%lu,"invalidated":%lu},{"submitted":%lu,"admitted":%lu,"capacity_denied":%lu,"invalidated":%lu},{"submitted":%lu,"admitted":%lu,"capacity_denied":%lu,"invalidated":%lu}],"crowd":{"snapshot_actors":%lu,"move_queries":%lu,"inspected_neighbors":%lu,"corrected_endpoints":%lu,"yielded_moves":%lu,"overlap_recoveries":%lu,"truncated_queries":%lu,"maximum_inspected_per_query":%lu}}',10,0
million: dq 1000000.0
section .bss
samples: resq 100000
deadline: resq 2
projectile_peak: resd 1
scenario_mode: resd 1
scenario_seen: resd 1
event_cursor: resd 1
event_counts: resd 10
events_unobserved: resd 1
section .text
global main
main:
 push rbx
 push rbp
 push r12
 push r13
 push r14
 push r15
 sub rsp,584
 mov r12d,edi
 mov r13,rsi
 mov r14d,8192
 mov r15d,600
 mov ebp,1
 mov ebx,1
 mov dword [rsp+52],0
.parse:
 cmp ebx,r12d
 jae .init
 mov rdi,[r13+rbx*8]
 lea rsi,[arg_realtime]
 call strcmp
 test eax,eax
 jnz .pair
 mov dword [rsp+52],1
 inc ebx
 jmp .parse
.pair:
 mov eax,ebx
 inc eax
 cmp eax,r12d
 jae .bad
 mov rdi,[r13+rbx*8]
 lea rsi,[arg_scenario]
 call strcmp
 test eax,eax
 jz .scenario
 mov rdi,[r13+rbx*8]
 lea rsi,[arg_units]
 call strcmp
 test eax,eax
 jz .units
 mov rdi,[r13+rbx*8]
 lea rsi,[arg_ticks]
 call strcmp
 test eax,eax
 jz .ticks
 mov rdi,[r13+rbx*8]
 lea rsi,[arg_seed]
 call strcmp
 test eax,eax
 jnz .bad
 mov dword [rsp+48],2
 jmp .value
.scenario:
 cmp dword [scenario_seen],0
 jne .bad
 mov dword [scenario_seen],1
 mov rdi,[r13+rbx*8+8]
 lea rsi,[air_battle_name]
 call strcmp
 test eax,eax
 jnz .frontscenario
 mov dword [scenario_mode],1
 jmp .parsed
.frontscenario:
 mov rdi,[r13+rbx*8+8]
 lea rsi,[scale_front_name]
 call strcmp
 test eax,eax
 jnz .hotspotscenario
 mov dword [scenario_mode],2
 jmp .parsed
.hotspotscenario:
 mov rdi,[r13+rbx*8+8]
 lea rsi,[scale_hotspot_name]
 call strcmp
 test eax,eax
 jnz .defaultscenario
 mov dword [scenario_mode],3
 jmp .parsed
.defaultscenario:
 mov rdi,[r13+rbx*8+8]
 lea rsi,[scale_open_name]
 call strcmp
 test eax,eax
 jnz .bad
 mov dword [scenario_mode],0
 jmp .parsed
.units: mov dword [rsp+48],0
 jmp .value
.ticks: mov dword [rsp+48],1
.value:
 mov rdi,[r13+rbx*8+8]
 cmp byte [rdi],'0'
 jb .bad
 cmp byte [rdi],'9'
 ja .bad
 lea rsi,[rsp+56]
 mov edx,10
 call strtoul
 mov rcx,[rsp+56]
 cmp byte [rcx],0
 jne .bad
 mov ecx,0xffffffff
 cmp rax,rcx
 ja .bad
 cmp dword [rsp+48],0
 je .set_units
 cmp dword [rsp+48],1
 je .set_ticks
 mov ebp,eax
 jmp .parsed
.set_units: mov r14d,eax
 jmp .parsed
.set_ticks:
 test eax,eax
 jz .bad
 cmp eax,100000
 ja .bad
 mov r15d,eax
.parsed:
 add ebx,2
 jmp .parse
.init:
 mov edi,r14d
 mov esi,ebp
 call sim_init
 test eax,eax
 jnz .bad
 mov edi,[scenario_mode]
 call sim_scenario
 test eax,eax
 jnz .bad
 xor ebx,ebx
 mov qword [rsp+64],0
 mov edi,1
 lea rsi,[deadline]
 call clock_gettime
 test eax,eax
 jnz .bad
.tick:
 mov edi,1
 lea rsi,[rsp]
 call clock_gettime
 test eax,eax
 jnz .bad
 call sim_tick
 mov eax,[sim_projectile_count]
 cmp eax,[projectile_peak]
 jbe .peakrecorded
 mov [projectile_peak],eax
.peakrecorded:
 mov edi,1
 lea rsi,[rsp+16]
 call clock_gettime
 test eax,eax
 jnz .bad
 mov rax,[rsp+16]
 sub rax,[rsp]
 imul rax,1000000000
 add rax,[rsp+24]
 sub rax,[rsp+8]
 lea rcx,[samples]
 mov [rcx+rbx*8],rax
 add [rsp+64],rax
 call collect_events
 cmp dword [rsp+52],0
 je .next_tick
 add qword [deadline+8],33333333
 cmp qword [deadline+8],1000000000
 jb .sleep
 sub qword [deadline+8],1000000000
 inc qword [deadline]
.sleep:
 mov edi,1
 mov esi,1
 lea rdx,[deadline]
 xor ecx,ecx
 call clock_nanosleep
 cmp eax,4
 je .sleep
 test eax,eax
 jnz .bad
.next_tick:
 inc ebx
 cmp ebx,r15d
 jb .tick
 lea rdi,[samples]
 mov esi,r15d
 mov edx,8
 lea rcx,[compare_ns]
 call qsort
 mov eax,r15d
 dec eax
 imul eax,95
 xor edx,edx
 mov ecx,100
 div ecx
 lea rcx,[samples]
 cvtsi2sd xmm1,qword [rcx+rax*8]
 divsd xmm1,[million]
 cvtsi2sd xmm0,qword [rsp+64]
 cvtsi2sd xmm2,r15d
 divsd xmm0,xmm2
 divsd xmm0,[million]
 movsd [rsp+32],xmm0
 movsd [rsp+40],xmm1
 call sim_checksum
 ; Seven integer args: checksum and engaged exceed register argument slots.
 mov [rsp+8],rax
 mov eax,[sim_engaged]
 mov [rsp],rax
 lea rdi,[fmt]
 mov esi,r14d
 mov edx,r15d
 mov ecx,ebp
 mov r8d,[sim_alive]
 mov r9d,[sim_alive+4]
 movsd xmm0,[rsp+32]
 movsd xmm1,[rsp+40]
 mov eax,[sim_operation_state]
 mov [rsp+16],rax
 mov eax,[sim_requisition]
 mov [rsp+24],rax
 mov eax,[sim_requisition+4]
 mov [rsp+32],rax
 mov eax,[sim_supply]
 mov [rsp+40],rax
 mov eax,[sim_supply+4]
 mov [rsp+48],rax
 mov eax,[sim_projectile_count]
 mov [rsp+56],rax
 mov eax,[projectile_peak]
 mov [rsp+64],rax
 mov eax,[sim_projectile_dropped]
 mov [rsp+72],rax
 ; Additional read-only diagnostics are outside the timed simulation pass.
 lea rdx,[nav_metrics]
 mov ecx,8
 xor r10d,r10d
.nav_report:
 mov eax,[rdx+r10*4]
 mov [rsp+r10*8+80],rax
 inc r10d
 loop .nav_report
 mov eax,[event_counts+EVENT_BOMB_LAUNCH*4]
 mov [rsp+144],rax
 mov eax,[event_counts+EVENT_BOMB_IMPACT*4]
 mov [rsp+152],rax
 mov eax,[event_counts+EVENT_AIR_GUN*4]
 mov [rsp+160],rax
 mov eax,[event_counts+EVENT_AIR_DESTROYED*4]
 mov [rsp+168],rax
 mov eax,[events_unobserved]
 mov [rsp+176],rax
 lea rdx,[hazard_metrics]
 xor r10d,r10d
.hazard_report:
 mov rax,[rdx+r10*8]
 mov [rsp+r10*8+184],rax
 inc r10d
 cmp r10d,8
 jb .hazard_report
 lea rdx,[ordnance_metrics]
 xor r10d,r10d
.ordnance_report:
 mov rax,[rdx+r10*8]
 mov [rsp+r10*8+248],rax
 inc r10d
 cmp r10d,16
 jb .ordnance_report
 lea rdx,[air_admission_metrics]
 xor r10d,r10d
.air_admission_report:
 mov rax,[rdx+r10*8]
 mov [rsp+r10*8+376],rax
 inc r10d
 cmp r10d,16
 jb .air_admission_report
 lea rdx,[crowd_metrics]
 xor r10d,r10d
.crowd_report:
 mov rax,[rdx+r10*8]
 mov [rsp+r10*8+504],rax
 inc r10d
 cmp r10d,8
 jb .crowd_report
 ; Restore register varargs overwritten by diagnostic reads.
 mov edx,r15d
 mov ecx,ebp
 mov eax,2
 call printf
 xor eax,eax
 jmp .out
.bad:
 lea rdi,[usage]
 call puts
 mov eax,2
.out:
 add rsp,584
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
 ; Headless-only read observer: event losses are explicit, never guessed totals.
collect_events:
 mov ecx,[sim_event_sequence]
 mov eax,ecx
 sub eax,[event_cursor]
 cmp eax,EVENT_CAPACITY
 jbe .within
 sub eax,EVENT_CAPACITY
 add [events_unobserved],eax
 mov eax,ecx
 sub eax,EVENT_CAPACITY
 mov [event_cursor],eax
.within:
 mov edx,[event_cursor]
.loop:
 cmp edx,ecx
 jae .done
 inc edx
 mov eax,edx
 and eax,EVENT_CAPACITY-1
 shl eax,5
 lea rsi,[sim_events]
 add rsi,rax
 cmp [rsi+EVENT_SEQUENCE],edx
 jne .loop
 mov eax,[rsi+EVENT_KIND]
 cmp eax,9
 ja .loop
 lea rsi,[event_counts]
 inc dword [rsi+rax*4]
 jmp .loop
.done:
 mov [event_cursor],ecx
 ret
compare_ns:
 mov rax,[rdi]
 cmp rax,[rsi]
 mov eax,0
 je .done
 mov eax,1
 ja .done
 mov eax,-1
.done: ret
section .note.GNU-stack noalloc noexec nowrite progbits
