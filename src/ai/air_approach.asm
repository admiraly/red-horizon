; Owned runway approach guidance; air_tick retains all physical actuators.
%include "schemas/entity.inc"
%include "schemas/aircraft.inc"
%include "schemas/air_approach.inc"
default rel
extern air_recovery_goal,air_base_goal,air_fuel_status,terrain_height
extern air_traffic_request,air_traffic_release
extern sim_entities,sim_aircraft,sim_count,air_bases
section .bss align=64
global sim_air_approaches
sim_air_approaches: resb ENTITY_CAPACITY*AIR_APPROACH_STRIDE
; generation, selected base, phase (0interior circuit/2final), reserved0
section .rodata
one: dd 1.0
negative: dd -1.0
entry: dd AIR_APPROACH_ENTRY
crosswind: dd AIR_APPROACH_CROSSWIND
radial_gain: dd AIR_APPROACH_RADIAL_GAIN
arrival2: dd AIR_APPROACH_POINT_RADIUS_SQ
alignment: dd AIR_APPROACH_ALIGNMENT
corridor: dd AIR_APPROACH_CORRIDOR
near_distance: dd AIR_APPROACH_FINAL_NEAR
far_distance: dd AIR_APPROACH_FINAL_FAR
exit_distance: dd AIR_APPROACH_FINAL_EXIT
lookahead: dd AIR_APPROACH_LOOKAHEAD
clearance: dd AIR_APPROACH_CLEARANCE
slope: dd AIR_APPROACH_SLOPE
threshold: dd 600.0
cruise: dd 110.0,140.0
align 16
abs_mask: dd 0x7fffffff,0,0,0
section .text
global air_approach_init,air_approach_goal,air_approach_hash
air_approach_init:
 lea rdi,[sim_air_approaches]
 xor eax,eax
 mov ecx,ENTITY_CAPACITY*AIR_APPROACH_STRIDE/4
 rep stosd
 ret
; EDI owned ID, XMM0/1 fallback ->EAX1 goalXZ/XMM2 absolute height, 0fallback.
; Own generation/base/phase only may change; all public/facility/fuel sources pure.
; Nonvolatile GPRs/stack preserved. Failure preserves XMM0/1/2. No allocations.
air_approach_goal:
 push rbx
 push rbp
 push r12
 push r13
 sub rsp,40
 mov ebx,edi
 movss [rsp],xmm0
 movss [rsp+4],xmm1
 movss [rsp+8],xmm2
 call air_recovery_goal
 test eax,eax
 jz .clear
 mov edi,ebx
 call air_fuel_status
 cmp eax,1
 ja .clear ; empty/invalid cannot fly a powered go-around
 mov edi,ebx
 call air_base_goal
 cmp eax,-1
 je .clear
 mov r13d,eax
 mov ecx,ebx
 shl ecx,5
 lea r12,[sim_entities]
 add r12,rcx
 shl ecx,1
 lea rbp,[sim_aircraft]
 add rbp,rcx
 ; Guard actual owned motion before mutating private route state.
 mov edx,[rbp+AIR_Y]
 cmp edx,__float32__(12000.0)
 ja .failure
 mov edx,[rbp+AIR_SPEED]
 cmp edx,__float32__(5.0)
 jb .failure
 cmp edx,__float32__(7.0)
 ja .failure
 mov edx,[rbp+AIR_VX]
 and edx,0x7fffffff
 cmp edx,__float32__(7.0)
 ja .failure
 mov edx,[rbp+AIR_VZ]
 and edx,0x7fffffff
 cmp edx,__float32__(7.0)
 ja .failure
 xorps xmm4,xmm4
%macro approach_velocity 1
 mov edx,[rbp+%1]
 and edx,0x7fffffff
 cmp edx,__float32__(7.0)
 ja .failure
 movss xmm5,[rbp+%1]
 mulss xmm5,xmm5
 addss xmm4,xmm5
%endmacro
 approach_velocity AIR_VX
 approach_velocity AIR_VY
 approach_velocity AIR_VZ
%unmacro approach_velocity 1
 mov edx,__float32__(24.9)
 movd xmm5,edx
 ucomiss xmm4,xmm5
 jb .failure
 mov edx,__float32__(49.1)
 movd xmm5,edx
 ucomiss xmm4,xmm5
 ja .failure
 movss [rsp+12],xmm0 ; base centre
 movss [rsp+16],xmm1
 movss xmm3,[negative] ; interior approach for western bases, toward -X
 cmp r13d,3
 jb .direction
 movss xmm3,[one]
.direction:
 movss [rsp+20],xmm3
 mov ecx,ebx
 shl ecx,4
 lea rbx,[sim_air_approaches]
 add rbx,rcx
 mov edx,[r12+ENTITY_GENERATION]
 cmp [rbx],edx
 jne .reset
 cmp [rbx+4],r13d
 je .same
.reset:
 mov [rsp+36],edx
 call .release
 mov edx,[rsp+36]
 mov [rbx],edx
 mov [rbx+4],r13d
 mov qword [rbx+8],0
.same:
 cmp dword [rbx+8],2
 ja .failure
 cmp dword [rbx+12],0
 jne .failure
 cmp dword [rbx+8],2
 jae .final
 ; Capture an already aligned upstream aircraft without needless circuit.
 movss xmm4,[r12+ENTITY_X]
 subss xmm4,[rsp+12]
 mulss xmm4,xmm3
 mulss xmm4,[negative]
 ucomiss xmm4,[near_distance]
 jb .staging
 ucomiss xmm4,[far_distance]
 ja .staging
 movss xmm5,[r12+ENTITY_Z]
 subss xmm5,[rsp+16]
 andps xmm5,[abs_mask]
 ucomiss xmm5,[corridor]
 ja .staging
 movss xmm5,[rbp+AIR_VX]
 mulss xmm5,xmm3
 movss xmm6,[rbp+AIR_SPEED]
 mulss xmm6,[alignment]
 ucomiss xmm5,xmm6
 jb .staging
 call .request
 cmp eax,1
 jne .staging
 mov dword [rbx+8],2
 jmp .final
.staging:
 ; Interior800m circuit: intercept the runway-aligned tangent at its edge.
 ; Front2 reverses the lateral offset to keep the full circuit off map edges.
 movss xmm4,[rsp+20]
 mulss xmm4,[entry]
 movss xmm0,[rsp+12]
 subss xmm0,xmm4 ; circuit centreX
 movss xmm1,[rsp+16]
 movss xmm6,[one]
 cmp r13d,2
 je .reverse_offset
 cmp r13d,5
 jne .offset
.reverse_offset:
 movss xmm6,[negative]
.offset:
 movaps xmm4,xmm6
 mulss xmm4,[crosswind]
 addss xmm1,xmm4 ; circuit centreZ
 movss xmm2,[r12+ENTITY_X]
 subss xmm2,xmm0
 movss xmm3,[r12+ENTITY_Z]
 subss xmm3,xmm1
 movaps xmm4,xmm2
 mulss xmm4,xmm2
 movaps xmm5,xmm3
 mulss xmm5,xmm3
 addss xmm4,xmm5
 ucomiss xmm4,[one]
 jae .normalize
 movss xmm2,[one]
 xorps xmm3,xmm3
 movss xmm4,[one]
.normalize:
 sqrtss xmm4,xmm4
 divss xmm2,xmm4
 divss xmm3,xmm4
 movss xmm5,[crosswind]
 subss xmm5,xmm4
 divss xmm5,[crosswind]
 mulss xmm5,[radial_gain]
 minss xmm5,[one]
 maxss xmm5,[negative]
 ; clockwise tangent*(−flightDirection*offsetSign), plus radial correction.
 mulss xmm6,[rsp+20]
 mulss xmm6,[negative]
 movaps xmm0,xmm3
 mulss xmm0,xmm6
 movaps xmm4,xmm2
 mulss xmm4,xmm5
 addss xmm0,xmm4
 movaps xmm1,xmm2
 mulss xmm1,xmm6
 mulss xmm1,[negative]
 mulss xmm3,xmm5
 addss xmm1,xmm3
 mulss xmm0,[lookahead]
 mulss xmm1,[lookahead]
 addss xmm0,[r12+ENTITY_X]
 addss xmm1,[r12+ENTITY_Z]
 jmp .cruise_height
.final:
 call .request
 cmp eax,1
 jne .go_around
 movss xmm4,[r12+ENTITY_X]
 subss xmm4,[rsp+12]
 mulss xmm4,[rsp+20]
 mulss xmm4,[negative] ; positive upstream distance
 ucomiss xmm4,[exit_distance]
 jb .go_around
 movss xmm5,[r12+ENTITY_Z]
 subss xmm5,[rsp+16]
 andps xmm5,[abs_mask]
 ucomiss xmm5,[crosswind]
 ja .go_around
 movss xmm0,[rsp+20]
 mulss xmm0,[lookahead]
 addss xmm0,[r12+ENTITY_X]
 movss xmm1,[rsp+16]
 ; Descending final levels at safe70m above existing ground. Ground contact
 ; remains fatal; no touchdown exemption or synthetic airborne refill exists.
 subss xmm4,[threshold]
 mulss xmm4,[slope]
 addss xmm4,[clearance]
 maxss xmm4,[clearance]
 mov eax,[rbp+AIR_ROLE]
 lea rcx,[cruise]
 minss xmm4,[rcx+rax*4]
 movss [rsp+24],xmm4
 jmp .height
.go_around:
 call .release
 mov dword [rbx+8],0
 jmp .staging
.cruise_height:
 mov eax,[rbp+AIR_ROLE]
 lea rcx,[cruise]
 movss xmm4,[rcx+rax*4]
 movss [rsp+24],xmm4
.height:
 movss [rsp+28],xmm0
 movss [rsp+32],xmm1
 movss xmm0,[r12+ENTITY_X]
 movss xmm1,[r12+ENTITY_Z]
 call terrain_height
 addss xmm0,[rsp+24]
 movaps xmm2,xmm0
 movss xmm0,[rsp+28]
 movss xmm1,[rsp+32]
 mov eax,1
 jmp .done
.clear:
 mov edi,ebx
 call air_traffic_release
 ; Bounded own slot reset when genuine recovery/base/fuel eligibility clears.
 cmp ebx,[sim_count]
 jae .failure
 cmp ebx,ENTITY_CAPACITY
 jae .failure
 cmp dword [sim_count],ENTITY_CAPACITY
 ja .failure
 mov ecx,ebx
 shl ecx,4
 lea rdx,[sim_air_approaches]
 mov qword [rdx+rcx],0
 mov qword [rdx+rcx+8],0
.failure:
 movss xmm0,[rsp]
 movss xmm1,[rsp+4]
 movss xmm2,[rsp+8]
 xor eax,eax
.done:
 add rsp,40
 pop r13
 pop r12
 pop rbp
 pop rbx
 ret
; Internal helpers derive only the already-validated own physical ID.
.request:
 lea rdi,[sim_entities]
 mov rax,r12
 sub rax,rdi
 shr eax,5
 mov edi,eax
 mov esi,r13d
 sub rsp,8
 call air_traffic_request
 add rsp,8
 ret
.release:
 lea rdi,[sim_entities]
 mov rax,r12
 sub rax,rdi
 shr eax,5
 mov edi,eax
 sub rsp,8
 call air_traffic_release
 add rsp,8
 ret
air_approach_hash:
 lea rsi,[sim_air_approaches]
 mov ecx,[sim_count]
 shl ecx,4
 test ecx,ecx
 jz .done
.bytes:
 movzx edx,byte [rsi]
 xor rax,rdx
 imul rax,r8
 inc rsi
 dec ecx
 jnz .bytes
.done: ret
section .note.GNU-stack noalloc noexec nowrite progbits
