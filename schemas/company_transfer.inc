%ifndef COMPANY_TRANSFER_INC
%define COMPANY_TRANSFER_INC
%define COMPANY_TRANSFER_VERSION 1
%define COMPANY_TRANSFER_PLAYERS 4
%define COMPANY_TRANSFER_STRIDE 48
%define COMPANY_TRANSFER_LIFETIME 450
; proposal[requester]48: active,target,requesterKey,targetKey,requesterGen,
; targetGen,requesterLease,targetLease,expires,sequence,reserved64.
; Cleared records retain only the sequence. Both players keep one company.
; API(action):0 propose,1 accept,2 decline,3 cancel. Non-propose requires
; the exact visible proposal sequence, never implied consent or assistance.
%endif
