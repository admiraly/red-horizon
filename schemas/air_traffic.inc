; Exclusive airborne final-approach leases; runway surface is not yet serviced.
%ifndef AIR_TRAFFIC_INC
%define AIR_TRAFFIC_INC
%define AIR_TRAFFIC_VERSION 1
%define AIR_TRAFFIC_STRIDE 16
%define AIR_TRAFFIC_LEASE_TICKS 60
; Per-base u32 ownerIDPlusOne, ownerGeneration, lastGuidanceTick, owningSide.
; Empty record is allzero; six fixed entries, no queue or heap.
%endif
