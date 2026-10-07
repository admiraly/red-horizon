; Authored terrain-conforming runway rectangles and facility association.
%ifndef AIR_BASES_INC
%define AIR_BASES_INC
%define AIR_BASE_VERSION 1
%define AIR_BASE_COUNT 6
%define AIR_BASE_STRIDE 32
; Four f32 centreXZ/halfLength/halfWidth, u32 site/birthSide/front/reserved.
; air_runway_body(XMM0X,XMM1Z,XMM2radius)->1 whole circle on runway/0off/-1invalid.
; air_base_goal(EDI own aircraft)->baseID0..5 or-1, success XMM0/1centreXZ.
%endif
