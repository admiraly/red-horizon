%ifndef COMPANY_CONTROL_INC
%define COMPANY_CONTROL_INC
%define COMPANY_CONTROL_VERSION 1
%define COMPANY_CONTROL_SLOTS 1536
%define COMPANY_CONTROL_STRIDE 32
%define COMPANY_CONTROL_PLAYERS 4
%define COMPANY_CONTROL_COST 5
; company key=(side*3+front)*256+(stable actor ID>>7), same as assault cohorts.
; record32: owner+0, ownerGeneration+4, mode+8, ordered+12, goalXZ+16/20,
; sequence+24, acceptedTick+28. owner=-1 means autonomous commander.
; player assignment16: key+0, ownerGeneration+4, leaseSerial+8, reserved+12.
%endif
