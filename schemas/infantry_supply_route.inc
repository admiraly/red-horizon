%ifndef INFANTRY_SUPPLY_ROUTE_INC
%define INFANTRY_SUPPLY_ROUTE_INC
%define INFANTRY_SUPPLY_ROUTE_VERSION 1
%define INFANTRY_SUPPLY_ROUTE_LOW 30
%define INFANTRY_SUPPLY_ROUTE_RADIUS_SQ 360000.0
%define INFANTRY_SUPPLY_ROUTE_COHORTS 256
%define INFANTRY_SUPPLY_ROUTE_SLOTS 3072
; Temporary local detour for moving infantry; primary orders remain unchanged.
; At most12 finite stores, nearest within600m; normal speed/nav/hazards/LOS debit.
; Nav namespace: site*256+(physicalID>>7), separate from squad/scout goals.
%endif
