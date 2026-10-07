; Bounded authoritative crash snapshots; no local physics or authority writes.
%define AIR_CRASH_WIRE_STRIDE 100
%define AIR_CRASH_WIRE_MAX 11
; slot:u32 + crash96, whole-packet validation; modular tick/sequence ordering.
; Same sequence retains identity/birth; landed pose cannot move or resume flight.
; Latest accepted source tick expires records, reset clears session history.
