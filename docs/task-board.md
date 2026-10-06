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
consume the same generation-stamped pose. Root frozen candidate a8fd4b7 is under
integration verification; worker passes alone do not establish final acceptance.
The original 30-tick18m steady-drive gate remains after a measured acceleration
phase. Original8k/16k95%army progress and1200tick wall recovery remain unchanged.
Driver corner recovery fixtures explicitly steer tangent and allow90ticks for
physical pivot/acceleration; human50tick fixtures remain unchanged.

Next ready physical batch: authoritative road/off-road surface sampling and slope
constraints with distinct tracked/wheeled handling, requiring actual terrain data
and independent uphill/downhill, contact, camera-independent and same-input replay
proofs. Separate useful followups are oriented hulls, safe army formation spacing,
traffic recovery, damage handling and useful wreck cover. Uniform constants or
cosmetic rotation cannot establish terrain-dependent movement. Full operation,
intelligence, streaming, Windows, runtime jobs, recorded craft and four-client
hardware quality remain independently required; the complete goal stays active.

Terrain prerequisite discovered during integration: authoritative terrain_height
and both GLSL height functions currently share the same analytic bowl/ridge.
Its conservative gradient norm is <0.023 (roughly1.31degrees); there is no road
surface data. Therefore natural current-map driving cannot establish steep-slope
rejection or road traction. Next terrain implementation must add real shared
surface geometry and meaningful height variation before claiming those behaviors,
retain body/corridor reachability and keep collision independent of visual loading.
Artificial steep development fixtures must exercise the same authoritative sampler,
not replace slope observations with uniform role constants.
