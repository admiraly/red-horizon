%ifndef WRECK_NAV_INC
%define WRECK_NAV_INC
%define WRECK_NAV_VERSION 2
%define WRECK_NAV_QUEUE 512
%define WRECK_NAV_BUILDS_PER_TICK 8
%define WRECK_NAV_LOOKAHEAD 32.0
%define WRECK_NAV_PLAN_DISTANCE 64.0
%define WRECK_NAV_ENDPOINT_INCREMENT 8.0
%define WRECK_NAV_ENDPOINT_MAX_DISTANCE 96.0
%define WRECK_NAV_LOOKAHEAD_SQUARED 1024.0
%define WRECK_NAV_PLAN_DISTANCE_SQUARED 4096.0
%define WRECK_NAV_MAX_WRECKS 8
%define WRECK_NAV_MAX_NODES 54
%define WRECK_NAV_MAX_PATH 28
%define WRECK_NAV_WINDOW_MARGIN 16.0
%define WRECK_NAV_CORNER_MARGIN 1.0
%define WRECK_NAV_MAX_LEG_SQUARED 9216.0
%define WRECK_NAV_GOAL_CHANGE_SQUARED 64.0
%define WRECK_NAV_REACHED_SQUARED 0.01
%define WRECK_NAV_SOURCE_DISTANCE_WEIGHT 0.03125
; Local route proposals, not a replacement for exact actual-motion sweeps.
; wreck_nav_goal(EDI actor,XMM0/1 chosen static goal)->XMM0/1 routed goal.
; Init/tick/hash are owned by navigation; no entity, wreck or controller writes.
; Stable FIFO, bounded local graph, original ground roles/radii, no allocations.
; Calls preserve SysV nonvolatile GPRs. Floats and volatile GPRs may clobber.
%endif
