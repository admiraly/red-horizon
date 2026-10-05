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
