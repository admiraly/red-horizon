# Authoritative aircraft

Aircraft sidecar ABI v1 preserves entity32. Absolute body Y, heading, pitch,
bank, metres-per-tick speed, role, mode, finite ammo, target and velocity are
hashed as actual authoritative state. Generation plus AIR_ACTIVE guards fixture
fallback (terrain+92). All combat/player body queries share sim_entity_height.

Flight updates before ground movement at 30 Hz. Aircraft cannot stop under hold,
turn instantly, or use terrain detour teleports: bombers fly 150 m/s, fighters
210 m/s, with bounded heading changes of 0.025/0.04 radians per tick, bounded
climb/descent of 0.5 m per tick, and bank/pitch driven by actual steering. Map
edges trigger inward turns 650 m ahead. Stable aircraft groups alternate roles.

Bombers acquire actual opposing ground actors through range-limited terrain LOS
and the bounded ground spatial reservoir. New approach targets lie 750–1200 m
away; acquisition is staggered every four ticks and inspects at most 121 cells
with 24 samples each. An observed victim stays attached to the pass only while
revalidated in LOS/range every tick. An aligned pass releases a real bomb
with inherited aircraft velocity; gravity, swept walls/ground/actor contact and
36 m enemy-only LOS blast apply later. After a release they egress for 210 ticks.
Fighters use a separate linear-built air index, at most 72 candidates per local
query, physically observe opposing aircraft within 750 m in 3D, prioritize fighters,
steer with short lead,
and fire only inside the forward cone and altitude tolerance. Their real moving
rounds sweep contacts and damage the contacted opposing actor without a blast.
Automatic infantry, tanks and artillery do not target aircraft. Explicit cannon
and player rifle APIs still use actual airborne height for valid aimed shots.

Stores are finite (8 bombs or 180 gun rounds); depletion returns aircraft toward
their own side. There is no invented rearm supply, landing, runway, or ammunition
regeneration. Ground AI can occupy 416 projectile records, preserving 64 further
AI opportunities for air and 32 slots for human launches. Saturation refuses
rather than inventing damage. Events 6/7/8/9 represent actual bomb launch/impact,
air-gun launch and aircraft destruction.

Verified locally: fast core suite, focused combat and waypoints; the dedicated
aircraft fixture proves continuous held flight, bounded yaw, aligned moving bomb
and delayed ground damage, no ammo regeneration, physical fighter acquisition,
aerial gun travel/damage, distant-enemy rejection and seeded 8192-unit replay.
Final integrated8192-unit seed42 over900ticks records70 bomb launches,
63 impacts,5134 air-gun launches and179 aircraft destructions;16384 records
41/37/9763/370 respectively. Counts reflect actual retained authoritative events,
with zero overwritten unobserved events. Ground navigation changes encounters,
so earlier worker-only counts are not the final integrated outcome. Physical
travel/replay, rendered authority encounters and dedicated-server self-contained
pose updates have separate tests. Exact final checkpoints are recorded in
`docs/evidence/air-navigation-session.json`. Spectacle and human play quality
remain unaccepted. No flight simulator,
formation escorts, aerodynamic stalls or runway operations
are claimed.

The2026-10-05 continuation adds actual surviving-damage fighter jink/climb and bomber abort/egress. Commitments are finite and repeated hits cannot renew them; map safety retains priority. Production gun contact, generation reset, invalid/zero damage, checksum replay and reacquisition are verified. Direction is deterministic by actor index, without shooter-direction or incoming-projectile perception. Latest900tick seed42 counts are68/62/4950/168 at8192 and58/48/9691/352 at16384. See [air defense evidence](verification/air-defense.md) and docs/evidence/air-spectacle-session.json for the superseding integration.
