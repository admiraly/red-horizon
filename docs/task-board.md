# Task graph and ready queue — current integration
| Task | Owner | Dependency | State / acceptance evidence |
|---|---|---|---|
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
