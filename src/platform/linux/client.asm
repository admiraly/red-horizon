; Linux SysV client. GLFW provides only OS window/context/input services.
default rel
%include "schemas/player.inc"
%include "schemas/combat.inc"
global main
extern environment_init,environment_apply,environment_step,environment_parse,environment_select,environment_cycle,environment_name,environment_preset,environment_weather
extern view_settings_parse,view_settings_apply,view_width,view_height,view_sensitivity,view_projection,view_half_size
extern visibility_init,visibility_begin,visibility_world_end,visibility_finish,visibility_report,visibility_shutdown,visibility_write_map
extern hazard_warning_update,hazard_warning_uniform
extern sim_scenario
extern net_projectiles,net_projectiles_update
extern air_trails_update,air_trails_records,air_trails_active
extern effects_update,effects_records,effects_tracers,effects_active
extern meshes_init,meshes_draw,mesh_high_instances,mesh_low_instances,mesh_marker_instances,mesh_source_triangles,mesh_animation_sample
extern mesh_asset_count
extern battle_metrics_reset,battle_metrics_capture,battle_metrics_report
extern metrics_init,metrics_frame_begin,metrics_gpu_begin,metrics_gpu_end,metrics_frame_end,metrics_report
extern audio_footsteps_update,audio_footsteps_reset
extern audio_init,audio_shot,audio_update,audio_shutdown,audio_scene_update
extern glfwGetVersion
extern sim_init,sim_tick,sim_count,sim_entities
extern company_for_player,company_control_order,company_controls
extern net_company_for_player,net_company_records,net_company_offer,net_company_transfers
extern net_client_transfer
extern sim_sites,sim_requisition,sim_supply,sim_operation_state
extern player_join,player_input,sim_players
extern sim_player_vehicle,sim_vehicles,sim_projectiles
extern net_client_open,net_client_poll,net_client_input,net_client_order,net_client_close
extern net_connected,net_player_id,net_front,net_server_tick,net_last_status,net_pending
extern terrain_height,terrain_obstacles,terrain_obstacle_count
extern world_body_step_context,net_wrecks,net_wreck_count,net_wreck_query_revision
extern battle_vertex_source,battle_fragment_source
extern command_hud_init,command_hud_begin,command_hud_draw
extern glfwInitHint,glfwInit,glfwTerminate,glfwWindowHint,glfwCreateWindow,glfwDestroyWindow
extern glfwMakeContextCurrent,glfwSwapInterval,glfwSwapBuffers,glfwPollEvents
extern glfwWindowShouldClose,glfwGetKey,glfwGetMouseButton,glfwGetCursorPos
extern glfwSetInputMode,glfwSetWindowTitle,glfwGetTime,glfwSetKeyCallback
extern glCreateShader,glShaderSource,glCompileShader,glGetShaderiv,glGetShaderInfoLog
extern glCreateProgram,glAttachShader,glLinkProgram,glGetProgramiv,glGetProgramInfoLog
extern glUseProgram,glGetUniformLocation,glUniform3f,glUniform2f,glUniform1i,glUniform4f
extern glGenVertexArrays,glBindVertexArray,glGenBuffers,glBindBuffer,glBufferData
extern glEnableVertexAttribArray,glDisableVertexAttribArray,glVertexAttribPointer,glVertexAttribDivisor
extern glBlendFunc,glDepthMask
extern glDisable,glEnable,glClearColor,glClear,glViewport,glDrawArrays,glDrawArraysInstanced
extern glReadPixels,glPixelStorei,glGetString
extern strcmp,atoi,puts,printf,snprintf,fopen,fwrite,fclose,sinf,cosf
section .rodata
command_panel_fmt: db 'COMPANY %d | FRONT %u | 1 ADVANCE 2 HOLD 3 RETREAT | TAB MAP',0
command_panel_lost: db 'CO-OP CONNECTION LOST - COMPANY COMMANDS UNAVAILABLE',0
title: db 'RED HORIZON | WASD move SHIFT sprint | mouse aim/fire | TAB tactical | 1/2/3 advance/hold/retreat | ESC quit',0
weather_opt: db '--weather',0
weather_suffix: db '%s | WEATHER %s (F4 cycle)',0
scenario_opt: db '--scenario',0
air_battle_name: db 'air-battle',0
scale_front_name: db 'scale-front',0
scale_hotspot_name: db 'scale-hotspot',0
scale_open_name: db 'scale-open',0
frames_opt: db '--frames',0
shot_opt: db '--screenshot',0
census_opt: db '--census',0
census_map_opt: db '--census-map',0
map_opt: db '--tactical',0
connect_opt: db '--connect',0
port_opt: db '--port',0
help_opt: db '--help',0
help_text: db 'RED HORIZON: [--connect IPv4 --port 7777] [--weather clear|overcast|rain|fog] [--scenario scale-open|air-battle|scale-front|scale-hotspot] [--width 320..3840 --height 240..2160 --fov 35..110 --sensitivity 0.00001..0.05] [--tactical] [--frames N --screenshot PATH.ppm] [--census --census-map PATH.r32ui]',10,'WASD move; Shift sprint; Ctrl crouch; Space jump; E board armor / Q exit; mouse aim / held left rifle; R reload; Tab map; F1-F3 front; 1/2/3 advance/hold/retreat; map left-click waypoint; F4 weather; Escape quit.',10,'Health green / suppression amber / redeploy red. Co-op commands require your assigned company front; snapshots cover your current region.',0
transfer_none: db 'F5-F8: request exchange with P0-P3 | F11: cancel own offer',0
transfer_offer_fmt: db 'P%u OFFERS COMPANY EXCHANGE | F9 accept | F10 decline | F11 cancel own',0
transfer_changed: db 'COMPANY ASSIGNMENT UPDATED',0
transfer_proposed: db 'COMPANY EXCHANGE REQUEST SENT',0
transfer_accepted: db 'COMPANY EXCHANGE ACCEPTED',0
transfer_declined: db 'COMPANY EXCHANGE DECLINED',0
transfer_cancelled: db 'COMPANY EXCHANGE CANCELLED',0
transfer_missing: db 'NO CURRENT COMPANY EXCHANGE OFFER',0
transfer_failed: db 'COMPANY EXCHANGE REQUEST REJECTED',0
transfer_ack_messages: dq transfer_proposed,transfer_accepted,transfer_declined,transfer_cancelled
local_company_fmt: db '%s | COMPANY %u | %s',0
local_ready_text: db 'COMPANY READY',0
local_reject_text: db 'ORDER DENIED: INVALID POINT OR INSUFFICIENT REQUISITION',0
net_fmt: db '%s | CO-OP P%u OWN FRONT %u TICK %u | %s | COMPANY %d | %s | scoped region data',0
joining_text: db 'JOINING / CONNECTION LOST',0
net_ready_text: db 'CONNECTED',0
net_denied_text: db 'ORDER DENIED: SELECT YOUR OWN FRONT',0
net_bounds_text: db 'ORDER DENIED: POINT OUTSIDE MAP',0
net_queue_text: db 'ORDER QUEUED',0
net_busy_text: db 'ORDER BUSY: WAIT FOR SERVER ACK',0
net_sent_text: db 'ORDER ACCEPTED: COST 5',0
net_reject_text: db 'SERVER REJECTED REQUEST',0
mesh_metrics: db 'meshes loaded=%u high=%u low=%u markers=%u source_triangles=%u animation_frame=%u',10,0
net_metrics: db 'network connected=%u player=%u front=%u server_tick=%u known_living=%u local_sim_ticks=%u',10,0
projection_name: db 'projection',0
ppm_format: db 'P6',10,'%u %u',10,'255',10,0
cam_name: db 'camera',0
angle_name: db 'angle',0
terrain_name: db 'terrain',0
tactical_name: db 'tactical',0
weapon_name: db 'weaponState',0
operation_name: db 'operationInfo',0
goal_name: db 'selectedGoal',0
health_name: db 'playerHealth',0
vehicle_name: db 'vehicleState',0
incoming_name: db 'incomingThreat',0
vehicle_fmt: db 'ARMOR #%u CANNON %u COOLDOWN %u HULL %u | Q exit',0
onfoot_text: db 'ON FOOT | E board Q exit',0
local_name: db 'localPlayer',0
write_mode: db 'wb',0

view_failure: db 'Invalid view setting: supply each flag once; width 320..3840 and height 240..2160 integer pixels; vertical FOV 35..110 degrees; sensitivity 0.00001..0.05 radians/pixel. Use --help.',0
failure: db 'Client context/shader creation failed.',0
shader_error: db 'Shader/program error:',0
metrics: db 'camera_x=%.2f camera_z=%.2f shots=%u hits=%u last_order=%u',10,0
summary: db 'client frames=%u submitted_entities=%u screenshot=%s',10,0
no_shot: db '(none)',0
title_fmt: db 'RED HORIZON | %u units | rifle %u/30 %s | front %u order %u | REQ %u SUP %u | %s | HP %u SUPPRESS %u REDEPLOY %u | %s | TAB map/click F1-F3 front R reload',0
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
crouch_prediction: dd 0.083333333
walk_prediction: dd 0.166666667
sprint_prediction: dd 0.3
net_predict_timeout: dq 0.2
eyes: dd 1.8
offscreen: dd -20000.0
smooth_rate: dd 15.0
snap_distance: dd 25.0
sixty: dd 60.0
onehundred: dd 100.0

pitch_max: dd 1.3
pitch_min: dd -1.3

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
global air_trails_visible,net_projectiles_visible,net_projectiles_clock_frozen
air_trails_visible: dd 1
net_projectiles_visible: dd 1
net_projectiles_clock_frozen: dd 0
yaw: dd 0.0
pitch: dd -0.04
frame_limit: dd 0
magazine: dd 30
mouse_seed: dd 3
server_port: dd 7777
command_message: dq net_ready_text
section .bss
command_panel: resb 160
quit_latched: resd 1
window: resq 1
program: resd 1
vao: resd 1
vbo: resd 1
projection_loc: resd 1
cam_loc: resd 1
angle_loc: resd 1
terrain_loc: resd 1
tactical_loc: resd 1
weapon_loc: resd 1
operation_loc: resd 1
goal_loc: resd 1
health_loc: resd 1
local_loc: resd 1
vehicle_loc: resd 1
incoming_loc: resd 1
vehicle_buf: resb 160
local_player: resd 1
connect_address: resq 1
global network_mode
network_mode: resd 1
global census_requested
census_requested: resd 1
census_map_path: resq 1
census_frame: resd 1
census_finished: resd 1
final_frame_ended: resd 1
scenario_mode: resd 1
scenario_seen: resd 1
network_joined: resd 1
last_owned_company: resd 1
transfer_pending: resd 1
transfer_action: resd 1
transfer_other: resd 1
transfer_sequence: resd 1
transfer_key_mask: resd 1
incoming_owner: resd 1
incoming_sequence: resd 1
transfer_info: resb 192
last_net_tick: resd 1
last_net_time: resq 1
known_entities: resd 1
local_sim_ticks: resd 1
command_pending: resd 1
command_front: resd 1
command_mode: resd 1
command_goal: resd 2
net_goal: resd 6
net_goal_valid: resd 3
order_down_mask: resd 1
visual_target: resd 3
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
weather_down: resd 1
weather_title_buf: resb 768
title_buf: resb 384
net_title_buf: resb 640
glfw_version: resd 3
ppm_header: resb 64
ppm_header_len: resd 1
row_bytes: resd 1
pixels: resb 24883200 ; bounded 3840x2160 RGB maximum
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
 xor esi,esi
 lea eax,[rbx+1]
 cmp eax,r12d
 jge .viewparse
 mov rsi,[r13+rax*8]
.viewparse:
 call view_settings_parse
 test eax,eax
 js .viewinvalid
 jz .ordinaryarg
 inc ebx
 jmp .nextarg
.ordinaryarg:
 mov rdi,[r13+rbx*8]
 lea rsi,[frames_opt]
 call strcmp
 test eax,eax
 jnz .shotarg
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rdi,[r13+rbx*8]
 call parse_frame_limit
 test eax,eax
 jle .fail
 mov [frame_limit],eax
 jmp .nextarg
.shotarg:
 mov rdi,[r13+rbx*8]
 lea rsi,[shot_opt]
 call strcmp
 test eax,eax
 jnz .censusarg
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rax,[r13+rbx*8]
 mov [shot_path],rax
 jmp .nextarg
.censusarg:
 mov rdi,[r13+rbx*8]
 lea rsi,[census_opt]
 call strcmp
 test eax,eax
 jnz .censusmaparg
 cmp dword [census_requested],0
 jne .fail
 mov dword [census_requested],1
 jmp .nextarg
.censusmaparg:
 mov rdi,[r13+rbx*8]
 lea rsi,[census_map_opt]
 call strcmp
 test eax,eax
 jnz .maparg
 cmp qword [census_map_path],0
 jne .fail
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rax,[r13+rbx*8]
 cmp byte [rax],0
 je .fail
 mov [census_map_path],rax
 jmp .nextarg
.maparg:
 mov rdi,[r13+rbx*8]
 lea rsi,[map_opt]
 call strcmp
 test eax,eax
 jnz .connectarg
 mov dword [tactical],1
 jmp .nextarg
.connectarg:
 mov rdi,[r13+rbx*8]
 lea rsi,[connect_opt]
 call strcmp
 test eax,eax
 jnz .portarg
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rax,[r13+rbx*8]
 mov [connect_address],rax
 mov dword [network_mode],1
 jmp .nextarg
.portarg:
 mov rdi,[r13+rbx*8]
 lea rsi,[port_opt]
 call strcmp
 test eax,eax
 jnz .weatherarg
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rdi,[r13+rbx*8]
 call atoi
 cmp eax,1
 jl .fail
 cmp eax,65535
 ja .fail
 mov [server_port],eax
 jmp .nextarg
.weatherarg:
 mov rdi,[r13+rbx*8]
 lea rsi,[weather_opt]
 call strcmp
 test eax,eax
 jnz .scenarioarg
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rdi,[r13+rbx*8]
 call environment_parse
 test eax,eax
 js .fail
 mov edi,eax
 mov esi,1
 call environment_select
 jmp .nextarg
.scenarioarg:
 mov rdi,[r13+rbx*8]
 lea rsi,[scenario_opt]
 call strcmp
 test eax,eax
 jnz .helparg
 cmp dword [scenario_seen],0
 jne .fail
 mov dword [scenario_seen],1
 inc ebx
 cmp ebx,r12d
 jge .fail
 mov rdi,[r13+rbx*8]
 lea rsi,[air_battle_name]
 call strcmp
 test eax,eax
 jnz .frontscenario
 mov dword [scenario_mode],1
 jmp .nextarg
.frontscenario:
 mov rdi,[r13+rbx*8]
 lea rsi,[scale_front_name]
 call strcmp
 test eax,eax
 jnz .hotspotscenario
 mov dword [scenario_mode],2
 jmp .nextarg
.hotspotscenario:
 mov rdi,[r13+rbx*8]
 lea rsi,[scale_hotspot_name]
 call strcmp
 test eax,eax
 jnz .defaultscenario
 mov dword [scenario_mode],3
 jmp .nextarg
.defaultscenario:
 mov rdi,[r13+rbx*8]
 lea rsi,[scale_open_name]
 call strcmp
 test eax,eax
 jnz .fail
 mov dword [scenario_mode],0
 jmp .nextarg
.helparg:
 mov rdi,[r13+rbx*8]
 lea rsi,[help_opt]
 call strcmp
 test eax,eax
 jnz .fail
 lea rdi,[help_text]
 call puts
 xor eax,eax
 jmp .exit
.viewinvalid:
 lea rdi,[view_failure]
 call puts
 mov eax,1
 jmp .exit
.nextarg:
 inc ebx
 jmp .args
.init:
 cmp dword [census_requested],0
 jne .validatecensus
 cmp qword [census_map_path],0
 jne .fail
 jmp .viewready
.validatecensus:
 cmp dword [frame_limit],1
 jb .fail
 cmp dword [frame_limit],10000
 ja .fail
.viewready:
 call view_settings_apply
 cmp dword [network_mode],0
 jne .networkinit
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
 mov edi,[scenario_mode]
 call sim_scenario
 test eax,eax
 jnz .fail
 mov dword [selected_front],1
 lea rax,[local_ready_text]
 mov [command_message],rax
 jmp .platforminit
.networkinit:
 cmp dword [scenario_mode],0
 jne .fail
 mov rdi,[connect_address]
 mov esi,[server_port]
 call net_client_open
 test eax,eax
 jnz .fail
.platforminit:
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
 mov edi,[view_width]
 mov esi,[view_height]
 lea rdx,[title]
 xor ecx,ecx
 xor r8d,r8d
 call glfwCreateWindow
 test rax,rax
 jz .terminatefail
 mov [window],rax
 mov rdi,rax
 lea rsi,[quit_key_event]
 call glfwSetKeyCallback
 mov rdi,[window]
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
 UNIFORM projection_name,projection_loc
 UNIFORM cam_name,cam_loc
 UNIFORM angle_name,angle_loc
 UNIFORM terrain_name,terrain_loc
 UNIFORM tactical_name,tactical_loc
 UNIFORM weapon_name,weapon_loc
 UNIFORM operation_name,operation_loc
 UNIFORM goal_name,goal_loc
 UNIFORM health_name,health_loc
 UNIFORM local_name,local_loc
 UNIFORM vehicle_name,vehicle_loc
 UNIFORM incoming_name,incoming_loc
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
 mov edx,[view_width]
 mov ecx,[view_height]
 call glViewport
 mov rdi,[window]
 lea rsi,[old_x]
 lea rdx,[old_y]
 call glfwGetCursorPos
 call glfwGetTime
 movsd [last_time],xmm0
 call environment_init
 test eax,eax
 jnz .destroyfail
 call meshes_init
 test eax,eax
 jnz .destroyfail
 mov edi,[program]
 call command_hud_init
 test eax,eax
 jnz .destroyfail
 cmp dword [census_requested],0
 je .nocensusinit
 call visibility_init
 test eax,eax
 jnz .destroyfail
.nocensusinit:
 mov edi,[program]
 call glUseProgram
 mov edi,[vao]
 call glBindVertexArray
 mov edi,0x8892
 mov esi,[vbo]
 call glBindBuffer
 call audio_init
 call audio_footsteps_reset
 call metrics_init
 call battle_metrics_reset
.loop:
 call metrics_frame_begin
 call audio_update
 call glfwPollEvents
 cmp dword [network_mode],0
 je .input
 call poll_network
.input:
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
 cmp dword [network_mode],0
 jne .networktick
 call sim_tick
 inc dword [local_sim_ticks]
 jmp .tick
.networktick:
 call network_tick
 jmp .tick
.render:
 call sync_player
 mov edi,[local_player]
 movss xmm0,[camera]
 movss xmm1,[camera+4]
 movss xmm2,[camera+8]
 movss xmm3,[yaw]
 call hazard_warning_update
 ; Camera right is (cos yaw, -sin yaw) in the authored x/z convention.
 mov edi,[local_player]
 movss xmm0,[camera]
 movss xmm1,[camera+4]
 movss xmm2,[camera+8]
 movss xmm3,[cos_yaw]
 movss xmm4,[sin_yaw]
 xorps xmm5,xmm5
 subss xmm5,xmm4
 movaps xmm4,xmm5
 call audio_scene_update
 mov edi,[local_player]
 movss xmm0,[frame_delta]
 call audio_footsteps_update
 movss xmm0,[frame_delta]
 call environment_step
 mov edi,[program]
 call environment_apply
 call update_visual
 mov edi,[local_player]
 movss xmm0,[frame_delta]
 call effects_update
 cmp dword [network_mode],0
 je .localcosmetics
 movss xmm0,[frame_delta]
 cmp dword [net_projectiles_clock_frozen],0
 je .networkcosmeticdt
 xorps xmm0,xmm0
.networkcosmeticdt:
 call net_projectiles_update
.localcosmetics:
 mov edi,[local_player]
 movss xmm0,[frame_delta]
 call air_trails_update
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
 mov dword [census_frame],0
 cmp dword [census_requested],0
 je .nocensusbegin
 mov eax,[frame_count]
 inc eax
 cmp eax,[frame_limit]
 jne .nocensusbegin
 call visibility_begin
 mov dword [census_frame],1
.nocensusbegin:
 mov edi,[cam_loc]
 movss xmm0,[camera]
 movss xmm1,[camera+4]
 movss xmm2,[camera+8]
 call glUniform3f
 mov edi,[projection_loc]
 movss xmm0,[view_projection]
 movss xmm1,[view_projection+4]
 call glUniform2f
 mov edi,[angle_loc]
 movss xmm0,[yaw]
 movss xmm1,[pitch]
 addss xmm1,[recoil]
 call glUniform2f
 mov edi,[tactical_loc]
 mov esi,[tactical]
 call glUniform1i
 mov edi,[vehicle_loc]
 mov eax,[local_player]
 lea rdx,[sim_player_vehicle]
 mov ecx,[rdx+rax*4]
 pxor xmm0,xmm0
 pxor xmm1,xmm1
 pxor xmm2,xmm2
 pxor xmm3,xmm3
 test ecx,ecx
 js .vehicleuniform
 movss xmm0,[fone]
 shl eax,5
 lea rdx,[sim_vehicles]
 cvtsi2ss xmm1,[rdx+rax+VEHICLE_AMMO]
 cvtsi2ss xmm2,[rdx+rax+VEHICLE_COOLDOWN]
 inc ecx
 cvtsi2ss xmm3,ecx
.vehicleuniform:
 call glUniform4f
 cmp dword [tactical],0
 jne .skyskip
 mov edi,0xb71
 call glDisable
 mov edi,[terrain_loc]
 mov esi,9
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,3
 call glDrawArrays
 mov edi,0xb71
 call glEnable
.skyskip:
 mov edi,[terrain_loc]
 mov esi,1
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,98304
 call glDrawArrays
 ; Bounded 5 m relief tile: 100 x 175 cells, six vertices each. The vertex
 ; shader clips only the coarse cells this replaces and retains terrain material.
 mov edi,[terrain_loc]
 mov esi,11
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,105000
 call glDrawArrays
 mov edi,[tactical]
 mov esi,[local_player]
 movss xmm0,[camera]
 movss xmm1,[camera+4]
 movss xmm2,[camera+8]
 movss xmm3,[yaw]
 movss xmm4,[pitch]
 addss xmm4,[recoil]
 movss xmm5,[frame_delta]
 movss xmm6,[recoil]
 movss xmm7,[reload_progress]
 call meshes_draw
 cmp dword [census_frame],0
 je .nocensusworldend
 call visibility_world_end
.nocensusworldend:
 mov edi,[program]
 call glUseProgram
 mov edi,[vao]
 call glBindVertexArray
 mov edi,0x8892
 mov esi,[vbo]
 call glBindBuffer
 mov edi,32
 call set_instance_layout
 cmp dword [tactical],0
 je .worldmodelsdone
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
.worldmodelsdone:
 mov edi,64
 call set_instance_layout
 mov edi,0x8892
 mov esi,32768
 lea rdx,[sim_projectiles]
 cmp dword [network_mode],0
 je .projectileupload
 cmp dword [net_projectiles_visible],0
 je .skipprojectiles
 lea rdx,[net_projectiles]
.projectileupload:
 mov ecx,0x88e0
 call glBufferData
 mov edi,[terrain_loc]
 mov esi,8
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,36
 mov ecx,512
 call glDrawArraysInstanced
.skipprojectiles:
 mov edi,32
 call set_instance_layout
 mov edi,0xbe2
 call glEnable
 mov edi,0x302
 mov esi,0x303
 call glBlendFunc
 xor edi,edi
 call glDepthMask
 mov edi,0x8892
 mov esi,2048
 lea rdx,[effects_records]
 mov ecx,0x88e0
 call glBufferData
 mov edi,[terrain_loc]
 mov esi,7
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,6
 mov ecx,64
 call glDrawArraysInstanced
 cmp dword [air_trails_visible],0
 je .trailsskip
 mov edi,0x8892
 mov esi,4096
 lea rdx,[air_trails_records]
 mov ecx,0x88e0
 call glBufferData
 mov edi,4
 xor esi,esi
 mov edx,6
 mov ecx,128
 call glDrawArraysInstanced
.trailsskip:
 cmp dword [tactical],0
 jne .rainskip
 mov edi,[terrain_loc]
 mov esi,10
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,3072
 call glDrawArrays
.rainskip:
 mov edi,1
 call glDepthMask
 mov edi,0xbe2
 call glDisable
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
 mov edi,[incoming_loc]
 movss xmm0,[hazard_warning_uniform]
 movss xmm1,[hazard_warning_uniform+4]
 movss xmm2,[hazard_warning_uniform+8]
 movss xmm3,[hazard_warning_uniform+12]
 call glUniform4f
 mov edi,0xb71
 call glDisable
 mov edi,[terrain_loc]
 mov esi,2
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,282
 call glDrawArrays
 cmp dword [tactical],0
 je .restoredepth
 call selected_goal
 mov edi,[goal_loc]
 call glUniform2f
 mov edi,[terrain_loc]
 mov esi,4
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,12
 call glDrawArrays
.restoredepth:
 call command_panel_draw
 mov edi,0xb71
 call glEnable
.nohud:
 call metrics_gpu_end
 call battle_metrics_capture
 inc dword [frame_count]
 mov eax,[frame_limit]
 test eax,eax
 jz .swap
 cmp [frame_count],eax
 jb .swap
 cmp dword [census_frame],0
 je .nocensusfinish
 ; Ordinary frame timing ends before diagnostic synchronization/readback/blit.
 call metrics_frame_end
 mov dword [final_frame_ended],1
 call visibility_finish
 test eax,eax
 jnz .destroyfail
 mov rdi,[census_map_path]
 call visibility_write_map
 test eax,eax
 jnz .destroyfail
 mov dword [census_finished],1
.nocensusfinish:
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
 cmp dword [census_requested],0
 je .censuscomplete
 cmp dword [census_finished],0
 je .destroyfail
.censuscomplete:
 cmp dword [final_frame_ended],0
 jne .frameended
 call metrics_frame_end
.frameended:
 call metrics_report
 cmp dword [census_finished],0
 je .nocensusreport
 call visibility_report
.nocensusreport:
 call battle_metrics_report
 sub rsp,16
 lea rdi,[mesh_metrics]
 mov esi,[mesh_asset_count]
 mov edx,[mesh_high_instances]
 mov ecx,[mesh_low_instances]
 mov r8d,[mesh_marker_instances]
 ; printf's sixth argument is triangles in R9, animation is the first stack arg.
 mov r9d,[mesh_source_triangles]
 mov eax,[mesh_animation_sample]
 mov [rsp],rax
 xor eax,eax
 call printf
 add rsp,16
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
 call selected_goal
 cvtss2sd xmm0,xmm0
 cvtss2sd xmm1,xmm1
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
 cmp dword [network_mode],0
 je .nonetreport
 sub rsp,16
 mov eax,[local_sim_ticks]
 mov [rsp],rax
 lea rdi,[net_metrics]
 mov esi,[net_connected]
 mov edx,[net_player_id]
 mov ecx,[net_front]
 mov r8d,[net_server_tick]
 mov r9d,[known_entities]
 xor eax,eax
 call printf
 add rsp,16
.nonetreport:
 call visibility_shutdown
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
 call visibility_shutdown
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
 cmp dword [network_mode],0
 je .closed
 call net_client_close
.closed:
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

; Continuous controls are polled. A delivered Escape press survives a slow
; frame even when release is delivered in the same glfwPollEvents batch.
quit_key_event:
 cmp esi,256
 jne .done
 cmp ecx,1
 jne .done
 mov dword [quit_latched],1
.done:
 ret

%macro KEY 1
 mov rdi,[window]
 mov esi,%1
 call glfwGetKey
%endmacro
update_input:
 push rbx
 cmp dword [quit_latched],0
 jne .quit
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
 KEY 293
 test eax,eax
 jz .weatherup
 cmp dword [weather_down],0
 jne .weatherdone
 call environment_cycle
 mov dword [weather_down],1
 jmp .weatherdone
.weatherup:
 mov dword [weather_down],0
.weatherdone:
 call transfer_refresh
 call transfer_keys
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
 jz .keyreleased
.networkorder:
 mov ecx,ebx
 sub ecx,49
 bts dword [order_down_mask],ecx
 jc .nextorder
 call selected_goal
 ; First advance selects the next hostile deployment/command site in this row.
 comiss xmm0,[fzero]
 jae .havegoal
 cmp ebx,49
 jne .playergoal
 mov eax,[selected_front]
 shl eax,7
 lea rdx,[sim_sites+64]
 add rdx,rax
 cmp dword [rdx+8],1
 je .sitegoal
 add rdx,32
.sitegoal:
 movss xmm0,[rdx]
 movss xmm1,[rdx+4]
 jmp .havegoal
.playergoal:
 call player_pointer
 movss xmm0,[rax+PLAYER_X]
 movss xmm1,[rax+PLAYER_Z]
.havegoal:
 mov edi,[selected_front]
 mov esi,ebx
 sub esi,49
 cmp dword [network_mode],0
 jne .sendnetwork
 call queue_local_order
 jmp .nextorder
.sendnetwork:
 call queue_network_order
 jmp .nextorder
.keyreleased:
 mov ecx,ebx
 sub ecx,49
 btr dword [order_down_mask],ecx
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
 mulss xmm0,[view_sensitivity]
 addss xmm0,[yaw]
 movss [yaw],xmm0
 movsd xmm0,[cursor_y]
 subsd xmm0,[old_y]
 cvtsd2ss xmm0,xmm0
 mulss xmm0,[view_sensitivity]
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
 cmp dword [network_mode],0
 jne .afterintent
 mov edi,[local_player]
 mov esi,[intent_buttons]
 movss xmm0,[wish_x]
 movss xmm1,[wish_z]
 movss xmm2,[yaw]
 movss xmm3,[pitch]
 call player_input
.afterintent:
 cmp dword [tactical],0
 je .title
 call tactical_click
.title:
 mov eax,[local_player]
 lea rdx,[sim_player_vehicle]
 mov ecx,[rdx+rax*4]
 test ecx,ecx
 js .onfoottitle
 shl eax,5
 lea rdx,[sim_vehicles]
 mov r8d,[rdx+rax+VEHICLE_AMMO]
 mov r9d,[rdx+rax+VEHICLE_COOLDOWN]
 lea rdi,[vehicle_buf]
 mov esi,160
 lea rdx,[vehicle_fmt]
 sub rsp,16
 mov eax,ecx
 shl eax,5
 lea r10,[sim_entities]
 mov eax,[r10+rax+8]
 mov [rsp],rax
 xor eax,eax
 call snprintf
 add rsp,16
 lea rbx,[vehicle_buf]
 jmp .havevehicletitle
.onfoottitle:
 lea rbx,[onfoot_text]
.havevehicletitle:
 sub rsp,80
 mov [rsp+64],rbx
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
 cmp dword [network_mode],0
 je .unitstitle
 mov ecx,[known_entities]
.unitstitle:
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
 add rsp,80
 cmp dword [network_mode],0
 je .localtitle
 mov edi,[net_player_id]
 call net_company_for_player
 sub rsp,32
 mov [rsp+16],rax
 lea rax,[transfer_info]
 mov [rsp+24],rax
 mov eax,[net_server_tick]
 mov [rsp],rax
 mov rax,[command_message]
 cmp dword [net_connected],0
 jne .netmsg
 lea rax,[joining_text]
.netmsg:
 mov [rsp+8],rax
 lea rdi,[net_title_buf]
 mov esi,640
 lea rdx,[net_fmt]
 lea rcx,[title_buf]
 mov r8d,[net_player_id]
 mov r9d,[net_front]
 xor eax,eax
 call snprintf
 add rsp,32
 mov rdi,[window]
 lea rsi,[net_title_buf]
 call set_weather_title
 jmp .titlereturn
.localtitle:
 mov edi,[local_player]
 call company_for_player
 mov r8d,eax
 lea rdi,[net_title_buf]
 mov esi,640
 lea rdx,[local_company_fmt]
 lea rcx,[title_buf]
 mov r9,[command_message]
 xor eax,eax
 call snprintf
 mov rdi,[window]
 lea rsi,[net_title_buf]
 call set_weather_title
.titlereturn:
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
 divss xmm0,[view_half_size]
 subss xmm0,[fone]
 mulss xmm0,[map_scale]
 addss xmm0,[map_centre]
 cvtsd2ss xmm1,[cursor_y]
 divss xmm1,[view_half_size+4]
 movss xmm2,[fone]
 subss xmm2,xmm1
 movaps xmm1,xmm2
 mulss xmm1,[map_scale]
 addss xmm1,[map_centre]
 cmp dword [network_mode],0
 je .localwaypoint
 mov edi,[selected_front]
 xor esi,esi
 call queue_network_order
 jmp .return
.localwaypoint:
 mov edi,[selected_front]
 xor esi,esi
 call queue_local_order
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
 jz .crouch
 or dword [intent_buttons],INPUT_SPRINT
.crouch:
 KEY 341
 test eax,eax
 jz .jump
 or dword [intent_buttons],INPUT_CROUCH
.jump:
 KEY 32
 test eax,eax
 jz .reload
 or dword [intent_buttons],INPUT_JUMP
.reload:
 KEY 82
 test eax,eax
 jz .trigger
 or dword [intent_buttons],INPUT_RELOAD
.trigger:
 KEY 69
 test eax,eax
 jz .exitvehicle
 or dword [intent_buttons],INPUT_ENTER
.exitvehicle:
 KEY 81
 test eax,eax
 jz .firevehicle
 or dword [intent_buttons],INPUT_EXIT
.firevehicle:
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

; One bounded pending order is retried before inputs; no local world tick runs.
poll_network:
 push rbx
 mov ebx,[net_front]
 call net_client_poll
 cmp dword [net_connected],1
 jne .count
 mov eax,[net_player_id]
 cmp eax,3
 ja .count
 mov [local_player],eax
 cmp dword [network_joined],0
 je .new_join
 cmp ebx,[net_front]
 je .new_join
 cmp ebx,[selected_front]
 jne .new_join
 mov eax,[net_front]
 mov [selected_front],eax
.new_join:
 cmp dword [network_joined],0
 jne .clock
 mov dword [network_joined],1
 mov dword [last_owned_company],-1
 mov eax,[net_front]
 mov [selected_front],eax
 mov dword [last_generation],0
.clock:
 mov eax,[net_server_tick]
 cmp eax,[last_net_tick]
 je .status
 mov [last_net_tick],eax
 call glfwGetTime
 movsd [last_net_time],xmm0
.status:
 cmp dword [net_last_status],0
 je .count
 lea rax,[net_reject_text]
 mov [command_message],rax
.count:
 mov edi,[local_player]
 call net_company_for_player
 cmp eax,-1
 je .company_count_done
 cmp dword [last_owned_company],-1
 je .company_count_store
 cmp eax,[last_owned_company]
 je .company_count_done
 lea rdx,[transfer_accepted]
 cmp [command_message],rdx
 je .company_count_store
 lea rdx,[transfer_changed]
 mov [command_message],rdx
.company_count_store:
 mov [last_owned_company],eax
.company_count_done:
 xor ecx,ecx
 xor edx,edx
 lea rax,[sim_entities]
.scan:
 cmp ecx,[sim_count]
 jae .done
 cmp dword [rax+8],0
 je .next
 inc edx
.next:
 add rax,32
 inc ecx
 jmp .scan
.done:
 mov [known_entities],edx
 pop rbx
 ret

; Display current validated company identity and existing command feedback.
command_panel_draw:
 push rbx
 call command_hud_begin
 cmp dword [network_mode],0
 jne .remote
 mov edi,[local_player]
 call company_for_player
 jmp .format
.remote:
 cmp dword [net_connected],1
 jne .lost
 mov edi,[local_player]
 call net_company_for_player
.format:
 lea rdi,[command_panel]
 mov esi,160
 lea rdx,[command_panel_fmt]
 mov ecx,eax
 mov r8d,[selected_front]
 xor eax,eax
 call snprintf
 lea rbx,[command_panel]
 jmp .draw
.lost:
 lea rbx,[command_panel_lost]
.draw:
 mov edi,[terrain_loc]
 mov esi,12
 call glUniform1i
 mov rdi,rbx
 xor esi,esi
 call command_hud_draw
 mov rdi,[command_message]
 mov esi,1
 call command_hud_draw
 cmp dword [network_mode],0
 je .done
 lea rdi,[transfer_info]
 mov esi,2
 call command_hud_draw
.done:
 pop rbx
 ret

selected_goal:
 mov eax,[selected_front]
 cmp dword [network_mode],0
 jne .network
 push rbx
 mov rbx,rax
 mov edi,[local_player]
 call player_pointer
 cmp ebx,[rax+PLAYER_FRONT]
 jne .localunknown
 mov edi,[local_player]
 call company_for_player
 cmp eax,-1
 je .localunknown
 shl eax,5
 lea rdx,[company_controls]
 cmp dword [rdx+rax+12],0
 je .localunknown
 movss xmm0,[rdx+rax+16]
 movss xmm1,[rdx+rax+20]
 pop rbx
 ret
.localunknown:
 pop rbx
 jmp .unknown
.network:
 ; Own selected front prefers own company; other fronts expose a validated
 ; allied owner's actual accepted intent. No optimistic ACK cache authority.
 push rbx
 push r12
 sub rsp,8
 mov ebx,eax
 mov r12d,[net_player_id]
 cmp r12d,4
 jae .remote_none
 mov edi,r12d
 call .remote_goal
 test eax,eax
 jz .remote_done
 xor r12d,r12d
.remote_scan:
 mov edi,r12d
 call .remote_goal
 test eax,eax
 jz .remote_done
 inc r12d
 cmp r12d,4
 jb .remote_scan
.remote_none:
 movss xmm0,[offscreen]
 movaps xmm1,xmm0
.remote_done:
 add rsp,8
 pop r12
 pop rbx
 ret
.remote_goal:
 sub rsp,8
 call net_company_for_player
 add rsp,8
 cmp eax,-1
 je .remote_missing
 shr eax,8
 cmp eax,ebx
 jne .remote_missing
 imul eax,r12d,40
 lea rdx,[net_company_records]
 cmp dword [rdx+rax+20],1
 jne .remote_missing
 movss xmm0,[rdx+rax+24]
 movss xmm1,[rdx+rax+28]
 xor eax,eax
 ret
.remote_missing:
 mov eax,-1
 ret
.unknown:
 movss xmm0,[offscreen]
 movaps xmm1,xmm0
 ret

; Solo uses the same exclusive lease, validation and single charge as authority.
; EDI selected front,ESI mode,XMM0/1 goal. One edge triggers one command.
queue_local_order:
 push rbx
 sub rsp,16
 mov [rsp],edi
 mov [rsp+4],esi
 mov edi,[local_player]
 call player_pointer
 mov ecx,[rsp]
 cmp ecx,[rax+PLAYER_FRONT]
 jne .denied
 mov edi,[local_player]
 call company_for_player
 cmp eax,-1
 je .denied
 mov esi,eax
 mov edi,[local_player]
 mov edx,[rsp+4]
 call company_control_order
 test eax,eax
 jnz .rejected
 inc dword [waypoint_orders]
 mov eax,[rsp+4]
 mov [order_mode],eax
 lea rax,[net_sent_text]
 mov [command_message],rax
 xor eax,eax
 jmp .done
.denied:
 lea rax,[net_denied_text]
 jmp .failure
.rejected:
 lea rax,[local_reject_text]
.failure:
 mov [command_message],rax
 mov eax,-1
.done:
 add rsp,16
 pop rbx
 ret

 ; Derived incoming offer display. Stable requester ordering; explicit user consent.
transfer_refresh:
 push rbx
 push r12
 sub rsp,8
 mov dword [incoming_owner],-1
 mov dword [incoming_sequence],0
 xor r12d,r12d
 cmp dword [net_connected],1
 jne .none
.scan:
 mov edi,[local_player]
 mov esi,r12d
 call net_company_offer
 cmp eax,-1
 jne .offer
 inc r12d
 cmp r12d,4
 jb .scan
.none:
 lea rdi,[transfer_info]
 mov esi,192
 lea rdx,[transfer_none]
 xor eax,eax
 call snprintf
 jmp .done
.offer:
 mov [incoming_owner],r12d
 mov [incoming_sequence],eax
 lea rdi,[transfer_info]
 mov esi,192
 lea rdx,[transfer_offer_fmt]
 mov ecx,r12d
 xor eax,eax
 call snprintf
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
transfer_keys:
 push rbx
 mov ebx,294
.loop:
 mov rdi,[window]
 mov esi,ebx
 call glfwGetKey
 mov ecx,ebx
 sub ecx,294
 test eax,eax
 jz .released
 bts dword [transfer_key_mask],ecx
 jc .next
 cmp ebx,298
 jae .response
 xor edi,edi
 mov esi,ebx
 sub esi,294
 xor edx,edx
 jmp .submit
.response:
 mov edi,ebx
 sub edi,297
 cmp edi,3
 je .cancel
 mov esi,[incoming_owner]
 cmp esi,-1
 je .missing
 mov edx,[incoming_sequence]
 jmp .submit
.cancel:
 mov eax,[local_player]
 cmp eax,4
 jae .missing
 imul eax,48
 lea rdx,[net_company_transfers]
 cmp dword [rdx+rax],1
 jne .missing
 mov esi,[rdx+rax+4]
 mov edx,[rdx+rax+36]
.submit:
 call queue_transfer
 jmp .next
.missing:
 lea rax,[transfer_missing]
 mov [command_message],rax
 jmp .next
.released:
 btr dword [transfer_key_mask],ecx
.next:
 inc ebx
 cmp ebx,301
 jb .loop
 pop rbx
 ret
queue_transfer:
 cmp dword [network_mode],1
 jne .invalid
 cmp dword [net_connected],1
 jne .invalid
 cmp dword [command_pending],0
 jne .invalid
 cmp dword [transfer_pending],0
 jne .invalid
 cmp edi,3
 ja .invalid
 cmp esi,4
 jae .invalid
 cmp esi,[local_player]
 je .invalid
 ; Movement may be awaiting ACK: retain the explicit action until transport free.
 mov [transfer_action],edi
 mov [transfer_other],esi
 mov [transfer_sequence],edx
 mov dword [transfer_pending],1
 lea rax,[net_queue_text]
 mov [command_message],rax
 ret
.invalid:
 lea rax,[transfer_failed]
 mov [command_message],rax
 ret

queue_network_order:
 cmp dword [transfer_pending],0
 jne .busy
 cmp dword [command_pending],2
 je .busy
 cmp dword [net_connected],1
 jne .unconnected
 cmp edi,[net_front]
 jne .denied
 ucomiss xmm0,[fzero]
 jp .bounds
 jb .bounds
 ucomiss xmm1,[fzero]
 jp .bounds
 jb .bounds
 ucomiss xmm0,[world_max]
 ja .bounds
 ucomiss xmm1,[world_max]
 ja .bounds
 mov [command_front],edi
 mov [command_mode],esi
 movss [command_goal],xmm0
 movss [command_goal+4],xmm1
 mov dword [command_pending],1
 lea rax,[net_queue_text]
 mov [command_message],rax
 xor eax,eax
 ret
.busy:
 lea rax,[net_busy_text]
 jmp .failure
.denied:
 lea rax,[net_denied_text]
 jmp .failure
.bounds:
 lea rax,[net_bounds_text]
 jmp .failure
.unconnected:
 lea rax,[joining_text]
.failure:
 mov [command_message],rax
 mov eax,-1
 ret

network_tick:
 push rbx
 cmp dword [transfer_pending],0
 jne .transfer_wait
 cmp dword [command_pending],2
 je .awaitack
 cmp dword [command_pending],0
 je .input
 mov edi,[command_front]
 mov esi,[command_mode]
 movss xmm0,[command_goal]
 movss xmm1,[command_goal+4]
 call net_client_order
 test eax,eax
 jnz .return
 mov dword [command_pending],2
 jmp .return
 .transfer_wait:
 cmp dword [net_connected],1
 jne .transfer_disconnected
 cmp dword [transfer_pending],1
 je .transfer_send
 cmp dword [net_pending],0
 jne .return
 mov dword [transfer_pending],0
 cmp dword [net_last_status],0
 jne .transfer_reject
 mov eax,[transfer_action]
 lea rdx,[transfer_ack_messages]
 mov rax,[rdx+rax*8]
 mov [command_message],rax
 jmp .return
.transfer_send:
 mov edi,[transfer_action]
 mov esi,[transfer_other]
 mov edx,[transfer_sequence]
 call net_client_transfer
 test eax,eax
 jnz .return
 mov dword [transfer_pending],2
 jmp .return
.transfer_disconnected:
 mov dword [transfer_pending],0
.transfer_reject:
 lea rax,[transfer_failed]
 mov [command_message],rax
 jmp .return
.awaitack:
 cmp dword [net_connected],1
 jne .disconnected
 cmp dword [net_pending],0
 jne .return
 mov dword [command_pending],0
 cmp dword [net_last_status],0
 jne .rejected
 inc dword [waypoint_orders]
 mov eax,[command_mode]
 mov [order_mode],eax
 mov eax,[command_front]
 lea rdx,[net_goal]
 movss xmm0,[command_goal]
 movss [rdx+rax*8],xmm0
 movss xmm0,[command_goal+4]
 movss [rdx+rax*8+4],xmm0
 lea rdx,[net_goal_valid]
 mov dword [rdx+rax*4],1
 lea rax,[net_sent_text]
 mov [command_message],rax
 jmp .return
.rejected:
 lea rax,[net_reject_text]
 mov [command_message],rax
 jmp .return
.disconnected:
 mov dword [command_pending],0
 lea rax,[joining_text]
 mov [command_message],rax
 jmp .return
.input:
 mov esi,[intent_buttons]
 movss xmm0,[wish_x]
 movss xmm1,[wish_z]
 movss xmm2,[yaw]
 movss xmm3,[pitch]
 call net_client_input
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
 mov edi,3
 call glEnableVertexAttribArray
 mov edi,3
 mov esi,4
 mov edx,0x1406
 xor ecx,ecx
 mov r8d,64
 mov r9d,48
 call glVertexAttribPointer
 mov edi,3
 mov esi,1
 call glVertexAttribDivisor
 jmp .done
.disable:
 mov edi,2
 call glDisableVertexAttribArray
 mov edi,3
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
 movss xmm0,[rbx+PLAYER_X]
 movss [visual_target],xmm0
 movss xmm0,[rbx+PLAYER_Y]
 movss [visual_target+4],xmm0
 movss xmm0,[rbx+PLAYER_Z]
 movss [visual_target+8],xmm0
 cmp dword [network_mode],0
 je .noprediction
 cmp dword [net_connected],1
 jne .noprediction
 cmp dword [rbx+PLAYER_HP],0
 je .noprediction
 mov eax,[local_player]
 lea rdx,[sim_player_vehicle]
 cmp dword [rdx+rax*4],0
 jge .noprediction ; boarded eye follows received hull authority, no foot strafe
 call glfwGetTime
 subsd xmm0,[last_net_time]
 comisd xmm0,[net_predict_timeout]
 ja .noprediction
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 movaps xmm2,xmm0
 movaps xmm3,xmm1
 addss xmm2,[wish_x]
 addss xmm3,[wish_z]
 movss xmm4,[crouch_prediction]
 test dword [intent_buttons],INPUT_CROUCH
 jnz .predictstep
 movss xmm4,[walk_prediction]
 test dword [intent_buttons],INPUT_SPRINT
 jz .predictstep
 movss xmm4,[sprint_prediction]
.predictstep:
 xor edi,edi
 lea rsi,[net_wrecks]
 mov edx,[net_wreck_count]
 mov rcx,[net_wreck_query_revision]
 call world_body_step_context
 movss [visual_target],xmm0
 movss [visual_target+8],xmm1
 call terrain_height
 mov eax,[local_player]
 lea rdx,[sim_player_vehicle]
 cmp dword [rdx+rax*4],0
 jl .previewfoot
 ; Preserve the authoritative armor eye height during this one-tick preview.
 movss xmm0,[rbx+PLAYER_Y]
 jmp .previewheight
.previewfoot:
 ; Preserve received standing/crouch/jump altitude during bounded XZ preview.
 movss xmm0,[rbx+PLAYER_Y]
.previewheight:
 movss [visual_target+4],xmm0
.noprediction:
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
 movss xmm0,[visual_target]
 subss xmm0,[camera]
 andps xmm0,[absolute_mask]
 comiss xmm0,[snap_distance]
 ja .snap
 movss xmm0,[visual_target+8]
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
 movss xmm0,[visual_target+off]
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

parse_frame_limit:
 xor eax,eax
 xor ecx,ecx
.framesdigits:
 movzx edx,byte [rdi]
 test edx,edx
 jz .framesend
 sub edx,'0'
 cmp edx,9
 ja .framesbad
 cmp eax,214748364
 ja .framesbad
 jne .framesmultiply
 cmp edx,7
 ja .framesbad
.framesmultiply:
 imul eax,10
 add eax,edx
 inc ecx
 inc rdi
 jmp .framesdigits
.framesend:
 test ecx,ecx
 jz .framesbad
 ret
.framesbad:
 xor eax,eax
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
 mov edx,[view_width]
 mov ecx,[view_height]
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
 mov esi,64
 lea rdx,[ppm_format]
 mov ecx,[view_width]
 mov r8d,[view_height]
 xor eax,eax
 call snprintf
 mov [ppm_header_len],eax
 mov eax,[view_width]
 imul eax,3
 mov [row_bytes],eax
 lea rdi,[ppm_header]
 mov esi,1
 mov edx,[ppm_header_len]
 mov rcx,rbx
 call fwrite
 cmp eax,[ppm_header_len]
 jne .closeerror
 mov r12d,[view_height]
 dec r12d
.rows:
 mov eax,r12d
 imul eax,[row_bytes]
 lea rdi,[pixels]
 add rdi,rax
 mov esi,1
 mov edx,[row_bytes]
 mov rcx,rbx
 call fwrite
 cmp eax,[row_bytes]
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

section .text
; Append cosmetic preset name without changing gameplay/UI state.
set_weather_title:
 push rbx
 push r12
 sub rsp,8
 mov rbx,rdi
 mov r12,rsi
 call environment_name
 mov r8,rax
 mov rcx,r12
 lea rdi,[weather_title_buf]
 mov esi,768
 lea rdx,[weather_suffix]
 xor eax,eax
 call snprintf
 mov rdi,rbx
 lea rsi,[weather_title_buf]
 call glfwSetWindowTitle
 add rsp,8
 pop r12
 pop rbx
 ret
