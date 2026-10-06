; Bounded source-mesh rendering and source-clip interpolation; no gameplay writes.
default rel
%include "schemas/entity.inc"
%include "schemas/player.inc"
%include "schemas/aircraft.inc"
%include "schemas/ground_motion.inc"
%include "schemas/ground_support.inc"
%include "schemas/ground_visual.inc"
%include "schemas/wreck.inc"
%include "schemas/wreck_instance.inc"
extern sim_wrecks,net_wrecks,net_connected,wreck_instance
extern view_projection,view_half_size
extern environment_apply
extern mesh_asset_load,mesh_asset_count,mesh_asset_descriptors,mesh_asset_clips
extern mesh_asset_vertices,mesh_asset_vec4_count,mesh_role_lookup
extern mesh_vertex_source,mesh_fragment_source
extern sim_ground_motion,ground_visual
extern company_for_player,net_company_for_player,network_mode
extern sim_count,sim_entities,sim_players,sim_player_vehicle,sim_sites,sim_aircraft
extern terrain_obstacles,terrain_obstacle_count
extern glCreateShader,glShaderSource,glCompileShader,glGetShaderiv,glGetShaderInfoLog
extern glCreateProgram,glAttachShader,glLinkProgram,glGetProgramiv,glUseProgram
extern glGenVertexArrays,glBindVertexArray,glGenBuffers,glBindBuffer,glBufferData,glBindBufferBase
extern glEnableVertexAttribArray,glVertexAttribPointer,glVertexAttribDivisor
extern glGetUniformLocation,glUniform3f,glUniform2f,glUniform2i,glUniform1i,glUniform1f
extern glDrawArraysInstanced,atan2f,puts
 global meshes_init,meshes_draw,mesh_high_instances,mesh_low_instances,mesh_marker_instances
 global mesh_aircraft_pose,mesh_ground_pose,mesh_ground_cache,mesh_frame
 global mesh_wreck_instances,mesh_wreck_pose,mesh_counts_complete
 global mesh_source_triangles,mesh_animation_sample,mesh_clock,mesh_selected_frames,mesh_selected_lerp
%define CACHE_COUNT 32772
section .rodata
projection_name: db 'projection',0
viewport_name: db 'halfViewport',0
camera_name: db 'camera',0
angle_name: db 'angle',0
geometry_name: db 'meshGeometry',0
scale_name: db 'meshScale',0
mode_name: db 'meshMode',0
census_name: db 'censusDetail',0
tactical_name: db 'tactical',0
weapon_name: db 'weaponMotion',0
mesh_error: db 'Animated source mesh shaders failed.',0
zero: dd 0.0
one: dd 1.0
half: dd 0.5
eyes: dd 1.8
phase_seed: dd 0.137
motion_hold: dd 0.12
motion_epsilon: dd 0.00001
dt_min: dd 0.001
run_speed: dd 6.0
high_range2: dd 22500.0
medium_range2: dd 640000.0
air_height: dd 90.0
align 16
tree_positions: dd 1900.,3720.,2100.,3740.,1800.,4150.,2250.,4100.,3450.,3500.,3550.,3530.,3650.,3520.,4500.,3700.,4600.,3730.,5500.,1300.,5520.,1330.,5500.,6500.,3000.,6100.,3020.,6120.,3300.,1700.,3370.,1730.
section .bss
mesh_counts_complete: resd 1 ; derived completed-pass telemetry, outside authority
mesh_wreck_instances: resd 1
mesh_wreck_pose: resd 16
mesh_ground_pose: resd 16 ; last actual ground instance, development diagnostics
mesh_aircraft_pose: resd 16 ; last actual aircraft instance, development diagnostics
mesh_program: resd 1
mesh_vao: resd 1
instance_vbo: resd 1
source_ssbo: resd 1
projection_loc: resd 1
viewport_loc: resd 1
camera_loc: resd 1
angle_loc: resd 1
geometry_loc: resd 1
scale_loc: resd 1
mode_loc: resd 1
census_loc: resd 1
tactical_loc: resd 1
weapon_loc: resd 1
view_weapon: resd 2
source_ptr: resq 1
shader_status: resd 1
shader_log: resb 2048
view_camera: resd 3
view_angle: resd 2
view_dt: resd 1
view_tactical: resd 1
view_player: resd 1
view_company: resd 1
view_vehicle: resd 1
mesh_clock: resd 1
mesh_frame: resd 1
mesh_ground_cache: resb 32768*VISUAL_STRIDE
mesh_high_instances: resd 1
mesh_low_instances: resd 1
mesh_marker_instances: resd 1
mesh_source_triangles: resd 1
mesh_animation_sample: resd 1
current_descriptor: resq 1
current_mode: resd 1
draw_lod: resd 1
side_budget: resd 2
alignb 16
instances: resb CACHE_COUNT*64
high_flags: resb 32768
last_generation: resd CACHE_COUNT
last_x: resd CACHE_COUNT
last_z: resd CACHE_COUNT
heading: resd CACHE_COUNT
moving_until: resd CACHE_COUNT
last_motion_clock: resd CACHE_COUNT
speed: resd CACHE_COUNT
mesh_selected_frames: resd CACHE_COUNT
mesh_selected_lerp: resd CACHE_COUNT
player_shots: resd 4
player_fire_until: resd 4
section .text
meshes_init:
 push rbx
 push r12
 push r13
 call mesh_asset_load
 test eax,eax
 jnz .failed
 mov edi,0x8b31
 lea rsi,[mesh_vertex_source]
 call .compile
 test eax,eax
 jz .shaderfailed
 mov r12d,eax
 mov edi,0x8b30
 lea rsi,[mesh_fragment_source]
 call .compile
 test eax,eax
 jz .shaderfailed
 mov r13d,eax
 call glCreateProgram wrt ..plt
 mov [mesh_program],eax
 mov edi,eax
 mov esi,r12d
 call glAttachShader wrt ..plt
 mov edi,[mesh_program]
 mov esi,r13d
 call glAttachShader wrt ..plt
 mov edi,[mesh_program]
 call glLinkProgram wrt ..plt
 mov edi,[mesh_program]
 mov esi,0x8b82
 lea rdx,[shader_status]
 call glGetProgramiv wrt ..plt
 cmp dword [shader_status],0
 je .shaderfailed
 mov edi,[mesh_program]
 call glUseProgram wrt ..plt
%macro LOCATION 2
 mov edi,[mesh_program]
 lea rsi,[%1]
 call glGetUniformLocation wrt ..plt
 mov [%2],eax
%endmacro
 LOCATION projection_name,projection_loc
 LOCATION viewport_name,viewport_loc
 LOCATION camera_name,camera_loc
 LOCATION angle_name,angle_loc
 LOCATION geometry_name,geometry_loc
 LOCATION scale_name,scale_loc
 LOCATION mode_name,mode_loc
 LOCATION census_name,census_loc
 LOCATION tactical_name,tactical_loc
 LOCATION weapon_name,weapon_loc
 mov edi,1
 lea rsi,[source_ssbo]
 call glGenBuffers wrt ..plt
 mov edi,0x90d2
 mov esi,[source_ssbo]
 call glBindBuffer wrt ..plt
 mov edi,0x90d2
 mov esi,[mesh_asset_vec4_count]
 shl rsi,4
 mov rdx,[mesh_asset_vertices]
 mov ecx,0x88e4
 call glBufferData wrt ..plt
 mov edi,0x90d2
 mov esi,3
 mov edx,[source_ssbo]
 call glBindBufferBase wrt ..plt
 mov edi,1
 lea rsi,[mesh_vao]
 call glGenVertexArrays wrt ..plt
 mov edi,[mesh_vao]
 call glBindVertexArray wrt ..plt
 mov edi,1
 lea rsi,[instance_vbo]
 call glGenBuffers wrt ..plt
 mov edi,0x8892
 mov esi,[instance_vbo]
 call glBindBuffer wrt ..plt
 xor ebx,ebx
.attribute:
 mov edi,ebx
 call glEnableVertexAttribArray wrt ..plt
 mov edi,ebx
 mov esi,4
 mov edx,0x1406
 xor ecx,ecx
 mov r8d,64
 mov r9d,ebx
 shl r9d,4
 call glVertexAttribPointer wrt ..plt
 mov edi,ebx
 mov esi,1
 call glVertexAttribDivisor wrt ..plt
 inc ebx
 cmp ebx,4
 jb .attribute
 xor eax,eax
 jmp .return
.shaderfailed:
 lea rdi,[mesh_error]
 call puts wrt ..plt
.failed:
 mov eax,-1
.return:
 pop r13
 pop r12
 pop rbx
 ret
.compile:
 push rbx
 mov [source_ptr],rsi
 call glCreateShader wrt ..plt
 mov ebx,eax
 mov edi,eax
 mov esi,1
 lea rdx,[source_ptr]
 xor ecx,ecx
 call glShaderSource wrt ..plt
 mov edi,ebx
 call glCompileShader wrt ..plt
 mov edi,ebx
 mov esi,0x8b81
 lea rdx,[shader_status]
 call glGetShaderiv wrt ..plt
 cmp dword [shader_status],0
 je .compilefailed
 mov eax,ebx
 pop rbx
 ret
.compilefailed:
 mov edi,ebx
 mov esi,2048
 xor edx,edx
 lea rcx,[shader_log]
 call glGetShaderInfoLog wrt ..plt
 lea rdi,[shader_log]
 call puts wrt ..plt
 xor eax,eax
 pop rbx
 ret

; EDI tactical,ESI local player; XMM0..4 cameraXYZ/yaw/pitch,XMM5 render dt.
meshes_draw:
 mov dword [mesh_counts_complete],0
 push rbp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 movss [view_weapon],xmm6
 movss [view_weapon+4],xmm7
 mov [view_tactical],edi
 and esi,3
 mov [view_player],esi
 movss [view_camera],xmm0
 movss [view_camera+4],xmm1
 movss [view_camera+8],xmm2
 movss [view_angle],xmm3
 movss [view_angle+4],xmm4
 maxss xmm5,[dt_min]
 inc dword [mesh_frame]
 jnz .frame_ok
 inc dword [mesh_frame]
.frame_ok:
 movss [view_dt],xmm5
 addss xmm5,[mesh_clock]
 movss [mesh_clock],xmm5
 lea rax,[sim_player_vehicle]
 mov eax,[rax+rsi*4]
 mov [view_vehicle],eax
 mov dword [view_company],-1
 mov edi,[view_player]
 cmp dword [network_mode],0
 jne .remote_company
 call company_for_player
 jmp .company_store
.remote_company:
 call net_company_for_player
.company_store:
 mov [view_company],eax
.company_ready:
 mov dword [mesh_high_instances],0
 mov dword [mesh_low_instances],0
 mov dword [mesh_marker_instances],0
 mov dword [mesh_wreck_instances],0
 lea rdi,[mesh_wreck_pose]
 xor eax,eax
 mov ecx,8
 rep stosq
 mov dword [mesh_source_triangles],0
 lea rdi,[high_flags]
 xor eax,eax
 mov ecx,4096
 rep stosq
 call .update_motion
 mov edi,[mesh_program]
 call glUseProgram wrt ..plt
 mov edi,[mesh_program]
 call environment_apply
 mov edi,[mesh_vao]
 call glBindVertexArray wrt ..plt
 mov edi,0x8892
 mov esi,[instance_vbo]
 call glBindBuffer wrt ..plt
 mov edi,[camera_loc]
 movss xmm0,[view_camera]
 movss xmm1,[view_camera+4]
 movss xmm2,[view_camera+8]
 call glUniform3f wrt ..plt
 mov edi,[projection_loc]
 movss xmm0,[view_projection]
 movss xmm1,[view_projection+4]
 call glUniform2f wrt ..plt
 mov edi,[viewport_loc]
 movss xmm0,[view_half_size]
 movss xmm1,[view_half_size+4]
 call glUniform2f wrt ..plt
 mov edi,[angle_loc]
 movss xmm0,[view_angle]
 movss xmm1,[view_angle+4]
 call glUniform2f wrt ..plt
 mov edi,[tactical_loc]
 mov esi,[view_tactical]
 call glUniform1i wrt ..plt
 mov edi,[weapon_loc]
 movss xmm0,[view_weapon]
 movss xmm1,[view_weapon+4]
 call glUniform2f wrt ..plt
 cmp dword [view_tactical],0
 jne .markers
 mov dword [draw_lod],0
.lodpass:
 xor r13d,r13d
.descriptor:
 mov eax,r13d
 shl eax,6
 mov r12,[mesh_asset_descriptors]
 add r12,rax
 mov [current_descriptor],r12
 cmp dword [r12],8
 je .army_descriptor
 cmp dword [r12],4
 jae .nextdescriptor
.army_descriptor:
 mov eax,[draw_lod]
 cmp [r12+4],eax
 jne .nextdescriptor
 xor r15d,r15d
 mov qword [side_budget],0
 call .army
 cmp dword [r12],0
 jne .submit
 call .humans
.submit:
 mov dword [current_mode],0
 call .upload_draw
.nextdescriptor:
 inc r13d
 cmp r13d,[mesh_asset_count]
 jb .descriptor
 inc dword [draw_lod]
 cmp dword [draw_lod],2
 jb .lodpass
 call .props
 call .weapon
.markers:
 call .wrecks
 call .marker_batch
 mov dword [mesh_counts_complete],1
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret

.wrecks:
 push rbp
 xor r13d,r13d
.wreck_descriptor:
 cmp r13d,[mesh_asset_count]
 jae .wreck_done
 mov eax,r13d
 shl eax,6
 mov r12,[mesh_asset_descriptors]
 add r12,rax
 cmp dword [r12+4],0
 jne .wreck_next_descriptor
 mov eax,[r12]
 dec eax
 cmp eax,1
 ja .wreck_next_descriptor
 mov [current_descriptor],r12
 xor r15d,r15d
 xor r14d,r14d
 lea rbx,[sim_wrecks]
 cmp dword [net_connected],0
 je .wreck_record
 lea rbx,[net_wrecks]
.wreck_record:
 test dword [rbx+WRECK_FLAGS],WRECK_ACTIVE
 jz .wreck_next_record
 mov eax,[rbx+WRECK_KIND]
 cmp eax,[r12]
 jne .wreck_next_record
 cmp dword [view_tactical],0
 jne .wreck_append
 movss xmm0,[rbx+WRECK_X]
 subss xmm0,[view_camera]
 mulss xmm0,xmm0
 movss xmm1,[rbx+WRECK_Z]
 subss xmm1,[view_camera+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ucomiss xmm0,[medium_range2]
 ja .wreck_next_record
.wreck_append:
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 mov esi,64
 mov rdx,rbx
 mov ecx,64
 call wreck_instance
 test eax,eax
 jnz .wreck_next_record
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 movups xmm0,[rdi]
 movups [mesh_wreck_pose],xmm0
 movups xmm0,[rdi+16]
 movups [mesh_wreck_pose+16],xmm0
 movups xmm0,[rdi+32]
 movups [mesh_wreck_pose+32],xmm0
 movups xmm0,[rdi+48]
 movups [mesh_wreck_pose+48],xmm0
 inc r15d
 inc dword [mesh_wreck_instances]
.wreck_next_record:
 add rbx,WRECK_STRIDE
 inc r14d
 cmp r14d,WRECK_CAPACITY
 jb .wreck_record
 mov dword [current_mode],0
 mov dword [draw_lod],0
 call .upload_draw
.wreck_next_descriptor:
 inc r13d
 jmp .wreck_descriptor
.wreck_done:
 pop rbp
 ret

.update_motion:
 push rbp
 xor r14d,r14d
 lea rbx,[sim_entities]
.motionloop:
 cmp r14d,[sim_count]
 jae .playermotion
 cmp dword [rbx+ENTITY_HP],0
 je .nextmotion
 mov edi,r14d
 mov eax,[rbx+ENTITY_GENERATION]
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 call .observe
.nextmotion:
 add rbx,32
 inc r14d
 jmp .motionloop
.playermotion:
 xor r14d,r14d
 lea rbx,[sim_players]
.playerloop:
 mov edi,r14d
 add edi,32768
 mov eax,[rbx+PLAYER_GENERATION]
 lea rdx,[last_generation]
 cmp eax,[rdx+rdi*4]
 setne bpl
 movss xmm0,[rbx+PLAYER_X]
 movss xmm1,[rbx+PLAYER_Z]
 call .observe
 lea rdx,[player_shots]
 mov eax,[rbx+PLAYER_SHOTS]
 cmp eax,[rdx+r14*4]
 je .nextplayer
 mov [rdx+r14*4],eax
 test bpl,bpl
 jnz .nextplayer
 movss xmm0,[mesh_clock]
 addss xmm0,[motion_hold]
 lea rdx,[player_fire_until]
 movss [rdx+r14*4],xmm0
.nextplayer:
 add rbx,64
 inc r14d
 cmp r14d,4
 jb .playerloop
 pop rbp
 ret
.observe:
 push rbx
 mov ebx,edi
 lea rdx,[last_generation]
 cmp [rdx+rbx*4],eax
 jne .generation
 lea rdx,[last_x]
 movss xmm2,[rdx+rbx*4]
 movss [rdx+rbx*4],xmm0
 subss xmm0,xmm2
 lea rdx,[last_z]
 movss xmm2,[rdx+rbx*4]
 movss [rdx+rbx*4],xmm1
 subss xmm1,xmm2
 movaps xmm2,xmm0
 mulss xmm2,xmm2
 movaps xmm3,xmm1
 mulss xmm3,xmm3
 addss xmm2,xmm3
 comiss xmm2,[motion_epsilon]
 jbe .observed
 sqrtss xmm2,xmm2
 lea rdx,[last_motion_clock]
 movss xmm3,[mesh_clock]
 movaps xmm4,xmm3
 subss xmm3,[rdx+rbx*4]
 maxss xmm3,[dt_min]
 movss [rdx+rbx*4],xmm4
 divss xmm2,xmm3
 lea rdx,[speed]
 movss [rdx+rbx*4],xmm2
 movss xmm2,[mesh_clock]
 addss xmm2,[motion_hold]
 lea rdx,[moving_until]
 movss [rdx+rbx*4],xmm2
 call atan2f wrt ..plt
 lea rdx,[heading]
 movss [rdx+rbx*4],xmm0
.observed:
 pop rbx
 ret
.generation:
 mov [rdx+rbx*4],eax
 lea rdx,[last_x]
 movss [rdx+rbx*4],xmm0
 lea rdx,[last_z]
 movss [rdx+rbx*4],xmm1
 lea rdx,[moving_until]
 mov dword [rdx+rbx*4],0
 lea rdx,[last_motion_clock]
 movss xmm0,[mesh_clock]
 movss [rdx+rbx*4],xmm0
 lea rdx,[heading]
 mov dword [rdx+rbx*4],0
 jmp .observed

.army:
 push rbp
 xor r14d,r14d
 lea rbx,[sim_entities]
.armyloop:
 cmp r14d,[sim_count]
 jae .armydone
 cmp dword [rbx+ENTITY_HP],0
 je .armynext
 call .visual_role
 cmp eax,[r12]
 jne .armynext
 cmp r14d,[view_vehicle]
 je .armynext
 call .distance
 comiss xmm0,[medium_range2]
 ja .armynext
 cmp dword [draw_lod],0
 jne .low
 comiss xmm0,[high_range2]
 ja .armynext
 cmp dword [mesh_high_instances],252
 jae .armynext
 mov eax,[rbx+ENTITY_SIDE]
 and eax,1
 lea rdx,[side_budget]
 cmp dword [rdx+rax*4],32
 jae .armynext
 inc dword [rdx+rax*4]
 inc dword [mesh_high_instances]
 lea rdx,[high_flags]
 mov byte [rdx+r14],1
 jmp .appendarmy
.low:
 lea rdx,[high_flags]
 cmp byte [rdx+r14],0
 jne .armynext
 inc dword [mesh_low_instances]
.appendarmy:
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 movss xmm0,[rbx+ENTITY_X]
 movss [rdi],xmm0
 mov dword [rdi+4],0
 cmp dword [rbx+ENTITY_KIND],3
 jne .groundarmy
 movss xmm0,[air_height]
 movss [rdi+4],xmm0
.groundarmy:
 movss xmm0,[rbx+ENTITY_Z]
 movss [rdi+8],xmm0
 lea rdx,[heading]
 movss xmm0,[rdx+r14*4]
 movss [rdi+12],xmm0
 mov esi,r14d
 call .animation
 call .unit_scale
 cvtsi2ss xmm0,r14d
 movss [rdi+48],xmm0
 cvtsi2ss xmm0,[rbx+ENTITY_SIDE]
 movss [rdi+52],xmm0
 cvtsi2ss xmm0,[rbx+ENTITY_KIND]
 movss [rdi+56],xmm0
 mov dword [rdi+60],0
 call .ground_pose
 call .air_pose
 call .owned_company
 inc r15d
.armynext:
 add rbx,32
 inc r14d
 jmp .armyloop
.armydone:
 pop rbp
 ret
.distance:
 movss xmm0,[rbx]
 subss xmm0,[view_camera]
 mulss xmm0,xmm0
 movss xmm1,[rbx+4]
 subss xmm1,[view_camera+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ret
.unit_scale:
 mov eax,0x3f800000
 mov [rdi+32],eax
 mov [rdi+36],eax
 mov [rdi+40],eax
 mov dword [rdi+44],0
 ret
; Map the entity kind to a distinct source role only for a live matching sidecar.
.visual_role:
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,3
 jne .visual_role_return
 mov edx,r14d
 shl edx,6
 lea rcx,[sim_aircraft]
 add rcx,rdx
 mov edx,[rbx+ENTITY_GENERATION]
 cmp edx,[rcx+AIR_GENERATION]
 jne .visual_role_return
 test dword [rcx+AIR_FLAGS],AIR_ACTIVE
 jz .visual_role_return
 cmp dword [rcx+AIR_ROLE],AIR_FIGHTER
 jne .visual_role_return
 mov eax,8
.visual_role_return:
 ret
; R14 stable entity index, RBX live entity, RDI finished render instance.
; A mismatched generation must never reuse a destroyed/recycled aircraft pose.
.air_pose:
 cmp dword [rbx+ENTITY_KIND],3
 jne .air_return
 mov eax,r14d
 shl eax,6
 lea rdx,[sim_aircraft]
 add rdx,rax
 mov eax,[rbx+ENTITY_GENERATION]
 cmp eax,[rdx+AIR_GENERATION]
 jne .air_done
 test dword [rdx+AIR_FLAGS],AIR_ACTIVE
 jz .air_done
 mov eax,[rdx+AIR_Y]
 mov [rdi+4],eax
 mov eax,[rdx+AIR_HEADING]
 mov [rdi+12],eax
 mov eax,[rdx+AIR_PITCH]
 mov [rdi+28],eax
 mov eax,[rdx+AIR_BANK]
 mov [rdi+44],eax
 mov dword [rdi+60],0x3f800000 ; absolute aircraft height
 cmp dword [rdx+AIR_ROLE],AIR_FIGHTER
 jne .air_done
 mov dword [rdi+56],0x41000000 ; role8 distinct sourced fighter/glyph
.air_done:
 movups xmm0,[rdi]
 movups [mesh_aircraft_pose],xmm0
 movups xmm0,[rdi+16]
 movups [mesh_aircraft_pose+16],xmm0
 movups xmm0,[rdi+32]
 movups [mesh_aircraft_pose+32],xmm0
 movups xmm0,[rdi+48]
 movups [mesh_aircraft_pose+48],xmm0
.air_return:
 ret
; Authoritative hull axis, including a tracked pivot with zero translation.
.ground_pose:
 mov eax,[rbx+ENTITY_KIND]
 cmp eax,1
 jb .ground_return
 cmp eax,2
 ja .ground_return
 mov edx,r14d
 shl edx,5
 lea rcx,[sim_ground_motion]
 add rcx,rdx
 cmp eax,[rcx+GROUND_KIND]
 jne .ground_stale
 mov edx,[rbx+ENTITY_GENERATION]
 cmp edx,[rcx+GROUND_GENERATION]
 jne .ground_stale
 test dword [rcx+GROUND_FLAGS],GROUND_ACTIVE
 jz .ground_stale
 mov eax,[rcx+GROUND_HEADING]
 mov [rdi+12],eax
 ; Generation-safe derived suspension; same 64-byte instance contract.
 ; Invalid/off-map support retains upright relative-height fallback.
 push rdi
 sub rsp,SUPPORT_STRIDE
 movss xmm0,[rbx+ENTITY_X]
 movss xmm1,[rbx+ENTITY_Z]
 movss xmm2,[rdi+12]
 movss xmm3,[view_dt]
 mov ecx,[rbx+ENTITY_KIND]
 mov edx,[rbx+ENTITY_GENERATION]
 mov r8d,[mesh_frame]
 mov eax,r14d
 shl eax,6
 lea rdi,[mesh_ground_cache]
 add rdi,rax
 mov rsi,rsp
 call ground_visual
 test eax,eax
 jnz .support_done
 mov rdi,[rsp+SUPPORT_STRIDE]
 mov eax,[rsp+SUPPORT_Y]
 mov [rdi+4],eax
 mov eax,[rsp+SUPPORT_PITCH]
 mov [rdi+28],eax
 mov eax,[rsp+SUPPORT_BANK]
 mov [rdi+44],eax
 mov dword [rdi+60],0x3f800000 ; absolute support height, not double terrain
.support_done:
 add rsp,SUPPORT_STRIDE
 pop rdi
 jmp .ground_record
.ground_stale:
 mov eax,r14d
 shl eax,6
 lea rcx,[mesh_ground_cache]
 mov dword [rcx+rax+SUSPENSION_FLAGS],0
.ground_record:
 movups xmm0,[rdi]
 movups [mesh_ground_pose],xmm0
 movups xmm0,[rdi+16]
 movups [mesh_ground_pose+16],xmm0
 movups xmm0,[rdi+32]
 movups [mesh_ground_pose+32],xmm0
 movups xmm0,[rdi+48]
 movups [mesh_ground_pose+48],xmm0
.ground_return:
 ret
; Derived ownership tint only. Actual company lease is validated once per
; frame against either authoritative solo ownership or current remote body generation.
.owned_company:
 mov eax,[view_company]
 cmp eax,-1
 je .owned_return
 cmp dword [rbx+ENTITY_SIDE],0
 jne .owned_return
 cmp dword [rbx+ENTITY_KIND],2
 ja .owned_return
 cmp dword [rbx+ENTITY_GENERATION],0
 je .owned_return
 mov ecx,[rbx+ENTITY_FRONT]
 cmp ecx,2
 ja .owned_return
 shl ecx,8
 mov edx,r14d
 shr edx,7
 add ecx,edx
 cmp ecx,eax
 jne .owned_return
 cmp dword [rdi+60],0x3f800000
 je .owned_absolute
 mov dword [rdi+60],0x40000000 ; relative height plus ownership
 ret
.owned_absolute:
 mov dword [rdi+60],0x40400000 ; absolute height plus ownership
.owned_return:
 ret
.animation:
 ; Preserve authored clip frames; mode chosen from actual observed motion.
 xor eax,eax
 lea rdx,[moving_until]
 movss xmm0,[mesh_clock]
 comiss xmm0,[rdx+rsi*4]
 ja .selectclip
 mov eax,1
 lea rdx,[speed]
 movss xmm0,[rdx+rsi*4]
 comiss xmm0,[run_speed]
 jbe .selectclip
 mov eax,2
.selectclip:
 cmp esi,32768
 jb .clipbegin
 mov edx,esi
 sub edx,32768
 lea r8,[player_fire_until]
 movss xmm0,[mesh_clock]
 comiss xmm0,[r8+rdx*4]
 ja .clipbegin
 mov eax,3
.clipbegin:
 mov edx,[r12+20]
 shl edx,4
 mov r8,[mesh_asset_clips]
 add r8,rdx
 mov r9,r8
 mov ecx,[r12+24]
.cliploop:
 cmp [r8+12],eax
 je .foundclip
 add r8,16
 dec ecx
 jnz .cliploop
 mov r8,r9
.foundclip:
 cmp dword [r8+4],1
 je .freezeclip
 test eax,eax
 jnz .playclip
 cmp dword [r8+12],0
 jne .freezeclip
.playclip:
 movss xmm0,[mesh_clock]
 mulss xmm0,[r8+8]
 cvtsi2ss xmm1,esi
 mulss xmm1,[phase_seed]
 addss xmm0,xmm1
 cvttss2si eax,xmm0
 cvtsi2ss xmm1,eax
 subss xmm0,xmm1
 movss [rdi+24],xmm0
 xor edx,edx
 div dword [r8+4]
 mov eax,edx
 add eax,[r8]
 cvtsi2ss xmm0,eax
 movss [rdi+16],xmm0
 lea rdx,[mesh_selected_frames]
 mov [rdx+rsi*4],eax
 cmp dword [r12],0
 jne .nonsoldiersample
 mov [mesh_animation_sample],eax
.nonsoldiersample:
 movss xmm0,[rdi+24]
 lea rax,[mesh_selected_lerp]
 movss [rax+rsi*4],xmm0
 ; Restore frame remainder because EDX was used for the sample address.
 mov edx,[rdi+16]
 movd xmm0,edx
 cvttss2si edx,xmm0
 sub edx,[r8]
 inc edx
 cmp edx,[r8+4]
 jb .frameb
 xor edx,edx
.frameb:
 add edx,[r8]
 cvtsi2ss xmm0,edx
 movss [rdi+20],xmm0
 mov dword [rdi+28],0
 ret
.freezeclip:
 mov eax,[r8]
 cvtsi2ss xmm0,eax
 movss [rdi+16],xmm0
 movss [rdi+20],xmm0
 mov dword [rdi+24],0
 mov dword [rdi+28],0
 lea rdx,[mesh_selected_frames]
 mov [rdx+rsi*4],eax
 lea rdx,[mesh_selected_lerp]
 mov dword [rdx+rsi*4],0
 ret
.humans:
 push rbp
 xor r14d,r14d
 lea rbx,[sim_players]
.humanloop:
 cmp dword [rbx+PLAYER_CONNECTED],0
 je .humannext
 cmp dword [rbx+PLAYER_HP],0
 je .humannext
 cmp r14d,[view_player]
 je .humannext
 movss xmm0,[rbx]
 subss xmm0,[view_camera]
 mulss xmm0,xmm0
 movss xmm1,[rbx+8]
 subss xmm1,[view_camera+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[medium_range2]
 ja .humannext
 cmp dword [draw_lod],0
 jne .humanlow
 comiss xmm0,[high_range2]
 ja .humannext
 inc dword [mesh_high_instances]
 jmp .appendhuman
.humanlow:
 comiss xmm0,[high_range2]
 jbe .humannext
 inc dword [mesh_low_instances]
.appendhuman:
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 movss xmm0,[rbx+PLAYER_X]
 movss [rdi],xmm0
 movss xmm0,[rbx+PLAYER_Y]
 subss xmm0,[eyes]
 movss [rdi+4],xmm0
 movss xmm0,[rbx+PLAYER_Z]
 movss [rdi+8],xmm0
 movss xmm0,[rbx+PLAYER_YAW]
 movss [rdi+12],xmm0
 mov esi,r14d
 add esi,32768
 call .animation
 call .unit_scale
 cvtsi2ss xmm0,r14d
 movss [rdi+48],xmm0
 mov dword [rdi+52],0x40000000
 mov dword [rdi+56],0
 mov dword [rdi+60],0x3f800000
 inc r15d
.humannext:
 add rbx,64
 inc r14d
 cmp r14d,4
 jb .humanloop
 pop rbp
 ret
.upload_draw:
 push rbp
 test r15d,r15d
 jz .drawdone
 mov edi,[mode_loc]
 mov esi,[current_mode]
 call glUniform1i wrt ..plt
 ; MRT actor output shares all normal geometry and depth tests.
 ; Non-army instances are excluded by shader identity checks.
 mov edi,[census_loc]
 xor esi,esi
 cmp dword [current_mode],2
 je .censusdetail
 mov esi,3
 cmp dword [current_mode],1
 je .censusdetail
 mov esi,[draw_lod]
 inc esi
.censusdetail:
 call glUniform1i wrt ..plt
 mov edi,[geometry_loc]
 xor esi,esi
 xor edx,edx
 cmp dword [current_mode],1
 je .geometry
 mov rax,[current_descriptor]
 mov esi,[rax+16]
 mov edx,[rax+8]
.geometry:
 call glUniform2i wrt ..plt
 mov edi,[scale_loc]
 movss xmm0,[one]
 cmp dword [current_mode],1
 je .setscale
 mov rax,[current_descriptor]
 movss xmm0,[rax+32]
.setscale:
 call glUniform1f wrt ..plt
 mov edi,0x8892
 mov esi,r15d
 shl rsi,6
 lea rdx,[instances]
 mov ecx,0x88e8
 call glBufferData wrt ..plt
 mov edx,3
 cmp dword [current_mode],1
 je .draw
 mov rax,[current_descriptor]
 mov edx,[rax+8]
 mov eax,edx
 imul eax,r15d
 xor ecx,ecx
 mov ecx,3
 xor edx,edx
 div ecx
 add [mesh_source_triangles],eax
 mov rax,[current_descriptor]
 mov edx,[rax+8]
.draw:
 mov edi,4
 xor esi,esi
 mov ecx,r15d
 call glDrawArraysInstanced wrt ..plt
.drawdone:
 pop rbp
 ret

.props:
 push rbp
 xor r13d,r13d
.proploop:
 mov eax,r13d
 shl eax,6
 mov r12,[mesh_asset_descriptors]
 add r12,rax
 cmp dword [r12+4],0
 jne .nextpropmesh
 mov eax,[r12]
 cmp eax,5
 jb .nextpropmesh
 cmp eax,7
 ja .nextpropmesh
 mov [current_descriptor],r12
 xor r15d,r15d
 xor r14d,r14d
 cmp eax,5
 je .bunkers
 cmp eax,6
 je .trees
 lea rbx,[sim_sites]
.sites:
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 call .static_instance
 mov eax,[rbx]
 mov [rdi],eax
 mov eax,[rbx+4]
 mov [rdi+8],eax
 mov dword [rdi+4],0
 mov dword [rdi+60],0
 mov eax,[rbx+8]
 cmp eax,1
 jbe .siteowner
 mov eax,3
.siteowner:
 cvtsi2ss xmm0,eax
 movss [rdi+52],xmm0
 inc r15d
 add rbx,32
 cmp r15d,12
 jb .sites
 jmp .submitprops
.bunkers:
 lea rbx,[terrain_obstacles]
.bunkerloop:
 cmp r14d,[terrain_obstacle_count]
 jae .submitprops
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 call .static_instance
 movss xmm0,[rbx]
 addss xmm0,[rbx+8]
 mulss xmm0,[half]
 movss [rdi],xmm0
 movss xmm0,[rbx+4]
 addss xmm0,[rbx+12]
 mulss xmm0,[half]
 movss [rdi+8],xmm0
 mov eax,[rbx+16]
 mov [rdi+4],eax
 movss xmm0,[rbx+8]
 subss xmm0,[rbx]
 divss xmm0,[r12+40]
 movss [rdi+32],xmm0
 movss xmm0,[rbx+20]
 divss xmm0,[r12+44]
 movss [rdi+36],xmm0
 movss xmm0,[rbx+12]
 subss xmm0,[rbx+4]
 divss xmm0,[r12+48]
 movss [rdi+40],xmm0
 inc r15d
 inc r14d
 add rbx,32
 jmp .bunkerloop
.trees:
 lea rbx,[tree_positions]
.treeloop:
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 call .static_instance
 mov eax,[rbx]
 mov [rdi],eax
 mov eax,[rbx+4]
 mov [rdi+8],eax
 mov dword [rdi+4],0
 mov dword [rdi+60],0
 inc r15d
 add rbx,8
 cmp r15d,16
 jb .treeloop
.submitprops:
 mov dword [current_mode],0
 call .upload_draw
.nextpropmesh:
 inc r13d
 cmp r13d,[mesh_asset_count]
 jb .proploop
 pop rbp
 ret
.static_instance:
 push rbp
 pxor xmm0,xmm0
 movups [rdi],xmm0
 movups [rdi+16],xmm0
 movups [rdi+48],xmm0
 call .unit_scale
 mov dword [rdi+52],0x40400000 ; source neutral material
 mov dword [rdi+60],0x3f800000 ; absolute world y
 pop rbp
 ret
.weapon:
 push rbp
 mov eax,[view_player]
 cmp dword [view_vehicle],0
 jge .weaponend
 shl eax,6
 lea rdx,[sim_players]
 cmp dword [rdx+rax+PLAYER_HP],0
 je .weaponend
 lea rdx,[mesh_role_lookup]
 mov eax,[rdx+8*4]
 shl eax,6
 mov r12,[mesh_asset_descriptors]
 add r12,rax
 mov [current_descriptor],r12
 lea rdi,[instances]
 call .static_instance
 mov esi,[view_player]
 add esi,32768
 call .animation
 mov r15d,1
 mov dword [current_mode],2
 call .upload_draw
.weaponend:
 pop rbp
 ret
.marker_batch:
 push rbp
 xor ebp,ebp ; unowned first, owned last for dense-map readability
 xor r15d,r15d
 xor r14d,r14d
 lea rbx,[sim_entities]
.markerloop:
 cmp r14d,[sim_count]
 jae .humanmarkers
 cmp dword [rbx+ENTITY_HP],0
 je .markernext
 cmp dword [view_tactical],0
 jne .appendmarker
 call .distance
 comiss xmm0,[medium_range2]
 jbe .markernext
.appendmarker:
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 call .static_instance
 mov eax,[rbx+ENTITY_X]
 mov [rdi],eax
 mov eax,[rbx+ENTITY_Z]
 mov [rdi+8],eax
 cvtsi2ss xmm0,r14d
 movss [rdi+48],xmm0
 mov dword [rdi+4],0
 mov dword [rdi+60],0
 cmp dword [rbx+ENTITY_KIND],3
 jne .markerground
 movss xmm0,[air_height]
 movss [rdi+4],xmm0
.markerground:
 cvtsi2ss xmm0,[rbx+ENTITY_SIDE]
 movss [rdi+52],xmm0
 cvtsi2ss xmm0,[rbx+ENTITY_KIND]
 movss [rdi+56],xmm0
 call .ground_pose
 call .air_pose
 call .owned_company
 cmp ebp,0
 jne .owned_marker_pass
 cmp dword [rdi+60],0x40000000
 je .markernext
 cmp dword [rdi+60],0x40400000
 je .markernext
 jmp .marker_include
.owned_marker_pass:
 cmp dword [rdi+60],0x40000000
 je .marker_include
 cmp dword [rdi+60],0x40400000
 jne .markernext
.marker_include:
 inc r15d
.markernext:
 add rbx,32
 inc r14d
 jmp .markerloop
.humanmarkers:
 test ebp,ebp
 jnz .marker_humans
 inc ebp
 xor r14d,r14d
 lea rbx,[sim_entities]
 jmp .markerloop
.marker_humans:
 xor r14d,r14d
 lea rbx,[sim_players]
.humanmarkerloop:
 cmp dword [rbx+PLAYER_CONNECTED],0
 je .nextmarkerhuman
 cmp dword [rbx+PLAYER_HP],0
 je .nextmarkerhuman
 cmp dword [view_tactical],0
 jne .appendhumanmarker
 cmp r14d,[view_player]
 je .nextmarkerhuman
 movss xmm0,[rbx]
 subss xmm0,[view_camera]
 mulss xmm0,xmm0
 movss xmm1,[rbx+8]
 subss xmm1,[view_camera+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 comiss xmm0,[medium_range2]
 jbe .nextmarkerhuman
.appendhumanmarker:
 mov eax,r15d
 shl eax,6
 lea rdi,[instances]
 add rdi,rax
 call .static_instance
 mov eax,[rbx+PLAYER_X]
 mov [rdi],eax
 mov eax,[rbx+PLAYER_Y]
 mov [rdi+4],eax
 mov eax,[rbx+PLAYER_Z]
 mov [rdi+8],eax
 mov dword [rdi+52],0x40000000
 inc r15d
.nextmarkerhuman:
 add rbx,64
 inc r14d
 cmp r14d,4
 jb .humanmarkerloop
 mov [mesh_marker_instances],r15d
 mov dword [current_mode],1
 call .upload_draw
 pop rbp
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
