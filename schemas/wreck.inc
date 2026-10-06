; Authoritative temporary wreck registry v1. CPU runtime NASM/SSE2.
%ifndef WRECK_INC
%define WRECK_INC
%define WRECK_VERSION 1
%define WRECK_CAPACITY 1024
%define WRECK_STRIDE 64
%define WRECK_LIFETIME_TICKS 1800
%define WRECK_X 0
%define WRECK_Y 4
%define WRECK_Z 8
%define WRECK_HEADING 12
%define WRECK_PITCH 16
%define WRECK_BANK 20
%define WRECK_KIND 24
%define WRECK_SIDE 28
%define WRECK_ENTITY 32
%define WRECK_GENERATION 36
%define WRECK_BIRTH 40
%define WRECK_EXPIRY 44
%define WRECK_SEQUENCE 48
%define WRECK_FLAGS 52
%define WRECK_ACTIVE 1
%define WRECK_UPRIGHT 2
; init resets all records, source-generation dedup, count/cursor/sequence.
; register(EDI source ID)->EAX0 added,1 already registered,-1 invalid.
; Requires actual dead HP0 kind1/2, valid side/gen/finite map XZ. No mutations
; on invalid/duplicate. Captures immutable death XYZ/heading/pitch/bank, using
; matching active ground motion and unsmoothed support/contact. Upright fallback
; explicitly flagged if motion/support is unavailable. No entity/HP/ammo writes.
; Ring capacity retires oldest accepted registration, independent of side labels.
; tick expires age>=1800 by modular unsigned age, retaining sequence tombstones.
; hash(RAX seed,R8 FNV) includes records, dedup and future-affecting metadata.
; SysV nonvolatile registers preserved, helper calls aligned; no heap allocation.
; Prerequisite registry only: collision/render/replication hooks remain separate.
%endif
