# ABI v1
Linux SysV AMD64, NASM, SSE2. Calls preserve RBX/RBP/R12–R15; RSP is 16-byte aligned before CALL. No pointers into reloadable code in persistent state.

Simulation: sim_init(EDI=count, ESI=seed) -> EAX=0 success/-1 invalid; sim_tick() -> void; sim_checksum() -> RAX deterministic hash; sim_order(EDI=side, ESI=front, EDX=mode) -> EAX status. Exports sim_count (u32), sim_tick_count (u32), sim_alive[2] (u32), sim_engaged (u32), sim_entities (capacity 32768, stride 32). Entity: x float offset 0, z float 4, hp u32 8, side u32 12, kind u32 16, front u32 20, target i32 24, generation u32 28. Coordinates 0..8000 metres. Kinds 0 infantry, 1 armour, 2 artillery, 3 aircraft. No client camera dependencies.

Headless and client are separate assembly entry points linking the same simulation. Renderer owns input, display and visual state, never simulation storage layout. Headless emits JSON statistics. Tools benchmark subprocesses, not a Python simulation.

Additional prototype APIs: sim_fire(EDI=index,ESI=damage1..100)->EAX0/-1 applies guarded damage to a living enemy only; sim_waypoint(EDI=side0/1,ESI=front0..2,XMM0=x,XMM1=z)->EAX0/-1 accepts finite0..8000 metre goals, preserves invalid state; sim_waypoints[6] has8-byte float x/z records in side*3+front order. Goals affect replay hashes. sim_spend(EDI=side,ESI=positivecost)->EAX0/-1 checks single-thread authoritative balance.

Twelve sites are described in docs/operation.md, with sim_sites stride32, sim_requisition/sim_supply[2], sim_operation_state. Operation state and warning timers are part of checksums; no saved schema migration exists. audio_init/audio_shot/audio_update/audio_shutdown and mixer test ABI are described in docs/audio.md. Standalone UDP proof has a separate version1 fixed32-byte contract in docs/network.md and is not yet the gameplay protocol.

Bounded moving-shell and event record layouts are in `schemas/combat.inc` and [combat](combat.md). The event ring is cosmetic and excluded from authoritative checksums. Shell pools and stocks participate in replay. Player vehicle ownership uses separate records and entity-index mappings, preserving player64/entity32 layouts. UDPv6 field layouts are canonical in `src/net/schema.txt`; vehicles and events are server-owned state, never client damage/position claims.

`sim_scenario(EDI=0 default/1 air-battle)` returns0/-1. Mode0 preserves state; mode1 requires a fresh >=2048-actor world and places64aircraft and256ground actors into an initial encounter while preserving the army. It initializes actual flight poses/stores, creates no shots/events, and places connected players behind allies. The ordinary client uses8192actors. See [air-battle](air-battle.md). `air_hit(EDI=stable_index)` is called only after positive surviving production damage and validates aircraft generation. `air_trails_update(EDI=local_player,XMM0=render_seconds)` owns128x32cosmetic records, separately from64event effects. `net_projectiles_update(XMM0=render_seconds)` owns512x64remote cosmetic trajectories; neither call may write authority.

Player motion: `player_motion[4]` uses32bytes per slot: footY f32+0, vertical metres/tick f32+4, generation u32+8, jump latch u32+12, grounded u32+16, initialized u32+20, previous eye f32+24, reserved+28. This is authoritative private state included in player_hash; player64 is unchanged. INPUT_CROUCH32/INPUT_JUMP64 extend the valid mask to127 across player, vehicle, adapter and server. `audio_footsteps_update(EDI=localSlot,XMM0=renderSeconds)` reads poses/motion and owns only cosmetic distance accumulation; bank2 is the CC0 recorded footstep with shared128voice budget. `view_settings_parse(RDI=flag,RSI=value)` returns0unknown/1accepted/-1invalid; startup width320..3840,height240..2160,FOV35..110,sensitivity0.00001..0.05 have strict finite full-string validation. Default projection stays bit-identical1.05/1.87.

## Dense scenario and battle diagnostic contracts

`sim_scenario(EDI)` modes0default/1air-battle/2scale-front/3scale-hotspot return0 or-1. Modes2/3 require a fresh tick0 world with at least8192 entities; invalid calls preserve authority. Existing entity/player/network layouts and schema versions are unchanged. Scenario initialization sets actual poses before production simulation, without combat-event or damage injection. See docs/scenario-layout.md.

`battle_metrics_reset/capture/report()` are SysV read-only diagnostic hooks. Capture samples current living, engaged, projectile, submitted high/low/marker, cosmetic effect/trail and audio voice counts after draws; nine last/peak u32 fields and sample/simultaneous u64 counters are cosmetic. Report emits one JSON row. Independent peaks need not coincide; the separate simultaneous counter requires positive projectiles, effect records and audio voices in the same sampled frame. Submission is not frustum or pixel visibility. CPU frame timing includes capture; GPU draw timing excludes it. Single-thread audio voice reads have no callback race in the current pump. Network clients have partial authority, so this report is not a global army census there.

## Optional pixel census

CLI `--census` requires explicit bounded client frames1..10000; benchmark default600 is bounded. `--census-map PATH` requires census and writes raw little-endian uint32 pixels with dimensions/tick in JSON. Low16bits encode stable army entity index+1; bits16..17 classify high1/low2/marker3. Zero is background or nonarmy occlusion. No entity/network ABI changes. GPU outputlocation0 retains ordinary colour; outputlocation1 writes identity into opt-in R32UI. Opaque terrain/props/weapon/humans occlude army IDs, and later translucent cosmetics/HUD mask that attachment.

`visibility_init/begin/world_end/finish/report/shutdown` own optional private GL resources and bounded static readback. Finishreturns0/-1 and rejects changed authority, invalidpixels orGLerrors. Begin/finish authoritativechecksums mustmatch. `visibility_reduce(RDI pixels,ESI word_count)` returns0/-1, resets privatecounts and deduplicatesactualIDs. Rawcapture and eight independent productiongeometry GLfixtures distinguish missing/occluded geometry and detailtypes. See docs/visibility-census.md for storage, masks, timing and scope.

## Observed incoming danger contract (integration in progress)

schemas/hazard.inc defines private512x64 incoming trajectory estimates and32-byte
per-entity generation/commitment state. World hooks init/tick/entity_goal/hash;
no entity/player/wire stride changes. Only existing artillery2/bomb3 projectiles
can create threats. Estimated ground intercept is bounded to120ticks, then tile
indices limit individual queries to8candidates. Read-only hazard_query accepts
an actual eye/side and returns enemy explosive index/impact/radius/ETA andLOS-call
count; current projectile range<=300m, local danger<=radius+20m and terrainLOS
are mandatory. It does not expose hidden enemy/unit/player positions. Fixed8tick
per-entity observation phases and a1024LOS/tick cap bound authority perception;
short40tick memories steer continuously at existing role speeds after perception.
Ground hazard goals temporarily interrupt hold/advance and bypass slow squad
corridors, but terrain_move still enforces collision/speed. A bounded helper chooses
reachable dispersion or nearby physical shelter. Player cues query read-only local
estimates; network client warnings remain a separately required integration.

Ground ordnance admission v1: schemas/ordnance.inc defines private queues and
four group cursors. Root owns world hooks/hash, module worker owns bounded queues.
Actual acquired target, live matching generation, opposing side, armor/artillery,
finite existing ammunition and ready cooldown required. Queues are derived
same-tick state; clear before target acquisition, interleave after targeting and
before air combat. Preserve production416AI/480air/512physical limits and human
headroom. No extra authority or new wire records. Armor/artillery use their real
cooldown instead of infantry8tick damage staggering; legacy mode0 keeps original
order/phase for physical negative comparisons. Replays include only enabled flag
and four last-admitted source cursors; diagnostics do not affect behavior.

Admission priority follows canonical physical source IDs: rank four group heads
by unsigned stable ID, empty queues last, and rotate the rank by tick&3. Group
metrics/cursors remain indexed by actual side and kind. A global side-label flip
must preserve the complete physical launch order and resulting actor health;
count equality alone is insufficient. The full-world symmetry check caught the
initial side-index-priority regression and remains required.

## Direct controller body queries

Private `schemas/crowd.inc` v2 preserves entity32/player64/wire layouts.
`crowd_step(EDI=armyHullID or ENTITY_CAPACITY+humanSlot, XMM0/1=currentXZ,
XMM2/3=originalLocalGoalXZ, XMM4=requestedStep)` returns actual XZ. Human/tank
caps are0.3/0.6m; accepted steps preserve requested components and terrain/body
sweeps, with contact slides or safe hold rather than AI detours. AI retains
`crowd_move` and normal0.12/0.5/0.2m role limits.

`crowd_occupied(EDI=ignoredBodyID or-1, ESI=groundRole0..2, XMM0/1=candidateXZ)`
returns1 for occupied/invalid/truncated,0clear. Placement must not ignore the
vehicle hull on disembark. `crowd_begin` refreshes the fixed army grid plus four
human snapshots; AI queries use immutable matching human snapshots, controllers
and occupancy use bounded live human validation. Boarding exclusion requires a
living allied tank and valid bidirectional generation-stamped ownership.

Player frames refresh final army positions only when living controllers exist;
direct vehicle helper calls refresh before driving. Joins/respawns/exits refresh
once before candidate placement. Four-player loops can require additional bounded
O(N) snapshot rebuilds; individual queries inspect at most512 records including
four human slots, with no all-army scan/heap allocation. Those phases and stable
player-slot ordering are deterministic; identical per-body motion under exchanged
player slots is not promised. Derived snapshots/metrics add no future replay state;
the enabled policy word remains checksummed. Exact evidence belongs to status.
