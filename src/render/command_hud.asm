; Bounded read-only command text overlay. CPU runtime is NASM, no font library.
default rel
extern glGetUniformLocation,glUniform1iv,glUniform2f,glDrawArraysInstanced
extern view_width,view_height
section .rodata
glyph_name: db 'commandGlyphs',0
viewport_name: db 'commandViewport',0
origin_name: db 'commandOrigin',0
origin_x: dd 16.0
bottom_margin: dd 114.0
line_step: dd 22.0
section .bss align=16
glyph_loc: resd 1
viewport_loc: resd 1
origin_loc: resd 1
global command_hud_glyphs,command_hud_length,command_hud_rows
command_hud_glyphs: resd 128
command_hud_length: resd 1
command_hud_rows: resd 1
section .text
global command_hud_init,command_hud_begin,command_hud_draw
; EDI linked battle program. All locations required, -1 on invalid shader.
command_hud_init:
 push rbx
 mov ebx,edi
 lea rsi,[glyph_name]
 call glGetUniformLocation
 mov [glyph_loc],eax
 mov edi,ebx
 lea rsi,[viewport_name]
 call glGetUniformLocation
 mov [viewport_loc],eax
 mov edi,ebx
 lea rsi,[origin_name]
 call glGetUniformLocation
 mov [origin_loc],eax
 xor eax,eax
 cmp dword [glyph_loc],0
 jl .bad
 cmp dword [viewport_loc],0
 jl .bad
 cmp dword [origin_loc],0
 jl .bad
 pop rbx
 ret
.bad:
 mov eax,-1
 pop rbx
 ret
command_hud_begin:
 mov dword [command_hud_rows],0
 ret
; RDI NUL text, ESI row0..2. Caller owns current program/VAO/depth state.
; Maximum128 bytes and width-clipped text; normalize lowercase without mutation.
command_hud_draw:
 push rbx
 push r12
 sub rsp,8
 mov r12d,esi
 cmp esi,2
 ja .done
 test rdi,rdi
 jz .done
 mov eax,[view_width]
 sub eax,32
 xor edx,edx
 mov ecx,12
 div ecx
 cmp eax,128
 jbe .cap
 mov eax,128
.cap:
 mov ebx,eax
 xor ecx,ecx
 lea rdx,[command_hud_glyphs]
.copy:
 cmp ecx,ebx
 jae .copied
 movzx eax,byte [rdi+rcx]
 test eax,eax
 jz .copied
 ; Pipe uses the compact font's unused backslash slot.
 cmp eax,124
 jne .letter
 mov eax,92
.letter:
 cmp eax,'a'
 jb .ascii
 cmp eax,'z'
 ja .ascii
 sub eax,32
.ascii:
 cmp eax,32
 jb .fallback
 cmp eax,95
 jbe .store
.fallback:
 mov eax,'?'
.store:
 mov [rdx+rcx*4],eax
 inc ecx
 jmp .copy
.copied:
 mov ebx,ecx
 mov [command_hud_length],ecx
 test ecx,ecx
 jz .done
 mov edi,[glyph_loc]
 mov esi,ecx
 call glUniform1iv
 mov edi,[viewport_loc]
 cvtsi2ss xmm0,[view_width]
 cvtsi2ss xmm1,[view_height]
 call glUniform2f
 mov edi,[origin_loc]
 movss xmm0,[origin_x]
 cvtsi2ss xmm1,[view_height]
 subss xmm1,[bottom_margin]
 cvtsi2ss xmm2,r12d
 mulss xmm2,[line_step]
 addss xmm1,xmm2
 call glUniform2f
 mov edi,4
 xor esi,esi
 mov edx,6
 mov ecx,ebx
 call glDrawArraysInstanced
 inc dword [command_hud_rows]
.done:
 add rsp,8
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
