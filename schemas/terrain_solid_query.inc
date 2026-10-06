; Prepared exact authored-solid point contact, not ground-height/contact hooks.
%ifndef TERRAIN_SOLID_QUERY_INC
%define TERRAIN_SOLID_QUERY_INC
%define TERRAIN_SOLID_QUERY_BYTES 16
%define TERRAIN_SOLID_QUERY_LIMIT 5
; RDI result16,ESI capacity,XMM0..5 startXYZ/endXYZ.
; EAX1hit,0clear,-1invalid caller,-2malformed source; output only on hit.
; Result first t:f32, obstacle slot:u32, source flags:u32, reserved0:u32.
; Closed3D bounds [xmin,base,zmin]/[xmax,base+height,zmax]; all current solids.
; Flag1 affects ground-body policy, not point-solid visibility/contact.
; Endpoints/geometry finite abs<=16000; nonnegative height, ordered XZ,
; flags0/1/reserved0. Readonly source count0..5 and32-byte records.
; Nearest f32 first entry, ties lower obstacle slot. SysV/SSE2, no heap.
; Does not include analytic terrain surface, living actors or wrecks.
%endif
