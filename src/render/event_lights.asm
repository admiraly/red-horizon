; Eight nearest finite event flash lights; cosmetic, allocation-free, single-thread.
default rel
extern effects_records
extern glGetUniformLocation,glProgramUniform1i,glProgramUniform4fv
section .data
global event_lights_enabled,event_lights_gain
event_lights_enabled: dd 1
event_lights_gain: dd 1.0
section .rodata
zero: dd 0.0
one: dd 1.0
mapmax: dd 8000.0
heightmax: dd 1000.0
radius_min: dd 0.25
radius_max: dd 12.0
flash_life: dd 0.45
rifle_life: dd 0.065
range_scale: dd 6.0
range_min: dd 8.0
lift_scale: dd 0.35
lift_min: dd 0.5
burst_colour: dd 8.0,1.4,0.08,0.0
rifle_colour: dd 3.0,1.2,0.4,0.0
count_name: db 'eventLightCount',0
positions_name: db 'eventLightPositions[0]',0
colours_name: db 'eventLightColours[0]',0
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .bss align=16
global event_light_count,event_light_positions,event_light_colours,event_light_slots
event_light_count: resd 1
alignb 16
event_light_positions: resb 8*16
event_light_colours: resb 8*16
event_light_slots: resd 8
scores: resd 8
view: resd 3
gain: resd 1
section .text
global event_lights_update,event_lights_apply
; XMM0/1/2 camera XYZ ->0success/-1invalid camera/gain. Clears output each frame.
; Reads64x32 existing cosmetic records, only active type2 authoritative flashes.
; Stable nearest8 selection, ties lower pool slot. No effect/authority writes.
event_lights_update:
 push rbx
 push r12
 push r13
 movss [view],xmm0
 movss [view+4],xmm1
 movss [view+8],xmm2
 mov dword [event_light_count],0
 lea rdi,[event_light_positions]
 xor eax,eax
 mov ecx,64
 rep stosd
 lea rdi,[event_light_slots]
 mov eax,-1
 mov ecx,8
 rep stosd
 cmp dword [event_lights_enabled],0
 je .done
 xor ecx,ecx
.camera:
 lea rdx,[view]
 mov eax,[rdx+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .invalid
 inc ecx
 cmp ecx,3
 jb .camera
 movss xmm0,[event_lights_gain]
 ucomiss xmm0,[zero]
 jp .invalid
 jb .invalid
 ucomiss xmm0,[one]
 ja .invalid
 movss [gain],xmm0
 lea rbx,[effects_records]
 xor r12d,r12d
.records:
 cmp dword [rbx+28],2
 jne .next
 movss xmm0,[rbx+12]
 ucomiss xmm0,[zero]
 jp .next
 jbe .next
 ucomiss xmm0,[flash_life]
 ja .next
 movss xmm0,[rbx+16]
 ucomiss xmm0,[radius_min]
 jp .next
 jb .next
 ucomiss xmm0,[radius_max]
 ja .next
 xor ecx,ecx
.coords:
 mov eax,[rbx+rcx*4]
 and eax,0x7fffffff
 cmp ecx,1
 je .height
 movss xmm0,[rbx+rcx*4]
 ucomiss xmm0,[zero]
 jb .next
 ucomiss xmm0,[mapmax]
 jp .next
 ja .next
 jmp .coord_ready
.height:
 cmp eax,__float32__(1000.0)
 ja .next
.coord_ready:
 inc ecx
 cmp ecx,3
 jb .coords
 movss xmm0,[rbx]
 subss xmm0,[view]
 mulss xmm0,xmm0
 movss xmm1,[rbx+4]
 subss xmm1,[view+4]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 movss xmm1,[rbx+8]
 subss xmm1,[view+8]
 mulss xmm1,xmm1
 addss xmm0,xmm1
 ; Insert into the small sorted list; no heap or unbounded camera query.
 mov r13d,[event_light_count]
 xor edx,edx
 lea r8,[scores]
.find:
 cmp edx,r13d
 jae .found
 ucomiss xmm0,[r8+rdx*4]
 jb .found
 inc edx
 jmp .find
.found:
 cmp edx,8
 jae .next
 cmp r13d,8
 jb .space
 dec r13d
 jmp .shift
.space:
 inc dword [event_light_count]
.shift:
 lea r9,[event_light_slots]
 cmp r13d,edx
 jbe .insert
 lea ecx,[r13d-1]
 mov eax,[r8+rcx*4]
 mov [r8+r13*4],eax
 mov eax,[r9+rcx*4]
 mov [r9+r13*4],eax
 dec r13d
 jmp .shift
.insert:
 movss [r8+rdx*4],xmm0
 mov [r9+rdx*4],r12d
.next:
 add rbx,32
 inc r12d
 cmp r12d,64
 jb .records
 xor r12d,r12d
.pack:
 cmp r12d,[event_light_count]
 jae .done
 lea rdx,[event_light_slots]
 mov eax,[rdx+r12*4]
 shl eax,5
 lea rbx,[effects_records]
 add rbx,rax
 mov eax,r12d
 shl eax,4
 lea rdi,[event_light_positions]
 add rdi,rax
 movss xmm0,[rbx+16]
 movaps xmm1,xmm0
 mulss xmm1,[range_scale]
 maxss xmm1,[range_min]
 movss [rdi+12],xmm1
 mulss xmm0,[lift_scale]
 maxss xmm0,[lift_min]
 addss xmm0,[rbx+4]
 movss [rdi+4],xmm0
 mov ecx,[rbx]
 mov [rdi],ecx
 mov ecx,[rbx+8]
 mov [rdi+8],ecx
 lea rdx,[burst_colour]
 movss xmm0,[rbx+12]
 divss xmm0,[flash_life]
 movss xmm1,[rbx+16]
 ucomiss xmm1,[radius_min]
 jne .power
 lea rdx,[rifle_colour]
 movss xmm0,[rbx+12]
 divss xmm0,[rifle_life]
.power:
 minss xmm0,[one]
 mulss xmm0,xmm0
 mulss xmm0,[gain]
 shufps xmm0,xmm0,0
 movups xmm1,[rdx]
 mulps xmm1,xmm0
 lea rdi,[event_light_colours]
 movups [rdi+rax],xmm1
 inc r12d
 jmp .pack
.invalid:
 mov eax,-1
 jmp .return
.done:
 xor eax,eax
.return:
 pop r13
 pop r12
 pop rbx
 ret
; EDI linked program. DSA preserves current program, VAO, texture and FBO bindings.
; Three bounded uniform lookups/uploads; callers own GL context/program lifecycle.
event_lights_apply:
 push rbx
 mov ebx,edi
 lea rsi,[count_name]
 call glGetUniformLocation wrt ..plt
 mov esi,eax
 mov edi,ebx
 mov edx,[event_light_count]
 call glProgramUniform1i wrt ..plt
 mov edi,ebx
 lea rsi,[positions_name]
 call glGetUniformLocation wrt ..plt
 mov esi,eax
 mov edi,ebx
 mov edx,[event_light_count]
 lea rcx,[event_light_positions]
 call glProgramUniform4fv wrt ..plt
 mov edi,ebx
 lea rsi,[colours_name]
 call glGetUniformLocation wrt ..plt
 mov esi,eax
 mov edi,ebx
 mov edx,[event_light_count]
 lea rcx,[event_light_colours]
 call glProgramUniform4fv wrt ..plt
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
