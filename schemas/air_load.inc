; Coordinated turn lift envelope; speed is metres per fixed30Hz tick.
%define AIR_LOAD_VERSION 2
%define AIR_LOAD_BOMBER_STALL_SPEED 2.2
%define AIR_LOAD_FIGHTER_STALL_SPEED 2.3
%define AIR_LOAD_BOMBER_STRUCTURAL 3.0
%define AIR_LOAD_BOMBER_EMERGENCY 4.5
%define AIR_LOAD_FIGHTER_STRUCTURAL 6.0
%define AIR_LOAD_FIGHTER_EMERGENCY 8.0
%define AIR_LOAD_LIFT_RESERVE 0.9
%define AIR_LOAD_TURN_GUARD 0.999999
; Maximum supported n=min(role normal/emergency, reserve*(speed/level_stall_speed)^2).
; Below supported level lift the requested bank is zero; the lift consumer handles sink.
