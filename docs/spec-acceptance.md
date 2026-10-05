# Specification acceptance ledger

Audit baseline: `716bbd011cfc2f788d64223951ff9c533b7fc470`, 2026-10-05. This is a requirement ledger for the complete `docs/spec.txt`, not a declaration that the game is complete. Root work on player motion, view settings and footsteps is concurrent and **not accepted by this audit**. Later integrations must supply their own exact source identity and scoped evidence.

The audit read the complete specification, project `AGENTS.md`, runtime paths, development CLI, workflow, and meaningful assertions in simulation, operation, player, tactics, navigation, reload and network tests. It inspected the recorded checkpoint and scale/GPU reports below. Historical prose in subsystem documents sometimes describes an earlier implementation; code, test assertions and source-matched results take precedence.

Status vocabulary: **Verified slice** means the stated implemented behavior has appropriately narrow evidence; it does not accept the whole requirement. **Partial** means required behavior is absent or acceptance is broader than evidence. **Missing** means no integrated path was found in this baseline. **Unverified** means a plausible path or demonstration lacks the required acceptance evidence. **External gate** means owner authorization, external platform access or human assessment is needed; independent implementation remains ready.

## Evidence anchors and their scope

| Anchor | Authoritative source / evidence | What it proves and what it does not |
|---|---|---|
| E0 | `docs/evidence/air-spectacle-session.json`, checkpoint `3f7287450497`, revision `c2642ebb5493d1c2b406c6f16134f2ba464edc6a-49aa6aa9a54c001c` | Frozen full extended job passed in 188.831 s; 31 recorded suite reports and 104 authored inputs compared. Baseline audit can use the recorded source match. Does not accept absent features, future root edits, Windows, human enjoyment or the complete operation. Retains failed attempts and diagnoses. |
| E1 | `tests/test_simulation.py`, `tests/test_tactics.py`; `src/sim/world.asm`, `src/ai/tactics.asm` | Real moving/targeting/damaged entities, baseline/stretch same-build replay, side-swap symmetry, three fronts and default army motion. Explicit small fixtures establish selected scout/flank/withdrawal outcomes, not a complete operational commander. |
| E2 | `tests/test_operation.py`, `tests/test_waypoints.py`; `src/sim/operation.asm` | Physical capture, contested/dead exclusion, supply graph cut/restoration, saturating resources and spending, final-defense/recapture/victory/defeat, exact destination arrival through real ticks. Fixtures are not complete 30–60 minute player operations. |
| E3 | `tests/test_terrain.py`, `tests/test_navigation.py`; `src/nav/terrain.asm`, `src/nav/squads.asm`; navigation-session evidence | Analytic terrain, static solids, swept movement and LOS, independent segment oracle, physically traversed cached corridors, FIFO overflow/retry, shelter and cancellation. No streamed hierarchy, mutable strategic destruction, slopes or crowd avoidance. |
| E4 | `tests/test_player.py`, `tests/test_vehicles.py`, `tests/test_client_gameplay.py`; `src/game/{player,vehicles}.asm` | Authoritative walk/sprint, rifle cadence/reload/LOS, actual suppression/death/safe redeployment; allied armor board/drive/cannon/exit and ownership validation. Neither full weapon/vehicle roster nor revive/vault. Enemy damage to humans is a bounded prototype pressure rule. |
| E5 | `tests/test_aircraft.py`, `tests/test_combat.py`, `tests/test_effects.py`, `tests/test_air_trails.py`, `tests/test_scenarios.py` | Continuous bounded flight, finite stores, gravity bombs and delayed damage, interception/swept guns, damage-triggered evasion, pooled cosmetics, actual air-battle replay. No aerodynamic solver, wingman coordination, landing/rearm or human spectacle acceptance. |
| E6 | `tests/test_coop.py`, `tests/test_coop_combat.py`, `tests/test_net_events.py`, `tests/test_net_projectiles.py`, `tests/test_client_coop.py`; `src/net/{coop_server,client}.asm` | Dedicated UDP shared authority, four real client slots, join/disconnect/recovery, duplicate/ownership/spend guards, MTU/loss/reorder coverage, two rendered clients and actual replicated shell. No four-client rendered full-operation test, listen server, player prediction/reconciliation or smooth remote actor interpolation. |
| E7 | `tests/test_graphics.py`, `tests/test_client_{aircraft,environment,meshes,shells,effects}.py`; actual GL reports in E0 | Software GL context/shader/link/input and paired actual pixel changes, source meshes/animation/weather, events with immutable authority. Isolated fixtures and submitted instances do not prove 1,024 detailed visible actors or human readability. |
| E8 | `docs/evidence/air-spectacle-scale-{open,stretch}.json` | Seed42/900 ticks, i7-14700K, single thread, 8,192 and 16,384 start counts, p95 4.352/8.745 ms, end engaged 1,504/3,415, peak RSS 10,120/10,068 KiB, navigation and rejected projectile metrics. Rendered/replicated/audio counts are zero/unmeasured. Not SCALE-FRONT/HOTSPOT/NET. |
| E9 | `docs/evidence/air-spectacle-gpu.json` | Accelerated Arc A770/Mesa26.2.3, 1,200 frames, 1280×720 local air-battle, CPU p95 9.370 ms/GPU draw p95 0.349 ms. Host input moved/fired; not controlled stationary or 1080p dense-front acceptance. GPU draw timers omit some whole-frame costs. |
| E10 | `tests/test_audio*.py`; `src/audio/{audio,emitters}.asm`; `content/asset-manifest.json`, credits, model/texture asset tests | Real recorded banks, assembly 128-voice PCM stereo mixer, attenuation/pan/culling, battle event dedup and provenance/parser rejection. ALSA-null output and waveform tests do not prove physical-device quality. Explosion is a log-drum/reverb surrogate, not a mature sound pack. |
| E11 | `tests/test_reload.py`, `tests/test_tools.py`; `src/reload/{host,module}.asm`, `tools/dev.py` | Standalone compatible/incompatible code/parameter reload proof, dependency-aware build invalidation and frozen asynchronous jobs. Game/session reload, snapshots/resume, Windows and worker-thread quiescence are absent. |
| E12 | `.github/workflows/verify.yml`, recorded historical remote run in status/task board | Pinned, read-permission Linux CI with timeout, concurrency and bounded artifacts exists; earlier remote run passed. No release-candidate exact SHA Linux/Windows matrix or current remote acceptance is inferred. |

## Locked requirements R01–R10

| ID | Required outcome | Baseline evidence / remaining acceptance |
|---|---|---|
| R01 | First-person shooter and real-time strategy in one playable game | **Partial:** E4/E7 direct combat and live tactical view/front destinations exist. Rich squad ownership, command wheel, recruitment, placement and assault planning are missing. |
| R02 | Pure cooperation against AI | **Verified slice:** E4/E6 ally/human direct-fire rejection and allied player slots; no PvP path found. Validate every new weapon/explosion and final operation policy. |
| R03 | Thousands of real individual units on each side | **Verified slice:** E1/E8 4,096 and 8,192 per side at initialization; actual motion/casualties and per-entity state. Complete-operation persistence, dense visible/detail and four-front-client scale still unaccepted. |
| R04 | Multiple fronts, large varied maps, combined arms | **Partial:** three fronts, 8 km coordinate extent, 12 sites, infantry/armor/artillery/air. No full streamed authored settlements/roads/woodland/bridges/fortifications operation or full combined-arms roster. |
| R05 | Intelligent coordinated army, squad and individual behavior | **Partial:** E1/E3 observed scouting, physical bounds/flanks and withdrawals; E5 flight. Full strategic/formation/squad intelligence, richer knowledge and danger reactions missing. |
| R06 | Spectacular scalable VFX and dense recorded SFX | **Partial:** actual events drive flashes/smoke/debris/trails and two recorded banks. Mature effects differentiation, sound categories/layers, production art, listening/readability and scale mix acceptance missing. |
| R07 | Engaging action, little involuntary downtime, recovery and meaningful choices | **Unverified:** safe redeployment and military outcome mechanics tested. No opportunity director, pacing telemetry or representative human complete-operation feedback. |
| R08 | All project-authored CPU runtime x86-64 assembly | **Verified slice:** inspected runtime assembly and development-only Python tooling, GLSL exception, platform libraries documented. Maintain source/dependency audit for every integration and Windows. |
| R09 | Measured maximum sustainable iteration speed | **Partial:** E11 incremental/dependency/frozen-job proof. Live game reload/resume metrics and continuous regression budgets missing. |
| R10 | Public GitHub, asynchronous CI and parallel agents | **Partial:** public project/earlier run recorded, isolated worker provenance and Linux asynchronous workflow. Exact final candidate CI/platform evidence and release authorization remain gates. |

## Section 3 — decisions and defaults

| ID | Requirement | Evidence / gap |
|---|---|---|
| 3a | Preserve locked title/FPS-RTS/co-op/massive/assembly/recorded/action choices; record material deviations | **Partial:** README/spec and GLFW ADR document choices. Do not silently turn scale fixtures or bounded prototype systems into accepted product substitutes. |
| 3b | Near-future allied versus autonomous enemy; 1–4 players, Linux and Windows; no required account/PvP/grind/metagame | **Partial:** E6 four allied slots and direct-IP no-account path; Linux works. Windows missing; differentiated enemy production/art incomplete. |
| 3c | Fixed major sites and bounded field placements; configurable short and 30–60 minute operations | **Partial:** 12 fixed sites and short headless runs. No field placements, operation duration configuration or completed long-operation demonstration. |
| 3d | Strong silhouettes/materials/lighting/atmospherics and scalable detail | **Partial:** licensed meshes/textures, actual source animation and weather tests. Static prototype materials/lighting; craft/readability unverified. |

## Section 4 — scale contract

| ID | Requirement | Evidence / gap |
|---|---|---|
| 4a | Baseline 4,096 living units/side, documented infantry/vehicle/artillery/air mix; stretch 8,192/side, no inflated counts | **Verified slice:** E1/E8 and init mix 75% infantry,12.5% armor,6.25% artillery,6.25% aircraft, stable entity records. Baseline count is starting living count; casualties are reported separately. |
| 4b | Streamed 8×8 km useful tactical operation, ≥3 active fronts, 8–16 useful sites, roads/settlements/woodland/ridges/valleys/fortifications/industry | **Partial:** extent, 3 fronts, 12 graph sites and analytic/static terrain. Full authored terrain/layout, streaming and capability-rich sites missing. |
| 4c | All SCALE-OPEN/FRONT/HOTSPOT/STRETCH/NET scenarios with their exact populations/stresses | **Partial:** E8 OPEN/STRETCH. FRONT/HOTSPOT explicitly refuse in CLI; NET absent. Air-battle's initial 320 relocated actors is not dense hotspot acceptance. |
| 4d | Distinguish simulated/engaged/replicated/visible/individually detailed; camera-independent tactical state | **Partial:** headless reports separate simulated/engaged and zero render/network; renderer reports submitted/LOD. Four-client and actual visible/detail reports incomplete; camera-independent core evidenced, streamed handoff absent. |
| 4e | Reference-class actual hardware, driver, revision, seed, settings, resolution; 1080p60, tick p95<33.3 ms, frame p95<16.7/p99<33.3, independent CPU/GPU | **Partial:** E8 tick goal achieved for specific single-thread runs; E9 is 720p only. Full baseline1080p and separately budgeted dense hotspot not accepted. |
| 4f | Peak memory/allocation/nav/actors/particles/audio/bandwidth/load stalls; fixed/native thread measurements | **Partial:** E8 RSS/static allocation audit/nav/actors/projectiles; rejection counts matter (46,138/133,572 launches; 526,679/2,810,427 fallback calls). Particle/voice/load stalls, aggregate bandwidth and native-thread reports incomplete. |

## Section 5 — operation and contribution

| ID | Requirement | Evidence / gap |
|---|---|---|
| 5a | Arrive inside an autonomous battle, choose deployment, fight/recon/command/capture, reinforce/recruit/prepare assaults, counterattack/connect routes, take command complex | **Partial:** E1/E2/E4 autonomous combat, sites and command-root mechanics. No complete connected player loop for recon/recruit/engineering/support/assaults or player-chosen deployment interface. |
| 5b | Military victory; defeat from lost command/recovery; visible final defensive opportunity; finite reinforcement by default | **Verified slice:** E2 command capture, 30-evaluation final defense/recapture, terminal outcomes, no hidden spawn. Recovery resources/production balance and user-facing long-operation fairness not accepted. |
| 5c | Vulnerable soldier and useful shooting/recon/command/engineering/support; competent solo allied assistance | **Partial:** E4 vulnerability/rifle/commands and E1 autonomous allied movement. Engineering/designation/recon contribution and competent full-operation assistance unverified. |

## Section 6 — first-person combat, vehicles and recovery

| ID | Requirement | Evidence / gap |
|---|---|---|
| 6a | Responsive aim, configurable sensitivity/FOV, sprint/crouch/jump/vault/reload/swap/interact/contextual command, grounded movement | **Partial:** E4/E7 mouse, walk/sprint/reload/interact. Baseline lacks crouch/jump/vault/swap and persisted sensitivity/FOV/remap settings. Concurrent root work is not acceptance here. |
| 6b | Server authoritative damage/movement validation with local prediction | **Partial:** E4/E6 authority and input validation verified; bounded one-tick visual XZ preview and camera correction exist in client.asm; timestamped prediction/resimulation and robust latency acceptance remain missing. |
| 6c | Assault rifle/LMG/shotgun/marksman/anti-armor/grenades/designator, distinct data recoil/reload/spread/audio/muzzle/hit policy/penetration/damage | **Partial:** rifle only; tests establish its fixed cadence/ammo/reload/LOS and cosmetics. No complete data-driven roster or penetration/material policy. |
| 6d | Immediate fire, recoil recovery, hit feedback, material impacts, suppression and strong near-field audio; weapon appropriate tracers | **Partial:** E4/E7 rifle response/recoil/HUD/tracer cadence and E10 sound. Cosmetic recoil does not modify aim, material-specific impact sets and complete near-field craft missing. |
| 6e | Friendly direct fire off, explicit configurable large-friendly-explosion policy consistently applied | **Verified slice:** rifle/shell/bomb enemy-only tests. Configurable documented player-facing policy and coverage across future weapons remain missing. |
| 6f | Transport/APC/MBT/self-propelled artillery/scout drone/AI strike planes; player ground driving/weapons | **Partial:** controllable generic allied armor/cannon, autonomous shell artillery and E5 planes. Distinct transports/APC/drone roles, troop seats/embarkation and all vehicle weapons missing. Pilotable aircraft are later scope. |
| 6g | Wheeled/tracked approximations, slope limits, road/off-road difference, readable damage and useful temporary wreck cover | **Partial:** movement speed and collision tested; no slope/road system or gameplay wreck cover, distinct mobility/damage states. |
| 6h | Brief revive then safe fast forward/squad deployment; dead players can command/mark; no spawn camping/blast-zone repeat | **Partial:** E4 30-tick retry and safe enemy-LOS deployment tested. Revive, blast hazard safe spawn, explicit deployment/map choice and dead-player commands/marks require integration tests. |

## Section 7 — command and cooperative interface

| ID | Requirement | Evidence / gap |
|---|---|---|
| 7a | Company assignment, autonomous squad tactics and army command outside human ownership | **Partial:** slots map to front assignments (fourth assists front0), autonomy and side/front orders. Actual company/squad membership/primary ownership absent; fronts are too coarse for final requirement. |
| 7b | Wheel: move/attack/defend/suppress/flank/regroup/retreat/follow/embark/disembark/support; pointing, acknowledgement, intent, remap | **Partial:** advance/hold/retreat and map waypoint/ACK. Wheel, target semantics, remaining orders, intent presentation and remapping missing. |
| 7c | Live multiplayer tactical map selects formations, supply/intel, waypoints/objectives/recruit/placement/scheduled assaults | **Partial:** live view, front/site/resource markers and one destination E7/E6. Formation selection, fog/intel, multi-waypoint plans/recruit/placement/schedule missing. |
| 7d | Shared voluntary ready/timing/countdown artillery+infantry+armor plans; cancel/delay/emergency without pause | **Missing:** no assault-plan state/protocol/UI in inspected baseline. |
| 7e | One primary owner/squad; transfer/assist, conflicting order prevention, reservation/atomic spend; no mandatory FPS-excluding commander | **Partial:** E6 front ownership and duplicate cost guards. Slot3/front0 shared assistance has no squad ownership transfer/reservation model. Final squad conflict and economic transaction contracts missing. |

## Section 8 — economy/logistics

| ID | Requirement | Evidence / gap |
|---|---|---|
| 8a | Data-driven requisition/supply capacity/costs; recruit/build/support and sustain capability | **Partial:** E2 connected capacity/income/checked spend. Hardcoded sites/income, spending on orders only; no production/recruit/build/support transactions or weapon resupply. |
| 8b | Deployment/depot/production/observation/air-control/artillery/command sites visibly change capability | **Partial:** four numeric roles and command/deployment/income paths. Observation/air/artillery unlocks and full capability/UI mapping absent. |
| 8c | Fixed major buildings, bounded field cover/repair/emplacements | **Missing:** static decorative structures are not a placement/repair implementation. |
| 8d | Capacity/connectivity primary logistics, selected meaningful physical convoys; local ammo/resupply/shortage; gradual readable route-cut degradation | **Partial:** E2 graph and E5 finite air stores/ground shell reserves. No local infantry ammo, rearm/resupply/convoys/warnings/capability degradation path. Supply capacity changes immediately; full logistics semantics missing. |
| 8e | Recovery reroute/escort/restore/rescue/seize supplies produces choices | **Partial:** graph recapture restores capacity. Full selectable recovery missions and player rewards absent. |

## Section 9 — terrain/streaming/destruction

| ID | Requirement | Evidence / gap |
|---|---|---|
| 9a | Tactical forests/ridges/plains/urban/bridges/passes affect sight/nav/cover/weapons/routes | **Partial:** E3 static LOS/collision/elevation/shelter and sourced terrain material. Material appearance is not forest concealment or route semantics; bridges/passes/urban tactical layout missing. |
| 9b | Authored strategy plus seeded detail/material/vegetation/geometry; all sites reachable by intended roles | **Partial:** authored coordinates, seeded army and generated baked assets. No full tactical layout or exhaustive site×unit reachability proof. |
| 9c | Async chunks/assets, collision/nav ahead of graphics, kilometre-safe origin with synchronized sound/effects | **Missing:** static preloaded coordinate world, no streamed regions/origin handoff; core camera independence alone does not meet streaming. |
| 9d | Authored walls/bridges/bunkers/trees/building/vehicle destruction, optional bounded crater changes | **Partial:** vehicle death/battle event cosmetics exist. Static terrain obstacles do not transition, no strategic bridge/building/tree/crater collision edits. |
| 9e | Local coalesced cover/nav invalidation; strategic persistence versus decorative debris; server damage/client fragments | **Partial:** E5 authoritative damage/read-only cosmetic fragments. No mutable obstacle versioning or local invalidation/state persistence. |

## Section 10 — intelligence

| ID | Requirement | Evidence / gap |
|---|---|---|
| 10a | Explicit bounded runtime plans/utility/FSM/squads; no required cloud inference | **Verified slice:** inspected deterministic NASM controllers, no network inference dependency. Neural policies not required. |
| 10b | Commander evaluates value/capacity/supply/observed enemy/loss/routes/risk; defenses/probes/raids/offensives/reinforcement/withdrawal/production/reserves; hysteresis/commitments | **Partial:** E1 side/front weights, observed threats, supply retreat and commitments. Full utility choices/reserves/production/loss/risk plans missing; no strategy personality acceptance. |
| 10c | Formation corridors/staging/mix/support/timing, combined-arms coordination and abort on failed assumptions | **Partial:** E1/E3 scout/support approach, flank corridors and observed withdrawal. Force mix/support scheduling/linked assault/route-security and reasoned abort unaccepted. |
| 10d | Squad observations/cover/formation/suppress/flank/bounds/retreat/support/regroup; artillery shelter/dispersion and anti-armor response | **Partial:** tested bounds/flank/retreat and selected infantry shelter. Artillery danger perception, regroup/support and anti-armor selection missing; default900tick cover choices are zero. |
| 10e | Individuals aim/reload/obey/nav/cover/crowd/explosion/hazard/stuck; urgent interrupt, smooth steering/animation despite slow plan | **Partial:** movement/targets, selected cover and bounded stuck logic; physical animation/continuous flight. Crowd/friendly obstruction and imminent hazard response absent; ground individual gun/reload behavior incomplete. |
| 10f | Ground truth separate from per-side observed position/confidence/time/identity/comms; scout propagation/staleness; no hidden player targeting | **Partial:** E1 observations derive acquired LOS, front timestamp/confidence and hidden-scout test. Full per-contact identity/certainty/comms/propagation and fog-of-war display missing; audit enemy-player pressure and future tactical queries. |
| 10g | Explicit difficulty planning/aim/reaction/resources/coordination; nonomniscient default; methodical siege/mobile encirclement/armored assault/defense-in-depth decisions | **Missing:** no configurable behaviorally distinct presets/difficulty acceptance in baseline. |
| 10h | Outcome scenarios: flank, hidden scout, overwhelming withdrawal, supply reinforcement, player order, artillery hazard, destruction cover recovery, bounded nav; decisions/reasons | **Partial:** E1/E3 physical scout/flank/withdrawal/order/nav assertions and replay. Supply withdrawal is not supply-aware reinforcement. Artillery hazard/destruction recovery and full reason reports missing. |

## Section 11 — pacing

| ID | Requirement | Evidence / gap |
|---|---|---|
| 11a | Agency/change/stakes/planning; win-seeking commander separate from economically eligible opportunity pacing, no fabricated armies/objective moves | **Missing:** no integrated opportunity director or complete win-seeking operational planning. Existing finite armies respect no-hidden-spawn slice. |
| 11b | Finite optional intercept/rescue/breach/artillery/observe/armor/base/assault opportunities with clear rewards and restrained notifications | **Missing:** no timed opportunity/reward/notification path. |
| 11c | Useful-objective idle/travel/spawn contribution/deaths/diversity/commands/recovery metrics; ~20s contribution/~15s idle recommendations tuned by playtests | **Unverified:** weapon/player counters exist; no required pacing telemetry or representative operation measurements. |
| 11d | Transport/deployment/front sites preserve map usability and voluntary quiet without forced shake/strobing/damage | **Partial:** sprint/armor/safe redeploy. Missing transport network, recommendations and comfort controls; human travel quality unverified. |

## Section 12 — rendering/VFX

| ID | Requirement | Evidence / gap |
|---|---|---|
| 12a | Assembly-owned renderer and explicit GLSL, GL4.5 capability; targeted alternate only if measured necessary | **Verified slice:** E7/E9 actual GL4.6; assembly orchestration and GLFW platform deviation ADR. No evidence requires renderer rewrite now. |
| 12b | Instancing, GPU visibility/LOD where beneficial, indirect draws, distance animation, terrain patches/material arrays/rigid or skeletal motion | **Partial:** instanced draws, CPU distance LOD/animation, terrain texture array and authored baked animation. GPU visibility/indirect/chunked patches missing; measure benefit before replacing working path. |
| 12c | Bounded directional shadows, HDR/light/bloom/fog and scalable particles, offline validation | **Partial:** fog/weather/lighting shaders, pooled billboard effects and shader checks. Shadow/HDR/bloom production pipeline and scalable particle-quality controls missing. |
| 12d | Explosion light/flash/fire/smoke/terrain dust/sparks/debris/decals/persistence/silhouettes; grenade/tank/fuel/artillery/bomb differentiation, GPU pools/lights/overdraw budget | **Partial:** E5/E7 actual flash/smoke/dust/debris/bombs/destruction. No complete differentiated roster/decals/fuel/wreck-fire/dynamic-light/overdraw budget. Cosmetic pools currently CPU-updated plus shader presentation. |
| 12e | Authoritative muzzle/tracer/impact/trail/blast/wreck/radio events, cosmetic seeds; bounded gameplay smoke; warnings through clutter | **Partial:** E5/E6/E7 authentic events and dedup. Radio/wreck persistent effects and authoritative smoke semantics/warning readability missing; current smoke grants no LOS cover. |
| 12f | Quality decorative-only scaling, preserve enemies/warnings/cover; shake/blur/flash/density toggles, safe repeated flash | **Missing:** fixed renderer/effects; no complete accessible quality/comfort configuration or repeated-flash limit acceptance. |
| 12g | Incoming sound/designation/trajectory/blast estimates and enemy reaction opportunities for strikes | **Partial:** visible trajectories/actual launch events. Player-facing designation/warning estimates/incoming recordings and ground AI hazard reaction missing. |

## Section 13 — recorded audio/assets

| ID | Requirement | Evidence / gap |
|---|---|---|
| 13a | Substantial verified redistributable sources; every URL/title/author/license/credit/original+derived hash/process/destination; generated notices, incompatible terms excluded | **Verified slice:** E10/model/texture asset tests and manifest source provenance for installed assets. Continue per-asset checks and ensure generated notices remain complete; code license separate. |
| 13b | Recorded shot variations/interior/exterior/distant, mechanics/passbys/material hits/grenade/artillery/bomb/engine/tracks/rotor-jet/terrain footsteps/debris/wreck/environment/radio | **Partial:** rifle and explosion surrogate only at baseline. Categories and layered variants largely missing; concurrent footsteps not accepted here. |
| 13c | Offline PCM conversion/documented narrow container, no hidden decoder/runtime language exception; installed offline starter/optional quality packs | **Partial:** actual installed PCM banks/conversion and no synthesized runtime replacement. Complete substantive starter pack, optional quality packaging and compressed streaming policy remain. |
| 13d | Assembly mixer native output; callback no allocate/block/load/sim locks; bounded queue/buffers;48kHz/device adaptation measured | **Partial:** bounded synchronous assembly mixer, ALSA nonblocking path and48kHz tests. Device adaptation/physical output/buffer/real callback architecture and Windows WASAPI not accepted. |
| 13e |128 configurable/profiled physical voices, logical emitters/priority/virtualization/distant aggregation; occlusion/pan/variation/reverb/headroom/delay/no hidden intel leak | **Partial:**128 fixed voices, culling/virtualization/pan/attenuation/replacement and waveform guards. Priority classes/aggregation/occlusion/reverb/event travel delay/configurable voices/physical mix quality missing. |
| 13f | Licensed starter+optional quality pack/offline, reproducible assets/no regenerated churn/source quota policy | **Partial:** source hashes/incremental models/local package work. Full sound pack distribution/optional storage and exact reproducible archive timestamps not accepted; external storage only after authorization/quota checks. |

## Section 14 — assembly/toolchain/ABI

| ID | Requirement | Evidence / gap |
|---|---|---|
| 14a | All own CPU runtime assembly, OS/GPU services exceptions; development tools not gameplay VM | **Verified slice:** E0 source match and inspected assembly build paths; GLFW choice explicitly documented. Maintain license/dependency audit. |
| 14b | x86-64/SSE2 baseline, optional dispatched AVX2 with fallback, no AVX512 dependency, measured optimization | **Verified slice:** core inspected SSE2 assembly; no optional ISA acceptance claimed. A systematic release ISA audit remains useful. |
| 14c | Pinned NASM/linker/dependency incremental builds, shared Linux ELF/Windows PE source; X11/GLX/ALSA and Win32/WGL/Winsock/WASAPI isolated | **Partial:** NASM2.16.03 bootstrap, actual transitive includes/cache and Linux services. Host linker varies by recorded machine; Windows build/bindings absent. GLFW deviation documented. |
| 14d | SysV/Win64 stacks/preservation/shadow/callback/error/unwind/debug; generated structs/offsets/fingerprints; every routine documented contract | **Partial:** SysV documented and generated entity/player/etc schemas used. Reload ABI remains separate hand-owned proof; comprehensive routine contract/ABI guard tests, Win64/unwind callbacks missing. |
| 14e | Debug/release symbols, guarded arenas/assertions/crash dumps/debugging and external bounds/invariant analysis | **Partial:** NASM DWARF, runtime/parser validation and test probes. Distinct debug/release/guard-page arena/crash dump/Windows debugging acceptance incomplete. |

## Section 15 — simulation/data/jobs/navigation

| ID | Requirement | Evidence / gap |
|---|---|---|
| 15a |30Hz authority independent render, high-frequency input/interpolation, swept fast projectiles and budgeted AI continuous movement | **Partial:** E1/E4/E5/E6 ticks/sweeps and slow controller/continuous flight. Local prediction and remote actor interpolation missing. |
| 15b | Dense stable generation IDs, bounded pools/grids/sectors/passes, no quadratic full-entity hot loops or unmeasured allocations | **Verified slice:** bounded grid candidate reservoir, arrays/generation checks, capped projectile/events/navigation pools and static core allocation audit. Future streaming/placement must preserve contracts; whole-process allocations not measured. |
| 15c | Runtime jobs with partition/dependency barriers/per-worker scratch/coarse granularity/capped workers/no global AI lock | **Missing:** single simulation thread. Dev background jobs and parallel agents are not runtime job-system acceptance. |
| 15d | Hierarchical regions/cached squad corridors/local steer/shared flows/vehicle constraints; urgent+fair capped queue/stale cancel/stuck/local destruction invalidation/safe overflow | **Partial:** E3 512FIFO,8builds/tick, cached corridors, cancellation/stuck diagnostics/overflow fallback. Hierarchical streamed regions/flow/slope/crowd/dynamic invalidation missing; substantial repeated overflow remains. |
| 15e | Sim fidelity independent LOD; persistent distant IDs/HP/orders/losses, conservative fidelity handoff/no observer-dependent results | **Verified slice:** camera-independent full individual core and visual LOD. No distant simulation LOD/handoff implemented; don't claim streaming proof. |
| 15f | Cosmetic separate from gameplay projectiles; travel/blasts/spatial queries; bounded corpses/debris/decals/fire/trails, persistent gameplay wrecks separately | **Partial:** E5/E6 separate cosmetic pool/trajectory and swept blasts, bounded effects/trails. Corpses/decals/fire lifecycle and gameplay wreck cover missing; AI pool saturation must be addressed at dense scale. |

## Section 16 — networking

| ID | Requirement | Evidence / gap |
|---|---|---|
| 16a | Authoritative dedicated and listen server, local solo same contracts, direct IP/LAN first, no mandatory GitHub/account | **Partial:** E6 dedicated UDP and solo shared core work; listen server missing. Internet NAT/relay/discovery explicitly later, not a completion blocker for direct IP. |
| 16b | Versioned binary UDP sequence/ACK/selective reliability orders/spawn/destruction; bounds/reassembly/MTU/faults; no bespoke crypto | **Partial:** UDPv5 MTU1196, sessions/ACK/retry/idempotent order tests. Snapshot/event destructive state is bounded sampled/tombstoned, not complete explicit reliable spawn/destruction recovery; no fragmented reassembly required by current fixed packets but richer snapshots need a contract. |
| 16c | Predict/reconcile local movement; remote interp/bounded extrap; interests camera/commanded formations/map, coarse distant intelligence | **Partial:** camera-near interest and bounded cosmetic shell extrapolation. Local player and remote actor smoothing absent; commanded-formation/tactical-map interests and fog-aware aggregate replication missing. |
| 16d | Validate owner/spend/rate/coordinates/IDs/packets/versions, never client damage; join-in-progress/disconnect/reconnect/ownership recovery | **Verified slice:** E6 actual authority and malformed/lost ACK/recovery tests. Final squad ownership/recruit/place support transactions need new validation coverage. |
| 16e | Compatible live schema/content reload; incompatible coordinated restart | **Missing:** version/hash reject exists at join; live reload/restart coordination absent. |
| 16f |0/50/100/150ms jitter≤5% loss/dup/reorder reproducible fixtures, per-client bandwidth/dense-front stress | **Partial:** E0/E6 fault matrix and packet bytes. Dense-front four-player operation/bandwidth/smoothness under these faults still unaccepted. |

## Section 17 — instant iteration

| ID | Requirement | Evidence / gap |
|---|---|---|
| 17a | Measure cold/incremental/startup/reload/resume/focused times +context, goals <1s module/<100ms parameter/<5s resume/<10s routine, investigate regressions | **Partial:** E11 build/noop/focused/reload-proof measurements. Live parameter/module reload and prepared operation resume missing; no continuous full metric summary/regression tracking. Goals are not observations. |
| 17b | Stable host/versioned table/fingerprint/persistent state; safe job-quiesced code swap and no dangling in-flight callbacks | **Partial:** E11 standalone serial proof. Game host/module partition/audio/render/net lifetime boundaries and runtime jobs quiescence missing. |
| 17c | Explicit migration/restart snapshot, clear incompatibility/old-code fallback, Windows loaded filename cleanup | **Partial:** proof rejects and retains prior module. Game snapshots/migrations/restart/Windows locking missing. |
| 17d | Off-thread validated atomic weapon/unit/AI/objective/effects/sound data reload; sound callback safe; shader only after compile; no world rebuild | **Missing:** proof reloads one decimal parameter; game databases and transactional sound/shader reload not implemented. |
| 17e | Source/tool/options asset caching, parallel independent files, incremental deps, no routine clean/redownload/whole bake | **Partial:** actual dependency build and preserved independent mesh records tested. Parallel assemble/conversion graph and full asset cache completeness not accepted. |
| 17f | Named direct fixtures, compatible saved schema/content/build snapshots; reload-safe debug camera/visualizers | **Partial:** OPEN/STRETCH/air-battle CLI only; required named fixtures/snapshot/resume/debug persistence missing (inventory below). |

## Sections 18–21 — execution, agents, CI and verification

| ID | Requirement | Evidence / gap |
|---|---|---|
| 18a | Frozen exact-source async slow jobs, log/PID/job IDs, useful independent work, ready queue, bounded polling and last known good | **Verified slice:** E0/E11 source-frozen jobs, worker provenance/reconciled failures and ready queue. Continue rule each session; old ledger does not reconcile newly launched root jobs. |
| 18b | Cheap focused checks, validated coherent integration, prioritize failures, bound speculative dependencies, version outputs and reconcile all handoff statuses | **Verified slice:** E0 retained failures/corrections and immutable revisions. Audit doc adds no runtime verification claim. |
| 19a | One shared-contract integrator; isolated workers/index/logs; 4–6 initially, measured contention; version/migration notes and small patches | **Verified slice:** E0 four clean isolated workers and cherry-pick identities. More runtime work needs measured concurrency, current ABI note and fresh merge evidence. |
| 19b | Maintain task-board/interfaces/decisions/status with owners/deps/evidence/state; no percentages | **Partial:** documents exist with concrete evidence and limitations; some older subsystem/interface prose is stale. Reconcile contracts after each new slice rather than inferring acceptance from a row. |
| 20a | Authorized repo CI/current plan/runner cost confirmation; finite timeout/cache/retention/pinned actions/read least privilege/no unsafe secrets/self-hosted PR trust | **Partial:** E12 read permissions, pinned actions,15min timeout and7day artifacts. Owner plan/current quota verification and complete tool/cache strategy not evidenced here. No paid runner selection authorized. |
| 20b | FAST/INTEGRATION Linux+Windows debug/release/protocol/replay/co-op/license; SCALE1k/4k/8k/16k realtime/throughput/soak; VISUAL; manual authorized RELEASE | **Partial:** one Linux push/PR/dispatch workflow runs fast/all/8k/16k+softwareGL. Windows/config matrix/1k4k/soak/license explicit reports/manual release workflow incomplete. |
| 20c | Branch concurrency cancellation isolated, exact SHA CI status, machine-readable failure/seed/crash/artifact logs; optional GPU gaps explicit | **Partial:** E12 workflow concurrency/artifacts and local frozen JSON. Current exact candidate remote statuses and crash/seed structured summaries required at candidate checkpoint. |
| 21a | Same-build replay stable RNG/order, no cross-platform bit-identical claim; snapshots include seed/ordered external input/content/build/checksums | **Partial:** E1/E2/E5 same-build reproducibility. No saved full snapshot/command/external-input replay format; Linux seed replay is not Windows determinism. |
| 21b | ABI/stack/bounds/overflow/generation/guarded pools/ownership/saturation; malformed parsing/debug finite health/membership/resource invariants | **Partial:** E0 meaningful validation suites/negative content/packet cases and safe caps. Guard-page harness/comprehensive ABI tests, squad membership/full resource totals assertions missing. |
| 21c | Kernel/system/co-op/army/hardware render+audio/playtests; meaningful fault detection, not mirrored constants | **Partial:** strong actual assembly/independent oracle/paired GL/fault tests; physical audio/full-operation/human and Windows acceptance missing. |
| 21d | Representative footage/screens/audio and player feedback; fun/art quality explicit unverified | **Partial:** actual silent12s clip and paired screenshots. No representative full-operation recorded audio or human feedback; never infer fun from pixels/checksums. |

## Sections 22–24 — repository, CLI and milestones

| ID | Requirement | Evidence / gap |
|---|---|---|
| 22a | Organized shared/platform/core/sim/ai/nav/render/audio/net/game/reload/shaders/schemas/content/tools/tests/docs/workflows and ignored revision builds/runs | **Partial:** existing functional paths follow most layout, no Windows/core runtime jobs yet. Suggested directories are organizational defaults, not acceptance from empty folders. |
| 22b | README/build/contribution/asset policy/notices/license decision, separate asset grants/no incompatible code | **Partial:** README/contribution/content policy/notices document installed assets. **External gate:** owner approval of code license pending; never invent MIT adoption. |
| 23a | Real consistent configure/build/run/server/test/bench/snapshot/resume/reload/jobs/collect/package/doctor commands | **Partial:** actual implemented command inventory below. Snapshot/resume missing; reload standalone proof, configure aliases doctor, not full platform configuration. |
| 23b | Slow background ID/revision/log/result, actionable fast errors; safe owned process management/no orphan/killing others | **Verified slice:** E11 frozen jobs tested and errors reject unsupported fixtures. Expand termination/recovery tests for game/server/streaming jobs, not only finite dev workers. |
| 23c | Doctor version/libs/GPU/writable/assets/optional auth/no secrets; minimal headless and full client | **Partial:** `doctor()` reports platform/tools/writable/rifle and GL probe when DISPLAY. No complete system library/all-assets/auth checks; headless/client builds verified Linux. |
| 24-M0 | ABI, incremental Linux/Windows, async tools/CI/diagnostics/parameter+compatible live reload/build timing/8,192 benchmark | **Partial:** foundational Linux/core scale/proof/tool slices. Windows/live host/jobs/debug diagnostics gaps prevent M0 completion. |
| 24-M1 | Satisfying FPS weapon/terrain/recorded audio/squads/command/30Hz/actual massive moving renderer and measured CPU/GPU/audio budgets | **Partial:** real prototype paths exist; satisfying action, physical audio, full budgets/hardware display acceptance absent. |
| 24-M2 |2-player listen/dedicated, authority/nav/cover/scout/flank/capture/supply/company/map/reinforcement/four-player fixtures/autonomous armies | **Partial:** dedicated/two rendered/four-slot fixtures and mechanics. Listen/company/recruitment/full map/complete allied intelligence missing. |
| 24-M3 | Ground vehicles/artillery/air/layered audio/effects/terrain tactics/destruction/assault/plans stressed together at scale | **Partial:** armor/artillery/air and bounded effects. Full roster/layered sound/dynamic destruction/linked assault/operational plans/dense integrated stress missing. |
| 24-M4 | Full streamed multiple-front map/all core roles/4,096side/logistics/outcomes/join/saved scenarios/hotspot/recovery/licensed pack | **Partial:** individual core/outcome/join/license slices. Full operation/streaming/logistics/saved/hotspot acceptance absent. |
| 24-M5 | Player pacing/AI improvements/craft/optimization/accessibility/Windows/stretch/release readiness | **Partial:** measured stretch experiment only; remaining human polish/platform/release criteria unaccepted. |

## Section 25 — completion gates

The complete goal remains active. Every gate below must be demonstrated on a declared candidate, rather than inherited from a narrow earlier checkpoint.

| ID | Required deliverable | Present scope / proof still required |
|---|---|---|
| 25a | Playable cooperative military operation, thousands/side, multiple useful fronts, meaningful command/combined arms/recorded sound/spectacle/intelligence/outcomes/acceptable hardware performance | **Not accepted:** prototype subsystem evidence E1–E10 does not compose into the full specified operation. All missing gameplay/platform/content dependencies above apply. |
| 25b | Linux and Windows release-candidate SHA builds | Linux baseline tested, not a final RC; Windows absent. Require exact candidate debug/release builds and smoke evidence on both. |
| 25c |1–4 player operation including join/disconnect/recovery | Four protocol slots and two rendered clients verified. Require completed solo and 2/3/4-human-or-test-client operation with meaningful simultaneous front actions, joins and recovery. |
| 25d | Baseline and dense-front metrics with actual entity/detail counts | E8/E9 limited. Require declared1080p baseline and dense visible hotspot/front budget with genuine simulated/engaged/replicated/visible/detailed and audio/effect counts. |
| 25e | Navigation/AI scenarios and reproducible seeds | Existing scout/flank/retreat/nav evidence useful. Complete artillery danger/destruction recovery/reinforcement/formation/commander scenarios and reason logs. |
| 25f | Audio/VFX demos and player readability | Actual pixels and silent clip useful. Require mature recorded categories, physical listening, representative combined battle and human warning/readability feedback. |
| 25g | Asset manifest/generated credits | Installed content verified; complete roster/pack additions must retain grants/hashes/credits. Owner code license remains a separate release gate. |
| 25h | Incremental build/reload/resume timings | Build and standalone proof only. Require live match parameter/module/sound/shader-safe reload and full saved-scenario resume measurements. |
| 25i | Honest limitations/failures/stretch | E0/E8 record caps, failed jobs and stretch. Continue fresh source-matched evidence; no silent relabeling or pending-tests-as-passed. |

## Named scenarios and command inventory

| Name / command | Baseline state and required next acceptance |
|---|---|
| `firing-range` | Missing named CLI fixture; rifle tests alone do not implement direct fixture launch. Add full weapon/input/material range and snapshots. |
| `squad-flank` | Physical test fixture in `test_tactics.py`; missing named scenario and reason/outcome report CLI. |
| `armour-assault` | Vehicle/combined threat tests exist; missing coordinated formation fixture. |
| `artillery-storm` | Moving shell/impact tests exist; missing dense hazard/warning/dispersion fixture. |
| `supply-cut` | E2 cut/restoration test; missing named launch and gradual ammo/capability/recovery scenario. |
| `bridge-collapse` | Missing dynamic bridge/nav/destruction implementation and direct fixture. |
| `co-op-join` | E6 join fixtures exist; missing named scenario launch/resume operation fixture. |
| `scale-open` / SCALE-OPEN | Working default8192 CLI/core; full streamed operation and1080p detailed performance not accepted. |
| `scale-front` / SCALE-FRONT | Registered but explicitly rejected as not implemented; must keep8192 total and ≥2048 regionally engaged, report actual engagement. |
| `scale-hotspot` / SCALE-HOTSPOT | Registered but explicitly rejected; must keep8192 and genuine visible1024 plus artillery/smoke/projectiles/vehicles/audio. |
| `scale-stretch` / SCALE-STRETCH | Headless16384 measured separately E8; no massive render/network envelope implied. |
| SCALE-NET | Missing four-client different-front integrated army stress and bandwidth/detail report. |
| `air-battle` | Working local full8192 with320initial relocated actors;300tick replay in E5. Not a substitute for named spec fixtures or hotspot. |
| `configure`, `doctor` | Both call doctor; versions/tools/GL when available, writable and rifle availability. Full configuration/library/all-asset/auth diagnosis incomplete. |
| `build --changed` | Dependency hashes actually skip unchanged objects/link; flag accepted, same incremental routine. ELF headless/client/coop only; client objects-only is no-link/no-GL evidence. |
| `run --scenario`, `server --headless`, `bench --scenario` | Real shared headless path; optional realtime30Hz; client only scale-open/air-battle. `server` is not UDP host; `coop` is dedicated UDP host. |
| `test --suite`, `--extended` | Real focused/core/UDP/softwareGL/tool suites; fast omits full-scale/GL/fault acceptance. No complete-operation or Windows test gate yet. |
| `snapshot`, `resume` | Missing subcommands and saved full world/commands/schema/content/build compatibility. |
| `reload` | Standalone proof/test, not current game reload. |
| `jobs`, `collect JOB_ID`, slow `--background` | Real frozen source jobs with own metadata/result logs; E11 positive isolation. `package` lacks background flag at baseline despite potentially slow builds. |
| `package` | Real local Linux archive/hash/credits, no public release; full byte-reproducibility and Windows package absent. |
| `doctor` headless/client platform | Headless no display/audio requirement tested; full graphics uses GLFW/GL/ALSA. Native physical audio and Windows require their own evidence. |

## Dependency-ready implementation queue

These tasks remain useful without licensing/publication/human-feedback authorization. Dependencies are interface work, not excuses to wait for external gates.

1. **Complete player movement/settings and weapon data contracts.** Preserve server authority and replay, add grounded crouch/jump/vault with swept clearance and safe landings; persisted sensitivity/FOV/remap and comfort controls. Concurrent root motion/view changes need exact focused and actual input evidence. Then data-driven full weapon roster and material impacts/launcher/grenades/designator, including friendly blast policy and event/sound roles.
2. **Add contact knowledge, danger and mutable world contracts.** Generation-tagged per-side contacts with stale confidence and communication, server hazard volumes/events, versioned bounded obstacles/destruction, cover/nav dirty-region queue. Start bridge/wall loss and artillery hazard fixtures with physical outcome negative controls; no global terrain rebake.
3. **Build true company/squad command and production transactions.** Stable squads/owners/transfer/assistance, reservations, atomic recruit/support/place costs, valid terrain placements, explicit order wheel and intent. Keep unrelated allied command autonomous; add live tactical selection/intel and shared timed assault state with cancel/delay.
4. **Implement logistics/vehicle roles and recovery.** Ammo consumption/resupply, capability-driven site roles, bounded route-cut degradation and warnings; transport/APC/seats/drone and mobility/slope/road rules, persistent wreck cover. Add a finite valuable convoy/recovery fixture after graph/production transactions are stable.
5. **Complete operational AI and pacing.** Utility/reserves/route-risk/production/plan commitments/force mixes, support and coordinated timing; difficulty/personalities with measurable different choices. Economic opportunity recommendations, contribution/travel/idle telemetry, full finite-operation commander victory/defeat/recovery fixture, then representative human feedback.
6. **Add async map/nav streaming and runtime jobs.** Region contracts/collision ahead of visibility, authored useful terrain/sites×role reachability, squad regional corridors/shared requests/local version invalidation and origin handling. Partition coarse runtime passes/per-worker scratch/barriers; compare fixed/native thread and reduce repeated nav fallback/pool saturation with measured alternatives.
7. **Finish network responsiveness and listen mode.** Separate render history for remote entity/air interpolation, local player intent prediction/reconciliation, generation/disconnect resets and bounded corrections under the existing fault matrix. Add listen host using same authority, reliable state recovery and command/map interests. Four rendered different-front clients/full operation comes after named front/hotspot fixtures.
8. **Expand sound and graphics craft with parallel content work.** Licensed recorded category pack, variants/layers/engines/terrain steps/jet/incoming/radio, voice priorities/occlusion/reverb/aggregation/delay, physical-device capture. Bounded shadows/HDR/effects differentiation/decals/wreck-fire and accessibility while retaining semantic warnings; actual detailed actor counts and overdraw/voice budgets.
9. **Integrate live reload/snapshot/resume and Windows.** Stable host module lifetime boundary, safe reload tables and schemas, full save/ordered-command compatibility, atomic data/shader/audio swap; platform ABI isolation/Win64 callbacks/WGL/Winsock/WASAPI, both debug/release builds. Independent Windows/tooling work can start before later gameplay; do not reduce final platform scope.
10. **Author final fixtures and candidate acceptance.** Direct named fixtures, SCALE-FRONT/HOTSPOT/NET with exact count semantics,1080p target runs/audio/streaming stalls, long finite operations, current CI candidate SHA Linux+Windows/soak/package, complete licenses/credits and human playtesting. Reconcile every launched job/failure before handoff.

## External gates, kept separate from ready work

- **Owner code license:** pending; prepare compatible code/asset notices and a concrete candidate, never choose MIT without approval. Does not block private implementation/tests.
- **Publication/release:** follow session authorization. This audit performs no push/repository/release action. Prior public snapshot does not authorize an unrequested release. Local candidates/packages remain ready work.
- **Windows execution and physical target audio:** arrange actual accessible test platform/device for final evidence while implementing bindings/tests locally; cross-assembly alone is not runtime parity.
- **Human craft/engagement/readability:** actual user/player feedback needed to accept enjoyment/spectacle. Produce representative reviewable operation footage/audio and concrete scenarios first; don't use automated pixel checks as that approval.

Section26 startup workflow is ongoing: canonical spec/instructions, preserved repo, isolated workers, source-frozen jobs and honest continuation points already exist. Its directive is sustained validated implementation, not acceptance from a plan or this ledger.

## Player-experience continuation supplement

The audit above retains its716bbd0baseline. The later1383caf continuation implements authoritative crouch/jump, strict startup resolution/FOV/sensitivity, and an actual CC0 recorded footstep starter bank. Scoped final acceptance evidence is recorded in docs/evidence/player-experience-session.json. These improve6a/6b/12/13/17/23 but do not complete them: vault, swap, remapping/persistence, full prediction/resimulation, complete audio categories/surfaces, Windows parity and dense-hotspot performance remain outstanding. No full-spec acceptance is inferred from this supplement.

## Dense encounter integration supplement

The later dense scenario continuation adds production modes2/3 and independently
checks living, physically target-valid regional ground actors in the preserved
8192army. Initial regional engagement reaches2560front/3837hotspot; later samples
fall and fluctuate, so this accepts an initial concentrated encounter, not a
sustained intelligent offensive. Exact evidence is recorded separately in
`docs/evidence/dense-encounter-session.json` after integration verification.

R03/§4 gain actual named dense paths and scoped CPU/GPU diagnostics. Frame peaks
measure submitted high/low/marker models, real projectile pools, cosmetic records
and audio voices. A separate count tracks positive projectile/effect/audio
co-occurrence in a frame. Peaks are independent; submissions do not prove visible
or individually detailed pixels. The required1024visible hotspot census,
four-rendered-client SCALE-NET, complete operation, native-thread budgets,
physical listening and human quality/playtesting are still not accepted.

Next renderer measurement must count depth-tested actor IDs from actual final
geometry at a specified frame/camera using a separate optional ID pass. It must
preserve authoritative state, normal geometry/LOD transforms, terrain/prop
occlusion and normal screenshot output; classify actual source/LOD detail, avoid
counting decorative geometry, exclude readback from the ordinary frame budget,
and record that additional pass cost separately. Frustum eligibility alone is
insufficient. The current mesh instance identity already contains stable actor ID,
side and role, so no shared entity/network layout change is needed.

## Pixel visibility supplement

The later optional final-frame census measures surviving opaque-depth actor IDs
and high/low/marker classes, with exact productionGL occlusion fixtures and an
independent raw attachment decoder. Source checkpoint10f76a5 hardware samples
count1859front/1545hotspot actors, of which1058/1003 are actual source meshes.
Zero invalid IDs and unchanged authority are required. A single sample, marker
visibility and a short hardware timing run do not accept sustained massive
operation, individually readable soldiers or human spectacle. Raw attachments,
per-actor sample thresholds and frozen verification are in
docs/evidence/visibility-session.json. The earlier missing census requirement is
closed for captured frames only; four-rendered-client and sustained-density
acceptance remain required.

## Observed explosive danger supplement

Runtime checkpoint `aed6e55` adds bounded prediction from actual flying artillery
and bombs, enemy-only current-projectile range/terrain-LOS observation, forty-tick
private evasion commitments, normal role-speed collision movement and read-only
local player warning estimates. Controlled production shell and bomb comparisons
start three infantry33m from the aim: disabled evasion kills all three; enabled
physical movement preserves100HP for each with the same actual impacttick41.
Replay, lifecycle and perception exclusions pass. Reachable actual wall shelter
selection and movement are tested; shelter survival advantage is not claimed.

This narrows the earlier gaps in10d/10e/10h/12g. It does not accept the complete
requirements: no named dense `artillery-storm`, grenade danger, incoming recording,
mutable destruction recovery, squad regroup/anti-armor planning, complete commander
or remote player warning path. Observation phases may delay response8ticks; each
cell retains only8threats and may omit others. Ground intercept estimates do not
predict all wall/actor collisions or narrow terrain crests. Exact integration and
scale evidence belongs in `docs/evidence/hazard-session.json` and `docs/status.md`.

## Ground ordnance fairness supplement

Runtime checkpoint `a9c7b99` introduces same-tick ready armor/artillery queues,
interleaves the four actual side/weapon groups and rotates successful participant
cursors. Priority ranks groups by stable physical source IDs, so changing faction
labels preserves physical processing order. The existing400-tick per-actor health
symmetry check caught the earlier side-index priority regression and remains
required. Ground weapons now use their actual30/90-tick cooldowns; infantry keeps
its8tick direct-damage phase. Same-tick generation/driver/ammunition/cooldown checks,
production trajectory/damage paths and416AI/480air/512physical ceilings remain.

Controlled real-world pressure proves the old fixed-index pass could give416
rounds to one side and none to the other despite equal physical eligibility.
Default admission gives208per side and104per side/role in saturated mixed cases.
Sustained physical comparisons include real impacts, losses and finite stores;
these initialized16k-ID fixtures have1024 living tank sources, and are distinct
from complete8192-living-army natural dense scenarios. Final frozen evidence and
limitations are recorded separately in `docs/evidence/ordnance-session.json`.

This improvesR05/10c/10e/15 but accepts no complete combined-arms or tactical
intelligence requirement. Ground fairness does not solve fixed-ID air release,
air-role contention, crowd avoidance, multi-weapon priorities or commander plans.
Pressure counters now count ready retries everytick and cannot be compared as
equivalent-cadence drop rates against the old eight-phase attempts.

## Aircraft admission supplement

Runtime `4e1b699` extends generation-safe real release admission to four aircraft
side/role groups while keeping continuous flight and genuine LOS/aim/bomb geometry.
Only actual success consumes finite ammunition and commits bomber egress. Controlled
production pressure gives240/240 side grants and120per side/role instead of480/0;
labels-only deployment mirrors preserve actual firing sources. Original32-slot
direct-weapon headroom and480air/512physical pool limits remain. Independent natural
finite-store accounting includes launches that retire between observed samples.

This improves bounded admission withinR05/10e/15 and preserves physical bombing/
interception portions ofR06/9/12. It does not accept full realism, wingman planning,
combined-arms priorities, crowd motion, audiovisual craft, complete operation,
four-client rendered massive warfare or hardware frame-budget requirements.
Ground and air ceilings remain total active-count policy; air lifetime/eligibility
can legitimately produce unequal natural grants and block ground weapons.
Exact integration/benchmark evidence belongs in docs/status.md and the aircraft
admission session manifest, separate from the worker baseline diagnosis.

## Physical ground steering supplement

Runtime `b9c71fa` introduces generation-safe immutable living ground snapshots,
role-sized body discs and bounded terrain-safe steering for actual nav/hazard
movement. Infantry/tank/artillery radii0.55/3.55/4.49m include both scale-one
vehicle mesh LOD bounds. Held allies and driven armor are indexed obstacles;
aircraft retain continuous independent flight. Local queries cap512 linked records
and ten candidate directions, with conservative yield on truncation and no heap
allocation. Exact coincidence uses actual goals and physical-ID priority derived
from already-hashed tick parity; partial overlaps require outward recovery.

This improves the bounded steering portions ofR05/10/15. It accepts no complete
intelligence, traffic or massive-battle collision requirement. Source role steps,
real terrain routes, fixed holds, relative swept body separation, eleven production
encounters and replay/physical label traces have focused proof. Original whole-world
tactics thresholds remain unchanged; unrestricted speed fixtures use physically
separated actors. Order-axis isolation disables avoidance only in its dedicated
simulation fixture, alongside its previous hazard isolation; fresh initialization
restores both defaults and preserves the original400tick health symmetry check.

Existing terrain centerpoint/slab collision is not an expanded vehicle hull test.
Separate human body/controller, driven-source avoidance, oriented hulls, initial
formation spacing and complex traffic recovery remain open. Dense initial layouts
include real overlaps; current-pose pair counts do not establish universally clear
relative sweeps. Above512 inspected records, movement may remain held. Final
source-matched frozen integration and CPU benchmarks are recorded in
`docs/evidence/crowd-session.json`; recorded failures retain the authored-body,
wall routing, coincident-intent and speed-fixture diagnoses. The complete game
specification and hardware/Windows/four-rendered-client gates remain unaccepted.

## Full-footprint static terrain supplement

Runtime `5da656d` adds separate role-aware body sweeps for actual army steering,
human planar motion, tank driving and deployment/boarding/exit occupancy. Ground
footprints0.55/3.55/4.49m gain1mm numerical inflation; static ground-solid boxes
are conservatively expanded and map centers inset. Every accepted full/component
step is swept; long goals and nearest-box/current-edge corners preserve actual
progress. LOS and projectile geometry remain distinct point paths. Policy enabled
state resets before game initialization and participates in replay hashing.

This narrows planar collision/navigation gaps withinR05/9/15; it does not accept
complete vehicle realism, strategic terrain or tactical intelligence. Independent
production assertions cover33 actual world/controller cases, non-deepening invalid-
start safe hold, body-safe arrival/progress, finite role speeds, exact replay and
army movement-label traces. Random double-oracle module checks and actual8k/16k
hotspot static sweep censuses provide separate scopes. Existing tactics thresholds
remain; the wall fixture now starts with clear authored-size hulls and checks full
body occupancy every tick. Route and infantry-cover margins are distinct. Direct human/tank controls use
collision-only steps, preserving requested axes and legal diagonal slides; AI
movement retains autonomous long-goal routing. New input-fidelity assertions
reject legacy unwanted steering rather than inferring correct controls from
geometric clearance alone. Map edge/corner component bounds also reject
free-axis amplification; original direction is normalized before endpoint clipping.

Expanded AABBs reject some circle-corner paths; shared max-role navigation edges
may omit narrow infantry/tank passages and rely on bounded local fallback. Initial-
invalid poses safely hold rather than universally recover. Five fixed solids,
planar footprints and limited real tank boarding do not accept oriented hulls,
vertical vault/slope physics, dynamic destruction/streaming, all-type deployment
reachability or player/driven interactor collision. Full frozen evidence and CPU
benchmarks belong to docs/evidence/terrain-body-session.json and docs/status.md.
The complete operation/game, Windows, four rendered clients and hardware quality
remain unaccepted.
