# Task graph and ready queue — current integration
| Task | Owner | Dependency | State / acceptance evidence |
|---|---|---|---|
| Attached aircraft wreck smoke/fire | integrator | authoritative falling registry/source-clock | integrated from4907e97; bounded32emitters/640quads, native/embeddedGL/local+UDP paired controls and original real aircraft regression pass; full443028e6200e pending, billboard craft/HDR/lights/hardware acceptance open |
| Physical falling airframes and remote lifecycle | integrator | genuine aircraft casualty/mesh/UDP | integrated0a1eb12; bounded128registry, role-correct read-only meshes, UDP40 snapshots/late join/real-time expiry. Complete aircraft/network, actual local/UDP GL,8k16k bounds pass; full40b03f364420 pending; no drag/cover/blast or spectacle acceptance |
| Aircraft critical-damage/empty recovery | integrator | physical flight/own condition | integratedef3be5c; real projectile-triggered withdrawal and four empty-store flights, native policy/core/aircraft/8k16k bounds/network/actual GL pass; full7c089c36ca91 passed1932.590514s, landing/rearm/safe-base tactics open |
| Confidence-weighted fighter pursuit | integrator | visible enemy memory/own mission | integrated85d1e31;10k native cases, causal public flight, original8k/16k bounds, complete aircraft/network/actual GL pass; full17efd869fb1b passed1911.905768s; flight/tactics/art acceptance open |
| Fighter visible enemy memory | integrator | aircraft perception/LOS | integrated c135e6e; native view/occlusion/expiry/hidden-body controls, original scale aircraft, ordinary network and actual GL pass; full8c64c8e62bd1 passed1946.258357s; broader tactics open |
| Canonical spec, ABI, isolated worktrees | integrator | repository | committed |
| Pinned incremental toolchain / frozen async jobs | integrator | ABI | tested cold/no-op/one-file invalidation, frozen job survives invalid source edit |
| Dense moving/targeting combat | simulation worker | ABI | baseline/stretch replay/count/order/damage/bounds/symmetry suites pass |
| Safe module / parameter reload proof | reload worker | NASM |19black-box cases pass; live host integration pending |
| Recorded audio /128voice mixer | reload worker + integrator | provenance/client |legacy16groups plus spatial mix/recorded routing and stereo ALSA null pass; physical audio quality unverified |
| OpenGL first-person mass renderer | client worker | simulation |actual GL4.6 context,8192instances,finite screenshots/input checks pass |
| Rifle magazine/reload/cadence/recoil | client worker | input/damage/audio |held-fire/empty/reload/refill tests pass |
| Capture/supply/resources/results | simulation worker | world |12physical sites,cut/restoration,spend,recapture/victory/defeat tests pass |
| Finite formation destinations | simulation worker | world/sites |bounds/role speeds/arrival then capture tests pass |
| Four-client UDP transport proof | reload worker | protocol |45real datagrams plus timeout/malformed/reorder/lostACK pass; standalone legacy proof retained; shared-world gameplay has its own row |
| Tactical markers/destination UI | client worker | site/waypoint ABI |privateXvfb input + markers/resources pass |
| CPU/GPU client profiling | integrator | GL renderer |bounded timer ring hooked; CPU/GPU samples observed headlessly |
| Local packaging | integrator | client/content |archive with hashes built; final revision package below session reports |
| Public GitHub | integrator | explicit authorization |repo created and first validated snapshot pushed |
| GitHub Actions | integrator |workflow credential scope |credential scope restored; baseline remote Actions run37305579434 passed |
| Windows parity | ready/unassigned | platform ABI |pending |
| Shared terrain/LOS/local detours and observed tactics | simulation worker | spatial/world |physical wall rejection, scout→defender defeat→capture, flank bounds, observed/supply retreat and override tests pass |
| Nearest obstruction / swept navigation steps | integrator | terrain/controller | independent segment oracle and original-code negative control pass; full checkpoint recorded in docs/evidence/navigation-session.json |
| Squad corridors / bounded infantry cover | integrator + navigation worker | terrain/controller | integrated physical route/replay, independent scout/support caches, observed-target shelter and FIFO cap pass; streamed hierarchy/crowd avoidance/strategic pacing pending |
| Continuous bombers / fighter combat / aerial rendering / UDPv5 | integrator + aircraft/render/network workers | aircraft sidecar/world | physical bomb passes, finite stores, banked interception and swept guns; real GL authority encounters and1196byte self-contained pose updates pass; final checkpoint in docs/evidence/air-navigation-session.json |
| Authoritative players and shared-world co-op | integrator + workers | terrain/player/UDP |four real slots, movement/fire/order authority, duplicate spending, snapshots and disconnect recovery pass; two actual rendered clients, remote-player pixels, rejected ACK rollback and server freeze checks pass; full extended integrated job2699ac0fcf9c passed |
| Moving shells, player ground armor, bounded impact VFX, spatial rifle mixer | three subsystem workers + integrator | world/render/audio |full frozen extended job1ee7970cae70 passed102.73s; real UDP + two rendered clients drive/fire/exit; recorded spatial routing and actual impact/HUD pixels verified |
| Projectile flight/render cleanup, active default army, licensed animated starter models | three workers + integrator | combat feedback/source provenance | full frozen extended jobaf800b6d2a47 passed128.92s;16source meshes22clips, realGL pose/Walk/track/expired-shell checks, large motion/replay, local+two-client vehicle controls and UDPfaults |
| Sourced temperate terrain and cosmetic weather | client/source/review workers + integrator | texture provenance/rendering | full frozen extended jobd87a7d59c26e passed143.80s;4CC0 texture layers,13negative pack cases,all presets/F4,real moving precipitation across forward/side views,paired impact controls,existing scale/co-op/UDPfaults |
| Recorded battle explosion bank | audio worker + integrator | combat events/audio provenance | two banks share128voices; real event routing, bounded dedup, exact waveform and14asset hashes pass; log-drum/reverb surrogate, physical listening and distinct engines pending |
| Military aircraft art, damage defense, trails, moving co-op ordnance and air-battle | four isolated workers + integrator | aircraft/render/network contracts | focused real damage, immutable cosmetics, actual GL trails and network shell, source/license and full-army scenario replay checks pass; integrated checkpoint recorded in docs/evidence/air-spectacle-session.json |
| Crouch/jump, configurable Linux view and recorded footsteps | four isolated workers + integrator | player/input/renderer/audio contracts | real core, strict view CLI/GL and actual wire/GUI movement/audio routing checks; final frozen verification recorded in docs/evidence/player-experience-session.json |
| Physical dense front/hotspot fixtures and frame diagnostics | four isolated workers + integrator | scenario/client contracts | frozen extendeda87c322acfd7 passed224.83s; fivejobs120matchedinputs; real regionaltargets2560/3837 and actual GL concurrentcombat/audio;1024pixel-visible census remains pending |
| Optional actual actor/detail pixel census | four isolated workers + integrator | renderer identity + GL capture | frozenextended3b5ed1f86a51 passed232.06s; exactGLocclusion/IDfixtures and realGPU rawdecodes; sustaineddensity/readability still pending |
| Observed shell/bomb danger, physical evasion and local warnings | four isolated workers + integrator | private hazard contract/terrain/projectiles | runtime aed6e55; frozen extended c7edbd70ea56 passed241.57s,50suite reports/137matched inputs; physical blast survival, readonly warning GL and budget pass; bounded cells may omit threats; exact integration evidence in docs/evidence/hazard-session.json |
| Ground ordnance admission fairness | three isolated workers + integrator | causal physical pressure + same-tick queues | runtime a9c7b99; balanced actual mixed grants and sustained mirrored pressure, full-world health/queue order label symmetry; exact verification in docs/evidence/ordnance-session.json; air contention remains pending |
| Physical nearby infantry resupply detours | integrator | finite infantry/depot stocks and corridor navigation |43e2439: genuine arrival90-round debit/resumption, real capture-cut, command/stock/ABI gates, fast84 explicit reports, UDP22 and original scale pass; frozen full2f3064f06f08 pending; no convoys or broader rearm |
| Causal supply hazard/wall/UDP regression coverage | integrator | finite detours |a1aa80f: combat28, genuine shell negative control, independent6223-segment wall trip and actual8192/four-peer resupply journey pass; full8ea5d34ac91d pending |
| Finite player rifle reserves/depot rearm and own-stock HUD | next ready | finite depot transaction/player64-byte ABI |unimplemented; player reload currently creates30 rounds. Contract/evidence requirements in docs/player-ammunition-design.md |
| Wider vehicles, layered recorded sound pack, production art/effects | next ready | current combat batch |pending |
| Streaming map,complete operation/recovery | next ready | terrain/nav/logistics |pending |

Current local FPS health/suppression/death/redeployment also passes actual XTest and GL HUD pixel checks.

No milestone completion claim: M0 needs live host reload/jobs diagnostics and Windows; M1 needs quality/action/art/audio performance evidence; M2–M5 acceptance remains largely outstanding. No percentages. Keep one integrator owning contracts and worker patches isolated. Reconcile launched jobs before handoff.

The full requirement ledger and dependency-ready streams are in docs/spec-acceptance.md. Next high-value batches: weapon roster/data with support warnings, dynamic wreck/terrain cover with hazard responses, credible commander/squad plans and intelligence, complete production/recovery operation, streamed navigation, real runtime jobs/reload/snapshot, Windows and dense-front/hotspot4-client performance. Owner licence and human craft/playtest gates do not block independent implementation.

Dense encounter implementation integrated; final extended checkpoint recorded in docs/evidence/dense-encounter-session.json: integrator owns contracts/integration,
`work/dense-scenarios` owns initial real layouts and core replay,
`work/dense-cli` owns Linux mode parsing,
`work/dense-driver` owns development forwarding/report scope,
`work/dense-verification` owns an independent physical engagement oracle.
Modes0/1 retain default/air-battle;2/3 are fresh8192+ front/hotspot initial layouts.
Integrator adds read-only frame diagnostic peaks and real GL smoke.
Full hotspot pixel-visible census, four-rendered-client and sustained dense battle
acceptance remain required independently of the initial layout or model submissions.

Measured next combat task: instrument launch refusals by side/role and distinguish legitimate target/loss differences from bounded-pool allocation starvation. Dense120tick actual pool records are in docs/evidence/dense-projectile-pressure.json. Both sides produce bombs/guns; some dense samples have no side1 tank rounds. No fairness/causal claim is accepted from these samples alone.

Pixel visibility continuation: isolatedshader/capture/oracle/driver workers
provide exactMRTIDs, bounded readback, independent adversarialGLgeometrytests
and strict report validation. Integrator owns Linux final-framehooks and caught
markerIDalias fix. Frozen checkpoint3b5ed1f86a51 passed232.06s; allthreejobs126matchedinputs and
fourworkers reconciled. Hardware finaldepth-visibleactors1859front/1545hotspot,
source models1058/1003; exactrawmaps independentlydecode. Evidence is in
docs/evidence/visibility-session.json. Oneframe
opaque-depth visibility remains separate from sustaineddensity, smoke readability
and human-quality or complete-operation acceptance.

Observed-danger batch: four isolated workers own prediction/budget, physical
steering, independent production outcomes and readonly HUD/GL proof. Integrator
owns world/client hooks, replay inclusion, headless diagnostics and frozen jobs.
This is a limited physical response, not complete coordinated tactics. Next
causal pool investigation must distinguish `projectile_spawn`'s416 AI threshold,
air480 threshold and true512 pool exhaustion, with eligible ammunition/cooldown/
LOS sources counted by side and kind; reverse side/index ordering with the same
physical fixture before choosing fair admission. Keep human cannon headroom and
finite stores; cosmetic trails or event counts cannot substitute for shots.

Ground admission continuation establishes caller-order saturation and fixes
side/role interleaving plus source rotation using physical canonical group order.
Existing per-actor400tick side-label symmetry is retained. Next coupled ordnance
task: apply actual generation-validated ready release admission to aircraft while
preserving continuous FSM updates, finite stores and success-only bomber egress;
instrument cross-class competition and distinguish fighters from bombers.


Aircraft allocation continuation: two isolated workers own bounded kernel/control
probe and independent production release/finite-store oracle. Root owns contracts,
aircraft FSM integration/hash, headless diagnostics, suite registration and frozen
verification. Actual saturated requests now interleave side/role with success-only
store/egress commits and labels-only firing sequence symmetry. This closes the
previous aircraft-order task, not complete air tactics or combined-arms acceptance.
Next physical movement task: bounded friendly separation/avoidance with actual
role footprints, stable generation-safe snapshot queries and no observer-dependent
movement; verify doorway/convoy progress, dense overlaps, opposing battle fronts,
real terrain collision and scaled budgets. Diagnose shared ground/air pool pressure
separately before changing lifetime or reserved capacity.

Physical crowd continuation: isolatedkernel/terrain-probe worker and independent
world-outcome/review worker; root owns world/hash/headless hooks and exact frozen
integration. Generation-safe living ground snapshots use actual role bodies,
bounded local swept steering and deterministic goal-following coincident recovery.
Tests retain true8k/16k motion and400tick health symmetry; old unrestricted speed
fixtures now start physically clear. Exact evidence and rejected prototypes are
recorded in docs/evidence/crowd-session.json and docs/status.md.

Next movement tasks: expanded terrain body footprints and oriented vehicle routes,
safe initial formation/deployment spacing, driven/player collision, complex local
traffic/stuck recovery. Commander/formation plans, streamed navigation, complete
operation/recovery, cross-class ordnance pressure and four-client dense quality
continue independently. This batch is a verified steering slice, not acceptance
of the complete army or game.

Static body-terrain continuation: isolatedNASM/independent-geometry worker and
production-world oracle worker; root owns army/player/driver/nav/init/hash hooks.
Footprint-aware actual sweeps now cover infantry/tanks/artillery and walking/
sprinting/crouching/jumping/tank driving, with normal-speed progress and explicit
safe holds for invalid starts. Point LOS/projectile paths remain distinct. Exact
verification/source/scale evidence: docs/evidence/terrain-body-session.json.

Next physical movement tasks: generation-safe human/driven interactor collision,
safe initial formation/deployment spacing, oriented vehicle turns/hulls and richer
route classes/traffic recovery. Current shared conservative max-role graph is a
bounded safety implementation, not streamed hierarchy or all narrow-pass acceptance.
Commander/formation plans, complete production/logistics/recovery operation, runtime
jobs/reload/snapshots, recorded audiovisual craft, Windows and sustained four-client
massive battle remain required independently.

Controller/body batch: coreworker owns boundedhumans, manualsteps, occupancy and
ABI/malformed/saturation checks; oracleworker owns independentproduction encounters,
placements, fourcontroller intersections/replays and mixedarmybody sweeps; root owns
controller/placement hooks, fixture integration, phase-overhead benchmark and frozen
verification. Runtime `6b23103`; evidence docs/evidence/controller-crowd-session.json.
Gen-safe player/driven planar interactor collision is addressed within that scope.

Next physicalmovement priorities: safe initialarmy formation/deployment spacing,
groundvehicle heading/acceleration and wheeled/tracked road/slope constraints,
oriented hulls/vertical interactions and richer traffic/route recovery. Current
contact sweeps do not replace those requirements. Strategiccommander/formationplans,
completeoperation/logistics/recovery, streamedworld, runtimejobs/reload/snapshots,
recorded audiovisualcraft, Windows/fourrenderedclients and hardwarequality remain
independent open tracks; no fullgame acceptance from this batch.

Ground-vehicle batch is integrated for verification: root owns motion/collision/
UDP contracts and world/controller hooks; isolated motion, collision, public-path
oracle and presentation workers supplied committed focused evidence. Shared hull
heading, acceleration, braking, bounded pivoting and human slow reverse are real
world state; collision accepts complete reachable segments, and UDPv7/rendering
consume the same generation-stamped pose. Root checkpoint `7d37522` passed full frozen extended job `8e107f76cc77`
in 480.14 seconds; exact source/evidence is in
`docs/evidence/ground-motion-session.json`. This verifies the stated slice,
not complete vehicle realism.
The original 30-tick18m steady-drive gate remains after a measured acceleration
phase. Original8k/16k95%army progress and1200tick wall recovery remain unchanged.
Driver corner recovery fixtures explicitly steer tangent and allow90ticks for
physical pivot/acceleration; human50tick fixtures remain unchanged.

Road/off-road handling and matching materials are now integrated at `53d2211`,
with compatibility correction `945ef20` and build-output correction `a429a7d`. Root owns shared contracts, actuator
hooks, build dependencies, generated data and content compatibility. Motion,
whole-body sampling, public outcomes and materials supplied isolated committed
worker evidence. Original 360-tick crowd arrival and 1,200-tick wall recovery
passed after bounded steering preview and exact discrete braking. Frozen full
verification `2804557c94cf` passed in 497.18s with 76 reports/158 matched inputs;
`status.md` records the scoped acceptance and failures.

Raised-terrain batch: root cc90b6d integrates canonical 64 m relief, nine closed
whole-body grade facets, 45/35/25 degree foot/tank/artillery caps, bounded 27-node
routes and a matching 5 m GPU tile. Four isolated workers provided grade, height,
rendering and public-path evidence. All 16 public outcomes pass against frozen
hill candidate; latest map-edge correction passes focused terrain-grade checks.
Full extended job 3d022b3c7d8e passed 533.82s/81reports with 177 matched
authored inputs. Seed42/900tick 8k/16k CPU benchmark p95 is 6.570/13.967ms.
Root owns final compatibility and evidence; none is complete-game acceptance.

Road-preferring navigation, practical wheeled roles, oriented hulls/vertical
interactions, suspension, safe initial formation spacing, traffic recovery,
damage handling and useful wreck cover remain required. Complete operation,
intelligence, streaming, Windows, runtime jobs, recorded audiovisual craft and
four-client hardware quality remain independently required. The full-game goal
stays active; no partial physical batch establishes complete vehicle realism.

Terrain support continuation: root 646ea71 integrates the verified NASM five-height
chassis frame and actual sourced-mesh pitch/bank/absolute height. Isolated kernel
68d5a1c is clean and verified. Root focused 361553e92439 passes with GPU source
vertex/normal and actual client instance/pixel proofs. Full job 86ca2085d678
passed 540.59s/84reports with all 183 authored inputs matched. Independent next
spring-response kernel work stays isolated; it cannot
be integrated before intermediate-frame contact correction is specified/verified.

Suspension continuation: root71c61c7 integrates the verified spring plus intermediate
five-point contact and per-generation render cache. Final focused snapshot
4c865d935b13 passes192actualGL cases/414144vertices, analytical dynamic client
responses and unchanged sampled authority. Full frozen dfc1f67207e7 passed545.82s/87reports with195matched inputs.
Independent eye-attachment audit afe4ee6 is integrated as documentation only.
Next read-only unsmoothed driver-eye query contract38ae5f4 is isolated in
feature/ground-eye; worker d6b1663 is clean and verified6488queries/58invalid
cases/three assembled negatives. No entry/driver/LOS/aim hook or eye feature
accepted yet; exact source hashes/evidence in evidence/ground-eye-prepared.json.

Driver-eye continuation: root12f83f9 integrates the verified stateless eye query
through boarding/LOS, held driving and cannon targets. Root owns the shared
contract, motion/generation validation, client preview and content fingerprint.
Independent public gameplay and actual local/UDP client oracles are integrated
from b8473db and1e51fbc. Frozen vehicles c086272ddad8 passes78.32s; actual
component/GL/client integration7c777004ac3e passes36.08s. Full extended
6950d874d02f passed574.9486s/90reports with201matched inputs at89b957e,
including legacy birth/bounds corrections9721bc2/89b957e; no complete-game acceptance is inferred. Original
physical radii/speed/grade/health/arrival gates remain. Verified source socket
metadata and turret groups are needed before the muzzle/articulation slice;
wreck cover, wider roster and all operation/platform/hardware work remain ready.

Independent next vehicle damage/wreck-cover audit is in wreck-cover-next.md.
Both real casualty paths, physical queries, persistent presentation/replication
and original density/recovery deadlines must be covered by that next slice.

Wreck lifecycle foundation: root143247e integrates shared genuine tank/artillery
casualty registration, immutable supported pose, generation dedup, deterministic
bounded retirement,60s expiry and hash/content identity. Isolated focused/fast
checks pass; root full089664de8436 passed584.1588s/93reports with207matched
inputs. All five frozen jobs and two extra sessions are reconciled. It does not yet supply cover,
rendering or wreck replication. Root-owned prepared segment/AABB first-contact
math atd238ea8 remains isolated; bounded spatial lookup and captured-pose cover
bounds are needed before actual physical query integration. Preserve the original
scale/health/symmetry/arrival gates and make local/remote presentation match cover.

Next cover presentation audit: exact existing pack frame0 high/low roof heights
differ by0.9204m tank and1.2990m artillery; collider/LOD geometry must agree.
See evidence/wreck-cover-mesh-bounds.json. Do not shrink physical cover to hide
missing visible geometry or imply solid near-field meshes are penetrable. The
spatial/query/shape and matched wreck presentation slices remain ready.

Captured-pose point query foundation is integrated at570b6ee (primitive686d20f).
32×32 bounded center buckets, transformed frame0 union AABBs, deterministic first
contact and mutation-driven derived cache pass focused/fast and real8k/16k
casualty queries. Full frozen4febd559b935 passed576.9970s/95reports with216matched inputs. Physical/rendered/replicated
cover remains open; see wreck-spatial-query.md and wreck-cover-integration-next.md.
Prepared immutable rendering inputs2fcfe4e and finer-grid07cf5b5 are isolated,
verified prerequisites, not main/full-checkpoint features. The next complete
cover batch must activate matching geometry and UDP state with body/weapon/LOS/
navigation hooks, preserve original gates and measure mixed query lengths.

Current wreck continuation integrates immutable frame0 local/co-op presentation
and UDPv8 global fair records with separate client cache/census. Full extended
checkpoint e9a99f39beb8 passed659.9070s with all227authored inputs matched.
No body/LOS/rifle/shell/navigation cover hooks are enabled. Prepared body query
at497e089 has2514calls and independent conservative contact/no-deepening escape
evidence, but remains isolated. Next: explicit local/remote query context, dynamic
detours/invalidation, weapon contact and useful far/map presentation, preserving
all original motion/health/symmetry/arrival/recovery gates.

Nearest sampled-actor first entry is integrated atfdb0f7b and accepted by full
cb0726815280 (644.1174s,103reports,234matched authored inputs). Existing4m opposing
actor envelope and216sample bound remain explicit limitations. UDPv9 fingerprints
contact policy. Isolated8c6791e exact five-solid contact is prepared; next merge
ground/solid/wreck/actor contact with typed ownership, blast LOS and body/nav
queries, preserving original scale/symmetry/arrival/recovery and matched co-op.


Current root continuation (2026-10-06): integrator/root owns wreck contracts.
Body movement/local detours/replicated-cache foot preview are integrated at
f8d80b8; full43b83242e4da passes123 reports/278 source-matched inputs. Dense
relevance prototype7e75121 is isolated; full3b2d4140c644 runs frozen from
0b224d6-32d403ce0bb136fb. Root investigates hotspot pass costs independently.
Acceptance requires original scale/arrival/recovery/health/label gates, real GL
and UDP faults; focused24-route evidence does not replace that checkpoint.


Latest integrator update: prior3b2d4140c644 and0b1256549755 are FAILED, not
pending or accepted. Corrected dense/profile/quit/exterior-deploy candidate
 db54418 has full97b74ea394b4 running. Independent ground company-assault0479f0f
passes focused tactics, public physical controls and frozen fast24fff30243be;
full430466389e9b runs. Integrator owns shared policy/compatibility merging.
No new candidate is integrated until exact full/network/GL evidence passes;
combine private16/17 contracts coherently and validate again. Next AI work:
support targeting/reservations, protected bomber/intercept missions, ownership
and rendered intent; actual ranged acquisition must cover declared weapon range.

2026-10-06 continuation (root owns isolated worktrees): ground acquisition
205136b has actual long-range travel/hit, LOS/range negatives, mirrored labels,
replay, original tactics and fast evidence. Unintegrated: hotspot cost worsens;
near-first generated NASM preserves sampled complete authority but remains over
budget. Next: reduce measured query cost and verify full original scale gates.
Company full430466389e9b failed590.7751s at co-op input scheduling; exact log and
frozen causal rate-limit7 reproduction retained. Corrected observer passes
against frozen runtime; b7154c6 fullc2b6c894af84 verified live. Profile
full97b74ea394b4 remains verified live. Reconcile same handles and integrate only
matching verified coherent batches; main still f8d80b8/v14.

2026-10-06 integration: profile97b74ea394b4 PASSED1036.1950s/125reports;
all282 authored inputs match main. Root integrates coherent db54418 routing,
query envelope, exterior deployment and Escape callback changes at UDPv17.
Prior two failed checkpoints remain retained. Companyc2b6c894af84 remains
live/unintegrated; range candidate205136b remains isolated with hotspot cost
gap. Next measure exact nearest-visible heap prototype and preserve original
scale gates before any range/assault integration.

2026-10-06 coherent candidate: company rerunc2b6c894af84 FAILED919.5569s at
inherited dense deployment. Frozen unchanged repeat proves48 hotspot colours,
actual healthy redeployed1000/1300 and site wall in view. Combinedccff52f based
on accepted07d6536 includes company1 + full-range/heap acquisition2 + corrected
co-op observer and accepted deployment/query/input fixes. Its fast suite passes;
fullb0240f5853b8 is verified live atccff52f-1a1492e3fb5e47c0. Private UDPv19
union is not main. Nearest priority fault is detected;900tick exact-state paired
comparison retains outcomes but hotspot/stretch still fail tick budget. Ready:
measure finer wreck-query grid/mixed ray lengths or scheduled target decisions
without weakening actual range/LOS/health/motion/arrival/recovery gates. Protected
air missions and visible shared company intent remain gameplay acceptance work.

2026-10-06 row-search continuation: the accepted grid is already128×128/62.5m.
Isolated330cc74 conservatively narrows each row, retaining all exact geometry,
source/lifecycle and body checks. Long-path oracles pass; paired900tick worlds
remain identical at90 samples. Hotspot p9538.461→32.859ms, open scenes regress
slightly; see docs/wreck-row-query.md. Fast e6091687a43d and combined full
b0240f5853b8 are pending. Root runtime remains accepted07d6536/v17. Preserve
full gates before integration; protected air missions/shared company UI remain
ready gameplay work.

Combined b0240f5853b8 is terminal FAILED759.5345s at authentic wreck replay
after drops (test_wreck_network.py:93). Reproduce with frozen artifacts and
distinguish a dropped packet first delivery from duplicate/stale resurrection
before correcting any code or test. The prior v19 candidate remains unintegrated.

2026-10-06 causal replay correction and coherent checkpoint: initial-row fast
e6091687a43d PASSED208.1878s; short-query fallback3aad7b7 focused/900tick parity
passes. Wrong duplicate assertion reproduced with17 dropped genuine new wrecks;
corrected actual main/v19 extended streams pass. v19 paired900tick row search
keeps90 world/entity samples equal and improves hotspot p9557.994→47.462ms,
still above33.3ms. New full4f9cf0815524 is live atdc2c4fb-3795e595064024f2;
root v17 runtime remains accepted. Next: reconcile this handle, integrate matching
passed coherent source, then protected air missions/shared company intent and
remaining decision costs. Historical failed full logs remain retained.

2026-10-06 accepted coherent integration: full4f9cf0815524 PASSED1172.0055s,
124 structured suite reports, all311 frozen inputs match main plus one independently
verified development diagnostic. UDPv19 now integrates company1/acquisition2 and
optimized wreck rows fromdc2c4fb. Root builds follow. Dense tick budgets, proper
company ownership/UI/timed support, protected bomber missions and remaining full
specification gates remain open. Air-escort policy1/air acquisition2 is implemented
separately on feature/air-escort, focused flight/admission and1800tick controlled
mission checks pass; not integrated and not covered by this ground checkpoint.

2026-10-06 aircraft continuation: isolated1c8ceb1/8534fd5 escorts generation-valid
own bombers, follows moving trailing/flank goals, prioritizes real-range/LOS-gated
threats and fixes fighter750m cell coverage.1800public ticks and two assembled
controls pass; real gun/bomb release and delayed ground kill are verified, without
claiming a bomber survival benefit. Frozen fast f604660e9502 PASSED266.7072s;
actual GL encounters pass after correcting the executable asset path. Three900tick
scale runs retain original army sizes/finite stores but differ in decisions/hash;
hotspot47.952ms/stretch44.704ms still miss33.3ms. New fullcccb5e085005 is live
at8534fd5-e6a5f9beaf846fcc. Root v19 remains accepted. Independent next work:
physically coupled bank/turn/roll and safe air routing, shared company/air intent,
timed support and remaining scale/spectacle requirements.

2026-10-06 current accepted main: fullac6766acbf40 PASSED1156.8059s with125
structured reports and all315 authored inputs matching integration. UDPv20 now
includes generation-bound own-bomber missions, trailing/flank goals and physically
perceived threat priority. Rebuilt root actual escort controls and8192/180tick peers
pass. Initial cccb5 failed independent stale v19 test literals; failure is retained.
The earlier live/unintegrated paragraphs are historical. Current independent
v21 bank/roll/pitch/lead, staged strike recovery and boundary latch candidate is
committed00c3d9e; focused/admission/actualGL pass, frozen fast195a64c32e56 running.
Full verification, scale budget, safe arbitrary birth/ingress, shared company support
intent/UI, separation/rearming and human spectacle quality remain open.

Current isolated bank correction1f3ed26 passes matching GL/UDP and original
8k open/hotspot/16k open bounds through900ticks (1,839,823 living-aircraft steps).
Earlier00c3d9e fast passed but natural scale caught6 map-edge crossing fighters;
that result does not authorize integration. Corrected fast558332fecbfd and frozen
full831bb1419f53 are live. Main remains fully verified v20.

Current continuation: physical bank/roll/yaw, own observed bomber retry and projectile-time
fighter interception are integrated from1f3ed26 after frozen full831bb1419f53 passed.
Exclusive company control and actual solo/co-op GUI command routing are integrated
on main01dbd5c after matching focused API/physical UDP/GUI checks and runtime fast
ed14fd74253d passed. Main now uses UDPv23/schema0xc5c97e5b/content0xa89260de.
Matching extended0b0739a72b85 remains pending after correcting the exact nested-player
build dependency assertion. No transfer/shared membership UI or completed game claim.
The modest concave terrain-clear optimization remains isolated:40060 identical query
results and900tick sampled whole-state parity do not show a useful hotspot speedup.

Current accepted main4e8fec8: fully matching c0c8f04 aircraft/company/GUI/LOS
batch, full3112ca82aa0d PASSED1201.1398s,330 authored inputs,133 suite reports.
Boolean cover optimization retains all sampled authority and roughly halves
measured8k hotspot CPU tick time;16k/GPU/human quality remain incomplete.
Solo formation tint dfb8a95 is an isolated27-report actual graphics prototype.
Earlier company dependency/mesh-fixture failures above are superseded by this
passing full checkpoint; raw evidence remains preserved.

2026-10-06 main company visibility batch52e2a2a: UDPv24 carries complete
four-player company leases and accepted intent. Atomic/stale/generation checks,
own-company region exception, solo/co-op green formations, actual shared goal
pixels and timeout clearing are focused verified. The four-peer original8192
world test remains read-only; the separate remote stream test declares one
initial far infantry birth and never renews live state. Main matches all333
frozen authored inputs. Full72366ca35c1e FAILED at the final private-Xvfb display-open fixture; prior
full3112ca82aa0d is still the last complete checkpoint. The135 preceding suite reports passed, including rendered co-op. Bounded
display-open retry retains the actual timeout gates and the focused rerun passes.
Preserve the failed result; the isolated consent-transfer batch continues. Transfers/assistance, recruitment,
formation selection, remappable contextual commands, shared countdown/support,
full operation/content and target performance/human quality remain open.

Main consent-transfer batch7362317: guarded request/accept/decline/cancel,
current generations/leases and proposal IDs, cross-front ownership exchange,
preserved bodies/company intent, queued reliable controls and visible feedback.
Matching main API, original8192 read-only four-peer/production-adapter UDP and
actual two-client75ms/loss/reorder transfer checks pass. All338 authored inputs
match frozen43d31a2cf5a3, currently RUNNING. Preserve original scale, realGL and
UDP gates; collect that exact job. Last full pass remains3112ca82aa0d. Broader
contextual/remappable/fullscreen UI, assistance, splitting, recruitment, shared
countdown/support and remaining complete-operation/quality budgets remain ready work.

2026-10-06 continuation: effective retreat display7402233 is integrated on main.
Original fast60 reports and actual solo/two-client owner/observer framebuffer
checks pass; advance retains the original accepted waypoint. Independent NASM
command HUD is in feature/command-hud with actual solo/status and exchange-text
pixel checks passing; broader graphics/tooling jobs are still pending. Full
transfer checkpoint43d31a2cf5a3 remains independently tracked; no complete-game
acceptance claim follows from these command-interface slices.

Integrated command interfacee84cff2 combines effective retreat homes with NASM
framebuffer company/order/consent/timeout text. HUD worker graphics31 and tooling2
reports pass; initial ACK-observation race and corrected relay fixture are
retained in command-hud evidence. Previous full transfer checkpoint43d31a2cf5a3
PASSED1208.495s/139 reports and is collected. Matching main checks and the
new frozen combined checkpoint43d0d7f2c2bc are tracked in docs/status.md.
Contextual wheel, remapping, narrow-view wrapping, assistance/recruitment/timed
plans and wider game requirements remain open.


Current command integration: root owns authority/input/render interfaces.
Company follow is locally integrated (5f0687c) with physical API, fast, UDP and
actual rendered evidence in docs/evidence/company-follow-focused.json and
company-follow-main.json. Full checkpointc881a96c1725 failed at private Xvfb startup and is collected;
it does not include the separate command-wheel worktree.

Next command batch, feature/command-wheel: compact middle-button radial UI and
first-person terrain targeting use the existing four modes/cost/lease. Physical
ray/ABI, actual solo labels/cancel/key edges, minimum viewport and two actual
rendered UDP clients with delay/loss/reorder have scoped passes; routine fast63 reports pass and the batch is locally integrated. Matching main six checks pass atbc883ad-7643b2012d750bc6; frozen full
d6a9a612944d later failed the original economy observer and is collected. Full contextual order
roster, remapping, assistance, recruitment and shared timing remain dependency-
ready follow-up work rather than implied completed commands.


Saved control profiles integrated at3bc7e5d: root owns all30 action IDs, atomic
NASM file loading, key/mouse routing and dynamic hints. fast64 and seven focused
checks pass; different-profile co-op consent also passes under real delay/loss/
reorder. Main builds/six checks pass at3bc7e5d-f52a43dfd074c4e1; frozen full
7cc8322a2c38 is running with357 source inputs.
In-game editing, wider commands/assistance/recruitment/plans and full game
acceptance remain open. Evidence: docs/evidence/input-bindings-focused.json.


Area defense batch (integrator, feature/company-defend): authority, fixed
role-aware formation, terrain projection, remappable input and fifth wheel
sector implemented. Physical/terrain/hazard, solo/minimum-view, four-endpoint
UDP and two-rendered-client delay/loss/reorder checks pass. Final frozen-input
fast65 and network18 regressions pass; merged0b475d9c has32 matching reports
and360 matched authored inputs. Frozen full100a30b45dda is running, not passed. Adaptive defensive cover, remaining
commands and shared player assault plans remain ready subsequent work.


Finite infantry ammunition (integrator, feature/infantry-ammunition): infinite
army rifle damage is replaced by30-round magazines,90 carried rounds and60-tick
reloads. Causal exhaustion/LOS/lifecycle/ABI and original8k/16k replay/400tick
health symmetry pass; four real UDP endpoints conserve737280 initial army rounds
without authority writes. Final fast/network regressions precede integration.
Next logistics work: finite connected-depot inventory and genuine resupply;
observed own shortages/return routes, replicated presentation and NPC reload
animation. Do not use renewed bodies, HP, clocks or replenished test stores to
keep exhausted armies shooting. Existing full defense100a30b45dda stays isolated.

Finite depot follow-up contract (root, ready after ammunition integration):
The current12-site graph exposes owner+8, role+16, connected+20, health+24
and contest flags+28. Its sim_supply totals are recomputed capacity, not
consumable rounds, so they cannot be used as a refill inventory. Add a separate
bounded finite depot store, checked against actual allied healthy connected
uncontested depot/production capability and physical proximity. Preserve stock
conservation with cumulative received rounds when extending infantry records;
actual transfer must debit the depot before crediting an actor. Route cuts,
capture and destruction must block transfers without creating new ammunition.
Verify competing requests, exhaustion, cut/restoration, capture, generation
reuse and replay on independent fixtures, then original8192 read-only UDP.
Do not route units to hidden enemies or reset generations to regain equipment.
Supply-aware movement and readable shortages are subsequent dependent work.

Finite nearby infantry resupply (root, feature/depot-ammunition): implemented
atomic finite-source debit/actor credit, received-round conservation and world
hooks/hash. Physical combat, actual root restoration/contested occupation/
captured exhausted store, API bounds/LOS,135-request contention and5-entry ABI
pass. Original8192/16384 and staged four-endpoint resupply pass; final registered
network20/graphics checks pending reconciliation. Stock/UI route intelligence,
other weapon rearm and full logistics acceptance remain open. Next independent
slice: generation/lease-gated owned-company shortage and depot inventory report
for solo/co-op tactical HUD, bounded packet validation and truthful no-data/reset
states; then supply-aware physical return routes without overriding urgent hazards.

Finite player ammunition (root, integrated ee97d37):30+90 per actual body,
conserved60-tick reload, bounded real finite depot credit, own server message110
and client-only validated cache. Actual CPU depletion/store exhaustion, guarded
ABI/report, original8192/four-endpoint exact-stock and fault UDP, solo/co-op
full/minimum GL depletion and real two-client timeout pass. Frozen full
06b65992aceb is pending. See player-ammunition-session.json for exact epochs and
fixture/quality limits. Next weapon authority task: NPC damage against humans
must consume actual finite rifle stock and respect role weapons; existing
enemy_attack's16-tick synthetic threat damage bypass remains unaccepted.

Infantry human-threat stock correction (root, integrated0b4d7d6): actual
range/LOS damage now debits existing finite generation-valid rifle stock.
Sparse armed/exhausted/reload/corrupt/wall/replay, original focused player,
real gameplay/minimum co-op GL and corrected complete network25 pass. Frozen
fast78 passed at the earlier documented epoch; final full3ed19c6f8298 pending.
Derived completed-tick marker fixes the physical route observer without changing
gameplay/hash or its speed bound. Subsequent task: physical tank/artillery/bomb
blasts against humans; eliminate noninfantry synthetic rifle damage, preserve
co-op friendly protection, real LOS/death/crew recovery and finite source shots.

Joint infantry army/human target arbitration: integrated dc73e28/d92fe44. Actor8tick selection, nearest physical visible target, rotating human ties, finite shots, boarded protection and240m safe deployment verified. Frozen fast and complete UDP plus extended fault/death recovery, original8192/16384 replay,400tick ground label symmetry and real8192 GL gates pass. Evidence: docs/evidence/infantry-targets-session.json. Frozen full8a7e9b89d92e failed obsolete graphical tank-as-rifle death fixture; exact failed executable passes corrected finite-rifleman fixture; incremental tooling verification passed. Human aim/tracer metadata and broader tactical knowledge remain separate ready work.

Next coherent presentation task: publish cosmetic NPC rifle muzzle/report events only after actual successful finite shot gates for both army and human targets; route the recorded rifle bank and bounded flash effects through local/UDP event paths. Preserve source/target generation and finite-store semantics, do not infer firing from nearby actors or target IDs. Current event ring has source position/kind/side/tick/radius/sequence but no source/target ID; human aim direction needs an explicit compatible contract rather than encoding a human as an army ID. Required evidence: actual debit→one cosmetic event, empty/reloading/corrupt/blocked→none, replay-independent authority, production UDP compatibility and real GL/audio routing. This original planned task is superseded by verified integrated rifle presentation b394c8d/4c2026f.

Finite actual NPC rifle audiovisual presentation: integrator in isolated feature/infantry-presentation. One actual successful finite shot→one kind10 source event; recorded rifle routing and brief muzzle flash/no explosive layers verified, real original8192 paired4pixel GL and four-endpoint production-adapter event/debit proof passed. Exact physical trace/authority hash unchanged in matched sparse control and two original8192/400tick scale-front runs. CPU/core f3ac32c23e10 and complete network086e1dcc50b7 passed after correcting old unknown-kind10 fixtures to11, preserving malformed/bounded/fault checks. Frozen full20ea89c062f4 failed a missed60ms reload tap; exact failed executable passes physical-key acknowledgment correction. Event packet version38; public records unchanged. Detailed muzzle/weapon aiming/trajectory metadata remains separate.

Next aiming contract: current public `ENTITY_TARGET` contains only an army target and can remain a farther army ID when a nearer human wins actual shot arbitration. Rendering it as the current human-shot direction would be false. Add generation-safe current observed aim XYZ/source body identity and a bounded compatible remote representation before turning upper-body/rifle models toward human targets. Populate only from actual physically visible decisions; never infer hidden player coordinates in rendering-side tactical decisions. Preserve existing locomotion/body footprint and authority stock/cadence semantics. Require held/moving/blocked/reloading/dead-generation and UDP-ordering proofs plus real pixels for independently moving legs and aimed upper body. This contract is now implemented and verified in integrated main3116007; see the current batch entry below.

Infantry independent visible aiming: integrated main3116007 by integrator from feature/infantry-aim966aa4b; implementation and focused native/UDP/GL/asset/scale symmetry verified; frozen finalfast passed303.323971s and network passed218.486542s; full extendedb26bbca67339 pending. Actual moving army/human decisions drive upper shooting pose while lower locomotion remains independent; safe bounded pose-only v39 network has no target coordinate/body renewal. Reference-mask upper deformation is approximate. Next work after integration: bounded anatomical torso/body turn and authored bone weights/IK review; align rifle muzzle effects/tracers to actual weapon transform; full perception/FOV/knowledge/coordination and aircraft spectacle/operation/art/performance/Windows requirements remain active, not satisfied by this batch.

Infantry aiming full checkpointb26bbca67339 now passed/collected1687.820317s, exact mainc937b75 input bytes. Projected actor detail and heading-seam corrections remain isolated under graphics verification; full base-game acceptance is still incomplete.
Projected battlefield model detail: integrator, feature/battlefield-detail, source-size/projection-based actor LOD and matching marker thresholds implemented; focused GL and short/long A770 samples recorded. Corrected complete graphics rerun pending before integration.1177 detailed actors in short actual frame,645 in longer frame; sustained density/performance still incomplete. Large aircraft retained as true sourced/banked/pitched models beyond800m. No physical combat changes.
Infantry torso heading seam: isolated feature/infantry-turn-seam short-path yaw before weight application;60 real shader cases and old-shader negative control pass, actual8192 client check passes2059paired pixels before integration. Body-turn/anatomy/IK remains separate future work.

Current renderer batches integrated on main894a53c: projected actor detail57bb6e6, torso heading seamf4aecce and proof/co-op observer correction894a53c. Actual rebuilt-main GL shader/1200m aircraft/boundary/map/8192 finite NPC aiming pass. Six diagnosed graphics failures have focused corrections; corrected whole graphics1664f219f098 and full7dc8436c715c remain live/pending with exact source scope in main-job evidence. Earlier aiming fullb26bbca67339 passed/collected. Next ready scope: anatomical turning/bone/socket/muzzle fidelity, broader coordinated perception/AI/air spectacle and sustained operation/performance/Windows; full base-game goal remains active.

Aircraft physical cannon batch: fixed forwardXYZ rounds and shared full3D lead
plus bounded pitch guidance implemented; focused actual native/GL and frozen
fast pass. Original8k/16k finite continuous flight checks pass. Broader perception
cache/FOV, cannon aim effectiveness, squad/wingman coordination, air collision,
aerodynamics/fuel/landing/rearm, visual spectacle and full game acceptance remain
open. Evidence and checkpoint state: docs/status.md and air-gun-nose-*.json.

Fighter physical firing window: integrated bounded relative-motion closest
approach decision, finite-store efficiency/control and actual GL action proofs.
4same observed kills from886vs3687rounds; total damage slightly lower. Native
ABI/oracle, original8k/16k flight and ground-label health checks pass; full
checkpoint state remains in status. Future manoeuvre prediction, coordinated
air tactics, richer vertical flight and spectacle remain open.

Aircraft vertical flight: integrated44a85ba after complete focused aircraft, native
2036-case/17-invalid ABI, original8k/16k900tick physical bounds and actual main GL
proofs. Total XYZ cruise is conserved, VY slews at role-specific acceleration,
pitch matches actual motion, bomber ingress/release and escort lateral spacing
normalize horizontal motion separately. Ground admission contacts have declared
separate birth lanes; genuine airborne bomb interception is retained as its own
replayed proof. Frozen fast and full checkpoint remain tracked in status.md. Next
flight/AI work: energy-aware/steeper manoeuvres, observed incoming-fire evasion,
air separation and coordinated escort/strike decisions; full game remains open.

Visible incoming cannon warning integrateda37e3f8; isolated fast passed and ordinary complete network after independent content oracle correction passed. Bounded actual traces/LOS and committed defence are proven; general flight tactics/realism remain open. Aircraft break-up GPU presentation verified in isolated air-burst with authority-free actual cannon-death pixels/motion, delayed events, fixed pool and embedded shader oracle. Full spec spectacle, physical crash wrecks, dynamics, authored materials/lights/HDR, performance and operation/platform acceptance remain open; exact checkpoint state in status.md.

Aircraft break-up presentation integrateddd0670e with independently verified native/GPU/actual-main combat motion and authority controls; corrected independent content oracle561b137 passes whole ordinary network suite. Full extended5e414454524c pending; earlier obsolete-oracle full runs remain failed. Next ready product scope: fair aircraft perception/memory and coordinated air tactics, physical crashed airframes, bomb/material effects/light/shadows/HDR, sustained large-battle performance, operation/art/audio/platform acceptance. None is satisfied by the particle batch.

Current integrated aircraft scope: bounded visual memory/confidence pursuit, critical/empty withdrawal, physical falling/landed/expiring wrecks with UDP40 and attached source-aged smoke/fire, plus friendly convergence avoidance (7ef5d91). Final aircraft and network suites, original8192/16384 bounds and actual GL pass with precise scopes in status/evidence. Corrected local wreck background observer8042b3d passes against failed frozen binaries and integrated main. Fullac2986f1e3d0 pending; older88b8c32016cf retains original observer. Remaining: general air collision/traffic and obstacle response, energy/fuel/stalls/landing/rearm, coordinated wing tactics, authored spectacle/lighting/audio, hardware client performance and entire operation/platform acceptance. CPU hotspot p95 is23.113393ms, below33.3ms server target; no client16.7ms frame acceptance established.

Recovery holding integrated379ec9e: damaged/empty planes arrive then sustain bounded banked orbit, private lifecycle/checksum and versioned policy; native, real public arrival/holding replay on all three fronts, original8192/16384bounds, aircraft/network suites and actual bombing/destruction GL pass. Entry can invoke boundary steering; no landing/refill/traffic or aerodynamic-energy guarantees. Full944f025bb774 pending, olderac2986f1e3d0/88b8c32016cf exclude holding. Next real product gaps remain coordinated wing/strike timing and communication, swept physical air/obstacle collision, energy/fuel/stalls, safe base/landing/repair/rearm, authored lighting/materials/audio/spectacle, hardware frame and operation/platform acceptance. Exact evidence/limits in status.md.

Recorded moving aircraft engines integrated2b8ba98: genuine CC0 field recording/licence/credits, nearest8living admitted/local sources, continuous no-restart moving pan/gain and finite lifecycle, shared128voices/weapon priority. Whole focused audio, actual local8192and realUDP8192client emitted PCM/silence-toggle and ordinary network pass with exact scopes. Final full62f4725ea974 pending; prior holding944f025bb774 excludes engines. Corrected separation fullac2986f1e3d0 PASS, original observer88b8c32016cf FAIL preserved. Remaining audio: distinct engine models/throttle/Doppler/delay/occlusion/reverb/fades and full weapon/material/vehicle/environment/radio pack, quality/device performance/playtest; graphics lighting/materials/HDR/spectacle, tactics/physics and whole operation/platform acceptance still open.

2026-10-07, integrator/root: native listen-hoste19770a implemented, real host/guest and lifecycle checks pass; exact focused evidence listen-host-focused.json. Main rebuild verification underway; frozen full2e17f744fa0c excludes this batch. New full checkpoint required. Ready dependency: dedicated authored front/hotspot starts and threat-safe scenario-aware join/deployment, then matched native four-client/front and sustained1024-visible stress; do not maintain density by health/camera/clock renewal. Default synchronous solo still misses open16.7ms budget; explicit listen path separates authority, measured default view only. Required remaining jobs/render streaming/shadows/bloom/world lighting, AI/flight coordination, full weapon/vehicle roster, audio craft, operation/pacing/recovery and Windows/playtest/license/publication acceptance remain open.

Authored co-op starts and scenery census correction: focused native/shared-replay/four-peer/private-GL/lifecycle checks verified; final ordinary network and immutable all-extended checkpoints pending. Native listen dense birth modes still yield516/471 visible actors from default safe deployments; next acceptance work must establish genuine near-battle deployment/transport and sustained1024-visible stress without camera/HP/clock renewal. Full operation, four graphical players, Windows and spectacle acceptance remain open. User authorizes committing and pushing verified batches; GitHub no-reply privacy migration preserves local original unpublished history and published ancestors.

Authored squad deployment implemented in isolated feature/squad-deployment; actual8192 public joins/safety/reset/hash and focused player checks pass. Native actual front/hotspot owned authority puts players near fighting; natural front death/redeploy observed, final433/603 visible still below1024 acceptance. Ordinary network, routine fast and frozen full checkpoints running; active-blast spawn exclusion, revive/selection and sustained multiplayer/full operation acceptance remain open.

Bounded deployment blast exclusion implemented/verified in isolated feature/deployment-blast: real finite shell causal guard-vs-omitted-hook survival, read-only/ABI/ballistic/recent-impact/static-contact controls and unchanged four-peer near-battle gate pass. Initial unbounded corridor network failure retained and corrected by production contact forecasting. Full operation spawn-camping/revive/site-choice, dynamic cover and512-active forecast cost remain open. Old co-op full1da failed procfs observer ESRCH race; helper corrected without relaxing no-live-orphan gate, exact kernel lifecycle rerun passes. Current final network/full checkpoints pending, not passes.

2026-10-07, integrator/root: restrained half-resolution bloom implemented in isolated feature/bloom; real software/native pixel controls and native1080p listen starts pass. Whole graphics/frozen full checkpoint status recorded in status.md. Shadows, dynamic lights, complete flight/tactics and full game acceptance remain open.

2026-10-07, integrator/root: living aircraft terrain/solid anticipation and swept hull casualty path implemented in feature/air-world. Native causal ridge/wall controls and actual local/UDP crash pixels pass; exact frozen suite/checkpoint results in status.md. Full aerodynamics, air traffic/contact, dead-body obstacle response, landing/rearm, wing coordination, operation and art/platform acceptance remain open.

Event surface lighting implemented and focused native/production-GL/whole-client controls pass: nearest8 finite event lights on terrain/models/weapon, HDR/bloom integration, expiry, source/hash/ABI and tactical controls. Final frozen whole graphics985636007b0c and all-extended22e8255e8a7c cover exact authored inputs; status.md records their actual checkpoint states. Unshadowed lights do not establish directional/dynamic shadows, solid-cover occlusion, persistent-fire lighting, accessibility settings or artistic/performance acceptance. Remaining flight energy/fuel/stalls/landing/rearm, coordinated tactics, operation/roster/transport/streaming/platform and whole-spec gaps stay open.

2026-10-07, integrator/root: bounded current-frame directional sunlight shadows implemented in isolated feature/sun-shadows. Production CPU/filter/ABI and software/native shader checks pass, including moving/behind/coplanar controls; actual8192 whole-client source/hash, once-per-frame animation and paired tactical controls pass. Full graphics checkpoint revealed original timed firing/HUD deadline failure; diagnose without weakening its gates. Exact frozen and performance scopes in status.md. Remaining cascades/admission/art/accessibility/Windows/dense operation acceptance and full game gaps stay open.

Finite AI aircraft sortie fuel implemented in feature/air-fuel: both-role native reserve withdrawal and eventual powerless-glide terrain casualties, generation/tick/capacity/ABI/hash controls, actual8192 authority-to-adapter glide records and recorded-engine silence verified. Full focused aircraft and ordinary pre-version-bump network checkpoints pass; final protocol41 network/full frozen checks pending. Landing/depot refuel/repair/rearm, energy/stalls, full traffic/wing tactics, operation/art/audio/platform/performance acceptance remain open. Exact scopes in status.md.

2026-10-07, integrator/root: escort planner fuel eligibility corrected in isolated fix/air-escort-fuel. New assignments and active steering/threat queries now respect reserve withdrawal for both fighter and bomber;30-tick review clears/reassigns private commitment. Both-side native30 policy cases plus invalid-ID/count/getter ABI/read-only checks and four paired actual reserve-crossing flight scenarios pass. Original aircraft regression and frozen extended checkpoint launched; exact states in status/evidence. Landing requires authored reachable runways, approach/deceleration phases and explicit safe touchdown/finite service stocks; existing home orbits are not runways and no refill/landing is claimed.

2026-10-07, integrator/root: feature/airbases implements shared six-runway layout, rendered paving, physical tracked traction and current owned facility recovery/diversion. Native geometric/ABI/ownership and public1800-tick diversion controls, production software/native GL, actual native client presentation and frozen aircraft/network pass. Fast/full checkpoints pending as recorded in status.md. Next dependent batch: explicit approach/deceleration/touchdown/rollout with ground-aware flight validators and runway traffic, followed by finite supply-backed service; no landing/refill claimed.

2026-10-07 integrator/root: feature/air-approach implements powered interior circuit, velocity-aligned final, conservative descent to70m terrain clearance and actual go-around, preserving flight actuator/fuel/contact rules. Native12 direct/12 misaligned public flights and four paired omitted-guidance traces pass; existing home recovery/holding assertions retained on initial unavailable facilities. Original full crash/glide/fuel/8192/16384/UDP gates remain frozen pending individually. Next: variable speed/ground-aware approach validation, guarded touchdown/rollout and runway occupancy; finite physical service and takeoff follow. No touchdown/refill claimed.

2026-10-07 integrator/root: feature/air-traffic adds bounded generation-aware exclusive runway final leases, deterministic admission, heartbeat/expiry/wrap and lifecycle/release/capture handling integrated into actual pilot approach/init/replay hash. Native all-six/lifecycle/ABI and both-role/side paired public2400-tick scenarios twice pass; both waiters eventually admit, bypass control has440–459 shared-descent frames. Focused aircraft PASS; current network/fast/full checkpoints pending separately. Ground occupancy, fair/emergency queueing, approach speed/guarded touchdown/rollout and finite service/takeoff remain ready dependencies, not implemented claims.

2026-10-07 integrator/root: feature/air-final-clearance adds a120-tick uninterrupted descent forecast using production bank/vertical actuators and per-tick terrain/solid hull sweeps. Unsafe/source-invalid finals release the runway lease and physically rejoin the circuit. Native42 guard/ABI/read-only cases, four paired hazardous-wall public120-tick flights twice, preserved12 clear approaches/circuits and paired descent controls PASS. Routine aircraft/network/fast and frozen extended checkpoints remain separately pending; exact evidence in status.md. Next: variable speed/ground-aware validators, guarded touchdown and rollout/ground occupancy, finite supply-backed service and takeoff.

2026-10-07 integrator/root: feature/air-speed adds physical bounded longitudinal braking/acceleration in the shared5..7 airborne envelope, actual admitted final demand5 and fighter go-around demand7. Identical future-path speed control, empty-fuel no powered acceleration, complete speed/pose rollback. Native2050 math/12 malformed/ABI and four both-role/side paired900-tick flights twice, stale-preview and near-edge rollback controls PASS; routine/frozen tests pending separately. Next dependency remains role/mode-aware low-speed airborne domain, energy/stall-safe banking and guarded touchdown/rollout/ground traffic, followed by finite service/takeoff. Default bomber cruise remains5; no landing claimed.


2026-10-07 integrator/root: feature/air-load implements speed-dependent reserved lift and role normal/maneuver load caps in shared physical bank/preview, finite observed-combat/retained-mission reserve admission, flyable enlarged interior fallback holding, and retained-axis bombing ingress. Native equation/ABI/omitted-lift/public flight/capture-reserve controls and unchanged contested1500-tick bombing retry pass. Frozen final aircraft/network/fast/full checkpoints are running; do not treat them as passes. Next: true role/mode-aware low-speed domain and throttle/drag/energy/climb coupling, then stall-aware approach/contact/rollout/occupancy, finite depot service and takeoff. Exact limitations/status tracked separately; full game goal active.

Aircraft energy — integrator feature/air-energy, dependency flight speed/load; implemented shared kinetic/potential/induced-drag actuator in actual flight and final preview. Native math/ABI/assembled negative controls and paired public flights plus genuine8192 UDP energy replication passed. Aircraft and network gates passed; exact final aircraft699e3f42cb5e946d/native energy/forecast/scale/graphics and separate UDP evidence recorded. Final fast/extended remain pending. Ready for verified batch integration; recurring earlier UDP crash-draw timeout remains failed and targeted diagnostic rerun passes without reproducing its cause. Current minimum-speed saturation is not stall/landing acceptance; next lower-speed domain and grounded lifecycle remain open.

Energy batch integrated: aircraft/fast/native public/forecast controls and realUDP/Arc checks passed with exact scopes. Shared flight guards centralized with byte/data/BSS/relocation equivalence; next lower-speed domain can update one contract. Crash-render fixture now maintains real accepted peer traffic; declared quiet-gap causal failure/pass and original local/UDP draw checks verified without runtime timeout changes. Main exact final extended754e8dc60e12 pending; older7c5eabd30950 and energy97532d366376 remain separately pending. Collect original IDs.
