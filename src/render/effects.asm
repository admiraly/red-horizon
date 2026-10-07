; Allocation-free cosmetic pool. Reads authority; never modifies gameplay records.
default rel
%include "schemas/player.inc"
%include "schemas/combat.inc"
%include "schemas/aircraft.inc"
global effects_update,effects_records,effects_tracers,effects_active,effects_impacts,effects_event_cursor,effects_rifle_flashes,effects_particle_quads
extern sim_players,sinf,cosf
extern sim_player_vehicle
extern sim_events,sim_event_sequence,sim_tick_count
section .rodata
zero: dd 0.0
life: dd 0.14
reach: dd 100.0
forward: dd 3.0
right: dd 0.22
down: dd 0.25
rifle_life: dd 0.065
rifle_radius: dd 0.25
flash_life: dd 0.45
smoke_life: dd 2.5
air_smoke_life: dd 6.0
air_debris_life: dd 3.0
air_burst_radius: dd 8.0
min_radius: dd 1.5
max_radius: dd 12.0
view_range2: dd 490000.0
ticks_per_second: dd 30.0
max_dt: dd 0.25
section .bss
align 16
effects_records: resb 64*32 ; start xyz,remaining; end xyz,type1 tracer
seen_generation: resd 4
seen_shots: resd 4
next_slot: resd 1
effects_tracers: resd 1
effects_active: resd 1
effects_impacts: resd 1
effects_event_cursor: resd 1
effects_rifle_flashes: resd 1
effects_particle_quads: resd 1
view_x: resd 1
view_z: resd 1
dt: resd 1
sy: resd 1
cy: resd 1
pitch_sin: resd 1
cp: resd 1
section .text
; XMM0 elapsed render time. Counters observed exactly once despite repeated frames.
effects_update:
 push rbx
 push r12
 push r13
 and edi,3
 shl edi,6
 lea rax,[sim_players]
 movss xmm1,[rax+rdi+PLAYER_X]
 movss [view_x],xmm1
 movss xmm1,[rax+rdi+PLAYER_Z]
 movss [view_z],xmm1
 movd eax,xmm0
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .bad_dt
 ucomiss xmm0,[zero]
 jp .bad_dt
 jb .bad_dt
 minss xmm0,[max_dt]
 jmp .dt_ready
.bad_dt:
 xorps xmm0,xmm0
.dt_ready:
 movss [dt],xmm0
 lea rbx,[effects_records]
 mov ecx,64
 xor edx,edx
.decay:
 movss xmm1,[rbx+12]
 subss xmm1,xmm0
 maxss xmm1,[zero]
 movss [rbx+12],xmm1
 ucomiss xmm1,[zero]
 jbe .next
 inc edx
.next:
 add rbx,32
 loop .decay
 mov [effects_active],edx
 xor r12d,r12d
 lea r13,[sim_players]
.players:
 lea rdx,[seen_generation]
 lea rcx,[seen_shots]
 mov eax,[r13+PLAYER_GENERATION]
 cmp dword [r13+PLAYER_CONNECTED],0
 je .baseline
 cmp eax,[rdx+r12*4]
 jne .baseline
 lea rdx,[sim_player_vehicle]
 cmp dword [rdx+r12*4],0
 jge .baseline
 mov eax,[r13+PLAYER_SHOTS]
 cmp eax,[rcx+r12*4]
 jbe .baseline
 mov ebx,eax
 xor edx,edx
 mov esi,3
 div esi
 mov esi,eax
 mov eax,[rcx+r12*4]
 xor edx,edx
 mov edi,3
 div edi
 mov [rcx+r12*4],ebx
 cmp esi,eax
 je .advance
 ; Collapse skipped snapshot intervals to at most one current cosmetic tracer.
 call .tracer
 jmp .advance
.baseline:
 mov eax,[r13+PLAYER_GENERATION]
 lea rdx,[seen_generation]
 mov [rdx+r12*4],eax
 mov eax,[r13+PLAYER_SHOTS]
 lea rcx,[seen_shots]
 mov [rcx+r12*4],eax
.advance:
 add r13,PLAYER_STRIDE
 inc r12d
 cmp r12d,4
 jb .players
 call .events
 ; Count the finished pool, including records emitted this update.
 lea rbx,[effects_records]
 mov ecx,64
 xor edx,edx
 xor esi,esi
.recount:
 movss xmm0,[rbx+12]
 ucomiss xmm0,[zero]
 jbe .recount_next
 inc edx
 cmp dword [rbx+28],8
 je .smoke_quads
 cmp dword [rbx+28],9
 je .debris_quads
 inc esi
 jmp .recount_next
.smoke_quads:
 add esi,8
 jmp .recount_next
.debris_quads:
 add esi,16
.recount_next:
 add rbx,32
 loop .recount
 mov [effects_active],edx
 mov [effects_particle_quads],esi
 pop r13
 pop r12
 pop rbx
 ret
.tracer:
 push rbx
 movss xmm0,[r13+PLAYER_YAW]
 call sinf wrt ..plt
 movss [sy],xmm0
 movss xmm0,[r13+PLAYER_YAW]
 call cosf wrt ..plt
 movss [cy],xmm0
 movss xmm0,[r13+PLAYER_PITCH]
 call sinf wrt ..plt
 movss [pitch_sin],xmm0
 movss xmm0,[r13+PLAYER_PITCH]
 call cosf wrt ..plt
 movss [cp],xmm0
 mov eax,[next_slot]
 inc dword [next_slot]
 and dword [next_slot],63
 shl eax,5
 lea rbx,[effects_records]
 add rbx,rax
 movss xmm0,[sy]
 mulss xmm0,[cp]
 movss xmm1,[pitch_sin]
 movss xmm2,[cy]
 mulss xmm2,[cp]
 movaps xmm3,xmm0
 movaps xmm4,xmm1
 movaps xmm5,xmm2
 mulss xmm3,[reach]
 mulss xmm4,[reach]
 mulss xmm5,[reach]
 addss xmm3,[r13+PLAYER_X]
 addss xmm4,[r13+PLAYER_Y]
 addss xmm5,[r13+PLAYER_Z]
 movss [rbx+16],xmm3
 movss [rbx+20],xmm4
 movss [rbx+24],xmm5
 mulss xmm0,[forward]
 mulss xmm1,[forward]
 mulss xmm2,[forward]
 movss xmm3,[cy]
 mulss xmm3,[right]
 addss xmm0,xmm3
 movss xmm3,[sy]
 mulss xmm3,[right]
 subss xmm2,xmm3
 addss xmm0,[r13+PLAYER_X]
 addss xmm1,[r13+PLAYER_Y]
 subss xmm1,[down]
 addss xmm2,[r13+PLAYER_Z]
 movss [rbx],xmm0
 movss [rbx+4],xmm1
 movss [rbx+8],xmm2
 movss xmm0,[life]
 movss [rbx+12],xmm0
 mov dword [rbx+28],1
 inc dword [effects_tracers]
 pop rbx
 ret
; Consume only matching actual impact/destruction records, bounded to ring capacity.
.events:
 mov r12d,[sim_event_sequence]
 mov r13d,[effects_event_cursor]
 cmp r12d,r13d
 jb .reset
 mov eax,r12d
 sub eax,r13d
 cmp eax,256
 jbe .eventloop
 mov r13d,r12d
 sub r13d,256
.eventloop:
 cmp r13d,r12d
 jae .eventdone
 inc r13d
 mov eax,r13d
 and eax,255
 shl eax,5
 lea rbx,[sim_events]
 add rbx,rax
 cmp [rbx+EVENT_SEQUENCE],r13d
 jne .eventloop
 movss xmm0,[rbx]
 subss xmm0,[view_x]
 mulss xmm0,xmm0
 movss xmm1,[rbx+8]
 subss xmm1,[view_z]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[view_range2]
 ja .eventloop
 mov eax,[sim_tick_count]
 sub eax,[rbx+EVENT_TICK]
 cmp dword [rbx+EVENT_KIND],EVENT_AIR_DESTROYED
 jne .normal_age
 cmp eax,180
 ja .eventloop
 jmp .age_ready
.normal_age:
 cmp eax,60
 ja .eventloop
.age_ready:
 mov eax,[rbx+EVENT_KIND]
 cmp eax,EVENT_INFANTRY_RIFLE
 je .rifle
 cmp eax,EVENT_TANK_IMPACT
 jb .eventloop
 cmp eax,EVENT_AIR_DESTROYED
 ja .eventloop
 ; Age effects from the actual event tick: late packets never reignite a flash.
 mov eax,[sim_tick_count]
 sub eax,[rbx+EVENT_TICK]
 cvtsi2ss xmm2,eax
 divss xmm2,[ticks_per_second]
 movss xmm0,[flash_life]
 subss xmm0,xmm2
 ucomiss xmm0,[zero]
 jbe .smoke
 mov edx,2
 call .impact
.smoke:
 cmp dword [rbx+EVENT_KIND],EVENT_AIR_DESTROYED
 je .air_burst
 cmp dword [rbx+EVENT_KIND],EVENT_AIR_GUN
 je .countimpact
 movss xmm0,[smoke_life]
 subss xmm0,xmm2
 mov edx,3
 call .impact
 cmp dword [rbx+EVENT_KIND],EVENT_BOMB_IMPACT
 je .layers
 cmp dword [rbx+EVENT_KIND],EVENT_AIR_DESTROYED
 jne .countimpact
.layers:
 ; Additional real-event layers share the same bounded pool and actual age.
 movss xmm0,[smoke_life]
 subss xmm0,xmm2
 mov edx,3
 call .impact
 movss xmm0,[smoke_life]
 subss xmm0,xmm2
 mov edx,5 ; low expanding dust: ground bomb impact only
 cmp dword [rbx+EVENT_KIND],EVENT_AIR_DESTROYED
 je .debris
 call .impact
.debris:
 movss xmm0,[smoke_life]
 subss xmm0,xmm2
 mov edx,4
 call .impact
 call .impact
 call .impact
 call .impact
.air_burst:
 cmp dword [rbx+EVENT_KIND],EVENT_AIR_DESTROYED
 jne .countimpact
 ; Two records expand into eight smoke puffs and sixteen GPU debris/fire pieces.
 ; Actual event age drives both; no old packet can restart the hot flash.
 movss xmm0,[air_smoke_life]
 subss xmm0,xmm2
 mov edx,8
 call .impact
 movss xmm0,[air_debris_life]
 subss xmm0,xmm2
 ucomiss xmm0,[zero]
 jbe .countimpact
 mov edx,9
 call .impact
.countimpact:
 inc dword [effects_impacts]
 jmp .eventloop
.rifle:
 mov eax,[sim_tick_count]
 sub eax,[rbx+EVENT_TICK]
 cvtsi2ss xmm2,eax
 divss xmm2,[ticks_per_second]
 movss xmm0,[rifle_life]
 subss xmm0,xmm2
 ucomiss xmm0,[zero]
 jbe .eventloop
 mov edx,2
 call .impact
 inc dword [effects_rifle_flashes]
 jmp .eventloop
.reset:
 ; Scenario/ring reset clears old cosmetics before baselining the new stream.
 lea rdi,[effects_records]
 mov ecx,64
.clear_old:
 mov dword [rdi+12],0
 add rdi,32
 loop .clear_old
 mov r13d,r12d
.eventdone:
 mov [effects_event_cursor],r12d
 ret
.impact:
 mov eax,[next_slot]
 inc dword [next_slot]
 and dword [next_slot],63
 shl eax,5
 lea rdi,[effects_records]
 add rdi,rax
 mov eax,[rbx]
 mov [rdi],eax
 mov eax,[rbx+4]
 mov [rdi+4],eax
 mov eax,[rbx+8]
 mov [rdi+8],eax
 movss [rdi+12],xmm0
 cmp dword [rbx+EVENT_KIND],EVENT_INFANTRY_RIFLE
 jne .blast_radius
 movss xmm1,[rifle_radius]
 jmp .radius_ready
.blast_radius:
 movss xmm1,[rbx+EVENT_RADIUS]
 maxss xmm1,[min_radius]
 minss xmm1,[max_radius]
 cmp dword [rbx+EVENT_KIND],EVENT_BOMB_LAUNCH
 je .launch_radius
 cmp dword [rbx+EVENT_KIND],EVENT_AIR_GUN
 jne .radius_ready
.launch_radius:
 movss xmm1,[min_radius] ; release/muzzle smoke cannot resemble a ground impact
.radius_ready:
 cmp edx,8
 jb .radius_store
 movss xmm1,[air_burst_radius]
.radius_store:
 movss [rdi+16],xmm1
 mov dword [rdi+20],0
 cmp edx,8
 jb .seed_ready
 mov eax,[rbx+EVENT_SEQUENCE]
 mov [rdi+20],eax
.seed_ready:
 mov dword [rdi+24],0
 mov [rdi+28],edx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
