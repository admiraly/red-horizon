; Explicit initial encounter layouts. All combat/flight afterwards is production.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/player.inc"
default rel
extern sim_entities,sim_aircraft,sim_count,sim_tick_count,sim_players,terrain_height
section .bss
global scenario_air_selected,scenario_ground_selected
scenario_air_selected: resd 2
scenario_ground_selected: resd 2
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
eye: dd 1.8
section .text
global sim_scenario
; EDI0 default unchanged;1 air-battle. Only a fresh >=2048-actor world is valid.
; Returns0/-1; invalid calls preserve authority. No weapon/event/pool writes.
sim_scenario:
 test edi,edi
 jz .unchanged
 cmp edi,1
 jne .invalid
 cmp dword [sim_count],2048
 jb .invalid
 cmp dword [sim_tick_count],0
 jne .invalid
 push rbx
 push rbp
 push r12
 push r13
 sub rsp,8
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
.next:
 inc r12d
 add rbx,ENTITY_STRIDE
 cmp r12d,[sim_count]
 jb .loop
 ; Connected local players start behind the allied cohort. No HP/ammo changes.
 lea rbx,[sim_players]
 mov r12d,PLAYER_CAPACITY
.players:
 cmp dword [rbx+PLAYER_CONNECTED],0
 je .playernext
 movss xmm0,[player_x]
 movss xmm1,[player_z]
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
