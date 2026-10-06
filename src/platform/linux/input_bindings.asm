; Linux startup-only saved action bindings. No gameplay writes; NASM parsing.
%include "schemas/input_bindings.inc"
default rel
extern open,read,close,fstat,strcmp,printf
extern glfwGetKey,glfwGetMouseButton
section .rodata
action_offsets: dd action_0-action_offsets,action_1-action_offsets,action_2-action_offsets,action_3-action_offsets,action_4-action_offsets,action_5-action_offsets,action_6-action_offsets,action_7-action_offsets,action_8-action_offsets,action_9-action_offsets,action_10-action_offsets,action_11-action_offsets,action_12-action_offsets,action_13-action_offsets,action_14-action_offsets,action_15-action_offsets,action_16-action_offsets,action_17-action_offsets,action_18-action_offsets,action_19-action_offsets,action_20-action_offsets,action_21-action_offsets,action_22-action_offsets,action_23-action_offsets,action_24-action_offsets,action_25-action_offsets,action_26-action_offsets,action_27-action_offsets,action_28-action_offsets,action_29-action_offsets,action_30-action_offsets
action_0: db 'forward',0
action_1: db 'back',0
action_2: db 'left',0
action_3: db 'right',0
action_4: db 'sprint',0
action_5: db 'crouch',0
action_6: db 'jump',0
action_7: db 'reload',0
action_8: db 'enter_vehicle',0
action_9: db 'exit_vehicle',0
action_10: db 'fire',0
action_11: db 'tactical_map',0
action_12: db 'command_wheel',0
action_13: db 'command_cancel',0
action_14: db 'quit',0
action_15: db 'advance',0
action_16: db 'hold',0
action_17: db 'retreat',0
action_18: db 'follow',0
action_19: db 'front_1',0
action_20: db 'front_2',0
action_21: db 'front_3',0
action_22: db 'weather',0
action_23: db 'exchange_0',0
action_24: db 'exchange_1',0
action_25: db 'exchange_2',0
action_26: db 'exchange_3',0
action_27: db 'exchange_accept',0
action_28: db 'exchange_decline',0
action_29: db 'exchange_cancel',0
action_30: db 'defend',0
key_offsets: dd key_0-key_offsets,key_1-key_offsets,key_2-key_offsets,key_3-key_offsets,key_4-key_offsets,key_5-key_offsets,key_6-key_offsets,key_7-key_offsets,key_8-key_offsets,key_9-key_offsets,key_10-key_offsets,key_11-key_offsets,key_12-key_offsets,key_13-key_offsets,key_14-key_offsets,key_15-key_offsets,key_16-key_offsets,key_17-key_offsets,key_18-key_offsets,key_19-key_offsets,key_20-key_offsets,key_21-key_offsets,key_22-key_offsets,key_23-key_offsets,key_24-key_offsets,key_25-key_offsets,key_26-key_offsets,key_27-key_offsets,key_28-key_offsets,key_29-key_offsets,key_30-key_offsets,key_31-key_offsets,key_32-key_offsets,key_33-key_offsets,key_34-key_offsets,key_35-key_offsets,key_36-key_offsets,key_37-key_offsets,key_38-key_offsets,key_39-key_offsets,key_40-key_offsets,key_41-key_offsets,key_42-key_offsets,key_43-key_offsets,key_44-key_offsets,key_45-key_offsets,key_46-key_offsets,key_47-key_offsets,key_48-key_offsets,key_49-key_offsets,key_50-key_offsets,key_51-key_offsets,key_52-key_offsets,key_53-key_offsets,key_54-key_offsets,key_55-key_offsets,key_56-key_offsets,key_57-key_offsets,key_58-key_offsets,key_59-key_offsets,key_60-key_offsets,key_61-key_offsets,key_62-key_offsets,key_63-key_offsets,key_64-key_offsets,key_65-key_offsets,key_66-key_offsets,key_67-key_offsets,key_68-key_offsets,key_69-key_offsets,key_70-key_offsets,key_71-key_offsets,key_72-key_offsets,key_73-key_offsets,key_74-key_offsets,key_75-key_offsets,key_76-key_offsets
key_codes: dd 65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,48,49,50,51,52,53,54,55,56,57,290,291,292,293,294,295,296,297,298,299,300,301,32,256,257,258,259,260,261,262,263,264,265,266,267,268,269,340,341,342,344,345,346,65536,65537,65538,65539,65540,65541,65542,65543
key_0: db 'A',0
key_1: db 'B',0
key_2: db 'C',0
key_3: db 'D',0
key_4: db 'E',0
key_5: db 'F',0
key_6: db 'G',0
key_7: db 'H',0
key_8: db 'I',0
key_9: db 'J',0
key_10: db 'K',0
key_11: db 'L',0
key_12: db 'M',0
key_13: db 'N',0
key_14: db 'O',0
key_15: db 'P',0
key_16: db 'Q',0
key_17: db 'R',0
key_18: db 'S',0
key_19: db 'T',0
key_20: db 'U',0
key_21: db 'V',0
key_22: db 'W',0
key_23: db 'X',0
key_24: db 'Y',0
key_25: db 'Z',0
key_26: db '0',0
key_27: db '1',0
key_28: db '2',0
key_29: db '3',0
key_30: db '4',0
key_31: db '5',0
key_32: db '6',0
key_33: db '7',0
key_34: db '8',0
key_35: db '9',0
key_36: db 'F1',0
key_37: db 'F2',0
key_38: db 'F3',0
key_39: db 'F4',0
key_40: db 'F5',0
key_41: db 'F6',0
key_42: db 'F7',0
key_43: db 'F8',0
key_44: db 'F9',0
key_45: db 'F10',0
key_46: db 'F11',0
key_47: db 'F12',0
key_48: db 'SPACE',0
key_49: db 'ESC',0
key_50: db 'ENTER',0
key_51: db 'TAB',0
key_52: db 'BACKSPACE',0
key_53: db 'INSERT',0
key_54: db 'DELETE',0
key_55: db 'RIGHT',0
key_56: db 'LEFT',0
key_57: db 'DOWN',0
key_58: db 'UP',0
key_59: db 'PAGEUP',0
key_60: db 'PAGEDOWN',0
key_61: db 'HOME',0
key_62: db 'END',0
key_63: db 'LSHIFT',0
key_64: db 'LCTRL',0
key_65: db 'LALT',0
key_66: db 'RSHIFT',0
key_67: db 'RCTRL',0
key_68: db 'RALT',0
key_69: db 'LMB',0
key_70: db 'RMB',0
key_71: db 'MMB',0
key_72: db 'MOUSE4',0
key_73: db 'MOUSE5',0
key_74: db 'MOUSE6',0
key_75: db 'MOUSE7',0
key_76: db 'MOUSE8',0
default_codes: dd 87,83,65,68,340,341,32,82,69,81,65536,258,65538,65537,256,49,50,51,52,290,291,292,293,294,295,296,297,298,299,300,53
default_indices: dd 22,18,0,3,63,64,48,17,4,16,69,51,71,70,49,27,28,29,30,36,37,38,39,40,41,42,43,44,45,46,31
report_fmt: db 'binding %s=%s',10,0
section .data
global binding_codes,binding_key_indices
binding_codes: dd 87,83,65,68,340,341,32,82,69,81,65536,258,65538,65537,256,49,50,51,52,290,291,292,293,294,295,296,297,298,299,300,53
binding_key_indices: dd 22,18,0,3,63,64,48,17,4,16,69,51,71,70,49,27,28,29,30,36,37,38,39,40,41,42,43,44,45,46,31
section .bss align=16
buffer: resb 4097
stage_codes: resd BINDING_COUNT
stage_indices: resd BINDING_COUNT
seen: resd 1
global bindings_error_line
bindings_error_line: resd 1
section .text
global bindings_load,bindings_down,bindings_label,bindings_report
; EDI action -> RAX immutable display label, empty string on invalid index.
bindings_label:
 cmp edi,BINDING_COUNT
 jae .invalid
 lea rax,[binding_key_indices]
 mov eax,[rax+rdi*4]
 lea rdx,[key_offsets]
 movsxd rax,dword [rdx+rax*4]
 add rax,rdx
 ret
.invalid:
 lea rax,[action_0+7] ; NUL
 ret
; RDI GLFW window, ESI logical action -> current physical pressed state.
; A mouse code has bit16; keyboard codes are ordinary GLFW codes.
bindings_down:
 cmp esi,BINDING_COUNT
 jae .up
 lea rax,[binding_codes]
 mov esi,[rax+rsi*4]
 test esi,65536
 jz .key
 and esi,7
 jmp glfwGetMouseButton wrt ..plt
.key:
 jmp glfwGetKey wrt ..plt
.up:
 xor eax,eax
 ret
; RDI regular-file path. EAX0 accepts atomically, -1 preserves current bindings.
; At most4096 bytes,30 distinct actions, bounded named physical inputs. LF/CRLF,
; whitespace, blank lines and full-line comments allowed. No embedded NUL.
; Stage defaults and overrides; validate final exclusivity before publishing.
bindings_load:
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,160
 mov dword [bindings_error_line],0
 mov dword [seen],0
 mov esi,0x800 ; nonblocking open, followed by regular-file validation
 xor eax,eax
 call open wrt ..plt
 test eax,eax
 js .bad
 mov ebx,eax
 mov edi,ebx
 mov rsi,rsp
 call fstat wrt ..plt
 test eax,eax
 jnz .closebad
 mov eax,[rsp+24]
 and eax,0xf000
 cmp eax,0x8000
 jne .closebad
 xor r12d,r12d
.read:
 mov edi,ebx
 lea rsi,[buffer]
 add rsi,r12
 mov edx,4097
 sub edx,r12d
 call read wrt ..plt
 test rax,rax
 js .closebad
 jz .eof
 add r12,rax
 cmp r12,4096
 ja .closebad
 jmp .read
.eof:
 mov edi,ebx
 call close wrt ..plt
 xor ecx,ecx
 lea rsi,[buffer]
.validate_bytes:
 cmp rcx,r12
 jae .defaults
 cmp byte [rsi+rcx],0
 je .bad
 inc ecx
 jmp .validate_bytes
.defaults:
 lea rsi,[default_codes]
 lea rdi,[stage_codes]
 mov ecx,BINDING_COUNT
 rep movsd
 lea rsi,[default_indices]
 lea rdi,[stage_indices]
 mov ecx,BINDING_COUNT
 rep movsd
 lea r13,[buffer]
 lea r14,[buffer]
 add r14,r12
 mov byte [r14],0
 mov dword [bindings_error_line],1
.line:
 cmp r13,r14
 jae .conflicts
 ; Split one bounded line without ever reading past the acquired buffer.
 mov r15,r13
.endline:
 cmp r15,r14
 jae .split
 cmp byte [r15],10
 je .split
 inc r15
 jmp .endline
.split:
 mov byte [r15],0
 mov rdi,r13
 call .trim
 mov r13,rax
 cmp byte [r13],0
 je .nextline
 cmp byte [r13],'#'
 je .nextline
 mov rbx,r13
.equals:
 cmp byte [rbx],'='
 je .parts
 cmp byte [rbx],0
 je .bad
 inc rbx
 jmp .equals
.parts:
 mov byte [rbx],0
 inc rbx
 mov rdi,r13
 call .trim
 mov r13,rax
 mov rdi,rbx
 call .trim
 mov rbx,rax
 xor r12d,r12d
.action:
 mov rdi,r13
 lea rax,[action_offsets]
 movsxd rsi,dword [rax+r12*4]
 add rsi,rax
 call strcmp wrt ..plt
 test eax,eax
 jz .actionfound
 inc r12d
 cmp r12d,BINDING_COUNT
 jb .action
 jmp .bad
.actionfound:
 bts dword [seen],r12d
 jc .bad
 mov [rsp+144],r12d
 xor r12d,r12d
.keylookup:
 mov rdi,rbx
 lea rax,[key_offsets]
 movsxd rsi,dword [rax+r12*4]
 add rsi,rax
 call strcmp wrt ..plt
 test eax,eax
 jz .keyfound
 inc r12d
 cmp r12d,77
 jb .keylookup
 jmp .bad
.keyfound:
 mov ecx,[rsp+144]
 lea rax,[key_codes]
 mov edx,[rax+r12*4]
 lea rax,[stage_codes]
 mov [rax+rcx*4],edx
 lea rax,[stage_indices]
 mov [rax+rcx*4],r12d
.nextline:
 lea r13,[r15+1]
 inc dword [bindings_error_line]
 jmp .line
.conflicts:
 xor ecx,ecx
 lea rax,[stage_codes]
.outer:
 mov edx,ecx
 inc edx
.inner:
 cmp edx,BINDING_COUNT
 jae .nextaction
 mov esi,[rax+rcx*4]
 cmp esi,[rax+rdx*4]
 je .bad
 inc edx
 jmp .inner
.nextaction:
 inc ecx
 cmp ecx,BINDING_COUNT
 jb .outer
 lea rsi,[stage_codes]
 lea rdi,[binding_codes]
 mov ecx,BINDING_COUNT
 rep movsd
 lea rsi,[stage_indices]
 lea rdi,[binding_key_indices]
 mov ecx,BINDING_COUNT
 rep movsd
 mov dword [bindings_error_line],0
 xor eax,eax
 jmp .done
.closebad:
 mov edi,ebx
 call close wrt ..plt
.bad:
 mov eax,-1
.done:
 add rsp,160
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
; RDI terminated bounded line -> RAX whitespace-trimmed subspan, NUL at end.
; Internal only. Spaces, tabs and CR are whitespace; LF already split above.
.trim:
 mov rax,rdi
.leading:
 cmp byte [rax],32
 je .lead
 cmp byte [rax],9
 je .lead
 cmp byte [rax],13
 jne .tail
.lead: inc rax
 jmp .leading
.tail:
 mov rdx,rax
.scan:
 cmp byte [rdx],0
 je .back
 inc rdx
 jmp .scan
.back:
 cmp rdx,rax
 je .trimdone
 cmp byte [rdx-1],32
 je .erase
 cmp byte [rdx-1],9
 je .erase
 cmp byte [rdx-1],13
 jne .trimdone
.erase:
 dec rdx
 mov byte [rdx],0
 jmp .back
.trimdone: ret
; Print all loaded action/key names once before window initialization.
bindings_report:
 push rbx
 xor ebx,ebx
.loop:
 mov edi,ebx
 call bindings_label
 mov rdx,rax
 lea rax,[action_offsets]
 movsxd rsi,dword [rax+rbx*4]
 add rsi,rax
 lea rdi,[report_fmt]
 xor eax,eax
 call printf wrt ..plt
 inc ebx
 cmp ebx,BINDING_COUNT
 jb .loop
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
