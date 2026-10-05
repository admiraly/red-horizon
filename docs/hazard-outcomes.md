# Observed artillery danger: physical outcome oracle

`tests/test_hazard_outcomes.py LIBSIM` runs the actual assembled world, projectile,
terrain, local perception and movement code through a development-only ctypes
harness. It compares the same seed, initial poses, ammunition and explicit manual
hold orders with `hazard_enabled=1` and the explicit negative control
`hazard_enabled=0`. The control participates in authoritative hashing; it is not
a gameplay difficulty toggle or a hidden default weakening.

The encounter places three ordinary infantry actors 33 metres from a fixed
artillery aim, with the enemy gun 240 metres away. Initialization authors only
poses, living counts and one initial gun round. `projectile_launch` creates the
real moving ballistic shell, spends the actual store and emits the launch event.
Subsequent `sim_tick` calls provide real perception, movement, collision, impact,
damage and expiry. The harness does not create hazard records, pretend shots,
impact events or damage. Each infantry step must retain the ordinary 0.12 metre
per-tick speed. Actors must physically leave the blast radius, receive less actual
damage than the stationary control, preserve the gun's HP and spent store, and
resume the manual hold after the finite danger commitment expires. Identical
runs must produce identical reported outcomes and authoritative checksums.

A companion bomb encounter uses `projectile_air_launch`, actual inherited 5m/tick
horizontal velocity and gravity, and the same enabled/disabled comparison. Its
initial low-altitude flight pose is deliberately controlled for a 40-tick fall;
this is a local ground response oracle, not evidence of normal bomber approach
planning. The launch primitive validates but does not spend the aircraft store;
that is owned by the production air FSM. The oracle reports that unchanged store
as one, rather than pretending it was spent. An initial 210-tick egress commitment
prevents the aircraft FSM from adding an unrelated second bomb to this encounter.

An actual observed artillery trajectory near the wall corner also selects a
reachable goal at (3988,1098) from (3980,1090). Both direct swept path clearance and
blast-center-to-goal terrain occlusion are checked. The actor physically follows
the selected goal and remains alive. This corner control was already
blast-occluded; no shelter survival advantage is claimed for this fixture.

Separate real-launch fixtures reject friendly rounds, an actual shell beyond
300 metres, a shell hidden by the central opaque wall and a nonexplosive tank
round. Danger queries must preserve the authoritative checksum. Generation reuse
and vehicle boarding must reject previously committed independent ground goals.

This is evidence for a bounded observed artillery response, physical dispersion,
and interruption/resumption of an explicit order. It does not establish complete
strategic or squad intelligence, dense artillery-storm acceptance, player support
warnings, network warning delivery or every possible terrain/shelter arrangement.
The JSON report includes positions/distances, actual HP, first movement timing,
physical impact events, finite stores, decisions/reasons and replay checksums.

Observed draft integration result: artillery and bomb negative controls each
lose all three 100HP infantry. Enabled responses preserve all three at 100HP,
react on ticks 5/6/7, and physically finish approximately 37.75–37.80m from the
impact. Artillery impact tick41 and bomb impact tick41 are identical between each
control/active pair. The final hold resumes by tick100. These numbers describe the
controlled encounters; authoritative checkpoint evidence is recorded by the
integrator in docs/status.md.
