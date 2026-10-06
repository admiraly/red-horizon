; Root-owned stateless tracked surface policy v1, fixed 30Hz units.
; Road contact: entire conservative body circle contained in one paved capsule.
; Conservative off-road at union junctions when no single capsule contains it.
; terrain_road_body(XMM0 X,XMM1 Z,XMM2 radius) -> EAX0offroad/1road/-1invalid.
; Finite [0,8000] coordinates, finite radius [0,8000]. SysV integer preserved;
; no writes/state/allocations. Bounded 19 records. XMM caller-saved.
; Terrain data is collision-available independently of renderer/content loading.
; Multipliers affect desired speed/acceleration/reverse, never clamp momentum.
; Existing braking/contact/yaw caps and max forward envelopes remain unchanged.
%ifndef GROUND_SURFACES_INC
%define GROUND_SURFACES_INC
%include "schemas/terrain_body.inc"
%define GROUND_SURFACE_VERSION 1
%define GROUND_TANK_OFFROAD 0.8
%define GROUND_ARTILLERY_OFFROAD 0.7
%define GROUND_TANK_RADIUS BODY_TANK_RADIUS
%define GROUND_ARTILLERY_RADIUS BODY_ARTY_RADIUS
%endif
