; Linux SysV client. GLFW provides only OS window/context/input services.
default rel
global main
extern audio_init,audio_shot,audio_update,audio_shutdown
extern glfwGetVersion
extern sim_init,sim_tick,sim_order,sim_fire,sim_count,sim_entities
extern battle_vertex_source,battle_fragment_source
extern glfwInitHint,glfwInit,glfwTerminate,glfwWindowHint,glfwCreateWindow,glfwDestroyWindow
extern glfwMakeContextCurrent,glfwSwapInterval,glfwSwapBuffers,glfwPollEvents
extern glfwWindowShouldClose,glfwGetKey,glfwGetMouseButton,glfwGetCursorPos
extern glfwSetInputMode,glfwSetWindowTitle,glfwGetTime
extern glCreateShader,glShaderSource,glCompileShader,glGetShaderiv,glGetShaderInfoLog
extern glCreateProgram,glAttachShader,glLinkProgram,glGetProgramiv,glGetProgramInfoLog
extern glUseProgram,glGetUniformLocation,glUniform3f,glUniform2f,glUniform1i,glUniform4f
extern glGenVertexArrays,glBindVertexArray,glGenBuffers,glBindBuffer,glBufferData
extern glEnableVertexAttribArray,glVertexAttribPointer,glVertexAttribDivisor
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
write_mode: db 'wb',0
ppm_header: db 'P6',10,'1280 720',10,'255',10
ppm_header_len equ $-ppm_header
failure: db 'Client context/shader creation failed.',0
shader_error: db 'Shader/program error:',0
metrics: db 'camera_x=%.2f camera_z=%.2f shots=%u hits=%u last_order=%u',10,0
summary: db 'client frames=%u submitted_entities=%u screenshot=%s',10,0
no_shot: db '(none)',0
title_fmt: db 'RED HORIZON | %u units | rifle %u/30 %s | front %u order %u | R reload TAB map F1-F3 front 1-3 orders ESC',0
reload_text: db 'RELOADING',0
weapon_metrics: db 'weapon ammo=%u reloads=%u front=%u',10,0
fps_text: db 'FIRST PERSON',0
map_text: db 'TACTICAL',0
fzero: dd 0.0
world_max: dd 8000.0
height_a: dd 0.003
height_b: dd 0.002
height_c: dd 0.013
height_d: dd 0.006
height_15: dd 15.0
height_5: dd 5.0
eye_height: dd 1.8
fone: dd 1.0
speed: dd 5.0
sprint: dd 9.0
sensitivity: dd 0.002
pitch_max: dd 1.3
pitch_min: dd -1.3
shot_interval: dq 0.12
reload_interval: dq 2.0
recoil_step: dd 0.008
recoil_rate: dd 0.08
flash_decay: dd 8.0
thirty: dq 0.03333333333333333
maxdt: dq 0.1
minus: dd -1.0
aim_limit: dd 0.998
far_dist: dd 1000.0
target_height: dd 1.0
air_height: dd 90.0
section .data
camera: dd 4000.0,5.0,3200.0
yaw: dd 0.0
pitch: dd -0.04
frame_limit: dd 0
magazine: dd 30
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
selected_front: resd 1
reload_count: resd 1
reload_active: resd 1
reload_until: resq 1
next_shot: resq 1
weapon_now: resq 1
weapon_delta: resd 1
reload_progress: resd 1
recoil: resd 1
hit_flash: resd 1
shot_flash: resd 1
frame_count: resd 1
tactical: resd 1
tab_down: resd 1
fire_down: resd 1
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
step: resd 1
sin_yaw: resd 1
cos_yaw: resd 1
sin_pitch: resd 1
cos_pitch: resd 1
shader_status: resd 1
ray_x: resd 1
ray_y: resd 1
ray_z: resd 1
ray_best: resd 1
height_temp: resd 1
source_ptr: resq 1
log: resb 4096
title_buf: resb 256
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
.loop:
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
 mov edi,[weapon_loc]
 cvtsi2ss xmm0,[magazine]
 movss xmm1,[reload_progress]
 movss xmm2,[hit_flash]
 movss xmm3,[shot_flash]
 call glUniform4f
 mov edi,0xb71
 call glDisable
 mov edi,[terrain_loc]
 mov esi,2
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,216
 call glDrawArrays
 mov edi,0xb71
 call glEnable
.nohud:
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
 mov rdi,[window]
 call glfwWindowShouldClose
 test eax,eax
 jz .loop
.done:
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
 cmp dword [frame_count],3
 jae .aimdelta
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
 movss xmm0,[pitch]
 call sinf
 movss [sin_pitch],xmm0
 movss xmm0,[pitch]
 call cosf
 movss [cos_pitch],xmm0
 movss xmm0,[speed]
 movss [step],xmm0
 KEY 340
 test eax,eax
 jz .walk
 movss xmm0,[sprint]
 movss [step],xmm0
.walk:
 ; Movement uses actual frame elapsed, capped to prevent suspend jumps.
 call glfwGetTime
 subsd xmm0,[last_time]
 minsd xmm0,[maxdt]
 cvtsd2ss xmm0,xmm0
 mulss xmm0,[step]
 movss [step],xmm0
 KEY 87
 test eax,eax
 jz .back
 movss xmm0,[step]
 call move_forward
.back:
 KEY 83
 test eax,eax
 jz .left
 movss xmm0,[step]
 mulss xmm0,[minus]
 call move_forward
.left:
 KEY 65
 test eax,eax
 jz .right
 movss xmm0,[step]
 mulss xmm0,[minus]
 call move_right
.right:
 KEY 68
 test eax,eax
 jz .fire
 movss xmm0,[step]
 call move_right
.fire:
 movss xmm0,[camera]
 maxss xmm0,[fzero]
 minss xmm0,[world_max]
 movss [camera],xmm0
 movss xmm0,[camera+8]
 maxss xmm0,[fzero]
 minss xmm0,[world_max]
 movss [camera+8],xmm0
 call camera_height
 call update_weapon
.title:
 sub rsp,16
 mov eax,[selected_front]
 mov [rsp],rax
 mov eax,[order_mode]
 mov [rsp+8],rax
 lea rdi,[title_buf]
 mov esi,256
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
 xor eax,eax
 call snprintf
 add rsp,16
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
; Rifle timing uses monotonic platform time. Reload, cadence, visual recovery are
; frame-rate independent. Persistent data contains no callback pointers.
update_weapon:
 push rbx
 call glfwGetTime
 movsd [weapon_now],xmm0
 subsd xmm0,[last_time]
 minsd xmm0,[maxdt]
 cvtsd2ss xmm0,xmm0
 movss [weapon_delta],xmm0
 mulss xmm0,[recoil_rate]
 minss xmm0,[recoil]
 movss xmm1,[recoil]
 subss xmm1,xmm0
 movss [recoil],xmm1
 movss xmm1,[pitch]
 subss xmm1,xmm0
 movss [pitch],xmm1
 movss xmm0,[weapon_delta]
 mulss xmm0,[flash_decay]
 movss xmm1,[hit_flash]
 subss xmm1,xmm0
 maxss xmm1,[fzero]
 movss [hit_flash],xmm1
 movss xmm1,[shot_flash]
 subss xmm1,xmm0
 maxss xmm1,[fzero]
 movss [shot_flash],xmm1
 cmp dword [reload_active],0
 je .reloadkey
 movsd xmm0,[reload_until]
 subsd xmm0,[weapon_now]
 pxor xmm1,xmm1
 comisd xmm0,xmm1
 jbe .finishreload
 divsd xmm0,[reload_interval]
 cvtsd2ss xmm0,xmm0
 movss [reload_progress],xmm0
 jmp .return
.finishreload:
 mov dword [magazine],30
 mov dword [reload_active],0
 mov dword [reload_progress],0
.reloadkey:
 KEY 82
 test eax,eax
 jz .trigger
 cmp dword [magazine],30
 je .trigger
 mov dword [reload_active],1
 inc dword [reload_count]
 movsd xmm0,[weapon_now]
 addsd xmm0,[reload_interval]
 movsd [reload_until],xmm0
 movss xmm0,[fone]
 movss [reload_progress],xmm0
 jmp .return
.trigger:
 mov rdi,[window]
 xor esi,esi
 call glfwGetMouseButton
 test eax,eax
 jz .return
 cmp dword [magazine],0
 je .return
 movsd xmm0,[weapon_now]
 comisd xmm0,[next_shot]
 jb .return
 addsd xmm0,[shot_interval]
 movsd [next_shot],xmm0
 dec dword [magazine]
 call fire_weapon
 movss xmm0,[pitch]
 movaps xmm1,xmm0
 addss xmm0,[recoil_step]
 minss xmm0,[pitch_max]
 movss [pitch],xmm0
 subss xmm0,xmm1
 addss xmm0,[recoil]
 movss [recoil],xmm0
 movss xmm0,[fone]
 movss [shot_flash],xmm0
.return:
 pop rbx
 ret

move_forward:
 movss xmm1,[sin_yaw]
 mulss xmm1,xmm0
 addss xmm1,[camera]
 movss [camera],xmm1
 mulss xmm0,[cos_yaw]
 addss xmm0,[camera+8]
 movss [camera+8],xmm0
 ret
move_right:
 movss xmm1,[cos_yaw]
 mulss xmm1,xmm0
 addss xmm1,[camera]
 movss [camera],xmm1
 mulss xmm0,[sin_yaw]
 subss xmm0,[camera+8]
 mulss xmm0,[minus]
 movss [camera+8],xmm0
 ret

camera_height:
 sub rsp,8
 movss xmm0,[camera]
 movss xmm1,[camera+8]
 call terrain_height
 addss xmm0,[eye_height]
 movss [camera+4],xmm0
 add rsp,8
 ret

; Shader-identical analytic terrain height. XMM0=x XMM1=z -> XMM0=y.
terrain_height:
 sub rsp,24
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 mulss xmm0,[height_a]
 call sinf
 movss [rsp+8],xmm0
 movss xmm0,[rsp+4]
 mulss xmm0,[height_b]
 call sinf
 mulss xmm0,[rsp+8]
 mulss xmm0,[height_15]
 movss [rsp+8],xmm0
 movss xmm0,[rsp]
 mulss xmm0,[height_c]
 movss xmm1,[rsp+4]
 mulss xmm1,[height_d]
 addss xmm0,xmm1
 call sinf
 mulss xmm0,[height_5]
 addss xmm0,[rsp+8]
 add rsp,24
 ret

; Local-solo 3D aim cone; no terrain occlusion or network validation yet.
; Nearest enemy within 1000m. sim_fire alone owns guarded health mutation.
fire_weapon:
 inc dword [shot_count]
 push rbx
 push r12
 push r13
 call audio_shot
 lea rbx,[sim_entities]
 xor r12d,r12d
 mov r13d,-1
 movss xmm0,[far_dist]
 movss [ray_best],xmm0
.scan:
 cmp r12d,[sim_count]
 jae .hit
 cmp dword [rbx+8],0
 je .next
 cmp dword [rbx+12],1
 jne .next
 movss xmm0,[rbx]
 movss xmm1,[rbx+4]
 call terrain_height
 addss xmm0,[target_height]
 cmp dword [rbx+16],3
 jne .ground
 addss xmm0,[air_height]
.ground:
 subss xmm0,[camera+4]
 movss [ray_y],xmm0
 movss xmm0,[rbx]
 subss xmm0,[camera]
 movss [ray_x],xmm0
 movss xmm1,[rbx+4]
 subss xmm1,[camera+8]
 movss [ray_z],xmm1
 movaps xmm2,xmm0
 mulss xmm2,xmm2
 movaps xmm3,xmm1
 mulss xmm3,xmm3
 addss xmm2,xmm3
 movss xmm3,[ray_y]
 mulss xmm3,xmm3
 addss xmm2,xmm3
 sqrtss xmm2,xmm2
 comiss xmm2,[fone]
 jb .next
 comiss xmm2,[ray_best]
 jae .next
 mulss xmm0,[sin_yaw]
 mulss xmm1,[cos_yaw]
 addss xmm0,xmm1
 mulss xmm0,[cos_pitch]
 movss xmm1,[ray_y]
 mulss xmm1,[sin_pitch]
 addss xmm0,xmm1
 divss xmm0,xmm2
 comiss xmm0,[aim_limit]
 jb .next
 movss [ray_best],xmm2
 mov r13d,r12d
.next:
 add rbx,32
 inc r12d
 jmp .scan
.hit:
 cmp r13d,-1
 je .return
 mov edi,r13d
 mov esi,34
 call sim_fire
 test eax,eax
 jnz .return
 inc dword [hit_count]
 movss xmm0,[fone]
 movss [hit_flash],xmm0
.return:
 pop r13
 pop r12
 pop rbx
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
