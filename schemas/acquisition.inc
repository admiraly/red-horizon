; Range-complete cell envelope, while retaining the bounded cell reservoir.
%define ACQUIRE_VERSION 2
%define ACQUIRE_INF_CELLS 1
%define ACQUIRE_TANK_CELLS 2
%define ACQUIRE_ARTY_CELLS 3

; Private scratch, not persistent state or packet layout. Max bomber envelope:
; 11x11 cells, at most24 original reservoir samples per cell,8-byte keys.
%define ACQUIRE_HEAP_MAX 2904
%define ACQUIRE_HEAP_BASE 128
%define ACQUIRE_STACK_BYTES 23360
