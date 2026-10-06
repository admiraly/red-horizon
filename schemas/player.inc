; Player ABI v1: four authoritative records, 64-byte stride.
%define PLAYER_CAPACITY 4
%define PLAYER_STRIDE 64
%define PLAYER_X 0
%define PLAYER_Y 4
%define PLAYER_Z 8
%define PLAYER_YAW 12
%define PLAYER_PITCH 16
%define PLAYER_HP 20
%define PLAYER_AMMO 24
%define PLAYER_RELOAD 28
%define PLAYER_COOLDOWN 32
%define PLAYER_RESPAWN 36
%define PLAYER_FRONT 40
%define PLAYER_CONNECTED 44
%define PLAYER_SHOTS 48
%define PLAYER_HITS 52
%define PLAYER_SUPPRESSION 56
%define PLAYER_GENERATION 60
%define INPUT_FIRE 1
%define INPUT_RELOAD 2
%define INPUT_SPRINT 4

; Input protocol revision: new movement bits; public64-byte record unchanged.
%define INPUT_CROUCH 32
%define INPUT_JUMP 64

; Exterior site deployment uses existing finite offsets and full threat checks.
%define PLAYER_DEPLOY_POLICY_VERSION 2
