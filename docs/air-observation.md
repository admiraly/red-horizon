# Fighter visual memory

Fighter acquisition now requires actual terrain/world line of sight, a750m
three-dimensional range, and a240degree field centred on actual XYZ flight
velocity. The rear120degree sector is blind. The existing bounded49cell,
eight-samples-per-cell candidate search and escort priority remain; this is
not an exhaustive nearest-target search or a newly claimed global LOS budget.

Each physical fighter owns a fixed64byte private record containing last seen
XYZ and velocity, owner and observed target generation, target ID, observation
tick and validity. Fresh sightings replace it atomically. Recall validates the
owner and stored data and never looks up the enemy body, current HP, pose or
generation. An unseen dead/reused target can therefore leave a historical point
until it expires; this is uncertainty, not live target knowledge. Memory expires
at90ticks (three seconds); constant-velocity prediction stops after30ticks.
Predicted points are clamped to the map/height bounds. Linear confidence is
returned but is not currently a steering weight or sensor fusion system.

Horizontal and pitch guidance use this observation estimate and the existing
cannon intercept calculation. Without valid memory the fighter returns to its
own mission/escort goal. Gunnery still requires fresh acquisition and physical
forward cannon alignment; historical memory does not permit blind fire. Private
records reset on initialization/owner generation changes and participate in the
simulation checksum. Bombers retain their existing independently owned strike
memory; initial mission guidance no longer reads a live ground target first.
No HP, ammunition, body generations or clocks are renewed.

Content fingerprint0xd98a95bc includes the six observation policy fields. Both
the build canonicalizer and independent co-op oracle include them. UDP39,
schema0x212cb081 and public entity32/aircraft64/player64 records are unchanged.
Mixed-policy peers need a matching client/server restart.

The independent NASM test checks1521 view cases plus500 rotated/climbing
velocity cases,101 memory ages,11 malformed body cases and10 malformed cache
cases, actual terrain occlusion, labels-only symmetry, ABI and read-only recall.
Maximum observed estimate error is0.000239849m. Hidden enemy body changes in
separate declared getter fixtures leave candidate steering identical; the
live-body guidance control changes vertical guidance. These fixtures do not
claim physically flown enemy trajectories. Two initial aircraft births then
run360 genuine public ticks twice without in-flight world writes: two real
rounds, finalHP176 each,179rounds each,178 memory-only observation samples.

Regression fixture migrations establish visibility through initial births only:
reacquisition keeps the initially ahead enemy flying in the same direction;
650m cardinal range cases orient the pilot toward the target; the contested
escort decoy starts447m away at116.6degrees, outside the protected bomber's750m
radius, while the attacker is600m away. Target choice, actual protected-threat
damage, delayed bomb damage, finite full stores and old narrow-grid misses are
retained. The bomber strike fixture supplies an initial own mission waypoint
matching its straight ingress. None refresh actors during flight.

This is bounded visual memory, not complete intelligent AI, coordinated wing
communications, manoeuvre prediction, radar, fuel/energy/stall/landing physics
or spectacular art acceptance. Confidence-weighted pursuit and broader tactical
coordination remain open, as does full-game specification acceptance.
