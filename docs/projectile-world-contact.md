# Projectile first obstruction batch

The projectile tick now queries continuous analytic ground, all five authored
solid boxes, captured-pose wreck AABBs, and the existing sampled opposing actor
spheres together. Nearest float32 entry wins; exact equal entries prioritize
ground, authored solid, wreck, then actor. All cover sources are validated before
returning a hit. Malformed cover expires the projectile rather than allowing it
through. The result includes an explicit kind and physical identity/generation.
Air-gun direct damage requires an actor result with its current generation.

Ground contact partitions rays at every ridge and relief-field break. Each
piece is quadratic along the segment and its earliest closed root is solved in
double precision. Shared float32 terrain constants are promoted to double;
collision uses a 2mm upward skin. This is a continuous current-profile point
sweep, not an exact replica of every float32 height intermediate. Existing
terrain_height outputs were independently compared against freshly assembled
74daf98 sources at 100,000 deterministic map positions, bit for bit unchanged.

Impact events occur at contact. For a shell/bomb hitting solid/wreck cover,
blast evaluation moves at most 1cm toward the incoming segment, clamped to its
start, so a closed solid boundary does not occlude the entire explosion. Actor
and ground impacts retain the contact origin. Blast radius/damage, projectile
stores/TTL, actor radii, motion budgets and health rules are unchanged.

The wreck grid and per-slot transformed-pose memo came from the previously
prepared query work. Source pointer/revision keys are retained; accepted remote
lifecycle changes advance a derived revision without entering authority/hash.
Prepared body/context queries are verified but do not activate body collision,
navigation, connected prediction, vision/rifle or blast shielding by wrecks.
Actors still use at most216 opposing4m sphere candidates from the existing
start-cell reservoir. Friendly actors and oriented live-body hitboxes remain
outside this batch. Ground is the current8km base/ridge/one-relief-field profile;
streamed arbitrary terrain is not established.

Verification evidence before the frozen integration checkpoint:

- Continuous ground oracle:1,853 calls,1,500 global paths,300 near-surface paths,
  seven malformed sources; Decimal80 first-t error≤2.964666567795149e-8.
  Three assembled controls detect missing relief, ridge cuts and later-root
  selection. The later-root fixture crosses opposing relief ramps, producing
  two roots in one piece; the initial monotone fixture was rejected as inadequate.
- Typed arbitration:2,031 calls/2,000 scripted source orders; exact ties,
  malformed-cover suppression, unchanged caller buffers and SysV GPR/stack
  preservation. Assembled later-hit and actor/wreck-alias controls fail.
- Air-gun launch/tick:11 scripted-contact cases using the actual public launch
  and projectile implementation. Cover aliases and retired generations do not
  enter direct damage; valid live actor generation takes24 damage. Two assembled
  controls remove the type/generation guards and are detected. This establishes
  routing, not natural dogfight quality.
- Actual production geometry/index:four readonly query cases establish actor
  before wall, wall before actor, narrow relief despite a clear far endpoint,
  and genuine casualty wreck before wall/actor. Public tank shell stops on the
  independently transformed captured wreck boundary; an actor behind at5155m
  retains100 HP. The observed X5136.7783203125m follows captured yaw/pitch/bank,
  not an assumed upright local half-width. No mid-flight state renewal.
- Original point query2,063/body2,514/context401 checks pass. Pose refresh
  transforms512/0/1/0/0/0 slots for initial/unchanged/one change/same bytes/
  expiry/reactivation, including128 same-revision source switches.

Compatibility is UDPv10/schema0x68cc0f99/content0x6a9c717a. Wire layouts are
unchanged; canonical content SHA256 is
6a9c717ad1bb1b47dcb7f9ee73771a1e8d15489d8dad9edae9f1ba83519853a8.
New collision profile/type/skin policy is included in both canonical tooling
and the independent network observer. Older peers are incompatible.

Full scale, real graphics and lossy UDP acceptance must be recorded separately
from the focused evidence above. This file is not a whole-game completion claim.
