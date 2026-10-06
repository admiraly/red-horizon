%ifndef COMPANY_REMOTE_INC
%define COMPANY_REMOTE_INC
%define COMPANY_REMOTE_VERSION 1
%define COMPANY_REMOTE_COUNT 4
%define COMPANY_REMOTE_STRIDE 40
%define COMPANY_REMOTE_KEY_LIMIT 768
%define COMPANY_REMOTE_PAYLOAD (4+COMPANY_REMOTE_COUNT*COMPANY_REMOTE_STRIDE)
; record40: playerID,key,ownerBodyGeneration,leaseSerial,mode,ordered,
; goalX/Z,commandSequence,commandTick. Unassigned key=-1, metadata zero except serial.
; Complete four-record snapshot, atomic validation/apply, monotonic stream tick.
%endif
