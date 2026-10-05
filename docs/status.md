# Status — Linux shared-world prototype,2026-10-05

The observed-danger continuation keeps the full specification goal active.
Runtime checkpoint `aed6e55` observes actual hostile artillery and bomb flight
within300m and terrain LOS, predicts bounded ground interception, and temporarily
interrupts ground orders for physical dispersion or reachable wall shelter.
Ground role speeds and swept terrain collision remain in force. The cache has
512records,8candidates/cell, an8tick observation phase, a1024LOS/tick budget and
40tick commitments. Goal state participates in deterministic replay; derived
caches, diagnostics and camera-dependent warning queries do not.

Actual production artillery and bomb comparisons each place three infantry33m
from the aim. Disabled evasion kills all three; enabled movement preserves100HP
for each, moving4.80m at0.12m/tick, with unchanged actual impacttick41. Repeated
runs match. Friendly/out-of-range/opaque-wall/nonexplosive and generation/boarding
exclusions pass. Actual wall shelter goals have clear travel paths and obstructed
blast LOS; physical movement is verified, without claiming shelter survival
advantage. The bomb test exercises the production launch primitive; it does not
prove the whole bomber FSM. The fixed-position hold/symmetry test explicitly
disables evasion as a negative control; the gameplay default remains enabled.

The independently counted controlled8192actor budget test hits exactly1024LOS
calls and896skips at five ticks. Production seed42/900tick headless results on
the i7-14700K are:

| Fixture | Starting actors | Tick mean/p95 ms | Acquired goals | Dispersion/shelter | Cell overflow attempts | Final active goals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| scale-hotspot |8192|3.996/7.011|11129|11128/1|83765|203|
| scale-stretch |16384|9.674/16.879|16985|16971/14|55455|1043|

These two jobs overlapped, use one simulation thread and do not measure graphics,
audio or replicated clients. Overflow counts are insert/replace attempts over
time, not unique lost shells. Bounded cell omission remains real. Projectile
launch refusals remain41901/126450 and navigation overflow466087/2666537, so
allocation fairness and crowded tactical quality are not established. Current
operation state stays0 after900ticks; no complete-operation claim follows.

Warnings are a compact bearing/ETA HUD cue sourced from read-only local hazard
queries. The actual GL paired production-launch fixture gives2284changed pixels
only within x461..818/y57..90 at1280x720. Enemy threat outputs bearing0.500005
and ETA0.433333s; the friendly control outputs zero. Both authoritative checksums
and tick counters stay unchanged. Paired screenshots were visually inspected. Co-op clients do not yet receive this private hazard cache. No incoming
sound recording is added. Estimates can differ from actual wall/actor impacts or
narrow terrain crests; no grenade danger, guaranteed escape/shelter, coordinated
regroup, destruction recovery or full commander behavior is accepted.

Frozen full extended checkpoint `c7edbd70ea56` passed in241.571489476s at
`0c979cb7db000a24b6f4dacd3a194a86dccf8e2b-46820edea2876254`, with50suite JSON
reports and137authored runtime/development/content inputs byte-matched to root.
All five root jobs are terminal and all four worker worktrees are clean. The
other snapshots retain identical47runtime inputs; their development test/driver
differences and added files are recorded explicitly. The failed98.36s attempt
omitted the new HUD module from a dependency assertion; the failed196.20s attempt
assumed hold prevented danger movement in an idle-animation fixture. Both logs
are retained, with exact test corrections and production enabled controls.
Focused core/steering/outcome/budget/HUD, tools and separate actual GL tests also
passed; all foreground sessions closed. Full checks preserve8k/16k motion/replay,
real GL bombing/dogfights/weather/meshes/effects/player input and death, local plus
two rendered co-op vehicle/player clients, and0/50/100/150ms UDP delay with jitter,
loss and reorder. Evidence and artifact hashes: `docs/evidence/hazard-session.json`.
Full-spec acceptance remains open; next useful combat work is causal weapon-pool
admission/fairness and physical crowd/combined-arms coordination.

The pixel-visibility continuation keeps the complete specification goal active.
Integrated checkpoint `10f76a5` adds optional final-frame `--census` and
`--census-map PATH.r32ui`. The actual geometry draw writes normal colour and a
separate integer actor-ID attachment with high/low/marker classes. Opaque terrain,
props, weapon and humans participate in depth occlusion; translucent effects and
HUD preserve the ID attachment. Eight independent production-GL fixtures verify
exact IDs/classes, offscreen/behind-camera/below-terrain exclusions, opaque bunker
and aircraft occlusion, empty army and human exclusion. Before/after authoritative
checksums and frozen authority bytes match. This caught and fixed distant marker
instances incorrectly using actor ID0. A normal/capture image pair differs by at
most2/255 per colour channel; byte-identical presentation is not claimed.

The bounded NASM reducer checks actual live entity IDs, deduplicates pixels and
rejects invalid/stale records. Actual GL framebuffer tests cover integer readback,
attachment masks, default-buffer restoration, write failures and zero GL errors.
Maximum CPU readback is33,177,600 bytes static storage plus32,768 class flags;
normal runs leave it untouched and allocate no census GPU resources. Capture
rejects changed authority, invalid pixels or GL errors. Strict CLI/report tests
reject unbounded/malformed/duplicate capture requests and mismatched metadata.

Actual ArcA770 600-frame1920x1080 seed42 final-frame counts are:

| Fixture | Source tick | Depth-visible actors | High models | Low models | Markers | High/low union |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| scale-front |100|1859|36|1022|801|1058|
| scale-hotspot |101|1545|54|949|542|1003|

Both raw R32UI files independently decode to these exact ID/class sets, with
matching hashes and zero invalid codes. Gzipped attachments and per-actor sample
counts are retained. At least one sample counts as depth visibility: only272
hotspot source models and297 front source models have at least16 pixel samples.
This measures geometry visibility, not smoke perception, individually readable
soldiers, art quality or sustained1024 visibility. The hotspot final frame
exceeds1024 visible actors when its542 markers are included;1003 actual source
models are visible. Earlier uncaptured reports remain unmeasured.

Front CPUmean/p95/p99 is5.580/8.531/10.180ms and hotspot5.582/7.807/8.852ms;
GPUdrawmean/p95/p99 is0.728/1.218/1.474ms front and0.805/0.847/1.548ms hotspot.
Readback/reduction costs15.310/16.632ms separately. Allocation occurs at startup;
final MRT drawing and the pre-draw checksum remain in the last CPU frame, while
readback, reduction, blit, file writing and reporting occur after its timer ends.
GPU timing can omit its last eight pending queries, including the capture draw.
The hardware runs overlap frozen verification, use one thread and null ALSA, and
have no excluded warmup. These short idle-view samples do not accept the complete
operation, sustained density, physical audio or reference hardware envelope.

Frozen full extended checkpoint `3b5ed1f86a51` passed232.06s at
`10f76a50321059f4fc04e33895520b8e13b1a864-47d5165615f186d7`. All126authored
inputs match this checkout and all three final frozen jobs byte-for-byte.
Its44JSONsuite reports retain8k/16k motion/replay, realGL source aircraft/weather/
animation/combat/player/vehicles, two-rendered-client movement/audio and UDP
0/50/100/150ms+jitter/loss/reorder coverage, plus the exact census tests. All
three root jobs, root focused checks and four clean isolated workers are
reconciled. Source inventory, actual attachments, independent decodes, the
reproduced marker alias failure and corrected oracle, timings and limits are in
`docs/evidence/visibility-session.json`. No publication
occurred; owner code-licence approval remains pending. Next work includes credible
ground hazard/crowd tactics and commander plans, projectile allocation fairness,
remote aircraft interpolation, four-rendered-client dense operation, full roster,
streaming/live jobs/reload and Windows parity. Historical results follow below.

Dense encounter continuation2026-10-05: full specification goal remains active and
unachieved. Integrated source checkpoint `a0d2a8c` adds distinct local
`scale-front`/`scale-hotspot` fixtures, strict Linux CLI/development forwarding,
independent real-combat oracles, read-only per-frame diagnostic reductions and
actual GL smoke. Every fixture retains8192 real entities,4096per side and the
unchanged role mix. Initial physical layouts concentrate2560/3840ground actors
plus64aircraft, with normal production targeting, movement, firing and damage.
The independent oracle counts2560/3837living regional attackers with living enemy
ground targets inside role range and terrain LOS at tick1. Later front samples
fall to2012/1849/1047 and hotspot to974/772/2182 at ticks8/16/30. These are initial
concentration fixtures, not sustained intelligent offensive acceptance.

Read-only battle diagnostics sample actual living/engaged/projectile counts,
submitted high/low/marker models, effects/trails and audio voices. Independent
peaks need not coincide; a separate frame counter requires positive projectile,
effect and voice counts together. Actual pixel-visible or individually detailed
actor counts remain unmeasured. The two real softwareGL120frame smoke runs use
no runtime pose/damage writes and observe actual combat, source geometry, trails,
impacts and recorded-bank routing. Physical audio and human craft remain unverified.

Seed42 900tick headless measurements on i7-14700K report frontmean/p95
3.218/4.245ms and hotspot2.882/4.016ms, alongside verification. Final living counts
are2713/1953front and2428/1519hotspot, with actual attrition reducing later load;
final engaged834/601. Projectile peak480 refuses42095/43121launch requests;
nav pending0, repeatedfallback510100/504115 and cover choices0. Hotspot's dense
bounded event ring loses53unobserved air events, front0; this is a measured limit.
Neither throughput average establishes a sustained initial-density budget.
A separate actual120tick pool census in docs/evidence/dense-projectile-pressure.json
checks both sides producing bombs/guns and shows unequal tank occupancy in some
samples. Target/loss differences and allocation ordering need causal tests before
claiming either fairness or an allocation defect.

ArcA770/Mesa26.2.3 actual600frame1920x1080 frontCPUmean/p95/p99
5.585/7.707/8.545ms and hotspot5.653/7.475/8.438ms. GPUdrawmean/p95/p99 is
0.691/0.729/1.423ms front and0.787/0.837/1.548ms hotspot. Both initial idle players
remain alive at their authored encounter positions; no shots or host input were
recorded. Hardware runs overlap independent verification; one thread, no excluded
warmup, and GPUtiming excludes presentation. Actual model submission peaks are
high70/low2777front andhigh87/low3950hotspot; these are not1024visible actor proof.
Effects64/trails128/voices128 saturate;583front/545hotspot frames have positive
projectile/effect/audio activity together. NullALSA verifies routing only.

Frozen full extended checkpointa87c322acfd7 passed224.83s at
`a0d2a8c756a638c695c6f5f3003352535890abf2-4ad0c46d5ba5dfef`. Its40JSONsuite
reports include existing8k/16k replay/motion, realGL aircraft/weather/source
animation/input/vehicle/death/redeploy, actual two-rendered-client movement/audio
and0/50/100/150ms+jitter/loss/reorder UDP coverage, plus independent dense
physical combat, realGL dense smoke and diagnostic/driver checks. All120authored
runtime/content/shader/schema/tool/test inputs match this checkout and each of
the five frozen job snapshots byte-for-byte. All five jobs passed, all four
clean isolated workers and rootPTY checks are reconciled. Exact checksums,
reports, artefact hashes and limits are in
`docs/evidence/dense-encounter-session.json`.
No remote publication in this continuation; code licence remains owner-pending.
Next ready work: actual depth-tested actor/detail census; complete dense four-client
operation; sparse remote aircraft interpolation; commander/hazard/crowd behavior;
weapon/vehicle roster; streamed world, live runtime jobs/reload and Windows parity.
Earlier paragraphs below retain historical evidence and scope.

The persistent full-game goal remains active and unachieved. The complete requirement ledger is now docs/spec-acceptance.md, coveringR01–R10, specificationsections3–25, named scenarios/commands and final acceptance gates. The current continuation implements authoritative crouch/jump, configurable Linux resolution/FOV/sensitivity and actual recorded footsteps; it does not close the full operation, Windows, streamed world, live reload, weapon roster, intelligence or human playtest requirements.

Ctrl crouch lowers eye to1.1m and moves2.5m/s, overriding sprint. Space triggers a grounded6m/s jump with9.8m/s² gravity, finite landing and held-key suppression. Private4x32motion state participates in replay, with generation/death/boarding resets and unchanged player64/entity32. UDPv6 acceptsbits32/64 across every layer and keeps1196byte packet cap. Genuine64actor dedicated/client movement test observes peak eye offset3.731m, exact grounded crouch and actual2.397m/s under sparse snapshots; no pose writes. Two rendered co-op clients exercise real Ctrl/Space and camera height, and verify landing plus15further server ticks while held. The one-tick visual XZ preview now preserves serverY and respects crouch speed; full timestamped input resimulation remains pending.

Startup `--width/--height/--fov/--sensitivity` supports320..3840x240..2160, verticalFOV35..110 and0.00001..0.05radians/pixel. Default projection1.05/1.87 remains bit-identical. Strict kernel/CLI checks reject23malformed/duplicate/missing cases; actual GL verifies1280x720,1920x1080,800x600 and tactical1080p, dynamic PPM readback, and FOV45/90 aircraft sizes3496/590pixels with unchanged authority. Runtime is NASM plus GLSL; settings persistence, remapping, resize/HiDPI and Windows remain pending. Maximum screenshot buffer is24,883,200bytes staticBSS; default readback touches2,764,800bytes.

A CC0 GboxMikeFozzy actual subway-walking recording supplies7,388mono48k footstep samples in mixerbank2, sharing128voices with rifle/explosion. Grounded displacement yields17footfalls over32m at30/60/120Hz, with actual airborne/dead/boarded/stationary/reuse/teleport silence and network pose fallback. Real rendered co-op walking crosses the stride and routes this bank. Source, license, derivative hashes and credits are pinned; one hard-surface sound is not the complete terrain-specific audio pack, and null-device tests do not prove audible quality. The explosion remains a recorded log-drum/reverb surrogate.

Frozen full extended checkpoint6e225ce2d1d1 passed209.43s at1383cafbd170880942e4bcd3258186a14d3b58dc-897c954891888a05. All115authored inputs match the checkout and all three final benchmark snapshots exactly. It preserves8k/16k replay/motion, real GL aircraft/weather/animation/shell/effects/input, local and two-client ground armor, death/redeployment and0/50/100/150ms+jitter/loss/reorder UDP faults, plus the new movement/view/audio checks. All7root background jobs and four clean isolated workers are reconciled. Retained failures identify the stale startup diagnostic/printf arguments and a test incorrectly querying a graphical-only counter in the standalone adapter. Live probes also caught and fixed the dedicated input-mask rejection and standing-height camera preview. Exact evidence, hashes, job ledger, limitations and continuation queue are in docs/evidence/player-experience-session.json. No publication occurred; code licence still awaits owner approval.

Final900tick seed42 i7-14700K headless mean/p95 is3.730/4.396ms at8192 and7.747/8.721ms at16384, concurrently with verification. Army encounters retain68/62/4950/168 and58/48/9691/352actual air events. ArcA770 actual1200frame1920x1080 scale-open diagnostic reports CPUmean5.833,p958.909,p9910.018ms and GPUdrawmean0.694,p951.406,p992.324ms. The player actually died/redeployed during this brief scene; final mesh telemetryhigh0/low0/markers7563 is not a visible-detail census. This meets the tested view's timing targets only, not complete-operation or dense-front/hotspot acceptance. SCALE-FRONT/HOTSPOT, four-rendered-client operation, native-thread budget, streamed hierarchy and physical audio/human pacing evidence remain required.

The2026-10-05 air-spectacle continuation integrates CC0 F-111 tactical bomber and Eurofighter meshes, real surviving-damage defensive flight, pose-driven engine/damage trails, richer actual bomb/destruction effects and UDPv5 moving-projectile cosmetics. `python3 tools/dev.py run --client --scenario air-battle` starts the full8,192army with an initial320actor encounter in front of the player. No recording-time shots, damage or events are injected. Its300tick deterministic replay records65bomb releases,61impacts,2,590air gun bursts and84aircraft destructions across the full operation. A12second silent real-client recording is retained at runs/air-battle-demo-final.mp4, with authentic captures and source/license evidence in docs/evidence/air-spectacle-*.

Production damage now invokes bounded fighter jink/climb and bomber abort/egress; repeated hits cannot renew commitments. The128slot cosmetic trail pool is generation-validated, capped and deduplicated by actual simulation tick. Paired actual GL draws preserve authority and change24trail pixels,2,043bomb-impact pixels and409destruction pixels. UDPv5 sends up to18actual projectile records per10Hz snapshot, with1196byte maximum packets; separate512slot cosmetic prediction cannot apply damage.21malformed trajectory cases, genuine delayed bomb damage/tombstones and authentic loss/reorder/duplicate replay pass. The final rendered co-op probe observes4repeatable shell pixels at the projected real sample, comparing visible/hidden/restored draws with unchanged authority.

Frozen full extended checkpoint3f7287450497 passed188.83seconds atc2642ebb5493d1c2b406c6f16134f2ba464edc6a-49aa6aa9a54c001c. All104authored runtime/content/schema/shader/tool/test inputs match the checkout byte-for-byte. It retains8k/16k army replay/motion, actualGL aircraft/weather/source animation/shell/effects/input, local and two-client vehicle control, death/redeployment and0/50/100/150ms+jitter/loss/reorder UDP coverage. All10root background jobs and four isolated workers are reconciled. Retained failures diagnose a stale test content hash, omitted new include consumers and an arbitrary one-pixel shell cutoff; the corrected test checks restored visibility at the projected authority position. Exact results, hashes, failures, worker commits and limits are in docs/evidence/air-spectacle-session.json. No remote publication occurred; code licence remains pending owner approval.

Final900tick seed42 headless mean/p95 timings are3.780/4.352ms for8192 and7.689/8.745ms for16384, alongside verification on i7-14700K. Actual air events are68/62/4950/168 and58/48/9691/352 respectively (bombs/impacts/gun bursts/destructions), with zero overwritten unobserved events. Both navigation queues drain, but repeated initial fallback calls remain526679/2810427 and cover choices are0. Projectile peak480 refuses46138/133572launch requests. All57runtime/content/shader/schema files match final scale and hardware snapshots. ArcA7701200frame1280x720 air-battle diagnostic reports CPUmean5.831,p959.370,p9911.608ms and GPUdrawmean0.323,p950.349,p990.862ms; actual host input moved the camera and fired10rifle shots. This is not a controlled stationary comparison or dense-front1080p acceptance.

Remaining limits: bounded kinematic flight, static F-111 tactical-bomber wings/gear, no incoming-projectile perception/wingman coordination/landing/rearm; sparse network poses can jump and10Hz sampling can miss short-lived rounds. Cosmetic smoke/debris does not block LOS or collide. Full human spectacle, reference massive-battle GPU budgets, physical audio quality, dynamic ground solids/crowd avoidance and streamed navigation remain unaccepted. Earlier paragraphs below retain historical checkpoints and superseded surrogate/network descriptions.

The2026-10-05 aircraft/navigation continuation adds generation-validated64byte aircraft state, continuous150m/s bomber and210m/s fighter flight with bounded turning/climb/bank, actual gravity bombing/egress and fighter interception/swept gun damage. Stores are finite; depletion returns aircraft without invented rearm/landing. Ground occupation excludes overhead aircraft. Actual altitude reaches player/combat queries and every rendering distance; UDPv4 carries independent entity+pose updates at180air records/s,1196byte maximum. Real authority fixtures produce bomb launch/impact and fighter fire/destruction cosmetics; the two-bank128voice mixer routes real battle events with bounded dedup. Model art remains the existing Kenney winged space-craft surrogate; the explosion recording is a CC0 log-drum/reverb surrogate and air guns use the rifle bank. This is bounded kinematic flight and prototype feedback, not a complete realistic flight simulator or polished spectacle.

Ground movement now uses squad visibility corridors around the five physical static boxes followed by swept local steering. Direct scouts and flanking support retain independent caches. Eight requests/tick and512FIFO capacity remain bounded; overflow retries use local steering. Two integrated armor replays physically arrive around bunker/wall in8428ticks with identical checksums. Infantry shelter is proven by actual acquired-target LOS, reachable movement, blocked LOS at the shelter, target-loss commitment and manual cancellation. Default900tick scenarios select zero shelters, so broad tactical cover use is not established. Streamed regional hierarchy, slopes, dynamic solids and crowd avoidance remain pending.

Final900tick seed42 benchmarks report mean/p953.661/4.227ms for8192 and7.717/8.812ms for16384. Aircraft events are70bomb releases/63impacts/5134gun launches/179destructions and41/37/9763/370 respectively, with zero overwritten unobserved events. Both navigation queues drain to zero after2025/4026builds, but initial overload produces529422/2801230 repeated actor fallback/retry calls. Projectile peak480 refuses48174/132871launch requests. These are headless single-thread measurements alongside verification, not rendered/replicated budgets. Actual ArcA770600frame initial-view1280x720 diagnostic reports CPUmean6.939,p957.611,p998.252ms and GPUdrawmean0.479,p950.511,p990.748ms; it does not establish dense-front1080p acceptance. Exact reports and retained screenshots are in docs/evidence/air-navigation-* and docs/evidence/aircraft-*.png.

Frozen full extended checkpoint337dc75f48ab passed166.62seconds at0aa1e5c112262e48812589c54f16ae5530f24fd1-2dd0b9232e31b986. All97authored inputs match the current checkout byte-for-byte, and all runtime/shader/content/schema inputs match the final scale/GPU benchmark snapshots (later changes only correct development tests). The checkpoint retains8k/16k replay/motion, actual GL aircraft pose/ordnance/events, weather/source animation/shells/effects/input, local and two-client ground-vehicle controls, death/redeployment and0/50/100/150ms+jitter/loss/reorder UDP coverage. Dedicated-server evidence includes3240air records/180ticks,1195actual X/Z refreshes and47malformed whole-packet cases. Earlier full job72e4abb0fec6 also passed166.25seconds; two failed checkpoints and one explicitly cancelled unresolved-merge snapshot are retained with diagnoses. Input testing now starts at the allied base with full army/HP/ammo preserved and asserts unchanged player generation and actual W displacement. Source-animation comparisons wait for presented frames and separated real animation phases. All14root background jobs and five isolated workers are reconciled; no publication occurred. Exact hashes, reports, failures, limits and authentic screenshots are in docs/evidence/air-navigation-session.json.

Continuation on2026-10-05 uses an Intel i7-14700K/ArcA770 host (Nobara44/kernel7.2.3,Mesa26.2.3,NASM2.16.03), rather than the older laptop measurements below. Nearest-obstruction steering and swept ground movement/slide checks now prevent the reproduced bunker crossing. The independent terrain oracle passes1997 seeded queries and64973 route steps at actual infantry/artillery/armor step sizes plus large API stress steps. Original assembly fails the reproduced crossing; a separate sweep-removal control crosses a wall even with nearest-obstacle steering. Default600tick seed1 checksums are unchanged by the correction in paired baseline/stretch runs. Concurrent headless benchmarks report p953.383/6.540ms for8192/16384 actors, rendering/replicating zero; paired sequential runs during extended verification show about3–5% higher mean tick cost. These do not establish GPU budgets.

The initial full checkpoint0127cce3a666 exposed a weather fixture comparing playerHP while real enemy attacks continued (70→50). Its simulation scheduling freeze now precedes actual F4 input, with explicit tick preservation; cosmetic weather still transitions until the later paired-render freeze. The corrected focused weather test passes. Full frozen rerunfa24ffc6de29 passed126.69seconds at e60a16b51246f88d0eb5cf63a59354038480f1d8-83c907baf5791512, retaining8k/16k replay/motion, actualGL weather/animation/shell/impact/input, two rendered co-op clients, death/redeployment and the0/50/100/150ms+jitter/loss/reorder UDP matrix. Final fast and focused terrain/weather checks pass; all jobs are reconciled. Exact source hashes, both negative controls, scale reports, suite outcomes and the failed checkpoint are retained in docs/evidence/navigation-session.json. Hierarchical navigation, slope limits, dynamic obstacles and unit collision remain pending.

The game specification and milestones remain incomplete. Current CPU runtime is NASM x86-64, shaders are GLSL, and Python/shell are development/test tools. Hardware for local evidence: Intel i7-1355U/IrisXe, Mesa26.2.3, Nobara44/kernel7.2.6, NASM2.16.03/GCC16.2.1. Code licence remains pending owner approval.

Four real Poly Haven grass/mud/gravel/rock diffuse sources now produce a4,194,336byte terrain texture array with original and derived hashes, documented CC0 grants and voluntary credits. World-coordinate materials blend across grass patches, corridors, objectives and slopes. Clear/overcast/rain/fog presets share sky/cloud lighting, wet ground and distance fog;512 bounded world-space falling streaks remain visible across camera directions. F4 cycles smoothly; `--weather` selects startup. Weather is client cosmetic only. Runtime loading/controls/state are NASM; conversion is offline. See docs/textures.md and docs/environment-renderer.md.

Full frozen extended jobd87a7d59c26e passed143.80seconds atd5ff5f90c69dc1d46b7edb264143de16a5a60be8-271d816ac59cc0e7 with DISPLAY/WAYLAND_DISPLAY removed. All previous8k/16k scale/replay/motion, flight, source animation, combat/vehicle, two rendered co-op clients and UDPfault coverage is retained. New checks reject13 malformed/missing texture packs, render all presets, exercise actual F4 without changing player authority, and compare actual rain at two clock phases in forward/side views. The impact fixture now distinguishes23 actual acquired flash pixels from170965 brown terrain pixels using an identical frozen scene with only acquired cosmetics hidden; authority remains byte-identical and effects restore intact. A negative control correctly fails with0 changed pixels. All worker jobs and the full checkpoint are reconciled; exact outcomes/source comparison and authentic screenshots are in docs/evidence/environment-session.json. Diffuse-only textures and prototype cosmetic clouds/rain do not establish production PBR, weather gameplay, rain audio or reference-GPU performance.

The previous playtest batch fixes full-XYZ tank-shell speed, integer/discrete artillery flight time, aircraft altitude aiming, and the shell renderer reading DAMAGE instead of ACTIVE (spent shells remained visible). Rendered shell orientation now follows velocity. Autonomous support approaches while scouts survey, uses brief target-acquired firing dwells and keeps explicit advance moving. Default8192/16384 tests cover all six fronts, player bubbles and wall recovery; more than95% of living ground actors move at the checkpoints, versus about6.5% before. See docs/combat.md and docs/tactics.md.

Eight actual downloaded model sources now produce a11,328,032byte RHAM pack with16 high/low meshes and22clips. Soldier Idle/Walk/Run_Gun/Idle_Shoot and both tanks' forward actions are authored animation, baked offline; the assembly renderer loads and interpolates source geometry/material colors. Actual models cover human/army bodies, armor/artillery/air roles, rifle, fortifications, trees and buildings. Bounded nearby detail,800m simplified models and far markers preserve the army. Model sources, licenses, hashes, exact substitutions and reproducible tooling are in content/model-sources.json, content/asset-manifest.json and docs/models.md; runtime evidence is in docs/mesh-renderer.md. No Python or Blender executes in the game.

Full frozen extended jobaf800b6d2a47 passed in128.92seconds atfa1c4ba4a5e7fc0be686cfaf32d32ae0075b1a5b-89ff816e83dc8f78 with desktop display variables removed. It includes8192/16384 replay/scale, default strategic movement,24 cannon angles, real shell flight/contact, recorded stereo audio,23 malformed model packs, realGL idle/walk deformation and stationary tracks, expired-shell cleanup/orientation, actual delayed AI impact pixels, local E/drive/cannon/Q, player death/redeploy, two rendered co-op clients and the0/50/100/150ms+10msjitter+5%loss/reorder UDP matrix. The first checkpoint exposed an effects fixture competing with the now-active480-shell AI pool and standing inside enemy threat; that fixture was isolated without manufacturing projectiles/events. Both checkpoint jobs and all worker processes are reconciled. Exact reports, the failure diagnosis and current source fingerprint are in docs/evidence/feedback-session.json. The preview is actual software-rendered game output, not a target-hardware performance claim.

Current integrated headless600tick seed1 throughput is mean3.799/p954.026ms for8192 and8.186/9.008ms for16384, alongside active verification. These runs render/replicate zero actors. Active approach increases shell pressure:480peak with35031/90988 refusedAI launch requests. Capacity, sampled collision, missing network shell trajectories, reference-GPU performance, production navigation and human pacing remain limits.

The earlier combat batch adds exclusive allied armor boarding/driving/cannon/exit with generation cleanup and crew recovery;512 pooled moving tank/artillery shells, swept actor/terrain/solid contact, enemy-only physical blasts and32 slots reserved for human cannons;64 pooled cosmetic rifle tracers and aged impact flash/smoke;128 stereo recorded rifle voices with listener-relative panning, distance culling and remote-shot routing. Authoritative player/entity layouts remain unchanged. UDPv3 appends vehicle ownership and bounded nearby cosmetic events, with whole-packet validation and no client damage claims. Focused actual assembly, local GUI and UDP tests pass; two actual rendered network clients also pass E/drive/cannon/Q control. Full frozen integration job1ee7970cae70 passed in102.73seconds atfb92e5d-d1fa008a94434586 with DISPLAY/WAYLAND_DISPLAY removed. This includes8192/16384 replay/scale, physical shells/vehicles,15 malformed event/ownership fixtures, actual UDP board/drive/fire/exit, recorded stereo routing, real GL tracer/impact/HUD pixels, two rendered network clients, death/redeployment and the0/50/100/150ms fault matrix. All batch jobs are reconciled; exact evidence is in docs/evidence/combat-session.json. See docs/combat.md, docs/vehicles.md, docs/effects.md and docs/audio.md.

The shared authoritative world now includes8192/16384 living entities, four primitive unit roles, three fronts, bounded spatial candidates and deferred damage; twelve physical capture sites, contested occupation, connected supply/requisition and operation outcomes; shared analytic terrain, five solid wall/bunker volumes, physical LOS and bounded detours; observation-based scouting, alternating flank groups, supply/observed-strength withdrawal and explicit player command overrides. Controller tests prove physical movement, defender defeat and capture, rather than only state labels. See docs/tactics.md for the tested obstacle envelope and AI limits.

Four authoritative player records provide fixed30Hz movement/collision,30round rifles,4tick firing cooldown,60tick reload, LOS-filtered enemy damage, suppression, death and safe connected deployment. The local graphical client submits intent and reads authority; its private movement/weapon/damage simulation was removed. HUD, camera smoothing and shot/hit/audio feedback follow actual records. Shared terrain and obstacle geometry are rendered alongside individual army instances. Actual XTest/private-Xvfb tests verify movement, magazine exhaustion/reload blocking, rifle hit feedback, enemy damage, suppression, death and successful redeployment. See docs/player.md and docs/client-v2.md.

A dedicated assembly UDP server advances this same world at30Hz. It assigns four endpoint-bound player slots, validates movement/aim/buttons, checks front ownership, charges orders once, recovers disconnected slots and publishes player/site/resource state plus bounded nearby entity chunks at10Hz. The actual assembly client adapter applies snapshots without ticking a local world. Four-peer and real-adapter tests pass with8192 authoritative units, lost-ACK retries, malformed/oversized/reordered commands, generation changes and timeout recovery. Packets stay below1200bytes. Entity replication cycles at most640records/s per client; dense regions update sparsely and offscreen army intelligence is absent. This is not full-army-per-frame replication or authenticated internet matchmaking. See docs/coop.md.

Other retained paths:128voice recorded rifle PCM/ALSA mixer; standalone validated compatible-module/parameter reload proof; standalone UDP ownership proof; incremental assembly/link, immutable binary revisions, frozen-source background jobs and Linux packaging with asset hashes/credits. Live client/server hot reload and asynchronous runtime jobs remain unimplemented. The rifle recording is an attributed CC-BY-3.0 archive derivative; it is not a full audiovisual pack.

Evidence is tracked by exact source revision/hash, job results and machine-readable reports under docs/evidence and ignored runs/. Current integrated CPU-only job1b3efc8d201b passed in33.40seconds at e74e521-4cfa80c091cb05ea, including simulation/replay, operation, waypoints, terrain, tactics, players,19reload cases,16audio groups,45proof datagrams, actual co-op/adapter tests, build-tool freezing and asset checks. Earlier local client graphics jobcef4b1aa5363 passed in27.23seconds at d164e21-2cdaaeb3ad123b4e. Final combined job2699ac0fcf9c passed the full extended suite in97.79seconds at1f5ab89-cbed3b1751d43e0f with DISPLAY/WAYLAND_DISPLAY removed. It includes real local gameplay, two rendered co-op clients,18/24 remote-player pixels, ACK rejection rollback, paused-server authority freeze, solid-goal rejection without spending, real network death/redeployment and the four-delay UDP fault matrix. Exact outcomes, all reconciled job IDs and the verified local package are in docs/evidence/shared-world-session.json.

Fresh worker throughput evidence with terrain/controller/player, seed1/600ticks:8192 alive3705/3611, engaged41, checksumff32c15dc7b98404, p954.79ms;16384 alive7357/7225, engaged33, checksum6417afdf9222e1b4, p9512.63ms. These are headless single-thread wall timings, not GPU budgets or human pacing acceptance. Scouting/staging and cover reduce early engagement. Root sequential benchmarks at87dff5f-b58ed67d9863f39a report p955.81/14.28ms and peakRSS2556/2736KiB; their exact JSON and active-development timing context are in docs/evidence/terrain-tactics-scale-{open,stretch}.json. Headless benchmark runs render and replicate zero actors; network measurements are separate. No allocation calls exist in authored simulation passes by source audit; process-wide allocation counts remain unmeasured.

The public repository is https://github.com/admiraly/red-horizon . GitHub authentication has repo/workflow scope. Baseline remote Actions run37305579434 passed all steps. The retained workflow uses pinned actions and Ubuntu24.04, runs the complete suite and baseline/stretch benchmarks, and uploads evidence. Subsequent integrated publication/check results are recorded with their exact SHA.

Remaining acceptance: human weapon feel and strategic pacing, reference GPU budgets, robust hierarchical navigation/cover selection, remaining vehicle types, production projectiles/VFX, broader layered recorded sounds and art, streamed8km operation, Windows parity, complete operation/recovery, broad remote-network latency/loss coverage and live host reload. None is inferred from file presence, software screenshots or null-device audio. docs/task-board.md records the ready queue; reconcile every launched job before handoff.

Development iteration now uses an explicit fast suite and focused operation/waypoints/terrain/player/tactics checks. Measured atf9e0122-4c5bc06e7799c120: fast0.54–0.60seconds, player0.15seconds, warm build0.048seconds with zero reassembly. NASM transitive includes/incbins and compiler/flags control object invalidation; shader changes affect one renderer object, nested headers affect only users. Objects-only builds support assembly checks without graphics linking. Tooling checks verify source preservation and retained valid outputs after failure. Full extended frozen jobfc32437a65c6 passed in94.62seconds, including scale, real graphical co-op and the UDP fault matrix. That earlier tooling-only batch changed no game runtime source. Exact timing/coverage context: docs/evidence/development-loop.json. Full verification remains required at integration/publication checkpoints and runs in the background while independent work continues.

Current combat-scale evidence is in docs/evidence/combat-scale-{open,stretch}.json. Runs use600ticks and seed1, alongside active full verification and the other scale benchmark. The512-shell pool remains bounded; AI launches saturate at480, retain32 human slots and report refused launch requests. Saturation is a visible gameplay limitation, not a claim that all requested army shots fire. Crowd sampling can miss bodies/blast victims; network clients receive impact events but not moving shell trajectories. Reference GPU performance, physical audio listening, broader recorded layers, armor-facing damage, wreck cover and human pacing remain unverified.
