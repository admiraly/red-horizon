; Linux SysV client. GLFW provides only OS window/context/input services.
default rel
%include "schemas/player.inc"
global main
extern metrics_init,metrics_frame_begin,metrics_gpu_begin,metrics_gpu_end,metrics_frame_end,metrics_report
extern audio_init,audio_shot,audio_update,audio_shutdown
extern glfwGetVersion
extern sim_init,sim_tick,sim_order,sim_count,sim_entities
extern sim_sites,sim_requisition,sim_supply,sim_operation_state,sim_waypoint,sim_waypoints
extern player_join,player_input,sim_players
extern terrain_obstacles,terrain_obstacle_count
extern battle_vertex_source,battle_fragment_source
extern glfwInitHint,glfwInit,glfwTerminate,glfwWindowHint,glfwCreateWindow,glfwDestroyWindow
extern glfwMakeContextCurrent,glfwSwapInterval,glfwSwapBuffers,glfwPollEvents
extern glfwWindowShouldClose,glfwGetKey,glfwGetMouseButton,glfwGetCursorPos
extern glfwSetInputMode,glfwSetWindowTitle,glfwGetTime
extern glCreateShader,glShaderSource,glCompileShader,glGetShaderiv,glGetShaderInfoLog
extern glCreateProgram,glAttachShader,glLinkProgram,glGetProgramiv,glGetProgramInfoLog
extern glUseProgram,glGetUniformLocation,glUniform3f,glUniform2f,glUniform1i,glUniform4f
extern glGenVertexArrays,glBindVertexArray,glGenBuffers,glBindBuffer,glBufferData
extern glEnableVertexAttribArray,glDisableVertexAttribArray,glVertexAttribPointer,glVertexAttribDivisor
extern glDisable,glEnable,glClearColor,glClear,glViewport,glDrawArrays,glDrawArraysInstanced
extern glReadPixels,glPixelStorei,glGetString
extern strcmp,atoi,puts,printf,snprintf,fopen,fwrite,fclose,sinf,cosf
section .rodata
title: db 'RED HORIZON | WASD move SHIFT sprint | mouse aim/fire | TAB tactical | 1/2/3 advance/hold/retreat | ESC quit',0
frames_opt: db '--frames',0
shot_opt: db '--screenshot',0
map_opt: db '--tactical',0
cam_name: db 'camera',0
angle_name: db 'angle',0
terrain_name: db 'terrain',0
tactical_name: db 'tactical',0
weapon_name: db 'weaponState',0
operation_name: db 'operationInfo',0
goal_name: db 'selectedGoal',0
health_name: db 'playerHealth',0
local_name: db 'localPlayer',0
write_mode: db 'wb',0
ppm_header: db 'P6',10,'1280 720',10,'255',10
ppm_header_len equ $-ppm_header
failure: db 'Client context/shader creation failed.',0
shader_error: db 'Shader/program error:',0
metrics: db 'camera_x=%.2f camera_z=%.2f shots=%u hits=%u last_order=%u',10,0
summary: db 'client frames=%u submitted_entities=%u screenshot=%s',10,0
no_shot: db '(none)',0
title_fmt: db 'RED HORIZON | %u units | rifle %u/30 %s | front %u order %u | REQ %u SUP %u | %s | HP %u SUPPRESS %u REDEPLOY %u | TAB map/click F1-F3 front R reload',0
state_ongoing: db 'OPERATION ACTIVE',0
state_victory: db 'VICTORY',0
state_defeat: db 'DEFEAT',0
state_defense: db 'FINAL DEFENSE: RETAKE ALLIED COMMAND',0
operation_metrics: db 'operation state=%u req=%u supply=%u waypoint_orders=%u',10,0
goal_metrics: db 'selected_goal_x=%.3f selected_goal_z=%.3f',10,0
reload_text: db 'RELOADING',0
dead_text: db 'DOWN: SAFE REDEPLOY',0
player_metrics: db 'player id=%u hp=%u suppression=%u respawn=%u generation=%u',10,0
start_metrics: db 'start_player_x=%.3f start_player_z=%.3f',10,0
weapon_metrics: db 'weapon ammo=%u reloads=%u front=%u',10,0
fps_text: db 'FIRST PERSON',0
map_text: db 'TACTICAL',0
fzero: dd 0.0
world_max: dd 8000.0
fone: dd 1.0
smooth_rate: dd 15.0
snap_distance: dd 25.0
sixty: dd 60.0
onehundred: dd 100.0
sensitivity: dd 0.002
pitch_max: dd 1.3
pitch_min: dd -1.3
map_half_x: dd 640.0
map_half_y: dd 360.0
map_scale: dd 4300.0
map_centre: dd 4000.0
req_scale: dd 1000.0
sup_scale: dd 1200.0
recoil_step: dd 0.008
recoil_rate: dd 0.08
flash_decay: dd 8.0
thirty_ticks: dd 30.0
thirty: dq 0.03333333333333333
maxdt: dq 0.1
minus: dd -1.0
align 16
absolute_mask: dd 0x7fffffff,0x7fffffff,0x7fffffff,0x7fffffff
section .data
camera: dd 4000.0,5.0,3200.0
yaw: dd 0.0
pitch: dd -0.04
frame_limit: dd 0
magazine: dd 30
mouse_seed: dd 3
section .bss
window: resq 1
program: resd 1
vao: resd 1
vbo: resd 1
cam_loc: resd 1
angle_loc: resd 1
terrain_loc: resd 1
tactical_loc: resd 1
weapon_loc: resd 1
operation_loc: resd 1
goal_loc: resd 1
health_loc: resd 1
local_loc: resd 1
local_player: resd 1
player_hp: resd 1
player_suppression: resd 1
player_respawn: resd 1
player_generation: resd 1
last_generation: resd 1
start_recorded: resd 1
start_player_x: resd 1
start_player_z: resd 1
last_hp: resd 1
last_shots: resd 1
last_hits: resd 1
frame_delta: resd 1
wish_x: resd 1
wish_z: resd 1
forward_axis: resd 1
right_axis: resd 1
intent_buttons: resd 1
damage_flash: resd 1
map_down: resd 1
waypoint_orders: resd 1
selected_front: resd 1
reload_count: resd 1
reload_active: resd 1
reload_progress: resd 1
recoil: resd 1
hit_flash: resd 1
shot_flash: resd 1
frame_count: resd 1
tactical: resd 1
tab_down: resd 1
order_mode: resd 1
shot_count: resd 1
hit_count: resd 1
shot_path: resq 1
cursor_x: resq 1
cursor_y: resq 1
old_x: resq 1
old_y: resq 1
last_time: resq 1
accum: resq 1
sin_yaw: resd 1
cos_yaw: resd 1
shader_status: resd 1
source_ptr: resq 1
log: resb 4096
title_buf: resb 384
glfw_version: resd 3
pixels: resb 2764800
section .text
main:
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
 mov ebx,1
.args:
 cmp ebx,r12d
 jge .init
 mov rdi,[r13+rbx*8]
 lea rsi,[frames_opt]
 call strcmp
 test eax,eax
 jnz .shotarg
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rdi,[r13+rbx*8]
 call atoi
 test eax,eax
 jle .fail
 mov [frame_limit],eax
 jmp .nextarg
.shotarg:
 mov rdi,[r13+rbx*8]
 lea rsi,[shot_opt]
 call strcmp
 test eax,eax
 jnz .maparg
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rax,[r13+rbx*8]
 mov [shot_path],rax
 jmp .nextarg
.maparg:
 mov rdi,[r13+rbx*8]
 lea rsi,[map_opt]
 call strcmp
 test eax,eax
 jnz .fail
 mov dword [tactical],1
.nextarg:
 inc ebx
 jmp .args
.init:
 mov edi,8192
 mov esi,42
 call sim_init
 test eax,eax
 jnz .fail
 xor edi,edi
 mov esi,1
 call player_join
 test eax,eax
 jnz .fail
 mov dword [selected_front],1
 lea rdi,[glfw_version]
 lea rsi,[glfw_version+4]
 lea rdx,[glfw_version+8]
 call glfwGetVersion
 cmp dword [glfw_version],3
 jne .fail
 cmp dword [glfw_version+4],3
 jb .fail
 je .glfw_default
 mov edi,0x50003 ; GLFW 3.4 platform selection: X11/GLX (XWayland supported)
 mov esi,0x60004
 call glfwInitHint
.glfw_default:
 call glfwInit
 test eax,eax
 jz .fail
 mov edi,0x22002
 mov esi,4
 call glfwWindowHint
 mov edi,0x22003
 mov esi,5
 call glfwWindowHint
 mov edi,0x22008
 mov esi,0x32001
 call glfwWindowHint
 mov edi,0x20003 ; nonresizable: fixed screenshot/viewport dimensions
 xor esi,esi
 call glfwWindowHint
 mov edi,1280
 mov esi,720
 lea rdx,[title]
 xor ecx,ecx
 xor r8d,r8d
 call glfwCreateWindow
 test rax,rax
 jz .terminatefail
 mov [window],rax
 mov rdi,rax
 call glfwMakeContextCurrent
 mov edi,1
 call glfwSwapInterval
 mov rdi,[window]
 mov esi,0x33001
 mov edx,0x34003
 cmp dword [tactical],0
 je .initialcursor
 mov edx,0x34001
.initialcursor:
 call glfwSetInputMode
 mov edi,0x1f02
 call glGetString
 mov rdi,rax
 call puts
 mov edi,0x8b31
 lea rsi,[battle_vertex_source]
 call compile_shader
 test eax,eax
 jz .destroyfail
 mov r14d,eax
 mov edi,0x8b30
 lea rsi,[battle_fragment_source]
 call compile_shader
 test eax,eax
 jz .destroyfail
 mov r15d,eax
 call glCreateProgram
 mov [program],eax
 mov edi,eax
 mov esi,r14d
 call glAttachShader
 mov edi,[program]
 mov esi,r15d
 call glAttachShader
 mov edi,[program]
 call glLinkProgram
 mov edi,[program]
 mov esi,0x8b82
 lea rdx,[shader_status]
 call glGetProgramiv
 cmp dword [shader_status],0
 je .programfail
 mov edi,[program]
 call glUseProgram
%macro UNIFORM 2
 mov edi,[program]
 lea rsi,[%1]
 call glGetUniformLocation
 mov [%2],eax
%endmacro
 UNIFORM cam_name,cam_loc
 UNIFORM angle_name,angle_loc
 UNIFORM terrain_name,terrain_loc
 UNIFORM tactical_name,tactical_loc
 UNIFORM weapon_name,weapon_loc
 UNIFORM operation_name,operation_loc
 UNIFORM goal_name,goal_loc
 UNIFORM health_name,health_loc
 UNIFORM local_name,local_loc
 mov edi,1
 lea rsi,[vao]
 call glGenVertexArrays
 mov edi,[vao]
 call glBindVertexArray
 mov edi,1
 lea rsi,[vbo]
 call glGenBuffers
 mov edi,0x8892
 mov esi,[vbo]
 call glBindBuffer
 xor edi,edi
 call glEnableVertexAttribArray
 mov edi,1
 call glEnableVertexAttribArray
 xor edi,edi
 mov esi,4
 mov edx,0x1406
 xor ecx,ecx
 mov r8d,32
 xor r9d,r9d
 call glVertexAttribPointer
 mov edi,1
 mov esi,4
 mov edx,0x1406
 xor ecx,ecx
 mov r8d,32
 mov r9d,16
 call glVertexAttribPointer
 xor edi,edi
 mov esi,1
 call glVertexAttribDivisor
 mov edi,1
 mov esi,1
 call glVertexAttribDivisor
 mov edi,0xb71
 call glEnable
 xor edi,edi
 xor esi,esi
 mov edx,1280
 mov ecx,720
 call glViewport
 mov rdi,[window]
 lea rsi,[old_x]
 lea rdx,[old_y]
 call glfwGetCursorPos
 call glfwGetTime
 movsd [last_time],xmm0
 call audio_init
 call metrics_init
.loop:
 call metrics_frame_begin
 call audio_update
 call glfwPollEvents
 call update_input
 test eax,eax
 jnz .done
 call glfwGetTime
 movsd xmm1,xmm0
 subsd xmm0,[last_time]
 movsd [last_time],xmm1
 minsd xmm0,[maxdt]
 cvtsd2ss xmm2,xmm0
 movss [frame_delta],xmm2
 addsd xmm0,[accum]
 movsd [accum],xmm0
.tick:
 movsd xmm0,[accum]
 comisd xmm0,[thirty]
 jb .render
 subsd xmm0,[thirty]
 movsd [accum],xmm0
 call sim_tick
 jmp .tick
.render:
 call sync_player
 call update_visual
 call metrics_gpu_begin
 mov edi,32
 call set_instance_layout
 mov edi,0x8892
 mov esi,[sim_count]
 shl esi,5
 lea rdx,[sim_entities]
 mov ecx,0x88e0
 call glBufferData
 mov eax,0x3eae147b
 movd xmm0,eax
 mov eax,0x3ed70a3d
 movd xmm1,eax
 mov eax,0x3eeb851f
 movd xmm2,eax
 movss xmm3,[fone]
 call glClearColor
 mov edi,0x4100
 call glClear
 mov edi,[cam_loc]
 movss xmm0,[camera]
 movss xmm1,[camera+4]
 movss xmm2,[camera+8]
 call glUniform3f
 mov edi,[angle_loc]
 movss xmm0,[yaw]
 movss xmm1,[pitch]
 addss xmm1,[recoil]
 call glUniform2f
 mov edi,[tactical_loc]
 mov esi,[tactical]
 call glUniform1i
 mov edi,[terrain_loc]
 mov esi,1
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,98304
 call glDrawArrays
 mov edi,[terrain_loc]
 xor esi,esi
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,72
 mov ecx,[sim_count]
 call glDrawArraysInstanced
 mov edi,0x8892
 mov esi,384
 lea rdx,[sim_sites]
 mov ecx,0x88e0
 call glBufferData
 mov edi,[terrain_loc]
 mov esi,3
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,72
 mov ecx,12
 call glDrawArraysInstanced
 mov edi,0x8892
 mov esi,[terrain_obstacle_count]
 shl esi,5
 lea rdx,[terrain_obstacles]
 mov ecx,0x88e0
 call glBufferData
 mov edi,[terrain_loc]
 mov esi,5
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,36
 mov ecx,[terrain_obstacle_count]
 call glDrawArraysInstanced
 mov edi,64
 call set_instance_layout
 mov edi,0x8892
 mov esi,256
 lea rdx,[sim_players]
 mov ecx,0x88e0
 call glBufferData
 mov edi,[local_loc]
 mov esi,[local_player]
 call glUniform1i
 mov edi,[terrain_loc]
 mov esi,6
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,72
 mov ecx,4
 call glDrawArraysInstanced
 mov edi,32
 call set_instance_layout
 mov edi,[operation_loc]
 cvtsi2ss xmm0,[sim_requisition]
 divss xmm0,[req_scale]
 cvtsi2ss xmm1,[sim_supply]
 divss xmm1,[sup_scale]
 cvtsi2ss xmm2,[sim_operation_state]
 call glUniform3f
 mov edi,[weapon_loc]
 cvtsi2ss xmm0,[magazine]
 movss xmm1,[reload_progress]
 movss xmm2,[hit_flash]
 movss xmm3,[shot_flash]
 call glUniform4f
 mov edi,[health_loc]
 cvtsi2ss xmm0,[player_hp]
 divss xmm0,[onehundred]
 cvtsi2ss xmm1,[player_suppression]
 divss xmm1,[onehundred]
 cvtsi2ss xmm2,[player_respawn]
 divss xmm2,[thirty_ticks]
 movss xmm3,[damage_flash]
 call glUniform4f
 mov edi,0xb71
 call glDisable
 mov edi,[terrain_loc]
 mov esi,2
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,258
 call glDrawArrays
 cmp dword [tactical],0
 je .restoredepth
 mov edi,[goal_loc]
 mov eax,[selected_front]
 lea rdx,[sim_waypoints]
 movss xmm0,[rdx+rax*8]
 movss xmm1,[rdx+rax*8+4]
 call glUniform2f
 mov edi,[terrain_loc]
 mov esi,4
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,12
 call glDrawArrays
.restoredepth:
 mov edi,0xb71
 call glEnable
.nohud:
 call metrics_gpu_end
 inc dword [frame_count]
 mov eax,[frame_limit]
 test eax,eax
 jz .swap
 cmp [frame_count],eax
 jb .swap
 call screenshot
 test eax,eax
 jnz .destroyfail
 jmp .done
.swap:
 mov rdi,[window]
 call glfwSwapBuffers
 call metrics_frame_end
 mov rdi,[window]
 call glfwWindowShouldClose
 test eax,eax
 jz .loop
.done:
 call metrics_frame_end
 call metrics_report
 lea rdi,[summary]
 mov esi,[frame_count]
 mov edx,[sim_count]
 mov rcx,[shot_path]
 test rcx,rcx
 jnz .print
 lea rcx,[no_shot]
.print:
 xor eax,eax
 call printf
 lea rdi,[metrics]
 cvtss2sd xmm0,[camera]
 cvtss2sd xmm1,[camera+8]
 mov esi,[shot_count]
 mov edx,[hit_count]
 mov ecx,[order_mode]
 mov eax,2
 call printf
 lea rdi,[weapon_metrics]
 mov esi,[magazine]
 mov edx,[reload_count]
 mov ecx,[selected_front]
 xor eax,eax
 call printf
 lea rdi,[operation_metrics]
 mov esi,[sim_operation_state]
 mov edx,[sim_requisition]
 mov ecx,[sim_supply]
 mov r8d,[waypoint_orders]
 xor eax,eax
 call printf
 mov eax,[selected_front]
 lea rdx,[sim_waypoints]
 cvtss2sd xmm0,[rdx+rax*8]
 cvtss2sd xmm1,[rdx+rax*8+4]
 lea rdi,[goal_metrics]
 mov eax,2
 call printf
 lea rdi,[player_metrics]
 mov esi,[local_player]
 mov edx,[player_hp]
 mov ecx,[player_suppression]
 mov r8d,[player_respawn]
 mov r9d,[player_generation]
 xor eax,eax
 call printf
 lea rdi,[start_metrics]
 cvtss2sd xmm0,[start_player_x]
 cvtss2sd xmm1,[start_player_z]
 mov eax,2
 call printf
 mov rdi,[window]
 call glfwDestroyWindow
 call glfwTerminate
 xor eax,eax
 jmp .exit
.programfail:
 mov edi,[program]
 mov esi,4096
 xor edx,edx
 lea rcx,[log]
 call glGetProgramInfoLog
 lea rdi,[log]
 call puts
.destroyfail:
 mov rdi,[window]
 call glfwDestroyWindow
.terminatefail:
 call glfwTerminate
.fail:
 lea rdi,[failure]
 call puts
 mov eax,1
.exit:
 mov ebx,eax
 call audio_shutdown
 mov eax,ebx
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret

compile_shader:
 push rbx
 mov [source_ptr],rsi
 call glCreateShader
 mov ebx,eax
 mov edi,eax
 mov esi,1
 lea rdx,[source_ptr]
 xor ecx,ecx
 call glShaderSource
 mov edi,ebx
 call glCompileShader
 mov edi,ebx
 mov esi,0x8b81
 lea rdx,[shader_status]
 call glGetShaderiv
 cmp dword [shader_status],0
 je .error
 mov eax,ebx
 pop rbx
 ret
.error:
 mov edi,ebx
 mov esi,4096
 xor edx,edx
 lea rcx,[log]
 call glGetShaderInfoLog
 lea rdi,[log]
 call puts
 xor eax,eax
 pop rbx
 ret

; Key polling has no application callbacks; all processing is assembly.
%macro KEY 1
 mov rdi,[window]
 mov esi,%1
 call glfwGetKey
%endmacro
update_input:
 push rbx
 KEY 256
 test eax,eax
 jnz .quit
 KEY 258
 test eax,eax
 jz .tabup
 cmp dword [tab_down],0
 jne .orders
 xor dword [tactical],1
 mov dword [mouse_seed],3
 mov rdi,[window]
 mov esi,0x33001
 mov edx,0x34003
 cmp dword [tactical],0
 je .cursorchange
 mov edx,0x34001
.cursorchange:
 call glfwSetInputMode
 mov dword [tab_down],1
 jmp .orders
.tabup:
 mov dword [tab_down],0
.orders:
 mov ebx,290
.frontloop:
 mov rdi,[window]
 mov esi,ebx
 call glfwGetKey
 test eax,eax
 jz .nextfront
 mov eax,ebx
 sub eax,290
 mov [selected_front],eax
.nextfront:
 inc ebx
 cmp ebx,293
 jb .frontloop
 mov ebx,49
.orderloop:
 mov rdi,[window]
 mov esi,ebx
 call glfwGetKey
 test eax,eax
 jz .nextorder
 mov edx,ebx
 sub edx,49
 mov [order_mode],edx
 xor edi,edi
 mov esi,[selected_front]
 call sim_order
.nextorder:
 inc ebx
 cmp ebx,52
 jb .orderloop
 mov rdi,[window]
 lea rsi,[cursor_x]
 lea rdx,[cursor_y]
 call glfwGetCursorPos
 cmp dword [tactical],0
 jne .seedcursor
 cmp dword [mouse_seed],0
 je .aimdelta
 dec dword [mouse_seed]
.seedcursor:
 movsd xmm0,[cursor_x]
 movsd [old_x],xmm0
 movsd xmm0,[cursor_y]
 movsd [old_y],xmm0
.aimdelta:
 movsd xmm0,[cursor_x]
 subsd xmm0,[old_x]
 cvtsd2ss xmm0,xmm0
 mulss xmm0,[sensitivity]
 addss xmm0,[yaw]
 movss [yaw],xmm0
 movsd xmm0,[cursor_y]
 subsd xmm0,[old_y]
 cvtsd2ss xmm0,xmm0
 mulss xmm0,[sensitivity]
 mulss xmm0,[minus]
 addss xmm0,[pitch]
 minss xmm0,[pitch_max]
 maxss xmm0,[pitch_min]
 movss [pitch],xmm0
 movsd xmm0,[cursor_x]
 movsd [old_x],xmm0
 movsd xmm0,[cursor_y]
 movsd [old_y],xmm0
 movss xmm0,[yaw]
 call sinf
 movss [sin_yaw],xmm0
 movss xmm0,[yaw]
 call cosf
 movss [cos_yaw],xmm0
 call collect_intent
 mov edi,[local_player]
 mov esi,[intent_buttons]
 movss xmm0,[wish_x]
 movss xmm1,[wish_z]
 movss xmm2,[yaw]
 movss xmm3,[pitch]
 call player_input
 cmp dword [tactical],0
 je .title
 call tactical_click
.title:
 sub rsp,64
 mov eax,[selected_front]
 mov [rsp],rax
 mov eax,[order_mode]
 mov [rsp+8],rax
 mov eax,[sim_requisition]
 mov [rsp+16],rax
 mov eax,[sim_supply]
 mov [rsp+24],rax
 lea rax,[state_ongoing]
 cmp dword [sim_operation_state],1
 jne .notvictory
 lea rax,[state_victory]
.notvictory:
 cmp dword [sim_operation_state],2
 jne .notdefeat
 lea rax,[state_defeat]
.notdefeat:
 cmp dword [sim_operation_state],3
 jne .statetitle
 lea rax,[state_defense]
.statetitle:
 mov [rsp+32],rax
 mov eax,[player_hp]
 mov [rsp+40],rax
 mov eax,[player_suppression]
 mov [rsp+48],rax
 mov eax,[player_respawn]
 mov [rsp+56],rax
 lea rdi,[title_buf]
 mov esi,384
 lea rdx,[title_fmt]
 mov ecx,[sim_count]
 mov r8d,[magazine]
 lea r9,[fps_text]
 cmp dword [tactical],0
 je .reloadtitle
 lea r9,[map_text]
.reloadtitle:
 cmp dword [reload_active],0
 je .fmt
 lea r9,[reload_text]
.fmt:
 cmp dword [player_hp],0
 jne .alive_title
 lea r9,[dead_text]
.alive_title:
 xor eax,eax
 call snprintf
 add rsp,64
 mov rdi,[window]
 lea rsi,[title_buf]
 call glfwSetWindowTitle
 xor eax,eax
 pop rbx
 ret
.quit:
 mov eax,1
 pop rbx
 ret
; Unpaused tactical command: map cursor maps to operation metres. API validates
; finite coordinates and ownership. Only accepted goals initiate an advance.
tactical_click:
 push rbx
 mov rdi,[window]
 xor esi,esi
 call glfwGetMouseButton
 test eax,eax
 jz .up
 cmp dword [map_down],0
 jne .return
 mov dword [map_down],1
 cvtsd2ss xmm0,[cursor_x]
 divss xmm0,[map_half_x]
 subss xmm0,[fone]
 mulss xmm0,[map_scale]
 addss xmm0,[map_centre]
 cvtsd2ss xmm1,[cursor_y]
 divss xmm1,[map_half_y]
 movss xmm2,[fone]
 subss xmm2,xmm1
 movaps xmm1,xmm2
 mulss xmm1,[map_scale]
 addss xmm1,[map_centre]
 xor edi,edi
 mov esi,[selected_front]
 call sim_waypoint
 test eax,eax
 jnz .return
 inc dword [waypoint_orders]
 mov dword [order_mode],0
 xor edi,edi
 mov esi,[selected_front]
 xor edx,edx
 call sim_order
 jmp .return
.up:
 mov dword [map_down],0
.return:
 pop rbx
 ret

; Input intent is submitted to shared authority. No client position, health,
; ammunition, ray damage or reload deadline mutates authoritative state.
collect_intent:
 push rbx
 mov dword [forward_axis],0
 mov dword [right_axis],0
 mov dword [intent_buttons],0
 KEY 87
 test eax,eax
 jz .back
 movss xmm0,[fone]
 movss [forward_axis],xmm0
.back:
 KEY 83
 test eax,eax
 jz .left
 movss xmm0,[forward_axis]
 subss xmm0,[fone]
 movss [forward_axis],xmm0
.left:
 KEY 65
 test eax,eax
 jz .right
 movss xmm0,[minus]
 movss [right_axis],xmm0
.right:
 KEY 68
 test eax,eax
 jz .direction
 movss xmm0,[right_axis]
 addss xmm0,[fone]
 movss [right_axis],xmm0
.direction:
 movss xmm0,[forward_axis]
 mulss xmm0,[sin_yaw]
 movss xmm1,[right_axis]
 mulss xmm1,[cos_yaw]
 addss xmm0,xmm1
 movss [wish_x],xmm0
 movss xmm1,[forward_axis]
 mulss xmm1,[cos_yaw]
 movss xmm2,[right_axis]
 mulss xmm2,[sin_yaw]
 subss xmm1,xmm2
 movss [wish_z],xmm1
 movaps xmm2,xmm0
 mulss xmm2,xmm2
 movaps xmm3,xmm1
 mulss xmm3,xmm3
 addss xmm2,xmm3
 sqrtss xmm2,xmm2
 maxss xmm2,[fone]
 divss xmm0,xmm2
 divss xmm1,xmm2
 movss [wish_x],xmm0
 movss [wish_z],xmm1
 KEY 340
 test eax,eax
 jz .reload
 or dword [intent_buttons],INPUT_SPRINT
.reload:
 KEY 82
 test eax,eax
 jz .trigger
 or dword [intent_buttons],INPUT_RELOAD
.trigger:
 cmp dword [tactical],0
 jne .return
 mov rdi,[window]
 xor esi,esi
 call glfwGetMouseButton
 test eax,eax
 jz .return
 or dword [intent_buttons],INPUT_FIRE
.return:
 pop rbx
 ret

; Shared VBO record layouts: army/sites/obstacles32, authoritative players64.
set_instance_layout:
 push rbx
 mov ebx,edi
 xor edi,edi
 mov esi,4
 mov edx,0x1406
 xor ecx,ecx
 mov r8d,ebx
 xor r9d,r9d
 call glVertexAttribPointer
 mov edi,1
 mov esi,4
 mov edx,0x1406
 xor ecx,ecx
 mov r8d,ebx
 mov r9d,16
 call glVertexAttribPointer
 cmp ebx,64
 jne .disable
 mov edi,2
 call glEnableVertexAttribArray
 mov edi,2
 mov esi,4
 mov edx,0x1406
 xor ecx,ecx
 mov r8d,64
 mov r9d,32
 call glVertexAttribPointer
 mov edi,2
 mov esi,1
 call glVertexAttribDivisor
 jmp .done
.disable:
 mov edi,2
 call glDisableVertexAttribArray
.done:
 pop rbx
 ret

player_pointer:
 mov eax,[local_player]
 shl eax,6
 lea rdx,[sim_players]
 add rax,rdx
 ret

; Smooth only visual camera correction. Safe deployment/generation changes snap.
; Shots/hits/ammunition/health are read directly from shared player records.
sync_player:
 push rbx
 call player_pointer
 mov rbx,rax
 mov eax,[rbx+PLAYER_HP]
 mov [player_hp],eax
 cmp eax,[last_hp]
 jae .hpunchanged
 movss xmm0,[fone]
 movss [damage_flash],xmm0
.hpunchanged:
 mov [last_hp],eax
 cmp dword [start_recorded],0
 jne .recorded
 test eax,eax
 jz .recorded
 movss xmm0,[rbx+PLAYER_X]
 movss [start_player_x],xmm0
 movss xmm0,[rbx+PLAYER_Z]
 movss [start_player_z],xmm0
 mov dword [start_recorded],1
.recorded:
 mov eax,[rbx+PLAYER_SUPPRESSION]
 mov [player_suppression],eax
 mov eax,[rbx+PLAYER_RESPAWN]
 mov [player_respawn],eax
 mov eax,[rbx+PLAYER_GENERATION]
 mov [player_generation],eax
 cmp eax,[last_generation]
 jne .snap
 movss xmm0,[rbx+PLAYER_X]
 subss xmm0,[camera]
 andps xmm0,[absolute_mask]
 comiss xmm0,[snap_distance]
 ja .snap
 movss xmm0,[rbx+PLAYER_Z]
 subss xmm0,[camera+8]
 andps xmm0,[absolute_mask]
 comiss xmm0,[snap_distance]
 ja .snap
 movss xmm3,[frame_delta]
 mulss xmm3,[smooth_rate]
 minss xmm3,[fone]
 jmp .interpolate
.snap:
 mov eax,[player_generation]
 mov [last_generation],eax
 movss xmm3,[fone]
.interpolate:
%assign off 0
%rep 3
 movss xmm0,[rbx+off]
 subss xmm0,[camera+off]
 mulss xmm0,xmm3
 addss xmm0,[camera+off]
 movss [camera+off],xmm0
%assign off off+4
%endrep
 mov eax,[rbx+PLAYER_AMMO]
 mov [magazine],eax
 mov eax,[rbx+PLAYER_RELOAD]
 test eax,eax
 setnz dl
 movzx edx,dl
 cmp edx,[reload_active]
 jbe .reloadstate
 inc dword [reload_count]
.reloadstate:
 mov [reload_active],edx
 cvtsi2ss xmm0,eax
 divss xmm0,[sixty]
 movss [reload_progress],xmm0
 mov eax,[rbx+PLAYER_SHOTS]
 mov [shot_count],eax
 cmp eax,[last_shots]
 je .hits
 mov [last_shots],eax
 call audio_shot
 movss xmm0,[fone]
 movss [shot_flash],xmm0
 movss xmm0,[recoil]
 addss xmm0,[recoil_step]
 movss [recoil],xmm0
.hits:
 mov eax,[rbx+PLAYER_HITS]
 mov [hit_count],eax
 cmp eax,[last_hits]
 je .done
 mov [last_hits],eax
 movss xmm0,[fone]
 movss [hit_flash],xmm0
.done:
 pop rbx
 ret

; Cosmetic feedback only: aim input never inherits visual recoil displacement.
update_visual:
 movss xmm0,[frame_delta]
 mulss xmm0,[recoil_rate]
 movss xmm1,[recoil]
 subss xmm1,xmm0
 maxss xmm1,[fzero]
 movss [recoil],xmm1
 movss xmm0,[frame_delta]
 mulss xmm0,[flash_decay]
%macro DECAY 1
 movss xmm1,[%1]
 subss xmm1,xmm0
 maxss xmm1,[fzero]
 movss [%1],xmm1
%endmacro
 DECAY hit_flash
 DECAY shot_flash
 DECAY damage_flash
 ret

screenshot:
 push rbx
 push r12
 sub rsp,8
 cmp qword [shot_path],0
 je .return
 mov edi,0xd05
 mov esi,1
 call glPixelStorei
 ; seventh argument on stack, aligned for SysV.
 sub rsp,16
 lea rax,[pixels]
 mov [rsp],rax
 xor edi,edi
 xor esi,esi
 mov edx,1280
 mov ecx,720
 mov r8d,0x1907
 mov r9d,0x1401
 call glReadPixels
 add rsp,16
 mov rdi,[shot_path]
 lea rsi,[write_mode]
 call fopen
 test rax,rax
 jz .error
 mov rbx,rax
 lea rdi,[ppm_header]
 mov esi,1
 mov edx,ppm_header_len
 mov rcx,rbx
 call fwrite
 cmp eax,ppm_header_len
 jne .closeerror
 mov r12d,719
.rows:
 imul eax,r12d,3840
 lea rdi,[pixels]
 add rdi,rax
 mov esi,1
 mov edx,3840
 mov rcx,rbx
 call fwrite
 cmp eax,3840
 jne .closeerror
 dec r12d
 jns .rows
 mov rdi,rbx
 call fclose
 test eax,eax
 jnz .error
.return:
 xor eax,eax
 jmp .end
.closeerror:
 mov rdi,rbx
 call fclose
.error:
 mov eax,1
.end:
 add rsp,8
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
