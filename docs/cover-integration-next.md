# Next physical-cover integration contract

This is an implementation contract from the caller audit, not feature acceptance.
Authoritative wreck vision and rifle/blast shielding are integrated at6226468
after full frozenffd071da659c passed. Movement, bounded wreck navigation and connected foot prediction are integrated
at f8d80b8, with full43b83242e4da passing all278 matching authored inputs.
The audit below retains the earlier integration contract; remaining work includes
relevant-cover freshness, overflow/performance, remote hazards and physical/visual
geometry parity. See docs/wreck-body-routing.md for exact evidence and limits.

Historical prepared gameplay hooks919a48b had13 actual movement and seven extracted
client-source controls. Zero penetrations are verified, but every direct wreck-
blocked AI route fails240tick arrival. Evidence69e899f is retained. This blocker was resolved by bounded persistent
detours and the complete checkpoint; the historical audit follows.

## Vision and fire

The world LOS/context wrapper has64 contract/18 actual-geometry checks;
production cover outcomes add24 cases. Atomic blast eligibility is connected
before damage application. Authoritative callers use world_los; explicit
remote sources and remote warning paths remain open. A separate wrapper lets foundational terrain component tests
retain their small independent link contract. It should query continuous ground,
authored solid boxes and wrecks; actor sampling belongs to shot contact, not
visibility. Caller/source faults are blocked. Preserve original eye/hull eye
origins and finite map rules; do not reintroduce seven-point ground marching.

Audit all existing terrain_los calls, including world acquisition and blast,
player spawn threat checks and fire, vehicle enter/fire, tactics, aircraft
acquisition/pass alignment, hazards/steering and squad cover placement. Each
caller needs an explicit authority/remote source choice and focused actual-path
verification. Changing the terrain primitive globally would silently expand
standalone component dependencies and does not establish those caller paths.

Blast damage must evaluate visibility against one pre-explosion cover state.
The earlier sim_blast applied casualties while walking candidates; adding wreck
LOS directly would let a newly killed earlier candidate shield later candidates
in the same instantaneous explosion. The connected two-pass implementation
collects the bounded eligible damage set before casualties, while retaining
immediate wreck registration during application. Verify ordering and label symmetry with multiple simultaneous genuine
vehicle casualties, both physical index orders and actual wreck sequences.

Contact events stay at the surface; cover blast evaluation uses the incoming
clear-side origin defined in the projectile contract. Test near-side damage,
far-side shielding, outgoing/embedded origins, another intervening wreck, ground
relief and expiry. Ground-impact blast origins need special verification: the
2mm contact skin plus float XYZ interpolation can put the event on the closed
ground boundary. A naive ground LOS call then rejects every ray at t=0. Define
an outward clear-side blast origin or a proven outgoing-surface policy before
activating the wrapper; test real gravity bomb/artillery impacts on slopes,
ridge breaks and raised relief without health/pose/clock renewal. Cover identities must never select direct living HP by index.

## Bodies and routes

An isolated ground-only composition is prepared on feature/wreck-body-world
at9b07e88 (foundation8c159bc/088a458):48 assembled source/role/radius/ABI cases and70 actual
geometry/source-switch cases. It is unconnected and not part of this accepted
candidate. The manual-step proposal additionally passes1,500 intents and two
actual-core omitted-sweep negatives; actual movement/hull/routes are unconnected.
The explicit world_body_*_context signature is EDI role,RSI stable
wreck source,EDX active count,RCX derived revision, with XMM ground coordinates.

Compose terrain/body/grade/support checks with the prepared planar wreck sweep
at the original .551/3.551/4.491m infantry/tank/artillery radii. Every accepted
movement fragment, including slide/fallback/controller fragments, must be swept.
Do not mechanically replace every long-goal squad query with the wreck grid:
the current wreck query visits an inclusive segment bounding rectangle, so an
8km diagonal can visit16,384cells. Keep actual movement sweeps exact and local,
and budget shared relevant-cover lookahead/detour work before adding dynamic
cover to distant static corridor edges. Measure cell visits and corridor
backlog rather than assuming the prepared spatial query makes long rays cheap.

The shared crowd actuator has explicit .terrain_candidate/.manual_candidate/
.hull_terrain paths, then .endpoint, plus a separate .legacy path when crowd
steering is disabled. Querying only the usual endpoint leaves the legacy path
unchecked; querying only long goals misses actual component slides. Placement
uses crowd_occupied and terrain_body_blocked and needs its own zero-motion
wreck occupation check. Squad route tests call terrain_body_path_clear at four
sites. Preserve controller final-army snapshot timing and hull eye/support tests.

Newly conservative wreck boxes can overlap living bodies: permit only the proven
non-deepening initial nearest-face escape. No shrinking radii, teleport escape,
or expiry clock renewal. Explicitly retain the planar approximation limitation.

Squad corridors currently have27 static nodes and bounded512 request slots,
eight builds per tick; no wreck-revision key exists. Add bounded local detours
around relevant cover and coalesce revision invalidation without delaying the
physical query. A death elsewhere must not invalidate every corridor or induce
unbounded full-registry transforms. Test bursts of real deaths/expiry/replacement,
held artillery arrivals≤360ticks, recovery≤1200ticks, 8k/16k≥95% motion and the
original400tick health/label-symmetry checks. Actual user driver/army navigation
must reach the same physical destinations.

Connected prediction must explicitly select net_wrecks/count/revision via the
context API; legacy wrappers read sim_wrecks. Same revision values across sources
must not reuse another source's bounds. Existing self-contained lossy packets
can take6.1seconds to scan a full1024 ring absent loss; there is no reliable join
barrier or guaranteed nearby freshness. Match newly admitted cover before
claiming prediction parity. Never import remote poses into authoritative hashes.

## Graphics and acceptance

The physical bound is the captured frame0 high/low geometry union plus skin.
High/low roof mismatch and800m draw culling remain explicit; map view currently
has no visible wreck pixels. Avoid making an invisible blocker acceptance claim.
Pair actual body/shot/visibility fixtures with local and co-op screenshots and
lossy UDP lifecycle evidence, including near relevant cover and retirement.
Preserve real graphics, scale and network fault coverage at the frozen full
checkpoint; passing focused geometry tests alone does not establish the game.
