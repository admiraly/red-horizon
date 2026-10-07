; Cosmetic-only terrain pack and smoothly interpolated weather. No authority writes.
default rel
global texture_asset_load,texture_asset_blob,environment_init,environment_update,environment_apply
 global environment_select,environment_cycle,environment_weather,environment_preset
extern fopen,fread,fclose,puts,strcmp
extern glGenTextures,glBindTexture,glTexImage3D,glTexParameteri,glGenerateMipmap,glActiveTexture
extern glGetUniformLocation,glUniform4f,glUniform1i
extern hdr_world_linear
%define PACK_BYTES 4194336
section .rodata
path: db 'content/textures/terrain.rhtx',0
mode: db 'rb',0
error: db 'Missing or invalid terrain texture pack: content/textures/terrain.rhtx',0
weather_name: db 'weather',0
hdr_name: db 'hdrOutput',0
sampler_name: db 'terrainTextures',0
names: dd clear-names,overcast-names,rain-names,fog-names
clear: db 'clear',0
overcast: db 'overcast',0
rain: db 'rain',0
fog: db 'fog',0
; cloud coverage, precipitation, additional exponential fog density
presets: dd 0.15,0.,0.00008, 0.82,0.,0.00018, 0.96,1.,0.00045, 0.70,0.,0.0012
rate: dd 0.65
one: dd 1.0
section .data
align 16
environment_weather: dd 0.,0.15,0.,0.00008
environment_preset: dd 0
section .bss
texture_asset_blob: resb PACK_BYTES+1
texture: resd 1
section .text
texture_asset_load:
 push rbx
 lea rdi,[path]
 lea rsi,[mode]
 call fopen wrt ..plt
 test rax,rax
 jz .bad
 mov rbx,rax
 lea rdi,[texture_asset_blob]
 mov esi,1
 mov edx,PACK_BYTES+1
 mov rcx,rbx
 call fread wrt ..plt
 push rax
 sub rsp,8
 mov rdi,rbx
 call fclose wrt ..plt
 add rsp,8
 pop rax
 cmp rax,PACK_BYTES
 jne .bad
 lea rdx,[texture_asset_blob]
 cmp dword [rdx],0x58544852
 jne .bad
 cmp dword [rdx+4],1
 jne .bad
 cmp dword [rdx+8],PACK_BYTES
 jne .bad
 cmp dword [rdx+12],512
 jne .bad
 cmp dword [rdx+16],512
 jne .bad
 cmp dword [rdx+20],4
 jne .bad
 cmp dword [rdx+24],32
 jne .bad
 cmp dword [rdx+28],1
 jne .bad
 xor eax,eax
 pop rbx
 ret
.bad:
 lea rdi,[error]
 call puts wrt ..plt
 mov eax,-1
 pop rbx
 ret
; EDI preset0.0.3. ESI nonzero instant startup, zero smooth target transition.
environment_select:
 cmp edi,3
 ja .invalid
 mov [environment_preset],edi
 test esi,esi
 jz .okay
 imul edi,edi,12
 lea rax,[presets]
 movss xmm0,[rax+rdi]
 movss [environment_weather+4],xmm0
 movss xmm0,[rax+rdi+4]
 movss [environment_weather+8],xmm0
 movss xmm0,[rax+rdi+8]
 movss [environment_weather+12],xmm0
.okay:
 xor eax,eax
 ret
.invalid:
 mov eax,-1
 ret
; RDI clear/overcast/rain/fog => EAX preset or -1.
global environment_parse,environment_name
environment_parse:
 push rbx
 push r12
 sub rsp,8
 mov r12,rdi
 xor ebx,ebx
.next:
 mov rdi,r12
 lea rax,[names]
 movsxd rsi,dword [rax+rbx*4]
 add rsi,rax
 call strcmp wrt ..plt
 test eax,eax
 jz .found
 inc ebx
 cmp ebx,4
 jb .next
 mov ebx,-1
.found:
 mov eax,ebx
 add rsp,8
 pop r12
 pop rbx
 ret
environment_name:
 mov eax,[environment_preset]
 lea rdx,[names]
 movsxd rax,dword [rdx+rax*4]
 add rax,rdx
 ret
environment_cycle:
 mov edi,[environment_preset]
 inc edi
 and edi,3
 xor esi,esi
 jmp environment_select
; XMM0 bounded render delta.
global environment_step
environment_update:
environment_step:
 movaps xmm1,xmm0
 addss xmm0,[environment_weather]
 movss [environment_weather],xmm0
 mulss xmm1,[rate]
 minss xmm1,[one]
 mov eax,[environment_preset]
 imul eax,eax,12
 lea rdx,[presets]
 movss xmm2,[rdx+rax]
 subss xmm2,[environment_weather+4]
 mulss xmm2,xmm1
 addss xmm2,[environment_weather+4]
 movss [environment_weather+4],xmm2
 movss xmm2,[rdx+rax+4]
 subss xmm2,[environment_weather+8]
 mulss xmm2,xmm1
 addss xmm2,[environment_weather+8]
 movss [environment_weather+8],xmm2
 movss xmm2,[rdx+rax+8]
 subss xmm2,[environment_weather+12]
 mulss xmm2,xmm1
 addss xmm2,[environment_weather+12]
 movss [environment_weather+12],xmm2
 ret
environment_init:
 push rbx
 call texture_asset_load
 test eax,eax
 jnz .done
 mov edi,1
 lea rsi,[texture]
 call glGenTextures wrt ..plt
 mov edi,0x84c0
 call glActiveTexture wrt ..plt
 mov edi,0x8c1a
 mov esi,[texture]
 call glBindTexture wrt ..plt
 ; TexImage3D ten arguments, four on the SysV stack.
 sub rsp,32
 mov edi,0x8c1a
 xor esi,esi
 mov edx,0x8058
 mov ecx,512
 mov r8d,512
 mov r9d,4
 ; border seventh argument precedes format, type, pointer; reserve4 args
 mov qword [rsp],0
 mov qword [rsp+8],0x1908
 mov qword [rsp+16],0x1401
 lea rax,[texture_asset_blob+32]
 mov [rsp+24],rax
 call glTexImage3D wrt ..plt
 add rsp,32
 mov edi,0x8c1a
 mov esi,0x2801
 mov edx,0x2703
 call glTexParameteri wrt ..plt
 mov edi,0x8c1a
 mov esi,0x2800
 mov edx,0x2601
 call glTexParameteri wrt ..plt
 mov edi,0x8c1a
 mov esi,0x2802
 mov edx,0x2901
 call glTexParameteri wrt ..plt
 mov edi,0x8c1a
 mov esi,0x2803
 mov edx,0x2901
 call glTexParameteri wrt ..plt
 mov edi,0x8c1a
 call glGenerateMipmap wrt ..plt
 xor eax,eax
.done:
 pop rbx
 ret
; EDI currently bound program; same uniform state for terrain, models and sky.
environment_apply:
 push rbx
 mov ebx,edi
 lea rsi,[weather_name]
 call glGetUniformLocation wrt ..plt
 mov edi,eax
 movss xmm0,[environment_weather]
 movss xmm1,[environment_weather+4]
 movss xmm2,[environment_weather+8]
 movss xmm3,[environment_weather+12]
 call glUniform4f wrt ..plt
 mov edi,ebx
 lea rsi,[sampler_name]
 call glGetUniformLocation wrt ..plt
 mov edi,eax
 xor esi,esi
 call glUniform1i wrt ..plt
 mov edi,ebx
 lea rsi,[hdr_name]
 call glGetUniformLocation wrt ..plt
 mov edi,eax
 mov esi,[hdr_world_linear]
 call glUniform1i wrt ..plt
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
