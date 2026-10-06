%ifndef DEPOT_SUPPLY_INC
%define DEPOT_SUPPLY_INC
%define DEPOT_SUPPLY_VERSION 1
%define DEPOT_SUPPLY_HEADER 16
%define DEPOT_SUPPLY_RECORD 24
%define DEPOT_SUPPLY_COUNT 12
%define DEPOT_SUPPLY_BYTES 304
%define DEPOT_SUPPLY_MAX_AGE 90
%define DEPOT_SUPPLY_KNOWN 1
%define DEPOT_SUPPLY_CONNECTED 2
%define DEPOT_SUPPLY_CONTESTED 4
%define DEPOT_SUPPLY_DESTROYED 8
%define DEPOT_SUPPLY_AVAILABLE 16
; Header: player,bodyGeneration,count,reserved. Twelve zero-padded records:
; site,remaining,issued,declaredInitial,flags,reserved. Allied current role1 only.
; Unknown inventory counters are all0; KNOWN distinguishes unknown from empty.
%endif
