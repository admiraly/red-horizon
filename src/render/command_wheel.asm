; Pixel-sized contextual order wheel, using the shared bounded NASM font.
%include "schemas/input_bindings.inc"
default rel
extern glGetUniformLocation,glUniform1i,glUniform2f,glDrawArrays
extern snprintf,bindings_label
extern view_width,view_height,command_hud_draw_at
section .rodata
mode_name: db 'commandWheelMode',0
viewport_name: db 'commandViewport',0
move_text: db 'MOVE',0
hold_text: db 'HOLD',0
retreat_text: db 'RETREAT',0
follow_text: db 'FOLLOW',0
release_text: db 'RELEASE / %s CANCEL',0
half: dd 0.5
scale: dd 0.4
radius_limit: dd 120.0
label_scale: dd 0.72
section .bss
release_buf: resb 128
mode_loc: resd 1
viewport_loc: resd 1
section .text
global command_wheel_hud_init,command_wheel_hud_draw
; EDI program ->0 or-1 if required uniforms are missing.
command_wheel_hud_init:
 push rbx
 mov ebx,edi
 lea rsi,[mode_name]
 call glGetUniformLocation
 mov [mode_loc],eax
 mov edi,ebx
 lea rsi,[viewport_name]
 call glGetUniformLocation
 mov [viewport_loc],eax
 xor eax,eax
 cmp dword [mode_loc],0
 jl .bad
 cmp dword [viewport_loc],0
 jl .bad
 pop rbx
 ret
.bad: mov eax,-1
 pop rbx
 ret
; EDI terrain uniform location, ESI mode(-1 center), current HUD render state.
command_wheel_hud_draw:
 push rbx
 sub rsp,32
 mov ebx,edi
 mov edx,esi
 mov edi,[mode_loc]
 mov esi,edx
 call glUniform1i
 mov edi,[viewport_loc]
 cvtsi2ss xmm0,[view_width]
 cvtsi2ss xmm1,[view_height]
 call glUniform2f
 mov edi,ebx
 mov esi,13
 call glUniform1i
 mov edi,4
 xor esi,esi
 mov edx,6
 call glDrawArrays
 mov eax,[view_width]
 shr eax,1
 mov [rsp],eax
 mov edx,[view_height]
 shr edx,1
 mov [rsp+4],edx
 mov eax,[view_width]
 cmp eax,[view_height]
 jbe .size
 mov eax,[view_height]
.size:
 cvtsi2ss xmm0,eax
 mulss xmm0,[scale]
 minss xmm0,[radius_limit]
 mulss xmm0,[label_scale]
 cvttss2si eax,xmm0
 mov [rsp+8],eax
 mov edi,ebx
 mov esi,12
 call glUniform1i
 lea rdi,[move_text]
 mov esi,[rsp]
 sub esi,24
 mov edx,[rsp+4]
 sub edx,[rsp+8]
 sub edx,8
 call command_hud_draw_at
 lea rdi,[hold_text]
 mov esi,[rsp]
 sub esi,[rsp+8]
 sub esi,24
 mov edx,[rsp+4]
 sub edx,8
 call command_hud_draw_at
 lea rdi,[follow_text]
 mov esi,[rsp]
 add esi,[rsp+8]
 sub esi,36
 mov edx,[rsp+4]
 sub edx,8
 call command_hud_draw_at
 lea rdi,[retreat_text]
 mov esi,[rsp]
 sub esi,42
 mov edx,[rsp+4]
 add edx,[rsp+8]
 sub edx,8
 call command_hud_draw_at
 mov edi,BIND_COMMAND_CANCEL
 call bindings_label
 mov rcx,rax
 lea rdi,[release_buf]
 mov esi,128
 lea rdx,[release_text]
 xor eax,eax
 call snprintf
 imul eax,6
 mov ebx,eax
 lea rdi,[release_buf]
 mov esi,[rsp]
 sub esi,ebx
 mov edx,[rsp+4]
 add edx,[rsp+8]
 add edx,26
 call command_hud_draw_at
 add rsp,32
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
