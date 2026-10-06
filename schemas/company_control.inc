%ifndef COMPANY_CONTROL_INC
%define COMPANY_CONTROL_INC
%define COMPANY_CONTROL_VERSION 2
%define COMPANY_CONTROL_SLOTS 1536
%define COMPANY_CONTROL_STRIDE 32
%define COMPANY_CONTROL_PLAYERS 4
%define COMPANY_CONTROL_COST 5
%define COMPANY_CONTROL_MAX_MODE 3
%define COMPANY_FOLLOW_SPACING 12.0
%define COMPANY_FOLLOW_TRAIL 24.0
%define COMPANY_FOLLOW_MARGIN 224.0
%define COMPANY_FOLLOW_MAX_ANCHOR 7776.0
%define COMPANY_FOLLOW_PROJECT_TRIES 5
%define COMPANY_FOLLOW_PROJECT_STEP 12.0
; mode0 advance,1 hold,2 retreat,3 follow current primary owner.
; Stable8-column/16-row world-axis slots; no formation rotation from mouse aim.
; company key=(side*3+front)*256+(stable actor ID>>7), same as assault cohorts.
; record32: owner+0, ownerGeneration+4, mode+8, ordered+12, goalXZ+16/20,
; sequence+24, acceptedTick+28. owner=-1 means autonomous commander.
; player assignment16: key+0, ownerGeneration+4, leaseSerial+8, reserved+12.
%endif
