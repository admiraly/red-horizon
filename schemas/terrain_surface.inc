; Stateless terrain surface sampler ABI v1. Root owns shared contract.
%ifndef TERRAIN_SURFACE_INC
%define TERRAIN_SURFACE_INC
%define TERRAIN_SURFACE_VERSION 1
%define TERRAIN_ROAD_STRIDE 24
%define TERRAIN_ROAD_LIMIT 19
%define TERRAIN_ROAD_FROM_X 0
%define TERRAIN_ROAD_FROM_Z 4
%define TERRAIN_ROAD_TO_X 8
%define TERRAIN_ROAD_TO_Z 12
%define TERRAIN_ROAD_HALF_WIDTH 16
%define TERRAIN_ROAD_FLAGS 20
%define TERRAIN_ROAD_ACTIVE 1
%define TERRAIN_OFFROAD 0
%define TERRAIN_ROAD 1
; terrain_surface(XMM0 X,XMM1 Z) -> XMM0 existing terrain_height,
; XMM1 analytic dh/dx,XMM2 analytic dh/dz,EAX centerclass0offroad/1road/-1invalid.
; Validate finiteXZ in[0,8000]; invalid outputs canonical+0. SysV callee-saved
; integer registers preserved, calls aligned. Stateless fixed rodata, bounded19
; capsule roads, no allocation or authoritative writes. Ridge cusp derivative0
; by explicit convention; endpoint cusp convention documented. No grade-clearance,
; speed, navigation, visual or network integration implied by this sampler.
; Exports read-only terrain_road_count and terrain_road_segments.
; Generated half-width0.001..8000m; float32 segmentlength >=0.001m.
; These bounds keep all SSE2/GLSL distance arithmetic finite and normal.
; Road24: fromX/fromZ/toX/toZ/pavedhalfwidth f32, flagsu32(1active).
%endif
