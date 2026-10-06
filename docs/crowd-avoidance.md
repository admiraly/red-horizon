# Tracked body corridor preview

Road policy lowers off-road desired speed without increasing the tracked hull's
turn cap. The original crowd steering checked other bodies only on its proposed
one-tick segment. It therefore restored forward intent while a slow-turning hull
still approached an obstacle. The authoritative actuator correctly stopped that
collision, but repeated acceleration and contact prevented timely arrival.

`crowd_move` now previews clear-started AI tank/artillery guidance along the
actual terrain-resolved candidate direction for `min(6m, original goal range)`.
Its output remains the original bounded one-tick steering intent. The actuator
and `crowd_hull_step` still decide and validate the actual whole motion segment;
there is no enlarged displacement, contact slide, pose write or yaw shortcut.
Infantry, manual controllers, exact hull segments and genuine initial physical
overlap recovery retain their actual short-segment checks. Overlap recovery
still requires outward separation rather than interpreting a distant preview
endpoint as recovery.

Preview data uses existing per-call stack scratch and the immutable current-tick
body snapshot. Query radius remains 16m for vehicles, with the existing 5×5 grid
neighborhood and maximum 512 inspected records (including human records).
6m plus both maximum hull radii and the existing neighbor movement anticipation
fits inside that radius. Saturated queries continue to hold safely. No public
layout, persistent state, allocation, network packet or checksum stride changes.

## Exact isolated verification

Worktree base: `23495a1`; runtime source `src/nav/crowd.asm` SHA256:
`2842c8578972415742549082113047ad1774fdb98e1371cb7b6a384389e8a833`.
Actual production shared library `/tmp/rh-road-avoidance-6m/libsim.so` SHA256:
`da92264aeaaed91e32fa05d6176b272e05f925f790aad681ea124d0757418de7`.
It links the frozen `68284a947b16` simulation/navigation/AI/game objects and
terrain probe, replacing only crowd with this candidate and ground_motion with
the unchanged base-23495a1 module (which includes the prior braking correction).
This isolates the preview from other changing root sources. It is a private
Linux SysV kernel/world proof, not the final integration artifact.

A paired baseline uses precisely the same objects and ground_motion replacement,
retaining the original frozen crowd object. Its actual library SHA256 is
`7bde06eeeb51d90c63f93fba0587861dac12b3818e4eff4a4d399cd9cc81dab1`.
Unchanged `tests/test_crowd_outcomes.py` fails the original held-artillery fixture:
(1000,2000) toward (1035,2000), held artillery at (1012,2000), 360 ticks,
7.465664790986766m remaining. Log `/tmp/rh-road-avoidance-baseline-crowd.log`.
With the 6m preview, that identical fixture arrives with zero reported float32
error and minimum swept free gap 0.20009062855818804m. Held armor reaches its
original 240-tick goal within 0.0001220703125m. All original controlled encounters,
initial overlap recovery, generation reuse, simultaneous relative sweeps,
faction-label swaps and deterministic replay pass. Session 3824 exited 0 and
was collected; JSON `/tmp/rh-road-avoidance-6m-outcomes.json`, log
`/tmp/rh-road-avoidance-6m-outcomes.log`.

The unchanged natural 8k front/hotspot 120-tick censuses also pass their original
movement gates. They are not universal collision-free acceptance: hotspot final
census still reports 14 overlapping nearby pairs, affected by natural deployment
and real combat. No hidden health preservation or scenario-duration change was
introduced.

The real standalone crowd kernel passed twice, including final session 95248
(exit 0, collected), log `/tmp/rh-road-avoidance-kernel-final.log`. New independent
controls check early tracked avoidance of a held body, unchanged .5/.2m intent
caps, nearby goals limiting the preview, immediate outward overlap recovery and
unchanged infantry behavior. The existing malformed 32k-count/generation/claim
checks, read-only authoritative bytes, SysV integer preservation, controller
component rules, exact hull endpoints, 512-record saturation and replay/physical
geometry gates remain intact. No probe implementation changed.

Unchanged production fixtures using the candidate library passed and all handles
were collected:

- Controller outcomes, session 42637: original ownership/input/relative sweeps
  and real 8k/16k controller cohorts; `/tmp/rh-road-avoidance-controller_crowd_outcomes.log`.
- Terrain-body outcomes, session 40716: original swept bodies/walls/edge recovery
  and natural 8k/16k movement; `/tmp/rh-road-avoidance-terrain_body_outcomes.log`.
- Tactics, session 75634: original 1200-tick wall recovery and default 8k/16k
  movement/replay gates; `/tmp/rh-road-avoidance-tactics.log`.
- Root's frozen `c4ca2beb8683` vehicles observer: authoritative boarding, original
  paved 18m/s steady drive, cannon damage, ownership/identity cleanup and safe exit;
  `/tmp/rh-road-avoidance-vehicles-paved.log`. Observer SHA256
  `e7cdce40e2eeca8b95c9c9d6e8e695b9e2764bebe66f634b3e4e77ba45e57ebd`.

The worker-base vehicles observer initially failed its unchanged exact-18m
assertion on an off-road fixture; root had already moved that free-speed control
onto explicit pavement. The root-frozen observer passed against this candidate;
no unowned vehicle fixture was changed here. An initial scratch linking attempt
also used a nonexistent probe filename and failed before creating its library;
it was corrected to the actual frozen terrain probe. These failures remain
separate from the passing runtime evidence.

The preview is bounded local guidance, not general obstacle planning or a
long-term tangent commitment. Unsatisfiable crowds may still hold. Root owns
full integration verification, content compatibility and final status evidence;
this isolated slice makes no graphics, networking, Windows, full-frame-rate,
steep-terrain or complete-operation acceptance claim.
