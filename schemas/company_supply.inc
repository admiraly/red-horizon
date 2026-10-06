%ifndef COMPANY_SUPPLY_INC
%define COMPANY_SUPPLY_INC
%define COMPANY_SUPPLY_VERSION 1
%define COMPANY_SUPPLY_STRIDE 40
%define COMPANY_SUPPLY_LOW_ROUNDS 30
; player0,bodyGeneration4,company8,livingInfantry12,low16,empty20,
; knownRounds24,unknownStock28,reserved32/36.
%define COMPANY_SUPPLY_PAYLOAD 44
%define COMPANY_SUPPLY_MAX_AGE 90
; Wire: leaseSerial:u32 followed by the40-byte report. Recipient only.
%endif
