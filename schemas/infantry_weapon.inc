%ifndef INFANTRY_WEAPON_INC
%define INFANTRY_WEAPON_INC
; Authoritative army rifle policy1; player/vehicle weapons are independent.
%define INFANTRY_WEAPON_VERSION 1
%define INFANTRY_WEAPON_STRIDE 32
%define INFANTRY_MAGAZINE 30
%define INFANTRY_RESERVE 90
%define INFANTRY_RELOAD_TICKS 60
; Per stable entity: bodyGeneration0,magazine4,reserve8,reloadTicks12,
; actualShots16,emptyTick20,reserved24/28. No replenishment without genuine birth.
%endif
