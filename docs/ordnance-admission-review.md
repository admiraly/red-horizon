# Bounded ordnance admission: causal review

Reviewed baseline `49ccd4d352e345df80e463ed0f3eaecfef013a9a` on
2026-10-05. This review concerns admission of real moving projectiles. It does
not establish overall damage balance, intelligent target choice, audiovisual
quality, or the complete combined-arms acceptance requirements.

## What the current source proves

`src/sim/world.asm:395` walks ground combat in ascending entity ID. Initialization
puts side0 IDs before side1 IDs (`sim_init`, around lines77–93). Once an actual
opposing ground target passes range and `terrain_los`, tanks/artillery call
`projectile_spawn` immediately at lines561–566. Fire eligibility is staggered by
`(sim_tick_count + entityID) & 7 == 0`; the per-source shell cooldown additionally
limits tanks to30 ticks and artillery to90 ticks. Infantry accumulated damage is
applied later, after the aircraft combat pass. Acquisition is bounded by sampled
spatial cells, not an all-entity scan.

`src/sim/projectiles.asm:87` verifies source and target bounds, opposing sides,
living HP, ground weapon kind, positive finite ammunition and zero cooldown.
It rejects a ready ground launch when the **total** active pool count is at least
`512−32−64 = 416`. Successful `projectile_launch` installs the physical trajectory,
generation, source identity, damage and blast radius, spends one source round,
sets cooldown, and emits the real launch event. Capacity rejection spends neither
ammo nor cooldown. The common pool search is also bounded by512 slots. Direct
`projectile_launch` uses physical free slots up to512; the player cannon calls
this API in `src/game/vehicles.asm:524`.

`src/ai/aircraft.asm:385` builds the sampled air index, then also walks combat
actors in ascending ID. Bombers preserve a previous target only while it is still
alive, opposing, ground, in range and actual current terrain LOS; new candidates
come from the observed ground target. Fighters acquire an opposing aircraft from
bounded nearby air cells and actual current LOS. All aircraft update target/mode
state even if no shot is possible. Release additionally needs finite stores,
zero cooldown, zero pass commitment, and actual nose/pass alignment. At line658,
`projectile_air_launch` is called immediately. Only success decrements `AIR_AMMO`,
sets cooldown3, and makes a bomber enter210tick egress and clear its target.

`src/sim/projectiles.asm:553` admits aircraft only while the **total** active pool
count is below `512−32 = 480`. It validates aircraft liveness, kind, sidecar active
flag and source generation, role, store and cooldown; a fighter also needs a live
opposing aircraft target. The launch API does not itself redo terrain LOS or
alignment, which are the FSM caller's responsibility. The aircraft target field
has no stored target generation. A queued request therefore needs a private
snapshot of both source and target generations if it survives acquisition.

The authoritative call order is ground admission → aircraft admission →
infantry damage application → `projectile_tick` → operation → `player_tick`
(`world.asm:573–599`). Thus free slots released by flight or impacts later in a
tick cannot help either preceding AI pass. Player cannon launches happen after
that release. The32 and64 margins are total-count ceilings, **not** pools reserved
for a particular kind: persistent aircraft rounds can occupy480 slots and stop
all ground launches at416. The air margin does not reserve bombs independently
from fighter gunfire.

## Causal boundary evidence

The isolated worktree's `python3 tools/dev.py test --suite combat` passed on the
reviewed baseline, built revision
`49ccd4d352e345df80e463ed0f3eaecfef013a9a-46820edea2876254`; its process terminated
with exit0. The resulting `build/libsim.so` SHA256 was
`d335b8a326ba2c8c05a9ed132cd957561deb1568c1a67c709c12b75a0b5e6c66`.

A separate development-only ctypes probe initialized32 actual entities and put
live tank12(side0) and tank28(side1) at clear opposite firing positions. It filled
415 slots by415 genuine `projectile_launch` calls, then called `projectile_spawn`
for the two sources with live opposing targets. Saturation construction reset
the fill source's cooldown and raised its ammunition; it wrote no active
projectile records, damage or events. This is a pool-policy probe, not a normal
battle or finite-ammunition acceptance demonstration.

| Order | Return values | Ammo12 before→after | Ammo28 before→after | Count | Drops |
| --- | --- | --- | --- | --- | --- |
|12,28|0,−1|585→584|64→64|416|1|
|28,12|0,−1|585→585|64→63|416|1|

Only the admitted source received cooldown30; the rejected source remained at0.
Swapping caller order swaps which side receives the final real shell. This
establishes the capacity boundary is caller-order dependent. Coupled with the
actual ascending-ID world loop and side-contiguous initialization, it explains a
specific asymmetry under simultaneous eligible demand. It does **not** prove that
this explains every unequal sampled battlefield occupancy; target availability,
finite stores, casualties, and flight duration also affect those counts.

`docs/evidence/dense-projectile-pressure.json` independently counted actual active
records for120 ticks. It reports8100 and10148 refused requests in front/hotspot,
and some sampled ticks with no side1 tank shell. Its independent peaks need not
coincide. That historical source's counts are supporting pressure evidence, not
a controlled attribution of every missing shell or a fairness acceptance result.

## Recommended bounded physical policy

Build private per-tick request arrays while doing the existing acquisition pass,
with at most one request per actor. Separate ground requests into four groups
`side × {tank,artillery}`. Each request records source ID/generation and target
ID/generation; no fabricated target positions or launch events. Admission consumes
actual free capacity by round-robin interleaving nonempty groups, beginning at a
rotating group, and cycling participants from a per-group stable-ID cursor.
Continue to call the production spawn function. Update a group's participant
cursor after its last successful admission. Advancing past every rejected item
when a pool is full can repeatedly restore the same eligible prefix.

**Avoid scheduling aliasing if preserving the old gate:** `startGroup = tick & 3`
always presents the same leader to actors whose eligibility repeats every8 ticks.
A counter advanced once per tick has the same failure when all eight phases have
requests. `(tick >> 3) & 3` or phase-specific starts avoid that aliasing.

The integrator's later contract `2fd67aa` instead removes the eight-tick eligibility
gate **only for armour/artillery**, retaining infantry's existing damage phase.
The actual30/90tick weapon cooldown remains authoritative. In the reviewed old
loop, the eight-tick gate rounded effective successful cadences to32/96 ticks;
removing it permits the specified30/90 cadence. Capacity-denied actors retain
stores and zero cooldown and can request again on the next tick, so `tick & 3`
rotation no longer aliases that old eight-phase schedule. This is a sound runtime
direction, not a verified implementation claim from this read-only worker.
Keep legacy phasing only as an explicit negative-control mode, not the default.
Queue collection under saturation can see up to eight times as many ready
requests, but remains O(N); existing target acquisition already runs every tick.
Measure the actual cost and bounded-drain diagnostics. Keep any stored private
future-affecting cursors in replay checksums.

With request collection and a single drain, work is O(entity count + requests),
with no allocation and a bounded pool search per successful launch. Stop launching
once the corresponding count ceiling is reached; count the remaining ready
requests as capacity refusals without calling a guaranteed-failing API for each
one. Keep preexisting ammo/cooldown rejection distinct from capacity rejection.
A lower bound on admissions for all equally eligible groups can be checked, but
no policy can promise every ready actor a shot while the physical pool is full.
Finite flight lifetimes and repeated opportunities are required for a waiting
bound. Do not report equal active occupancy as the definition of fairness.

Aircraft fairness remains a separate pending runtime change; the new ground
contract does not itself fix the aircraft ascending-ID loop. Aircraft can use
the same four groups `side × {bomber,fighter}`. Preserve the
entire existing bounded target/LOS/alignment evaluation for each actor, and queue
only a fully ready release. On admission, revalidate source/target generations,
liveness, side, role, sidecar generation, defense/pass commitment, stores,
cooldown, current observation and alignment. Commit store/cooldown/egress changes
only after production launch succeeds. A deferred fighter must not use another
actor's temporary target or stale pointer. Reacquiring every tick is preferable
to retaining failed requests across ticks; a long-lived queue would need explicit
expiry and loss-of-observation cancellation.

A rotation of the whole ID loop is simpler but does not interleave side/role
blocks and can still starve a smaller group during sustained pressure. A
request-based interleaver does not require changing poses, projectile physics,
finite stores, camera-dependent rules, authoritative entity32, aircraft64, or
network wire records. Derived queue scratch can be cleared each tick and omitted
from hashes; persistent participant/phase cursors must reset on initialization
and be included in private authority hashing. Do not hash diagnostic counters.

## Required verification for integration

- Symmetric live sources and real observed targets under controlled physical pool
  pressure: both sides and both roles obtain actual launches; reverse ID/group
  assignment and compare admission service. Verify default armour/artillery
  cooldown30/90 cadence and unchanged infantry eight-tick phasing. The explicit
  legacy negative control must retain its old schedule; if that schedule is ever
  paired with fair admission, cover all eight phases and more than32 ticks.
- Several eligible participants per group, restricted repeated free capacity:
  late IDs receive real physical launches, not merely a nonzero request count.
  Use existing finite ammunition and release real slots through flight/impact.
- Zero/full capacity, empty groups, stale source/target generations, dead source,
  kind conversion, driver boarding, exhausted stores, active cooldown, target
  behind terrain, and insufficient alignment must not publish/spend a shot.
- Aircraft success must still cause bomb egress and consume one finite store;
  denial must retain stores and the existing physical flight trajectory.
- Direct player/API launches retain physical headroom; replay hashes reproduce
  admission/cursors and changing observer state does not change combat.
- Actual8192/16384 front/hotspot timing and side/role request/admission/refusal
  counts, recorded alongside physical retained rounds and eventual impacts.
  Broader cross-class crowding from persistent aircraft gun rounds needs its own
  policy decision if measured after within-class ordering is corrected.

No runtime code was changed for this review. The controlled boundary probe and
combat suite are terminal; there are no outstanding jobs from this worker.
