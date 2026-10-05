; Local observed incoming-hazard sidecars v1. Entity32/player64/UDP unchanged.
%define HAZARD_CAPACITY 512
%define HAZARD_STRIDE 64
%define HAZARD_IMPACT_X 0
%define HAZARD_IMPACT_Z 4
%define HAZARD_RADIUS 8
%define HAZARD_SIDE 12
%define HAZARD_X 16
%define HAZARD_Y 20
%define HAZARD_Z 24
%define HAZARD_PROJECTILE 28
%define HAZARD_PROJECTILE_GENERATION 32
%define HAZARD_KIND 36
%define HAZARD_ETA 40
%define HAZARD_ACTIVE 44
%define HAZARD_STATE_STRIDE 32
%define HAZARD_STATE_GENERATION 0
%define HAZARD_STATE_UNTIL 4
%define HAZARD_STATE_GOAL_X 8
%define HAZARD_STATE_GOAL_Z 12
%define HAZARD_STATE_CENTER_X 16
%define HAZARD_STATE_CENTER_Z 20
%define HAZARD_STATE_PROJECTILE 24
%define HAZARD_STATE_PROJECTILE_GENERATION 28
%define HAZARD_TILE_COUNT 1024
%define HAZARD_TILE_CAPACITY 8
; hazard_query(EDI side,XMM0 eyeX,XMM1 eyeY,XMM2 eyeZ):
; EAX index/-1,EDX LOS calls(<=8),XMM0 impactX,XMM1 impactZ,XMM2 radius,
; XMM3 ETA ticks float. Read-only, spatial/range/LOS gated, enemy explosives only.
; hazard_choose_goal(EDI entity,XMM0 impactX,XMM1 impactZ,XMM2 radius):
; EAX0/-1,XMM0 goalX,XMM1 goalZ,EDX reason1dispersion/2shelter.
; hazard_entity_goal(EDI entity): EAX1 active goal/0none,XMM0 goalX,XMM1 goalZ.
; hazard_init/tick/hash: authoritative private sidecars. Query is cosmetic-safe.
