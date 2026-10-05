; Validated startup-only view settings. SysV; no simulation writes.
; parse(RDI flag, RSI value/null): EAX 0 unknown, 1 accepted, -1 invalid.
; Duplicate settings rejected. strtof consumes complete finite numeric strings.
default rel
global view_settings_parse,view_settings_apply
 global view_width,view_height,view_sensitivity,view_projection,view_half_size
extern strcmp,strtof,tanf
section .rodata
names: dd width_name-names,height_name-names,fov_name-names,sens_name-names
width_name: db '--width',0
height_name: db '--height',0
fov_name: db '--fov',0
sens_name: db '--sensitivity',0
minimum: dd 320.,240.,35.,0.00001
maximum: dd 3840.,2160.,110.,0.05
half_degree: dd 0.008726646259971648
half: dd 0.5
base_x: dd 1.05
base_y: dd 1.87
base_width: dd 1280.
base_height: dd 720.
one: dd 1.
section .data
view_width: dd 1280
view_height: dd 720
view_sensitivity: dd 0.002
view_projection: dd 1.05,1.87
view_half_size: dd 640.,360.
fov: dd 56.271327
seen: dd 0
section .text
view_settings_parse:
 push rbx
 push r12
 push r13
 sub rsp,16
 mov r12,rdi
 mov r13,rsi
 xor ebx,ebx
.loop:
 mov rdi,r12
 lea rax,[names]
 movsxd rsi,dword [rax+rbx*4]
 add rsi,rax
 call strcmp wrt ..plt
 test eax,eax
 jz .found
 inc ebx
 cmp ebx,4
 jb .loop
 xor eax,eax
 jmp .done
.found:
 bt dword [seen],ebx
 jc .invalid
 test r13,r13
 jz .invalid
 ; Prevent whitespace and hex formats; decimal/scientific notation accepted.
 mov al,[r13]
 cmp al,'+'
 je .number
 cmp al,'-'
 je .number
 cmp al,'.'
 je .number
 cmp al,'0'
 jb .invalid
 cmp al,'9'
 ja .invalid
.number:
 mov rdx,r13
.characters:
 mov al,[rdx]
 test al,al
 jz .convert
 cmp al,'0'
 jb .punctuation
 cmp al,'9'
 jbe .advance
.punctuation:
 cmp al,'+'
 je .advance
 cmp al,'-'
 je .advance
 cmp al,'.'
 je .advance
 cmp al,'e'
 je .advance
 cmp al,'E'
 jne .invalid
.advance:
 inc rdx
 jmp .characters
.convert:
 mov rdi,r13
 lea rsi,[rsp]
 call strtof wrt ..plt
 mov rax,[rsp]
 cmp rax,r13
 je .invalid
 cmp byte [rax],0
 jne .invalid
 movd eax,xmm0
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .invalid
 lea rax,[minimum]
 comiss xmm0,[rax+rbx*4]
 jb .invalid
 lea rax,[maximum]
 comiss xmm0,[rax+rbx*4]
 ja .invalid
 cmp ebx,2
 jae .float
 cvttss2si eax,xmm0
 cvtsi2ss xmm1,eax
 comiss xmm0,xmm1
 jne .invalid
 lea rdx,[view_width]
 mov [rdx+rbx*4],eax
 jmp .accepted
.float:
 cmp ebx,2
 jne .sens
 movss [fov],xmm0
 jmp .accepted
.sens:
 movss [view_sensitivity],xmm0
.accepted:
 bts dword [seen],ebx
 mov eax,1
 jmp .done
.invalid:
 mov eax,-1
.done:
 add rsp,16
 pop r13
 pop r12
 pop rbx
 ret
view_settings_apply:
 sub rsp,8
 cvtsi2ss xmm0,dword [view_width]
 mulss xmm0,[half]
 movss [view_half_size],xmm0
 cvtsi2ss xmm0,dword [view_height]
 mulss xmm0,[half]
 movss [view_half_size+4],xmm0
 movss xmm0,[base_y]
 test dword [seen],4
 jz .vertical
 movss xmm0,[fov]
 mulss xmm0,[half_degree]
 call tanf wrt ..plt
 movss xmm1,[one]
 divss xmm1,xmm0
 movaps xmm0,xmm1
.vertical:
 movss [view_projection+4],xmm0
 ; Calibrated aspect preserves the previous exact 1.05/1.87 projection.
 divss xmm0,[base_y]
 mulss xmm0,[base_x]
 cvtsi2ss xmm1,dword [view_height]
 divss xmm1,[base_height]
 mulss xmm0,xmm1
 cvtsi2ss xmm1,dword [view_width]
 movss xmm2,[base_width]
 divss xmm2,xmm1
 mulss xmm0,xmm2
 movss [view_projection],xmm0
 add rsp,8
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
