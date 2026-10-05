; Aircraft sidecar ABI v1: indexed by stable entity ID; entity32 remains unchanged.
; Heading radians: zero flies +Z, positive turns toward +X. Pitch nose-up;
; bank radians about local forward axis. XYZ velocity is metres per fixed tick.
%define AIR_STRIDE 64
%define AIR_Y 0
%define AIR_HEADING 4
%define AIR_PITCH 8
%define AIR_BANK 12
%define AIR_SPEED 16
%define AIR_ROLE 20
%define AIR_MODE 24
%define AIR_TARGET 28
%define AIR_COOLDOWN 32
%define AIR_AMMO 36
%define AIR_GENERATION 40
%define AIR_VX 44
%define AIR_VY 48
%define AIR_VZ 52
%define AIR_PASS_TICKS 56
%define AIR_FLAGS 60
%define AIR_BOMBER 0
%define AIR_FIGHTER 1
%define AIR_ACTIVE 1
%define AIR_PATROL 0
%define AIR_ATTACK 1
%define AIR_EGRESS 2
%define AIR_RETURN 3
%define PROJECTILE_BOMB 3
%define PROJECTILE_AIR_GUN 4
%define EVENT_BOMB_LAUNCH 6
%define EVENT_BOMB_IMPACT 7
%define EVENT_AIR_GUN 8
%define EVENT_AIR_DESTROYED 9
; air_init/air_tick: reset/update real aircraft; no allocation.
; sim_entity_height(EDI index): XMM0 absolute body-centre Y. Nonair terrain+2;
; converted/uninitialized aircraft fall back to terrain+92 for legacy fixtures.
; air_hash: same incoming RAX/R8 FNV chain convention as ai_hash.
