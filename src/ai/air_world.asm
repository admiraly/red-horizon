; Read-only swept aircraft envelope against actual ground and authored solids.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_flight.inc"
%include "schemas/terrain_solid_query.inc"
default rel
extern terrain_ground_query,terrain_obstacles,terrain_obstacle_count,segment_box
extern terrain_relief_count,terrain_relief_fields
extern sim_entities,sim_aircraft,sim_count
section .rodata
zero: dd 0.0
one: dd 1.0
mapmax: dd 8000.0
limit: dd 16000.0
radius: dd AIR_FLIGHT_BODY_RADIUS
lookahead: dd AIR_FLIGHT_WORLD_LOOKAHEAD
base_gradient: dd 1.0345 ; 1 + .008 + .0225 + .004, baseline height bounds
roundoff: dd 0.01
section .text
global air_world_sweep,air_world_warning
; RDI result16/ESI capacity, XMM0..5 start/end XYZ.
; -> EAX1 contact,0clear,-1caller,-2source. Result t,kind1ground/2solid,id,reserved.
; Swept axis-aligned4m half-extent hull; terrain uses conservative slope envelope.
; Output untouched on clear/error; all sources validated before publishing hit.
air_world_sweep:
 test rdi,rdi
 jz .bad_leaf
 cmp esi,16
 jb .bad_leaf
 push rbx
 push r12
 push r13
 sub rsp,96
 mov r13,rdi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 movss [rsp+12],xmm3
 movss [rsp+16],xmm4
 movss [rsp+20],xmm5
 xor ecx,ecx
.validate:
 mov eax,[rsp+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .bad
 cmp ecx,1
 je .coord
 cmp ecx,4
 je .coord
 movss xmm0,[rsp+rcx*4]
 ucomiss xmm0,[zero]
 jb .bad
 ucomiss xmm0,[mapmax]
 ja .bad
.coord:
 inc ecx
 cmp ecx,6
 jb .validate
 ; First exact query validates terrain records before computing their gradients.
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
 lea rdi,[rsp+24]
 mov esi,24
 call terrain_ground_query
 test eax,eax
 js .source
 movss xmm0,[base_gradient]
 cmp dword [terrain_relief_count],1
 jne .envelope
 lea rax,[terrain_relief_fields]
 cmp dword [rax+36],1
 jne .envelope
 ; A remote relief ramp cannot enlarge a low aircraft's local hull contact.
 ; Only segments whose swept XZ footprint overlaps its full support need it.
 movss xmm1,[rsp]
 movss xmm2,[rsp+12]
 minss xmm1,xmm2
 subss xmm1,[radius]
 ucomiss xmm1,[rax+12]
 ja .envelope
 movss xmm1,[rsp]
 maxss xmm1,xmm2
 addss xmm1,[radius]
 ucomiss xmm1,[rax]
 jb .envelope
 movss xmm1,[rsp+8]
 movss xmm2,[rsp+20]
 minss xmm1,xmm2
 subss xmm1,[radius]
 ucomiss xmm1,[rax+28]
 ja .envelope
 movss xmm1,[rsp+8]
 maxss xmm1,xmm2
 addss xmm1,[radius]
 ucomiss xmm1,[rax+16]
 jb .envelope
 movss xmm1,[rax+4]
 subss xmm1,[rax]
 movss xmm2,[rax+12]
 subss xmm2,[rax+8]
 minss xmm1,xmm2
 movss xmm2,[rax+32]
 divss xmm2,xmm1
 addss xmm0,xmm2
 movss xmm1,[rax+20]
 subss xmm1,[rax+16]
 movss xmm2,[rax+28]
 subss xmm2,[rax+24]
 minss xmm1,xmm2
 movss xmm2,[rax+32]
 divss xmm2,xmm1
 addss xmm0,xmm2
.envelope:
 mulss xmm0,[radius]
 addss xmm0,[roundoff]
 movaps xmm6,xmm0
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 subss xmm1,xmm6
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 subss xmm4,xmm6
 movss xmm5,[rsp+20]
 lea rdi,[rsp+24]
 mov esi,24
 call terrain_ground_query
 test eax,eax
 js .source
 mov dword [rsp+64],0
 jz .solids
 mov eax,[rsp+24]
 mov [rsp+60],eax
 mov dword [rsp+64],1
 mov dword [rsp+68],0
.solids:
 mov eax,[terrain_obstacle_count]
 cmp eax,TERRAIN_SOLID_QUERY_LIMIT
 ja .source
 mov [rsp+72],eax
 lea rbx,[terrain_obstacles]
 xor r12d,r12d
.loop:
 cmp r12d,[rsp+72]
 jae .finish
 xor ecx,ecx
.source_coords:
 mov eax,[rbx+rcx*4]
 and eax,0x7fffffff
 cmp eax,__float32__(16000.0)
 ja .source
 inc ecx
 cmp ecx,6
 jb .source_coords
 cmp dword [rbx+24],1
 ja .source
 cmp dword [rbx+28],0
 jne .source
 movss xmm0,[rbx+20]
 ucomiss xmm0,[zero]
 jb .source
 movss xmm0,[rbx]
 subss xmm0,[radius]
 movss [rsp+24],xmm0
 movss xmm0,[rbx+16]
 subss xmm0,[radius]
 movss [rsp+28],xmm0
 movss xmm0,[rbx+4]
 subss xmm0,[radius]
 movss [rsp+32],xmm0
 movss xmm0,[rbx+8]
 addss xmm0,[radius]
 movss [rsp+36],xmm0
 movss xmm0,[rbx+16]
 addss xmm0,[rbx+20]
 addss xmm0,[radius]
 movss [rsp+40],xmm0
 movss xmm0,[rbx+12]
 addss xmm0,[radius]
 movss [rsp+44],xmm0
 ; Source ordering must be valid before expanding the box.
 movss xmm0,[rbx]
 ucomiss xmm0,[rbx+8]
 ja .source
 movss xmm0,[rbx+4]
 ucomiss xmm0,[rbx+12]
 ja .source
 lea rdi,[rsp+24]
 mov esi,24
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 movss xmm3,[rsp+12]
 movss xmm4,[rsp+16]
 movss xmm5,[rsp+20]
 call segment_box
 test eax,eax
 js .source
 jz .next
 cmp dword [rsp+64],0
 je .take
 ucomiss xmm0,[rsp+60]
 jae .next
.take:
 movss [rsp+60],xmm0
 mov dword [rsp+64],2
 mov [rsp+68],r12d
.next:
 inc r12d
 add rbx,32
 jmp .loop
.finish:
 xor eax,eax
 cmp dword [rsp+64],0
 je .done
 movdqu xmm0,[rsp+60]
 movdqu [r13],xmm0
 mov dword [r13+12],0
 mov eax,1
 jmp .done
.bad:
 mov eax,-1
 jmp .done
.source:
 mov eax,-2
.done:
 add rsp,96
 pop r13
 pop r12
 pop rbx
 ret
.bad_leaf:
 mov eax,-1
 ret
; EDI living physical aircraft ID. ->0clear/1risk, invalid metadata0.
; Own velocity prediction only; no hidden opponent reads or authoritative writes.
air_world_warning:
 cmp edi,[sim_count]
 jae .clear_leaf
 cmp edi,ENTITY_CAPACITY
 jae .clear_leaf
 mov eax,edi
 shl eax,5
 lea rdx,[sim_entities]
 add rdx,rax
 cmp dword [rdx+ENTITY_HP],0
 je .clear_leaf
 cmp dword [rdx+ENTITY_KIND],3
 jne .clear_leaf
 cmp dword [rdx+ENTITY_SIDE],1
 ja .clear_leaf
 mov eax,edi
 shl eax,6
 lea rcx,[sim_aircraft]
 add rcx,rax
 mov eax,[rdx+ENTITY_GENERATION]
 test eax,eax
 jz .clear_leaf
 cmp eax,[rcx+AIR_GENERATION]
 jne .clear_leaf
 test dword [rcx+AIR_FLAGS],AIR_ACTIVE
 jz .clear_leaf
 cmp dword [rcx+AIR_ROLE],1
 ja .clear_leaf
 mov eax,[rcx+AIR_VX]
 and eax,0x7fffffff
 cmp eax,__float32__(AIR_FLIGHT_MAX_SPEED)
 ja .clear_leaf
 mov eax,[rcx+AIR_VZ]
 and eax,0x7fffffff
 cmp eax,__float32__(AIR_FLIGHT_MAX_SPEED)
 ja .clear_leaf
 mov eax,[rcx+AIR_VY]
 and eax,0x7fffffff
 cmp eax,__float32__(0.5)
 ja .clear_leaf
 sub rsp,24
 movss xmm0,[rdx+ENTITY_X]
 movss xmm1,[rcx+AIR_Y]
 movss xmm2,[rdx+ENTITY_Z]
 movss xmm3,[rcx+AIR_VX]
 mulss xmm3,[lookahead]
 addss xmm3,xmm0
 maxss xmm3,[zero]
 minss xmm3,[mapmax]
 movss xmm4,[rcx+AIR_VY]
 mulss xmm4,[lookahead]
 addss xmm4,xmm1
 movss xmm5,[rcx+AIR_VZ]
 mulss xmm5,[lookahead]
 addss xmm5,xmm2
 maxss xmm5,[zero]
 minss xmm5,[mapmax]
 mov rdi,rsp
 mov esi,16
 call air_world_sweep
 test eax,eax
 js .warning_out
 cmp eax,1
 sete al
 movzx eax,al
.warning_out:
 add rsp,24
 ret
.clear_leaf:
 xor eax,eax
 ret
section .note.GNU-stack noalloc noexec nowrite progbits
