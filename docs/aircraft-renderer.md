# Aircraft renderer

Aircraft entity IDs index the shared 64-byte `sim_aircraft` sidecar. Both source
mesh batches (near and mid detail) and distant/tactical markers accept sidecar
altitude and heading only when its generation matches the live entity and
`AIR_ACTIVE` is set. A recycled or legacy uninitialized entity retains the old
terrain plus 90 metre rendering fallback. The sidecar altitude is absolute;
terrain is not added a second time. Source mesh transforms apply local forward
axis bank, nose-up pitch, then world heading. Ground entities retain zero pitch
and bank. `mesh_aircraft_pose` reports the last actual generated aircraft
instance for development checks and does not affect authority.

Bombers use the existing twelve metre Kenney Space Kit winged craft surrogate.
Fighters adapt that same sourced mesh to 70% width, 75% height and 85% length,
with a lighter team tint. These are distinct visual roles, not new military
models. The existing asset manifest's space-craft limitation still applies.

The existing full 512-slot authoritative projectile upload renders kind 3 bombs
as dark, thicker velocity-oriented bodies and kind 4 air rounds as short bright
streaks behind the actual moving projectile position. Inactive records stay
hidden. No decorative dogfight shot generator exists. The existing client skips
projectile upload in network mode, so this patch does not claim remote-client
bomb/round replication.

The 64-slot cosmetic pool consumes actual events 6–9 in addition to existing
vehicle events. Launches and air gun events produce small flashes; launches,
impacts and aircraft destruction produce smoke, with destruction also producing
a timed cosmetic debris billboard. Event sequence matching, 700 metre observer
range, ring capacity and actual event age remain enforced. Late events cannot
restart expired flashes. Cosmetics never write gameplay records. Debris is a
single analytic cosmetic sprite, not collision-bearing physical fragments.

Verification: objects-only client assembly passed; modified `mesh.vert` and
`battle.vert` passed vertex validation and shader-pair interface linking with
`glslangValidator`. Linked client GL execution passed on private Xvfb with Mesa
software rendering against production aircraft commit `7209e8f` and renderer
commits `5f5d3db` / `4cb4186` (coherent local worktree commit `ffc0f94`, unchanged
runtime). This is not Arc A770 performance or visual-quality acceptance.

`tests/test_client_aircraft.py` uses explicitly development-only pose fixtures
with simulation frozen to verify real GL heading/pitch/bank, role silhouette,
altitude, near/mid/distant/map instance height and generation fallback. It then
runs production authority bombing and fighter encounters from initial fixture
cohorts, without writing weapon/event records during gameplay. Observed bomb
launch event 6 at tick 34, physical impact event 7 at tick 176; air gun event 8 at
tick 1 and aircraft destruction event 9 at tick 29. Actual impact/destruction
positions matched live cosmetic pool records. Paired cosmetic-only controls
preserved entity, aircraft, projectile and event state byte-for-byte, and changed
1,648 / 404 rendered pixels respectively (RGB difference above 10). Pose fixture
pixels: bomber 14,590; bank change 18,330; bomb 2,196; air round 1,196. Timing and
pixel counts may vary across renderers.

Screenshots were captured under `/home/levy/optane-tmp/red-horizon-aircraft-`,
including `level-bomber`, `banked`, `pitch-heading`, `fighter`, `raised`,
`falling-bomb`, `air-round`, `actual-bomb-impact`, and
`actual-aircraft-destruction` (PPM). The sourced space-craft surrogate remains
visually evident. Complete military art, layered debris, smoke trails, and
spectacular art-quality acceptance remain future work.

Final integrated encounter moves the initial ground cohort to2,900m so it lies within the actual updated bomber acquisition band. Only initial actor state is arranged; flight, launches, damage and effects come from production authority. Authentic PNG captures are retained in docs/evidence/aircraft-{banked,actual-bomb-impact,actual-aircraft-destruction}.png.

Final frozen extended checkpoint337dc75f48ab passes all these checks at0aa1e5c112262e48812589c54f16ae5530f24fd1-2dd0b9232e31b986; its authentic screenshots and complete report are in docs/evidence/air-navigation-session.json.
