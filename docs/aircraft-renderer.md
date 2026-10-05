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

Verification before integration: objects-only client assembly passed; modified
`mesh.vert` and `battle.vert` passed `glslangValidator -S vert`. These checks do
not establish linking, actual driver rendering, aircraft behaviour or visual
quality. `tests/test_client_aircraft.py` supplies explicitly development-only
pose fixtures to a real client with its simulation clock frozen, and checks
actual GL pixel changes for heading/pitch/bank, role silhouette and altitude,
plus near/mid/distant/map instance height and recycled-generation fallback.
Its execution and screenshots require the integrated aircraft simulation;
actual event rendering proof remains required at integration.
