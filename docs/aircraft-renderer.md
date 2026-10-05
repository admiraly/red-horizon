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

Bombers now use Captain_Ahab_62's CC0 F-111 tactical fighter-bomber at22metres; fighters use the distinct Eurofighter at16metres. Each has authored high/low static geometry and its own role selection. Existing Space Kit craft records remain in the pack for provenance, but these flight roles select the military meshes. These are static models without wing/landing animation. See content/licenses/Captain-Ahab-Fighter-Jets.txt and content/model-sources.json.

The existing full 512-slot authoritative projectile upload renders kind 3 bombs
as dark, thicker velocity-oriented bodies and kind 4 air rounds as short bright
streaks behind the actual moving projectile position. Inactive records stay
hidden. No decorative dogfight shot generator exists. Network mode now uploads the separate generation-validated cosmetic trajectory pool described in [network-projectiles](network-projectiles.md).

The 64-slot cosmetic pool consumes actual events 6–9 in addition to existing
vehicle events. Launches and air gun events produce small flashes; launches,
impacts and aircraft destruction produce smoke, with destruction also producing
four timed cosmetic debris billboards and impact dust. Event sequence matching, 700 metre observer
range, ring capacity and actual event age remain enforced. Late events cannot
restart expired flashes. Cosmetics never write gameplay records. Debris remains analytic cosmetic sprites without physical collision. A separate128slot trail pool emits engine wisps and wounded-aircraft smoke from actual generation-validated moving poses; frozen simulation ticks cannot emit new samples.

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
`actual-aircraft-destruction` (PPM). These earlier captures used the space-craft surrogate. The current military meshes, layered debris and smoke trails supersede that implementation; human visual-quality acceptance remains pending.

Final integrated encounter moves the initial ground cohort to2,900m so it lies within the actual updated bomber acquisition band. Only initial actor state is arranged; flight, launches, damage and effects come from production authority. Authentic PNG captures are retained in docs/evidence/aircraft-{banked,actual-bomb-impact,actual-aircraft-destruction}.png.

Final frozen extended checkpoint337dc75f48ab passes all these checks at0aa1e5c112262e48812589c54f16ae5530f24fd1-2dd0b9232e31b986; its authentic screenshots and complete report are in docs/evidence/air-navigation-session.json.

2026-10-05 integration supersedes the historical surrogate/pixel results below: production damage now invokes evasive flight; the final wounded20HP fighter fixture is genuinely destroyed at tick15, while a separate200HP gun-contact fixture proves surviving damage starts evasion. Paired software GL checks report24trail pixels with unchanged authority,2,043impact pixels and409destruction pixels. Role silhouette normalized IoU is0.6224. The full army air-battle capture shows production encounters without recording-time state writes. Exact latest evidence is in docs/evidence/air-spectacle-session.json; software GL is not visual-quality or GPU budget acceptance.
