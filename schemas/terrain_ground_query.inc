%ifndef TERRAIN_GROUND_QUERY_INC
%define TERRAIN_GROUND_QUERY_INC
%define TERRAIN_GROUND_QUERY_VERSION 1
%define TERRAIN_GROUND_QUERY_BYTES 16
%define TERRAIN_GROUND_QUERY_SKIN 0.002
%define TERRAIN_GROUND_QUERY_CUTS 16
; RDI result16,ESI capacity,XMM0..5 startXYZ/endXYZ ->1hit,0clear,-1caller,-2source.
; Hit t:f32 plus three zero u32s. Output untouched otherwise. Endpoints finite,
; XZ[0,8000],absY<=16000. Current one shared relief field plus ridge/base profile.
; Partition at every height-function break. On each piece the double-precision
; profile is quadratic along the segment; three exact double evaluations give
; its normalized coefficients, then solve earliest closed contact analytically.
; Profile uses shared f32 constants promoted to double; 2mm upward collision skin
; covers CPU float-height roundoff. Not a seven-sample or endpoint-only sweep.
; SysV/SSE2, source readonly/stable, stack scratch, no heap or world writes.
%endif
