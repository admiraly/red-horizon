; Root-owned stateless raised terrain component ABI v1; NOT world-integrated.
%ifndef TERRAIN_RELIEF_INC
%define TERRAIN_RELIEF_INC
%define TERRAIN_RELIEF_VERSION 1
%define TERRAIN_RELIEF_LIMIT 1
%define TERRAIN_RELIEF_STRIDE 40
%define RELIEF_X0 0
%define RELIEF_X1 4
%define RELIEF_X2 8
%define RELIEF_X3 12
%define RELIEF_Z0 16
%define RELIEF_Z1 20
%define RELIEF_Z2 24
%define RELIEF_Z3 28
%define RELIEF_HEIGHT 32
%define RELIEF_FLAGS 36
%define RELIEF_ACTIVE 1
; terrain_relief(XMM0X,XMM1Z)->XMM0additionalheight,XMM1dhdx,XMM2dhdz,
; EAX0valid/-1invalid. Finite XZ[0,8000], invalid canonical+0 floats.
; Piecewise linear trapezoidX * trapezoidZ * height; choose factor derivative0
; at all four factor breaks. Continuousheight; cuspchoice DOES NOT prove grade
; clearance. SysV integer registers preserved, SSE2, readonlybounded1field,
; no allocations, authoritative writes or profile state. No world/nav/render hooks.
; Exportreadonlyterrain_relief_count,terrain_relief_fields. Field40=9f32+flagsu32.
; Root canonical x5400/5480/5620/5820,z4800/5000/5400/5600,height64m.
; Steep central ramp gradient.8, gentle gradient-.32, side fades.32 maximum.
%endif
