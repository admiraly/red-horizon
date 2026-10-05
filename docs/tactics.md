# Terrain and tactics implementation evidence

## Shared terrain slice

`src/nav/terrain.asm` provides the ABI in `docs/next-contracts.md`. The authoritative SSE2 height is `12 + (x-4000)^2*0.000001 + (z-4000)^2*0.0000005 + max(0,1-abs(x-4000)/800)*18`, in metres. The client shader must use this same expression; matching source equations do not establish bit-identical CPU/GPU results.

Five fixed 32-byte obstacle records are exported as `terrain_obstacles`, with `terrain_obstacle_count=5`. They contain three central wall spans and two bunkers; bounds/base/height are physical and shared with rendering. Initial seeded ground spawns do not overlap any solid. Aircraft bypass ground solids, but remain subject to physical ray occlusion.

`terrain_los` sweeps each obstacle using a three-axis segment/AABB slab test, and additionally checks seven interior analytic-ground samples. Thin authored walls cannot be tunneled by the ray. Ground sampling is bounded rather than an exact continuous intersection proof for arbitrary long rays. Ground actors target at terrain height+2 m; aircraft add 90 m. These queries now gate actual army target selection and therefore damage.

`terrain_move` first checks the segment toward the destination against the five solid boxes. For a blocked corridor it selects an outside corner four metres from the obstacle edge, progresses along that edge, then resumes the goal. Movement is capped by the requested step, clamps map coordinates and rejects any resulting solid overlap. This bounded local corridor steering is integrated into actual advance and retreat. It is not a global path search or a proof that every arrangement of obstacles is navigable; the authored isolated rectangles are the tested envelope. No terrain slope constraints, unit-unit collision, dynamic destruction or navigation rebakes exist.

All functions preserve SysV nonvolatile registers, use caller-saved integer/SSE scratch, and allocate no memory. Query inputs are finite world coordinates supplied by validated simulation/player state. `terrain_move` returns x/z in XMM0/XMM1, so `tests/terrain_probe.asm` is a development-only return-value bridge for ctypes; it is not gameplay logic.

`tests/test_terrain.py` passes formula samples, ground blocking and aircraft bypass, exact wall occlusion/elevated clear rays, bounded corner detour without overlap, an actual world fixture where hidden opponents acquire no targets and take no damage, actual army detour/arrival after 1200 ticks, and all 32768 initial spawns outside solids. Existing simulation, operation and waypoint suites pass with the real terrain module linked. Player integration and strategic/squad behavior are a separate pending slice; no stub player or AI implementation was used for these claims.

Fresh terrain-integrated throughput evidence on Intel i7-1355U, seed 1, 600 ticks: 8192 units alive3291/3267, engaged667, checksum98dcd0a3b52ac857, mean4.042290ms/p954.339853ms; 16384 units alive6600/6549, engaged1439, checksum9bc327084a1b2ae0, mean8.267412ms/p959.150734ms. Timings include authoritative solid/ground LOS queries; no GPU/network/player-loop performance claim.

## Autonomous formations and bounded observations

`src/ai/tactics.asm` adds six 64-byte controller records (`ai_fronts`, side*3+front). Fields by byte offset: own weighted strength0, currently observed opposing strength4, observation tick8, confidence0–100 at12, intent16 (0 scout/stage,1 alternating advance,2 withdraw), selected site20, explicit override24, reserved28, last observed enemy x/z32/36, reserved40, objective x/z44/48, visible scout survey52, retreat commitment ticks56, reserved60. Weights are infantry1/armour4/artillery2/aircraft2. These are simple prototype utility weights, not intelligence estimates of the entire hidden army.

The controller evaluates every 30 ticks. It scans living own entities and only copies enemy data from their previously acquired, physically visible authoritative targets. A fixed entity-ID bitmask deduplicates observed targets per front. It never scans hidden opposing coordinates for strategic strength or goals. Last observations carry a timestamp, decay to confidence0 over 300 ticks, and are retained for diagnostics. Decisions currently react to fresh observed strength, not extrapolated stale coordinates. Own supply below 100 capacity triggers withdrawal; observed strength greater than twice own strength also triggers withdrawal with 90 ticks of commitment. There are no hidden reinforcements.

The authored front's next hostile middle site, then command site, supplies a strategic objective. Designated scouts (stable index divisible by 16) and aircraft move first; other troops remain staged until a living scout physically reaches within 200 metres and sees that site. Aircraft survey from their actual terrain + 90 m altitude. A visible survey permits the main formation to commit. Target selection and shooting continue to require actual LOS; the controller cannot grant hidden hits.

Stable groups of 16 IDs alternate cover/advance every 90 ticks. Advancing groups use opposing ±600m flank corridors until within 500m in x of their site, then converge onto its physical capture area. Solid detours respect the chosen corridor's side. Terrain movement tries bounded component slides when a resulting local step is blocked, then holds safely if neither component is reachable. This is tested local recovery and authored corridor coordination, not hierarchical navigation, tactical cover selection or a universal stuck-solving guarantee.

Successful `sim_order` or `sim_waypoint` explicitly overrides AI for that side/front until the next world initialization. Thus autonomous allied orders cannot overwrite a player's front command. Invalid calls do not override. Mixed-formation goals inside ground solids are rejected before goal/override mutation; the co-op server performs the same check before charging requisition. There is currently no separate return-to-AI command. AI state is included in replay hashing; scratch observation masks are rebuilt and need not persist. Player initialization/tick/hash use the actual root `src/game/player.asm` from commit 0590eeb; no stub implementation is linked.

`tests/test_tactics.py` verifies outcomes over real world ticks: troops stay staged while a hidden wall-separated site is scouted; the scout detours, kills a physical defender and captures its site; opposite squads move on opposite flank corridors while their peer group holds; observed armoured superiority causes infantry positions to retreat; disconnected capacity causes withdrawal; a player front hold keeps position; and repeat fixtures yield identical checksums. Existing waypoint fixture tests now issue explicit advance orders to isolate their original movement-kernel intent from new default autonomous staging. No legacy assertion was removed.

Final integrated terrain/controller/player throughput evidence, seed 1, 600 ticks on Intel i7-1355U:

|Units|Living allied/enemy|Engaged at final tick|Checksum|Mean tick ms|p95 tick ms|
|---|---|---|---|---|---|
|8192|3705/3611|41|ff32c15dc7b98404|4.134853|4.792126|
|16384|7357/7225|33|6417afdf9222e1b4|8.631333|12.631920|

Both twenty-second runs remain ongoing, with 600/600 connected capacity and 880/460 requisition. Reduced engagement relative to advance-only fixtures reflects autonomous staging/reconnaissance and physical wall occlusion; these figures do not claim compelling pacing. Full simulation/replay, operation, waypoint, terrain, tactics and real root player suites pass. The wall-edge recovery fixture allows 1 mm displacement tolerance for float32 rounding at kilometre coordinates. No GPU/client fun, remote transport, hierarchical navigation, robust strategic planning or complete operation acceptance is inferred from these tests.
