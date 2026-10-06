%ifndef INFANTRY_WEAPON_INC
%define INFANTRY_WEAPON_INC
; Authoritative army rifle policy2; player/vehicle weapons are independent.
%define INFANTRY_WEAPON_VERSION 2
%define INFANTRY_WEAPON_STRIDE 32
%define INFANTRY_MAGAZINE 30
%define INFANTRY_RESERVE 90
%define INFANTRY_RELOAD_TICKS 60
%define INFANTRY_RECEIVED_LIMIT 144000
%define INFANTRY_RESUPPLY_PERIOD 30
%define INFANTRY_RESUPPLY_RADIUS_SQ 3600.0
%define INFANTRY_RESUPPLY_EYE 1.0
; Per stable entity: bodyGeneration0,magazine4,reserve8,reloadTicks12,
; actualShots16,emptyTick20,receivedRounds24,lastSupplyTick28.
; magazine+reserve+shots = initial120+received; received debits finite depots.
%endif
