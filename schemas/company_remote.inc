%ifndef COMPANY_REMOTE_INC
%define COMPANY_REMOTE_INC
%define COMPANY_REMOTE_VERSION 2
%define COMPANY_REMOTE_COUNT 4
%define COMPANY_REMOTE_STRIDE 40
%define COMPANY_REMOTE_KEY_LIMIT 768
%include "schemas/company_transfer.inc"
%define COMPANY_REMOTE_PAYLOAD (4+COMPANY_REMOTE_COUNT*COMPANY_REMOTE_STRIDE+COMPANY_TRANSFER_PLAYERS*COMPANY_TRANSFER_STRIDE)
; record40: playerID,key,ownerBodyGeneration,leaseSerial,mode,ordered,
; goalX/Z,commandSequence,commandTick. Unassigned key=-1, metadata zero except serial.
; Followed by four complete48-byte transfer proposals.
; Complete four-record snapshot, atomic validation/apply, monotonic stream tick.
%endif
