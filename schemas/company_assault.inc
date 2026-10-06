%ifndef COMPANY_ASSAULT_INC
%define COMPANY_ASSAULT_INC
%define COMPANY_ASSAULT_VERSION 1
%define COMPANY_SLOTS 1536
%define COMPANY_STRIDE 128
%define COMPANY_MIN_GROUND 16
%define COMPANY_NEAR_SQ 360000.0
%define COMPANY_STAGE_DISTANCE 300.0
%define COMPANY_ARTY_BACK 60.0
%define COMPANY_ARMOUR_FORWARD 20.0
%define COMPANY_READY_SQ 36.0
%define COMPANY_STAGE_TIMEOUT 600
%define COMPANY_PREP_TIMEOUT 180
%define COMPANY_LOSS_PERCENT 25
%define COMPANY_INF_SPACING 2.0
%define COMPANY_INF_ROW 3.0
%define COMPANY_HULL_ROW 12.0
%define COMPANY_INF_LANE 12.0
%define COMPANY_ARMOUR_LANE 35.0
%define COMPANY_ARTY_LANE 20.0
%define COMPANY_WITHDRAW_DISTANCE 120.0
%define COMPANY_IDLE 0
%define COMPANY_STAGE 1
%define COMPANY_PREP 2
%define COMPANY_ADVANCE 3
%define COMPANY_WITHDRAW 4
; actor key=(side*3+front)*256+(stable ID>>7). Company128 private records.
; phase@0, objective@4, epoch@8, phaseTick@12, initialCount@16,
; currentCount@20, nonscout infantry@24/armour@28, artillery@32, ready@36,
; mean sumsXZ@40/44, stageXZ@48/52, objectiveXZ@56/60, directionXZ@64/68,
; genuine support launch tick@72, reason@76, supportWindowStart@80, artillery stores@88/ready@92.
; Reasons:0none,1scouted/staging,2ready/preparing,3real artillery release,
; 4losses,5support timeout,6staging timeout,7no ammunition.
; init/tick/hash integrate into AI. goal(EDIactor,XMM0/1 prior goal) ->newXZ.
; No entity, HP, ammunition, projectile or clock writes. SysV/SSE2/no heap.
%endif
