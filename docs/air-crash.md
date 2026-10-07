# Falling airframes — isolated core phase

The authoritative aircraft casualty path now captures a dead body into a
separate128record pool before its flight state can be reused. Each96byte record
contains death XYZ/velocity/heading/pitch/bank, role, faction, physical source ID
and generation, birth tick, sequence and falling/landed state. Living army counts
are not inflated and no living body, HP, stores or generation is renewed.

Fixed public ticks conserve inherited horizontal velocity, add inherited VY and
existing gravity, gradually pitch/roll the dead airframe and clamp horizontal
map exits. Terrain contact uses the body centre, stops velocity and leaves a
stationary record until1800tick expiry. It is a ballistic/contact approximation:
no drag, aerodynamic glide, footprint/obstacle collision, gameplay cover or crash
blast is implemented. Ground impact currently settles pitch/bank flat. At most128
records update per tick, no allocation; oldest registration is retired under
pressure. Source-generation dedup survives retirement, new generations can
register, reserved bytes are zero and same-tick calls cannot advance twice.
Record bytes, dedup, cursor, count, sequence and last-update tick are hashed.

Independent native verification passes18 malformed/atomic cases, nonvolatile
register/stack and living-record preservation,201 pressure registrations with
128retained records, duplicate rejection and source reuse. A genuine initial
producer cannon round kills an already damaged aircraft at tick5; its actual
pose/velocity is captured exactly. Public flight reaches centre-to-terrain
contact at180, becomes stationary, expires at1805 and replays identically across
1805ticks. Maximum closed-form ballistic position error is0.016988m, from float
accumulation. The initial producer call does not debit FSM stores; no in-flight
pose/HP/ammo/generation/clock fixture writes occur.

Core evidence is air-crash-core-focused.json/.log. Frozen fast3f3fc6313036 is
pending and not a pass. Content0x9118562d includes seven crash policy fields;
public entity/aircraft/player layouts remain unchanged. This phase is isolated
on feature/air-crash, not integrated or claimed visible in the game. Rendering,
role-correct falling/landed meshes, actual GL death motion, bounded replication,
remote warmup/lifecycle/fault controls and coherent full integration remain the
next required work. Existing main checkpoints exclude this candidate. Complete
flight realism, spectacle and whole-game specification acceptance remain open.
