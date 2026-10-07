; Explicit initial encounter layouts. All combat/flight afterwards is production.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/player.inc"
default rel
extern player_deployment_set
extern sim_entities,sim_aircraft,sim_count,sim_tick_count,sim_players,terrain_height
section .bss
global scenario_air_selected,scenario_ground_selected
scenario_air_selected: resd 2
scenario_ground_selected: resd 2
scenario_mode: resd 1
section .rodata
column_step: dd 40.0
ground_step: dd 20.0
air_x: dd 3400.0
ground_x: dd 3300.0
air_z: dd 2100.0,3150.0
ground_z: dd 2450.0,2830.0
heading: dd 0.0,3.14159265
speeds: dd 5.0,7.0
altitude: dd 110.0,140.0
row_step: dd 50.0
minus: dd -1.0
player_x: dd 3500.0
player_z: dd 2000.0
deployment_air_z: dd 2300.0
eye: dd 1.8
dense_x: dd 3200.0
; Front: 64x20 broad lines; hotspot: 64x30 compact lines.
dense_spacing_x: dd 10.0,8.0
dense_spacing_z: dd 8.0,6.0
dense_z: dd 2400.0,2580.0,2400.0,2610.0
dense_player_x: dd 3515.0,3452.0
dense_player_z: dd 2280.0,2300.0
section .text
global sim_scenario
; EDI0 unchanged;1 air-battle;2 scale-front;3 scale-hotspot.
; Nonzero modes require a fresh world; dense modes retain >=8192 actors.
; Returns0/-1; invalid calls preserve authority. No weapon/event/pool writes.
sim_scenario:
 test edi,edi
 jz .unchanged
 cmp edi,3
 ja .invalid
 mov eax,2048
 cmp edi,1
 je .minimum
 mov eax,8192
.minimum:
 cmp dword [sim_count],eax
 jb .invalid
 cmp dword [sim_tick_count],0
 jne .invalid
 push rbx
 push rbp
 push r12
 push r13
 sub rsp,8
 mov [scenario_mode],edi
 mov qword [scenario_air_selected],0
 mov qword [scenario_ground_selected],0
 xor r12d,r12d
 lea rbx,[sim_entities]
.loop:
 mov r13d,[rbx+ENTITY_SIDE]
 cmp r13d,1
 ja .next
 cmp dword [rbx+ENTITY_KIND],3
 jne .ground
 lea rdx,[scenario_air_selected]
 mov eax,[rdx+r13*4]
 cmp eax,32
 jae .next
 inc dword [rdx+r13*4]
 mov edx,eax
 and edx,7
 cvtsi2ss xmm0,edx
 mulss xmm0,[column_step]
 addss xmm0,[air_x]
 movss [rbx+ENTITY_X],xmm0
 shr eax,3
 cvtsi2ss xmm1,eax
 mulss xmm1,[row_step]
 test r13d,r13d
 jz .airrow
 mulss xmm1,[minus]
.airrow:
 lea rdx,[air_z]
 addss xmm1,[rdx+r13*4]
 movss [rbx+ENTITY_Z],xmm1
 ; Initialize generation-validated real poses, not shots or scripted movement.
 mov eax,r12d
 shl eax,6
 lea rbp,[sim_aircraft]
 add rbp,rax
 call terrain_height
 lea rdx,[scenario_air_selected]
 mov ecx,[rdx+r13*4]
 dec ecx
 and ecx,1
 mov [rbp+AIR_ROLE],ecx
 lea rdx,[altitude]
 addss xmm0,[rdx+rcx*4]
 movss [rbp+AIR_Y],xmm0
 lea rdx,[heading]
 mov eax,[rdx+r13*4]
 mov [rbp+AIR_HEADING],eax
 mov dword [rbp+AIR_PITCH],0
 mov dword [rbp+AIR_BANK],0
 lea rdx,[speeds]
 movss xmm0,[rdx+rcx*4]
 movss [rbp+AIR_SPEED],xmm0
 mov dword [rbp+AIR_MODE],AIR_PATROL
 mov dword [rbp+AIR_TARGET],-1
 mov dword [rbp+AIR_COOLDOWN],0
 mov eax,8
 test ecx,ecx
 jz .stores
 mov eax,180
.stores:
 mov [rbp+AIR_AMMO],eax
 mov eax,[rbx+ENTITY_GENERATION]
 mov [rbp+AIR_GENERATION],eax
 mov dword [rbp+AIR_VX],0
 mov dword [rbp+AIR_VY],0
 test r13d,r13d
 jz .velocity
 mulss xmm0,[minus]
.velocity:
 movss [rbp+AIR_VZ],xmm0
 mov dword [rbp+AIR_PASS_TICKS],0
 mov dword [rbp+AIR_FLAGS],AIR_ACTIVE
 jmp .next
.ground:
 lea rdx,[scenario_ground_selected]
 mov eax,[rdx+r13*4]
 cmp dword [scenario_mode],1
 jne .dense_ground
 cmp eax,128
 jae .next
 inc dword [rdx+r13*4]
 mov edx,eax
 and edx,15
 cvtsi2ss xmm0,edx
 mulss xmm0,[ground_step]
 addss xmm0,[ground_x]
 movss [rbx+ENTITY_X],xmm0
 shr eax,4
 cvtsi2ss xmm1,eax
 mulss xmm1,[ground_step]
 lea rdx,[ground_z]
 addss xmm1,[rdx+r13*4]
 movss [rbx+ENTITY_Z],xmm1
 jmp .next
.dense_ground:
 mov ecx,1280
 cmp dword [scenario_mode],2
 je .dense_limit
 mov ecx,1920
.dense_limit:
 cmp eax,ecx
 jae .next
 inc dword [rdx+r13*4]
 mov ecx,[scenario_mode]
 sub ecx,2
 mov edx,eax
 and edx,63
 cvtsi2ss xmm0,edx
 lea rdx,[dense_spacing_x]
 mulss xmm0,[rdx+rcx*4]
 addss xmm0,[dense_x]
 movss [rbx+ENTITY_X],xmm0
 shr eax,6
 cvtsi2ss xmm1,eax
 lea rdx,[dense_spacing_z]
 mulss xmm1,[rdx+rcx*4]
 shl ecx,1
 add ecx,r13d
 lea rdx,[dense_z]
 addss xmm1,[rdx+rcx*4]
 movss [rbx+ENTITY_Z],xmm1
.next:
 inc r12d
 add rbx,ENTITY_STRIDE
 cmp r12d,[sim_count]
 jb .loop
 ; Authored deployment anchor is authority configuration, not camera state.
 ; Connected-site/allied-formation/physical/threat gates remain in spawn_player.
 movss xmm0,[player_x]
 movss xmm1,[deployment_air_z]
 mov eax,[scenario_mode]
 cmp eax,1
 je .deployment
 sub eax,2
 lea rdx,[dense_player_x]
 movss xmm0,[rdx+rax*4]
 lea rdx,[dense_player_z]
 movss xmm1,[rdx+rax*4]
.deployment:
 call player_deployment_set
 ; Connected local players start behind the allied cohort. No HP/ammo changes.
 lea rbx,[sim_players]
 mov r12d,PLAYER_CAPACITY
.players:
 cmp dword [rbx+PLAYER_CONNECTED],0
 je .playernext
 movss xmm0,[player_x]
 movss xmm1,[player_z]
 mov eax,[scenario_mode]
 cmp eax,1
 je .playerpose
 sub eax,2
 lea rdx,[dense_player_x]
 movss xmm0,[rdx+rax*4]
 lea rdx,[dense_player_z]
 movss xmm1,[rdx+rax*4]
.playerpose:
 movss [rbx+PLAYER_X],xmm0
 movss [rbx+PLAYER_Z],xmm1
 call terrain_height
 addss xmm0,[eye]
 movss [rbx+PLAYER_Y],xmm0
.playernext:
 add rbx,PLAYER_STRIDE
 dec r12d
 jnz .players
 add rsp,8
 pop r13
 pop r12
 pop rbp
 pop rbx
.unchanged:
 xor eax,eax
 ret
.invalid:
 mov eax,-1
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
