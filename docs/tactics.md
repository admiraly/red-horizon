# Terrain and tactics implementation evidence

## Shared terrain slice

`src/nav/terrain.asm` provides the ABI in `docs/next-contracts.md`. The authoritative SSE2 height is `12 + (x-4000)^2*0.000001 + (z-4000)^2*0.0000005 + max(0,1-abs(x-4000)/800)*18`, in metres. The client shader must use this same expression; matching source equations do not establish bit-identical CPU/GPU results.

Five fixed 32-byte obstacle records are exported as `terrain_obstacles`, with `terrain_obstacle_count=5`. They contain three central wall spans and two bunkers; bounds/base/height are physical and shared with rendering. Initial seeded ground spawns do not overlap any solid. Aircraft bypass ground solids, but remain subject to physical ray occlusion.

`terrain_los` sweeps each obstacle using a three-axis segment/AABB slab test, and additionally checks seven interior analytic-ground samples. Thin authored walls cannot be tunneled by the ray. Ground sampling is bounded rather than an exact continuous intersection proof for arbitrary long rays. Ground actors target at terrain height+2 m; aircraft add 90 m. These queries now gate actual army target selection and therefore damage.

`terrain_move` checks the segment toward the destination against all five solid boxes and selects the nearest intersecting obstacle by its slab entry fraction. For a blocked corridor it selects an outside corner four metres from the obstacle edge, progresses along that edge, then resumes the goal. Movement is capped by the requested step and clamps map coordinates. The proposed movement segment is swept against every solid before acceptance; both component-slide fallbacks receive the same sweep. Clear endpoints alone cannot authorize movement through a bunker or wall. This bounded local corridor steering is integrated into actual advance and retreat. It is not a global path search or a proof that every arrangement of obstacles is navigable; the authored isolated rectangles are the tested envelope. No terrain slope constraints, unit-unit collision, dynamic destruction or navigation rebakes exist.

All functions preserve SysV nonvolatile registers, use caller-saved integer/SSE scratch, and allocate no memory. Query inputs are finite world coordinates supplied by validated simulation/player state. `terrain_move` returns x/z in XMM0/XMM1, so `tests/terrain_probe.asm` is a development-only return-value bridge for ctypes; it is not gameplay logic.

`tests/test_terrain.py` passes formula samples, ground blocking and aircraft bypass, exact wall occlusion/elevated clear rays, bounded corner detour without overlap, an actual world fixture where hidden opponents acquire no targets and take no damage, actual army detour/arrival after 1200 ticks, and all 32768 initial spawns outside solids. Existing simulation, operation and waypoint suites pass with the real terrain module linked. Player integration and strategic/squad behavior are a separate pending slice; no stub player or AI implementation was used for these claims.

Fresh terrain-integrated throughput evidence on Intel i7-1355U, seed 1, 600 ticks: 8192 units alive3291/3267, engaged667, checksum98dcd0a3b52ac857, mean4.042290ms/p954.339853ms; 16384 units alive6600/6549, engaged1439, checksum9bc327084a1b2ae0, mean8.267412ms/p959.150734ms. Timings include authoritative solid/ground LOS queries; no GPU/network/player-loop performance claim.

## Autonomous formations and bounded observations

`src/ai/tactics.asm` adds six 64-byte controller records (`ai_fronts`, side*3+front). Fields by byte offset: own weighted strength0, currently observed opposing strength4, observation tick8, confidence0–100 at12, intent16 (0 reconnaissance approach,1 surveyed approach,2 withdraw), selected site20, explicit override24, reserved28, last observed enemy x/z32/36, reserved40, objective x/z44/48, visible scout survey52, retreat commitment ticks56, reserved60. Weights are infantry1/armour4/artillery2/aircraft2. These are simple prototype utility weights, not intelligence estimates of the entire hidden army.

The controller evaluates every 30 ticks. It scans living own entities and only copies enemy data from their previously acquired, physically visible authoritative targets. A fixed entity-ID bitmask deduplicates observed targets per front. It never scans hidden opposing coordinates for strategic strength or goals. Last observations carry a timestamp, decay to confidence0 over 300 ticks, and are retained for diagnostics. Decisions currently react to fresh observed strength, not extrapolated stale coordinates. Own supply below 100 capacity triggers withdrawal; observed strength greater than twice own strength also triggers withdrawal with 90 ticks of commitment. There are no hidden reinforcements.

The authored front's next hostile middle site, then command site, supplies a strategic objective. Designated scouts (stable index divisible by 16) and aircraft lead directly toward the objective. Support squads immediately advance along opposite flank corridors, including while the distant site has not been surveyed. A living scout physically reaching within 200 metres with LOS records survey completion; aircraft survey from their actual terrain + 90 m altitude. The survey changes reconnaissance diagnostics, not permission to move. This avoids an indefinite gate if scouts die before reaching the far depot. Target selection and shooting continue to require actual LOS; the controller cannot grant hidden hits.

Stable groups of 16 IDs use opposing ±600m flank corridors until within 500m in x of their site, then converge onto its physical capture area. Actors with an actually acquired target take a twelve-tick firing dwell per 120-tick cycle; the opposite squad's dwell is offset by sixty ticks. With no acquired target, both squads keep approaching. Scouting and support therefore continue physically rather than waiting for a hidden remote-site condition. Solid detours respect the chosen corridor's side. Terrain movement tries bounded component slides when a resulting local step is blocked, then holds safely if neither component is reachable. This is tested local recovery and authored corridor coordination, not hierarchical navigation, tactical cover selection or a universal stuck-solving guarantee.

Successful `sim_order` or `sim_waypoint` explicitly overrides AI for that side/front until the next world initialization. Explicit advance now continues physically toward the waypoint while fighting; explicit hold and retreat retain their previous meaning. Thus autonomous allied orders cannot overwrite a player's front command. Invalid calls do not override. Mixed-formation goals inside ground solids are rejected before goal/override mutation; the co-op server performs the same check before charging requisition. There is currently no separate return-to-AI command. AI state is included in replay hashing; scratch observation masks are rebuilt and need not persist. Player initialization/tick/hash use the actual root `src/game/player.asm` from commit 0590eeb; no stub implementation is linked.

`tests/test_tactics.py` verifies outcomes over real world ticks: support moves while a hidden wall-separated site is scouted without acquiring hidden enemy knowledge; the scout detours, kills a physical defender and captures its site; opposite squads approach on opposite flank corridors, and acquired targets permit short alternating dwells; observed armoured superiority causes infantry positions to retreat; disconnected capacity causes withdrawal; a player front hold keeps position; and repeat fixtures yield identical checksums. Additional full default seed42 runs validate all six fronts at8192 and16384 units, including a joined player's initial front1 ground bubble, with repeated8192 replay checksums. At30 ticks at least95% of living ground actors must move>1m per front; at120/300 at least95% must move>5m, and at300 at least90% must advance>10m along their side's strategic x direction. Checkpoints also verify no ground solid overlaps. A real-world1200-tick scout/support armour wall-face fixture verifies both cross the wall, every step stays<=0.501m and no step overlaps a solid. The waypoint suite additionally verifies explicit advance keeps moving while its acquired target survives. These tests change the previous intentionally staged movement expectation to the user-requested active approach; ABI and role speeds remain unchanged.

Default seed42 play diagnosis and correction (joined idle player0/front1, no player input):

|Ticks|Prior mean living ground displacement per front|Corrected8192 mean range|Corrected16384 mean range|Moving ground in8192 player bubble|
|---|---|---|---|---|
|30|0.237–0.243m|5.061–5.104m|5.063–5.103m|417/417 (prior31/410)|
|120|0.923–0.986m|20.368–20.553m|20.348–20.456m|427/427 (prior32/404)|
|300|2.148–2.357m|50.833–51.580m|50.276–51.034m|466/466 (prior32/399)|

Previously all six fronts remained scout/stage and about93% of living ground actors stayed stationary for the full ten seconds. Front1 aircraft died before surveying the opposing depot (none alive by300 ticks); the old gate therefore never released its support. The correction changes movement permission without accelerating fixed30Hz speeds: infantry3.6m/s, armour15m/s, artillery6m/s and aircraft150m/s remain tested. Full default checkpoint measurements establish simulation motion, not animated rendering, compelling tactics or a safe idle player (the idle player's HP still reaches10 at300 ticks). There is no new global pathfinding, cover evaluation, unit-unit collision or survival planning for aircraft.

Historical pre-correction integrated terrain/controller/player throughput evidence, seed 1, 600 ticks on Intel i7-1355U:

|Units|Living allied/enemy|Engaged at final tick|Checksum|Mean tick ms|p95 tick ms|
|---|---|---|---|---|---|
|8192|3705/3611|41|ff32c15dc7b98404|4.134853|4.792126|
|16384|7357/7225|33|6417afdf9222e1b4|8.631333|12.631920|

Both twenty-second runs remain ongoing, with 600/600 connected capacity and 880/460 requisition. Reduced engagement relative to advance-only fixtures reflects autonomous staging/reconnaissance and physical wall occlusion; these figures do not claim compelling pacing. Full simulation/replay, operation, waypoint, terrain, tactics and real root player suites pass. The wall-edge recovery fixture allows 1 mm displacement tolerance for float32 rounding at kilometre coordinates. No GPU/client fun, remote transport, hierarchical navigation, robust strategic planning or complete operation acceptance is inferred from these tests.


Corrected standalone headless600-tick seed42 benchmarks on Intel i7-1355U (no joined player, renderer or transport), after the fast gate:

|Units|Living allied/enemy|Engaged|Checksum|Mean tick ms|p95 tick ms|
|---|---|---|---|---|---|
|8192|3361/3116|912|d7bc794e5477e888|3.537910|3.755610|
|16384|6805/6336|2369|f316683e91ab326a|7.207610|7.912303|

Both operations remain ongoing with capacity600/600 and requisition880/460. Moving support increases physical engagement and shell-pool pressure: the existing480-slot AI ceiling is reached, with25865/79005 rejected AI shell requests respectively; the32-slot direct/player reserve remains intact. These are headless measurements of this movement commit's existing projectile module, not the separately developed projectile correction or asset renderer. The corresponding development reports are `runs/bench-e276673d36.json` and `runs/bench-5287c81a48.json` in the worker checkout; reports are ignored build evidence, not committed runtime assets.

## Nearest obstruction and swept movement regression

The prior table-order detour selected central wall record0 before nearer bunker record3 for start(5243.89013671875,1564.114990234375), goal(3125.11279296875,5204.44287109375), and a1000m query step. Its endpoint(4808.64111328125,2464.42529296875) was clear but the movement segment crossed the bunker. The corrected query first reaches the bunker corner(5234,1604). A development-only build of the original terrain assembly fails the new independent segment/rectangle oracle at this exact crossing. The1000m step is an API stress fixture; normal army steps remain0.12/0.2/0.5m at30Hz.

The terrain suite checks1997 seeded clear-start cases with steps0.12/0.5/1000/8000m, entire movement segments against an independent double-precision rectangle oracle, and actual arrival along the bunker/wall route at0.12/0.2/0.5/1000m steps (64973 total steps). Aircraft retain direct solid bypass. These checks establish collision safety for the authored static boxes and progress on the tested route, not hierarchical pathfinding, arbitrary obstacle layouts, ground slope limits or unit collision. Full checkpoint and headless scale evidence are recorded in docs/evidence/navigation-session.json.

During full integration, the weather input fixture compared player health while real enemy combat continued (HP70→50). Its existing development-only simulation scheduling freeze now precedes the F4 check, which also asserts that authoritative ticks remain unchanged. Weather controls and rendering continue executing, and no player health or gameplay behavior is patched. This isolates cosmetic control effects from unrelated enemy attacks. The first failure and rerun are retained in navigation-session.json.
