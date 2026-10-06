# Next coherent wreck-cover integration

Query570b6ee is a read-only prerequisite. Instance rendering and UDPv8 are now
integrated atcff654e; observer correction81270ee retains packets during ACK waits.
The remaining batch must activate physical cover with matching local and remote
query context. Current800m culling and zero-pixel tactical cases require a useful
far/map representation before those views can explain solid cover.

Renderer: meshes.asm now submits a separate immutable-wreck batch using wreck_instance,
actual high-detail frame0 tank/artillery descriptors and matching bounds at every
mesh distance. Do not let wrecks consume living high-instance budgets or inflate
army visible/detail census. Use separate wreck telemetry/budgets. Existing
animation/suspension must never alter a captured death pose. Test real local and
network client death, expiry and ring replacement with shader geometry/depth and
census exclusion. High geometry cost and useful far representation need measured
budgets; the preparation test only verifies transform input/output.

UDP: integrated self-contained records carry slot and full64-byte wreck pose/identity.
A68-byte entry permits17 records in a40-byte-header1196-byte packet. Confirm the
actual current header before freezing a versioned wire contract. Carry source
tick/sequence, publish explicit tombstones and bound per-client fairness. Join in
progress needs complete state recovery with lost/reordered chunks; source-slot
retirement must clear old geometry without allowing a delayed old record to
resurrect it. Entity generation reuse must preserve old immutable wreck history.
Validate the entire packet before any registry mutation, reject old clock/sequence
with wrap-safe policy, clear state on disconnect and invalidate the derived query
cache whenever remote records change. Changing protocol/schema/content identity
is mandatory when these records become client-visible authority. Do not reuse the
query-cache revision as a wire authority sequence.

Vision: terrain_los currently owns swept fixed solids plus sampled ground checks.
A wreck ray can reject visibility using the shared conservative bounds, with
explicit-2 malformed-cover behavior. This must remain independent of camera,
render LOD, loaded assets and actor labels. Player rifle currently chooses the
nearest eligible target center inside a cone, then asks terrain_los to that
center; this is not an exact physical muzzle-ray hitscan. Preserve that stated
policy or implement/verify a deliberate real ray change rather than claiming
physical bullet interception from a target-center visibility check.

Shells: sim_shell_contact currently selects live actor contact; projectile_tick
uses its returned XYZ. Merge live actor/terrain/wreck first contact explicitly,
with deterministic tie policy and exact swept contact XYZ. A wreck must absorb a
shell without becoming a live actor/victim or awarding damage to an arbitrary
retired entity ID. Exercise a wreck before/after/behind a live target, start-inside,
grazing, reverse rays, zero motion and actual delayed blast. No health or pose
renewal during flight. Preserve finite ammo and admission symmetry.

Bodies/navigation: crowd/terrain_body use nominal planar body circles, with
original radii. The point query is not a body sweep: introduce bounded inflation
and a stated vertical/body-height policy before enabling body contact. Conservative
rotated world boxes can contain empty corners outside the original living body's
circle, so new wrecks can overlap an adjacent body at birth. Implement bounded
no-deepening escape and local path invalidation; do not trap actors until60s expiry
or relax arrival/recovery gates to hide the problem. Current jump does not provide
full capsule/wreck vertical collision or vault. Match local controller prediction
with server contact and test expire/retire/reuse recovery at genuine public ticks.

Checkpoint: preserve8192/16384>=95% army motion,400tick health/label symmetry,
360tick held artillery arrival,1200tick wall recovery and all original radii,
grades and speeds. Add naturally generated dense wreck cases without in-flight
HP/pose renewal. Measure actual query candidate cost with cover enabled; the
read-only Python probe's1.17–1.24us/query includes ctypes and establishes no full
server-tick budget. Full frozen scale/real graphics/audio/UDP fault verification
and hardware/human acceptance retain their existing roles.

Observed safe-point and route constraints for the next implementation:

- sim_tick expires wrecks before AI/nav/air/hazard/crowd movement. Infantry
  deferred casualties register after acquisition/ordnance, then projectile_tick
  and player_tick can register additional casualties in the same tick. Therefore
  one cache refresh per movement phase is plausible, but projectile/player
  queries can observe intervening deaths and need correct revision handling.
  Do not defer new solid cover silently to the next tick to hide rebuild cost.
- The current query rebuild transforms every active record after a revision
  change. Enabling cover during repeated same-tick blasts requires measured
  rebuild/candidate cost and potentially incremental dirty slots. Point-only
  timings do not establish the enabled server budget.
- squads.asm uses27fixed terrain nodes,512queued requests and eight builds/tick.
  It has no wreck-revision key. Adding1024wrecks as an unbounded all-pairs graph
  would defeat the existing budget. Preserve the queue cap and introduce bounded
  nearby detour nodes/route invalidation, with real multi-wreck arrival cases.
- Prepared7f652ab provides explicit sources and remote mutation revisions.
  The connected movement caller must select net_wrecks only for its prediction
  query, using accepted server-time lifecycle; server callers retain sim_wrecks.
  Shared query scratch is sequential. A future runtime job system must provide
  separate scratch/index contexts or publish immutable cache snapshots.

Replication latency is a separate cover requirement. Current global fairness
permits6.1seconds for a full1024-slot sweep even without loss, and provides no
join barrier. That is not a near-player cover freshness guarantee. Before enabled
connected prediction acceptance, add measured nearby/owned-hull priority while
retaining global fairness, or an explicit synchronization/recovery policy. Verify
a real newly destroyed hull across1..4clients at the original UDP fault settings,
with server-authoritative contact and visible correction; do not infer this from
late-join record convergence or a geometry fixture. Prepared remote revisions
remove redundant geometry rebuilding but cannot create undelivered cover state.
