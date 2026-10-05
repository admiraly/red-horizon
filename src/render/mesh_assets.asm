; RHAM v1 offline-baked source meshes. CPU runtime loader is NASM/SSE2.
default rel
global mesh_asset_load,mesh_asset_blob,mesh_asset_size,mesh_asset_count
 global mesh_asset_descriptors,mesh_asset_clips,mesh_asset_vertices,mesh_asset_vec4_count,mesh_role_lookup
extern fopen,fread,fclose,puts
%define MAX_BLOB 67108864
section .rodata
asset_path: db 'content/models/battle.rham',0
read_mode: db 'rb',0
asset_error: db 'Missing or invalid animated model pack: content/models/battle.rham',0
fone: dd 1.0
fps_max: dd 120.0
scale_min: dd 0.0001
scale_max: dd 100.0
bounds_max: dd 1000.0
section .bss
alignb 16
mesh_asset_blob: resb MAX_BLOB+1
mesh_asset_size: resd 1
mesh_asset_count: resd 1
mesh_asset_vec4_count: resd 1
mesh_asset_descriptors: resq 1
mesh_asset_clips: resq 1
mesh_asset_vertices: resq 1
mesh_role_lookup: resd 64
section .text
; Returns0 or-1, preserves SysV registers. Rejects unsafe and non-finite ranges.
mesh_asset_load:
 push rbx
 push r12
 push r13
 push r14
 push r15
 lea rdi,[asset_path]
 lea rsi,[read_mode]
 call fopen wrt ..plt
 test rax,rax
 jz .error
 mov rbx,rax
 lea rdi,[mesh_asset_blob]
 mov esi,1
 mov edx,MAX_BLOB+1
 mov rcx,rbx
 call fread wrt ..plt
 mov r12,rax
 mov rdi,rbx
 call fclose wrt ..plt
 cmp r12,48
 jb .error
 cmp r12,MAX_BLOB
 ja .error
 lea rbx,[mesh_asset_blob]
 cmp dword [rbx],0x4d414852
 jne .error
 cmp dword [rbx+4],1
 jne .error
 cmp [rbx+8],r12d
 jne .error
 mov [mesh_asset_size],r12d
 mov eax,[rbx+12]
 test eax,eax
 jz .error
 cmp eax,32
 ja .error
 mov [mesh_asset_count],eax
 mov ecx,[rbx+16]
 test ecx,ecx
 jz .error
 cmp ecx,128
 ja .error
 mov edx,[rbx+20]
 test edx,edx
 jz .error
 mov [mesh_asset_vec4_count],edx
 mov eax,[rbx+24]
 cmp eax,48
 jb .error
 test eax,15
 jnz .error
 lea r13,[rbx+rax]
 mov [mesh_asset_descriptors],r13
 mov edi,[mesh_asset_count]
 shl rdi,6
 add rdi,rax
 mov eax,[rbx+28]
 cmp rax,rdi
 jb .error
 test eax,15
 jnz .error
 lea r14,[rbx+rax]
 mov [mesh_asset_clips],r14
 shl rcx,4
 add rcx,rax
 mov eax,[rbx+32]
 cmp rax,rcx
 jb .error
 test eax,15
 jnz .error
 lea r15,[rbx+rax]
 mov [mesh_asset_vertices],r15
 shl rdx,4
 add rdx,rax
 cmp rdx,r12
 jne .error
 lea rdi,[mesh_role_lookup]
 mov eax,-1
 mov ecx,64
 rep stosd
 xor r12d,r12d
.descriptor:
 mov eax,[r13]
 cmp eax,31
 ja .error
 mov edx,[r13+4]
 cmp edx,1
 ja .error
 lea ecx,[rax*2]
 add ecx,edx
 lea rdi,[mesh_role_lookup]
 cmp dword [rdi+rcx*4],-1
 jne .error
 mov [rdi+rcx*4],r12d
 mov eax,[r13+8]
 test eax,eax
 jz .error
 cmp eax,30000
 ja .error
 xor edx,edx
 mov ecx,3
 div ecx
 test edx,edx
 jnz .error
 mov eax,[r13+12]
 test eax,eax
 jz .error
 cmp eax,128
 ja .error
 ; Product computed explicitly in64bits from validated u32 fields.
 mov eax,[r13+12]
 mov ecx,[r13+8]
 imul rax,rcx
 lea rax,[rax+rax*2]
 mov ecx,[r13+16]
 add rax,rcx
 mov ecx,[mesh_asset_vec4_count]
 cmp rax,rcx
 ja .error
 mov eax,[r13+24]
 test eax,eax
 jz .error
 cmp eax,8
 ja .error
 mov edx,[r13+20]
 mov ecx,edx
 add rcx,rax
 mov eax,[rbx+16]
 cmp rcx,rax
 ja .error
 movss xmm0,[r13+32]
 ucomiss xmm0,[scale_min]
 jp .error
 jb .error
 ucomiss xmm0,[scale_max]
 ja .error
%assign off 36
%rep 4
 movss xmm0,[r13+off]
 ucomiss xmm0,[scale_min]
 jp .error
 jb .error
 ucomiss xmm0,[bounds_max]
 ja .error
%assign off off+4
%endrep
 shl edx,4
 lea rdi,[r14+rdx]
 mov ecx,[r13+24]
.clips:
 mov eax,[rdi+4]
 test eax,eax
 jz .error
 mov edx,[rdi]
 add rax,rdx
 mov edx,[r13+12]
 cmp rax,rdx
 ja .error
 cmp dword [rdi+12],3
 ja .error
 movss xmm0,[rdi+8]
 ucomiss xmm0,[fone]
 jp .error
 jb .error
 ucomiss xmm0,[fps_max]
 ja .error
 add rdi,16
 dec ecx
 jnz .clips
 add r13,64
 inc r12d
 cmp r12d,[mesh_asset_count]
 jb .descriptor
 ; Every vec4 component is finite before it can become a GPU fetch.
 mov ecx,[mesh_asset_vec4_count]
 shl ecx,2
.floats:
 mov eax,[r15]
 and eax,0x7f800000
 cmp eax,0x7f800000
 je .error
 add r15,4
 dec ecx
 jnz .floats
 ; Army roles require both actual high and low meshes, weapon high mandatory.
 lea rdi,[mesh_role_lookup]
 xor ecx,ecx
.required:
 cmp dword [rdi+rcx*4],-1
 je .error
 inc ecx
 cmp ecx,9
 jb .required
 cmp dword [rdi+10*4],-1
 je .error
 cmp dword [rdi+12*4],-1
 je .error
 cmp dword [rdi+14*4],-1
 je .error
 cmp dword [rdi+16*4],-1
 je .error
 cmp dword [rdi+17*4],-1
 je .error
 xor eax,eax
 jmp .done
.error:
 lea rdi,[asset_error]
 call puts wrt ..plt
 mov eax,-1
.done:
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
