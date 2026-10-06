%ifndef WORLD_CONTACT_INC
%define WORLD_CONTACT_INC
%define WORLD_CONTACT_VERSION 2
%define WORLD_CONTACT_BYTES 24
%define WORLD_CONTACT_BLAST_SKIN 0.01
%define WORLD_CONTACT_GROUND 1
%define WORLD_CONTACT_SOLID 2
%define WORLD_CONTACT_WRECK 3
%define WORLD_CONTACT_ACTOR 4
; world_contact_query(RDI result24,ESI capacity,EDX side0/1,XMM0..5 endpoints).
; EAX1hit,0clear,-1caller,-2malformed source. Output untouched unless hit.
; Result t:f32,kind:u32,identity:u32,generation:u32,sequence:u32,reserved0.
; Ground identity0; solid slot; wreck physical entity/gen/seq; actor index/gen.
; Nearest f32 t wins, equal t uses kind priority ground/solid/wreck/actor.
; All cover sources validated even after an earlier hit. Actor candidates retain
; the existing opposing-only216sample budget/4m sphere. No body/LOS hooks implied.
; Endpoints finite, XZ[0,8000],absY<=16000; source stable during call, SysV.
%endif
