%ifndef DEPOT_AMMUNITION_INC
%define DEPOT_AMMUNITION_INC
; Finite site inventory prerequisite. No generation, capture or route refill.
%define DEPOT_AMMUNITION_VERSION 1
%define DEPOT_AMMUNITION_SITES 12
%define DEPOT_AMMUNITION_STRIDE 16
%define DEPOT_AMMUNITION_INITIAL 12000
%define DEPOT_AMMUNITION_MAX_TAKE 90
; remaining0,issued4,declaredInitial8,reserved12; one store per physical site.
%endif
