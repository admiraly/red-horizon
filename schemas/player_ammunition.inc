%ifndef PLAYER_AMMUNITION_INC
%define PLAYER_AMMUNITION_INC
%define PLAYER_AMMUNITION_VERSION 1
%define PLAYER_AMMUNITION_REPORT_VERSION 1
%define PLAYER_AMMUNITION_REPORT_BYTES 40
%define PLAYER_AMMUNITION_REPORT_MAX_AGE 90
%define PLAYER_AMMUNITION_KNOWN 1
%define PLAYER_AMMUNITION_STRIDE 32
%define PLAYER_AMMUNITION_MAGAZINE 30
%define PLAYER_AMMUNITION_RESERVE 90
%define PLAYER_AMMUNITION_INITIAL 120
%define PLAYER_AMMUNITION_RELOAD_TICKS 60
%define PLAYER_AMMUNITION_RECEIVED_LIMIT 144000
%define PLAYER_AMMUNITION_SUPPLY_PERIOD 30
%define PLAYER_AMMUNITION_SUPPLY_RADIUS_SQ 3600.0
; generation0,reserve4,spent8,received12,last successful supply tick16,
; declared initial20,reserved zeros24/28. Public player record remains64 bytes.
; magazine+reserve+spent=initial120+received for the current actual body.
; Separate lifetime receipt counter retains debits through new bodies/leaves.
%endif
