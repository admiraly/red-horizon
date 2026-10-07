; Private last physically visible enemy aircraft, not network ground truth.
%define AIR_OBSERVATION_VERSION 1
%define AIR_OBSERVATION_STRIDE 64
%define AIR_OBSERVATION_RANGE_SQ 562500.0
%define AIR_OBSERVATION_REAR_COS_SQ 0.25
%define AIR_OBSERVATION_MAX_AGE 90
%define AIR_OBSERVATION_PREDICT_TICKS 30
; XYZ@0,velocityXYZ@12,owner generation@24,target ID/generation@28/32,
; observed tick@36,known@40; remaining bytes zero. Forward240degree view.
