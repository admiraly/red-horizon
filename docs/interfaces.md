# ABI v1
Linux SysV AMD64, NASM, SSE2. Calls preserve RBX/RBP/R12–R15; RSP is 16-byte aligned before CALL. No pointers into reloadable code in persistent state.

Simulation: sim_init(EDI=count, ESI=seed) -> EAX=0 success/-1 invalid; sim_tick() -> void; sim_checksum() -> RAX deterministic hash; sim_order(EDI=side, ESI=front, EDX=mode) -> EAX status. Exports sim_count (u32), sim_tick_count (u32), sim_alive[2] (u32), sim_engaged (u32), sim_entities (capacity 32768, stride 32). Entity: x float offset 0, z float 4, hp u32 8, side u32 12, kind u32 16, front u32 20, target i32 24, generation u32 28. Coordinates 0..8000 metres. Kinds 0 infantry, 1 armour, 2 artillery, 3 aircraft. No client camera dependencies.

Headless and client are separate assembly entry points linking the same simulation. Renderer owns input, display and visual state, never simulation storage layout. Headless emits JSON statistics. Tools benchmark subprocesses, not a Python simulation.

Additional prototype APIs: sim_fire(EDI=index,ESI=damage1..100)->EAX0/-1 applies guarded damage to a living enemy only; sim_waypoint(EDI=side0/1,ESI=front0..2,XMM0=x,XMM1=z)->EAX0/-1 accepts finite0..8000 metre goals, preserves invalid state; sim_waypoints[6] has8-byte float x/z records in side*3+front order. Goals affect replay hashes. sim_spend(EDI=side,ESI=positivecost)->EAX0/-1 checks single-thread authoritative balance.

Twelve sites are described in docs/operation.md, with sim_sites stride32, sim_requisition/sim_supply[2], sim_operation_state. Operation state and warning timers are part of checksums; no saved schema migration exists. audio_init/audio_shot/audio_update/audio_shutdown and mixer test ABI are described in docs/audio.md. Standalone UDP proof has a separate version1 fixed32-byte contract in docs/network.md and is not yet the gameplay protocol.

Bounded moving-shell and event record layouts are in `schemas/combat.inc` and [combat](combat.md). The event ring is cosmetic and excluded from authoritative checksums. Shell pools and stocks participate in replay. Player vehicle ownership uses separate records and entity-index mappings, preserving player64/entity32 layouts. UDPv7 field layouts are canonical in `src/net/schema.txt`; vehicles and events are server-owned state, never client damage/position claims.

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

Private `schemas/crowd.inc` v3 preserves entity32/player64 layouts.
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

## Shared ground hull motion and UDP v7

`schemas/ground_motion.inc` v1 defines authoritative32-byte heading, signed speed,
applied turn, accepted X/Z velocity, generation, role and active flag records for
all32768 entity slots. `ground_init`, `ground_step` and `ground_hash` are wired
into actual world initialization, AI tank/artillery movement, human tank driving
and replay checksums. Heading zero faces+Z. AI uses crowd avoidance as steering
intent before bounded forward turning/acceleration; legitimate drivers can brake
through zero into slow reverse. No input brakes, and stopped heading persists.
Source positions must be in[0,8000]; local goals may span[-8000,16000].

`crowd_hull_step(EDI=hullID, ESI=AI0/driver1, XMM0/1=sourceXZ,
XMM2/3=reachableEndpointXZ, XMM4=absoluteSpeedBudget)` accepts the whole physical
segment or holds. It cannot normalize, slide or rotate that segment. Existing
bounded body/terrain sweeps remain authoritative. Contact stops translation;
bounded tracked pivots can continue. Shared tank envelope0.6m/tick permits gradual
braking from driver to AI0.5m target. Infantry keeps its existing controller path.

The full1MiB sidecar and enabled policy are hashed. Private16-byte
`vehicle_driver_generation[4]` stamps successful boarding and is hashed by
vehicle_hash; vehicle, collision, actuator and replication readers reject recycled
human claims. Entity32/player64/vehicle32 remain unchanged.

Canonical `src/net/schema.txt` now describes UDPv7, schema fingerprint0x4e2ac49b.
NET_GROUND105 carries at most18 self-contained64-byte entity-plus-pose records
in1196-byte datagrams. Legitimate owned hulls receive priority; an independent
bounded cursor refreshes other nearby hulls. The client validates entire batches
before publication, tracks generation/death/interest separately and clears poses
on disconnect. Near/mid models and distant/map markers read stamped headings,
including stationary pivots. Renderer state is cosmetic and read-only.

Canonical road contact: `terrain_road_body(XMM0=x,XMM1=z,XMM2=radius)` returns
EAX=1 for a complete circle contained in one paved capsule, 0 off-road, -1 invalid.
Input coordinates/radius must be finite and within the documented map bounds.
Generated read-only records come from `content/terrain/roads.json`; no surface
state or entity/player/wire stride is added. `schemas/ground_surfaces.inc` defines
tank/artillery off-road factors 0.8/0.7 and aliases the actual body-radius macros.
Desired speed, acceleration and reverse scale; braking/yaw/contact envelopes do
not. Retained boundary-crossing momentum decelerates through the actuator.
Terminal arrival uses the exact discrete braking sum; AI body guidance previews
at most 6 m without accepting any unchecked hull translation.

UDPv7 content fingerprint `0xaee4fda3` covers the actual asset-manifest hash,
canonical roads, relief, resolved handling and grade policy, sweep radii and
the fixed refined rendering tile. `tools/ground_content.py --check`
validates it before builds; co-op checks independently reconstruct it and retain
incompatible-client rejection. Schema fingerprint and wire layouts are unchanged.

Current shapes are planar conservative circles. Wheeled chassis,
oriented hulls, suspension, damage handling and wreck cover remain separate work.
Focused worker evidence is in ground-motion.md, ground-motion-outcomes.md and
ground-presentation.md; final integrated evidence belongs to status.md.

Raised terrain candidate: `terrain_relief` ABI v1 contributes stateless height
and derivatives to CPU world queries and both embedded GPU vertex shaders.
`terrain_grade_clear` ABI v1 validates whole swept circles via nine closed
facet intersections and four gradient corners per intersection, including both
cusp sides. Foot/tank/artillery limits 45/35/25 degrees are design choices;
air bypasses ground admission after coordinate validation. Expanded segment
rectangles conservatively reject some valid diagonal sweeps. The bounded graph
uses at most 27 nodes, adding four field corners and one gentle-side entrance;
shared cached routes remain artillery-conservative. Height preserves all GPRs
and XMM4–15 expected by established callers. CPU and GPU use canonical relief,
and a localized 105,000-vertex tile bounds analytic interpolation error to
0.027 m. Full checkpoint 3d022b3c7d8e passed; see status.md and the terrain
integration contract for exact evidence and remaining limitations.

Stateless ground presentation: ground_support ABI v1 in schemas/ground_support.inc
reads actual terrain at four rotated chassis corners and the centre, validates
all support samples, and publishes a 64-byte caller-owned Y/pitch/bank/frame
record atomically on success. Invalid input preserves output. Tank/artillery
policy is common across LODs and remains within physical circle bounds. Valid
stamped renderer sidecars populate existing instance pitch/bank and absolute-Y
fields; stale/inactive/invalid support uses upright relative-height fallback.
Geometry and normals share yaw × pitch × bank. No entity, motion, player or wire
stride changes; content 0x0fb51f27 includes support ABI/chassis dimensions.
Full checkpoint 86ca2085d678 proves scoped integration. Smoothed suspension
response remains isolated and requires corrected contact for intermediate angles.

Derived ground presentation now supersedes the isolated-response state above:
`ground_visual` ABI v1 consumes caller-owned64byte cache/output, generation, kind,
nonzero render frame, XZ/heading/dt. Its spring48byte prefix is generation-safe;
remaining words record frame/XZ continuity. Reset after missed frames, >4m jump or
dt>.1; same-frame unchanged queries validate with zero spring time.
`ground_contact` ABI v1 returns support64 for supplied current pitch/bank using
exact yaw*pitch*bank and five projected terrain points. Contact raises springY
and removes downwardY velocity when needed. Invalid output remains untouched;
derived active flag clears. No wire/authority layout or replay hash change.
Content0x2df28e7c includes contact, spring and continuity policy. Shared contracts
are schemas/ground_visual.inc, ground_contact.inc and suspension.inc.
Focused final snapshot4c865d935b13 passes; full dfc1f67207e7 passed545.82s/87reports with195matched inputs.
Eye/muzzle/camera authority remains upright; ground-attachments-next.md records
that gap and absent source socket metadata.

## Ground wreck registry foundation v1

Root-owned schemas/wreck.inc declares a64-byte captured ground-death record and
1024-slot ring with1800tick lifetime. wreck_register accepts only an actual dead
kind1/2 source with valid ID/generation/side/map coordinates, preserving the full
arena on invalid/duplicate calls. It uses matching unsmoothed ground support and
contact, or an explicitly flagged upright fallback. init resets record/history/
metadata; tick expires by modular elapsed age; hash includes all persistent state.
Both genuine casualty paths register once after HP0/alive-count decrement.
UDPv8 now carries these immutable records; current NET_CONTENT is0xdbb0a2ab.
Rendering and self-contained replication are integrated. Physical collision and
weapon/LOS/navigation cover hooks remain pending.
Prepared segment_box v1 at isolatedd238ea8 is read-only first parametric contact
against caller-owned AABB, with finite/capacity/bounds validation and SysV/SSE2.
It is not yet a root runtime caller contract or accepted physical cover.

### Captured-pose wreck point query foundation

`schemas/wreck_query.inc` defines read-only result24 first-t/slot/entity/gen/seq.
The conservative world AABBs derive from immutable death poses and actual frame0
mesh union. Accepted register/init/expiry invalidates a derived64-bit revision;
index/bounds/revision are excluded from the authoritative hash. Nearest ties use
physical identity, not faction or bucket order. Single simulation safe point;
no concurrent mutation. Clear/invalid source/caller paths do not write output.
No current body inflation/LOS/rifle/shell hooks. See wreck-spatial-query.md for
bounded cost and geometry limits. The isolated body query and finer grid remain
prepared; rendering and wire contracts below are integrated.

### Immutable wreck presentation and UDPv8

NET_WRECKS106 uses the40-byte header plus1..17entries of slot:u32 and record64,
with no count prefix and1196-byte maximum. Each client owns a separate fair
1024-slot cursor. Used slots include tombstones; at full capacity an uninterrupted
stream covers the ring in61snapshot opportunities. There is no reliable join
barrier or loss-completion latency guarantee.

wreck_receive validates the entire payload before mutation, including duplicate
slots, finite/bounded poses, kind/identity, canonical fallback, reserved fields,
1800tick lifetime and source-clock age. Per-slot modular tick/sequence guards
reject stale updates; equal sequence cannot change immutable fields or revive
inactive state. wreck_remote_expire uses accepted server time. Dedicated
net_wrecks1024x64 never replaces sim_wrecks or enters its authoritative hash.
Open/close/timeout resets the cache. See schemas/wreck_remote.inc and schema.txt.

wreck_instance maps one immutable record to64-byte existing mesh input: static
frame0, captured XYZ/yaw/pitch/bank, unit scale, absolute height, ID-1 and scenery
side3. Renderer uses separate mesh_wreck_instances/mesh_wreck_pose diagnostics
and high-detail frame0 tank/artillery geometry, leaving live census unchanged.
First-person culling is800m; tactical submissions can produce zero pixels.
The shared shader darkens only those wreck scenery roles. No useful far/map
representation, hardware budget or physical cover acceptance follows from this.

### Sampled actor first-entry policy v2

UDPv9/schema0xf90d92f8/content0x10001089 includes SHELL_CONTACT_VERSION2,
RADIUS4.0 and MAX_SAMPLES216 in independently reconstructed content identity.
All wire payload layouts remain unchanged. sim_shell_contact accepts EDI source
side/XMM0..5 segment endpoints, returns opposing sampled live entity or-1; on hit
XMM0..2 contain contact XYZ and XMM3 contains first t. Equal f32 entries tie by
physical ID. It is still an opposing-only proximity envelope, not an oriented
hull hitbox/all-actor sweep or terrain/wreck arbitration.

segment_sphere accepts readonly centerXYZ/radius16 with capacity, finite bounded
endpoints, radius.001..4096; returns1hit/0clear/-1invalid and first t only on hit.
Closed tangency/endpoints and start-inside t0 apply. Non-hit restores original
XMM0; SysV/readonly/SSE2 double intermediates, no heap or external calls.


## Integrated ground body and local wreck detours

At f8d80b8, UDPv14/schema0xda94decc/content0xd30d7e25 retains the wire
layout; body and route policy constants enter the compatibility fingerprint.
world_body_path_clear[_context] accepts role EDI0..2, XMM0..3 start/end XZ;
returns EAX1 clear or0 blocked, including source/terrain failures. Explicit
context RSI is stable1024x64 wreck storage, EDX active count, RCX revision.
world_body_blocked uses zero motion; world_body_step adds XMM4 step and returns
an independently swept proposal or component slide. Original .551/3.551/4.491m
sweep radii and nondeepening initial-overlap escape are retained. Authority
wrappers select sim_wrecks; connected foot preview explicitly selects net_wrecks.
Caller owns readable storage and revision advancement; source records are readonly.

wreck_nav_init/tick/goal/hash own32768x256 persistent actor commitments and a
512-entry FIFO. goal accepts EDI actor and chosen static goal XMM0/1, returning
a local waypoint or original goal. Identity/generation/role/goal reuse is guarded.
At most8 builds/tick;64m endpoints extend in8m increments to96m when needed,
never beyond the actual goal. Graph capacity54 nodes and retained path28 points.
All edge and actual-motion queries retain complete cover checking. Version1
rejects more than8 relevant wreck vertex sets safely; the separate VERSION2
relevance prototype is not integrated until its own full checkpoint passes.
Future commitments, FIFO and diagnostics enter nav_hash; graph scratch does not.
No global invalidation on distant deaths. See wreck-body-routing.md and schemas.

Verified integration07d6536: UDPv17/schema0x6aa0d743/content0x7138ea65.
Packet layouts remain unchanged. WRECK_NAV_VERSION2 selects at most8 relevant
vertices per bounded local graph, but all cover still participates in edge and
actuator checks. PLAYER_DEPLOY_POLICY_VERSION2 tests exterior authored offsets
rather than rendered site centres, retaining original safety validators. Query
envelope rejection is conservative; original exact collision/radii/ties and
initial-overlap escape remain. Companyv16 and acquisitionv18 are isolated policy
candidates; their combination requires recomputed compatibility and an exact
combined full checkpoint. Persistent company records remain private authority,
not a replicated or player-ownership interface.

Previous verified combined gameplay UDPv19/schema0xe683e0bb/content0xe310d315 at the
4f9cf0815524 checkpoint. Packet layouts remain unchanged. company_assault.inc
specifies1536x128 persistent plan records and normal hash participation; the
full-range acquisition heap is bounded private scratch with original distance/
reservoir-rank tie semantics. Wreck row projection changes only conservative
candidate enumeration, retaining exact slabs/escape/source/identity rules.
Verified gameplay UDPv20/schema0xf1a4fcab/content0xe84a7d53 now integrates
own-bomber escort policy1 and air acquisition2, fullac6766acbf40 passed.
Persistent16byte mission per owner contains leader ID/generation, owner generation
and expiry; own-side/front finite-store validity controls trailing/flank goals.
Only actual750m range/LOS acquisition admits enemy threat priority. Hash includes
missions; entity32/player64/aircraft64 and packet layouts remain unchanged.
Private v21 coordinated bank/strike/boundary contracts remain isolated in
feature/air-bank-flight; docs/air-bank-flight.md records scope and test changes.

Current accepted aircraft contract: UDPv21/schema0x3296bf93/content0x551748ea;
physical gradual bank-roll/yaw, own observed strike memory and boundary latch.
Exact schema and policy constants live in src/net/schema.txt and schemas/air_flight.inc.

Current company contract v23 (21b2cd4): company_assign(EDI player,ESI front)
returns own nearest unleased living ground cohort key or-1. company_for_player(EDI)
validates connected generation and bidirectional lease. company_control_order(EDI
player,ESI key,EDX mode,XMM0/1 XZ) returns0 accepted,-1 invalid,-2 ownership,-3
funds; validates before one5REQ charge and one sequence change. company_control_goal
(EDI actor) is readonly, returns0/XMMXZ move,1 hold,-1 autonomous. Hazard escape
retains priority. company_release clears ownership/intent on disconnect. Internal
company_redeploy preserves intent and updates the matching immediately preceding
body-generation lease after genuine successful redeploy only. These contracts are integrated on main with focused tests; the matching combined
extended checkpoint3112ca82aa0d now passes.

Current LOS optimization (c0c8f04/main): wreck_occlusion_context(RDI output24,
ESI bytes>=24,RDX stable1024x64 source,ECX active count,R8 revision,XMM0..5
start/endXYZ) returns0clear,1one real blocker,-1caller fault,-2source fault.
Its contact output is not promised nearest. Complete source validation/prepared
revision discipline precedes early exit. Only world_los consumes it; regular
wreck_query_context/body/projectile APIs retain closest contact and identity ties.
All original geometry/range/visibility/weapon/health/motion thresholds are retained.

Verified contextual wheel contract (integration evidence in status.md):
command_wheel_select(XMM0 screenDX,XMM1 screenDY) returns mode0/1/2/3 for
up/left/down/right or-1 within38pixel radius or on invalid coordinates.
command_terrain_point(RDI six-float originXYZ/directionXYZ) returns EAX0 with
XMM0/1 finite first sampled/refined visible terrainXZ, or-1. It is read-only,
uses private aligned stack scratch and preserves SysV nonvolatile GPRs. Bounds:
512 four-metre steps,12 bisections, existing finite static LOS. It does not read
actor/enemy coordinates. command_hud_draw_at(RDI text,ESI x,EDX y) provides
bounded128glyph, width-clipped pixel placement; command_hud_draw keeps rows0..2.
command_wheel_hud_init/draw own only cosmetic OpenGL uniforms/draws. No wire,
player/entity, lease, cost or authoritative clock contract change.


Local input binding contract v1 (schemas/input_bindings.inc):30 logical actions,
keyboard GLFW codes or bit16-tagged mouse0..7 codes. No network/content-policy
or entity layout change. bindings_load(RDI regular-file path) returns0 after
atomic publication or-1 with published codes/label indexes unchanged; fixed4096
byte input and staging buffers, SysV preserved GPRs/aligned calls. It is
startup-only and not concurrent. bindings_down(RDI GLFW window,ESI action)
returns the bound physical state; invalid action returns0. bindings_label(EDI
index) returns an immutable ASCII label or empty string; clobbers only RAX/RDX.
bindings_report prints loaded action/key names once. Client key/mouse callbacks
compare logical quit/cancel codes, preserving queued short taps and wheel cancel.
Actual movement/fire/order/transfer controllers still own all authority checks.


Defense contract amendment: company-control VERSION3/MAX_MODE4 adds area
formation goals without changing32byte authority or40byte remote records.
company_defend_goal(EDI stable actor ID,RDX validated own ground entity,
XMM0/1 accepted point) returns0 terrain-valid XZ or1 hold. It tail-calls the
existing bounded role-footprint/grade placement helper; no allocation, enemy
reads, pose/stores/order/clock writes. company_defend_anchor(XMM0/1 accepted XZ)
returns the same480..7520 effective anchor used by map presentation. Authority
validates raw coordinates and the bidirectional owner/body-generation lease
before deriving destinations. Hazard response retains movement priority.

UDP27/schema0x24a8a531/content0x00ac549b version the additional command and
formation policy. Client sender, server order validator and atomic remote
receiver accept0..4 and reject5+. Input contract2 appends DEFEND30/COUNT31,
default5, preserving existing IDs. Wheel mode4 occupies upper-right screen
vectors dx>0,dy<0 with .5<=dx/abs(dy)<=2 outside the38pixel deadzone; remaining
cardinal sectors are unchanged. GLSL uses the same boundaries. Defense wheel
release requires the captured visible terrain point, and network acceptance
feedback waits for the server ACK. Evidence/limits: status.md.


Army rifle policy2 (schemas/infantry_weapon.inc): infantry_weapons contains
32768x32byte server-owned records: entity generation0, magazine4, carried
reserve8, remaining reload ticks12, actual rounds fired16, empty tick20,
cumulative received rounds24, last supply tick28. World init clears and equips living valid infantry; authoritative
world tick recognizes genuine new living generations and advances reloads.
infantry_weapon_fire(EDI actor) returns0 for one spent round,1 unavailable,
-1invalid. World calls only after actual enemy range/LOS acquisition and existing
8tick cadence; it queues unchanged rifle damage only on0. The gate never selects
a target or directly applies damage. Dead actors freeze stocks; side/front/lease
changes cannot replenish them. Normal conservation is mag+reserve+shots=120+received, received<=144000.
Corrupt counts/stocks are atomic or skipped, including a nonempty magazine with
a pending reload. Explicit infantry_weapon_init is for fresh-world initialization,
not a resupply API. All entries preserve SysV nonvolatile GPRs and allocate nothing.
Records participate in sim_checksum. UDP29/schema0xc400bad2/content0x5964d91f
fingerprints the policy; entity/player wire layouts remain unchanged, NPC stock
metadata is not replicated. infantry_weapon_resupply(EDI actor) performs finite debit/credit and returns
rounds0..90/-1invalid. Proximity<=60m, clear ground/solid/wreck LOS and actual
owned healthy connected uncontested depot records gate transfer to reserves.
All capacity/generation/numeric/store checks precede debit; credit cannot fail.
At most one success per actor per tick. Automatic resupply is a physical-ID
stagger every30ticks, after operation_tick; it visits at mostceil(N/30) actors.
Site ownership/connectivity/contest records are evaluated once per second.
Capture/repair/restoration cannot reset12x16byte depot stores. World init seeds
only depot-role physical sites with12000 rounds, current map four sites/48000.
Store remaining+issued=declaredInitial; world checksum includes all stores.
No movement order, enemy knowledge, player/vehicle/air rearm or network stock
fields are introduced. Received counters reset only with declared genuine birth.

## Infantry policy5 joint visible targets

`infantry_human_fire(EDI=sourceID,ESI=already-visible living opposed ground army ID or0xffffffff)` returns1 when a human is selected (including a blocked finite weapon),0 to retain the army decision/no human,-1 invalid. Caller supplies the already acquired physical army LOS result. Eligible hostile infantry compares at most4 current connected living on-foot human bodies, with physical LOS and finite public XYZ, on its existing8tick actor phase. The closest visible target wins; exact army/human ties keep the army target, exact human ties rotate by actor and firing phase. Rifle range is240m horizontal and human damage10. All actual fire uses the existing conserved stock/shared cooldown gate.

There is no separate per-human enemy scan or extra firing budget. Humans are not encoded as army entity IDs: public `ENTITY_TARGET` remains an army ID or-1. Human aim orientation, target presentation and strategic observed-knowledge records remain pending. Safe deployment rejects physically visible hostile infantry within the same240m range; other role threat gates retain their previous conservative radius.

Policy5 changes semantic compatibility to UDPv37/schema0xf7443ce4/content0xabc84d82. Public entity32/player64/stock32/state848 layouts are unchanged. Incompatible sessions restart; no saved-state migration claim.

## NPC rifle cosmetic source events

`infantry_weapon_shot` publishes one `EVENT_INFANTRY_RIFLE10` only after actual successful conserved debit and cooldown start. Stock-only `infantry_weapon_fire` publishes no event. `infantry_rifle_event(EDI=sourceID)` bounds-checks current living infantry and finite source XYZ, then emits at body eye with0.25m radius; its rejection cannot revoke an already committed shot. No authority hash contribution or new persistent gameplay state. Event32 remains cosmetic XYZ/kind/side/tick/radius/sequence, no source identity/target/trajectory claim.

The renderer consumes matching current source events into the64-record cosmetic pool, produces a0.065s/0.25m flash with no smoke/debris, ages against actual tick, deduplicates frames and suppresses rifle flashes on the tactical map. Recorded bank0 routes spatially through the shared128voice mixer, deduplicated and at most15ticks old. NPC rifle diagnostics `audio_infantry_events`/`effects_rifle_flashes` are cosmetic. UDPv38 expands validated event kind range to1..10, packet layouts and authority content are unchanged; schema hash follows canonical src/net/schema.txt.

Infantry cosmetic aim v1: schemas/infantry_aim.inc defines private32768x32 source-generation/tick/heading/pitch/XYZ/flags (active1/human2/actualshot4). infantry_aim_mark(source, known physically visible target, humanMode0/1) observes without debiting authority; infantry_aim_shot marks only an actual successful same-tick finite shot. infantry_aim_pose(source,presentationTick,maxAge1..12) validates living infantry/current body generation/flags/angles and returnsflags(EAX),age(EDX),heading(XMM0),pitch(XMM1). Local caller age8, remote age12. Authority checksum excludes this presentation cache. Renderer leaves movement frames/body heading independent, packs active4/recoil8/age<<4 in instanceidentity.w with original low2 height/ownership flags. Authored semantic3 shooting clip contributes only reference-mask upper vertices. No bone IK or new firing cone.

UDPv39/schema0x212cb081/content0x7abe6425: NET_INFANTRY_AIM118 = countu32 plus at most32 records of sourceIDu32,generationu32,observedTicku32,headingf32,pitchf32,three reserved zero u32,flagsu32 (36bytes; maximum1196including40-byteheader). Nearest32 living source-interest candidates, hostile source additionally physical player-eye LOS; friendly source current nearby interest. No army/human target ID/XYZ transmitted. Entire batch validated before independent generation/headerTick/observedTick publication. Existing body records control position/HP/generation; metadata cannot publish a body. Admission observed age<8; presentation age<12. Reset on open/close/timeout. Incompatible peers must restart; no silent v38 adaptation.

Actor visual detail v1: renderer caches9 role thresholds from max source descriptor dimension*source scale*max(projection.x*halfwidth,projection.y*halfheight)/1.5pixels, with800m floor and8000m cap; both authored LOD extents share the larger threshold. Model and marker passes select the same validated visual role (fighter8/bomber3 via live matching sidecar); high-detail150m/cap unchanged. Cosmetic only; arrays/bodies/authority contracts unchanged. battle_metrics.initial_living snapshots actual sim_alive sum at diagnostic reset before first simulation frame, independently of real post-tick frame peaks. It is not an individually visible count or authoritative remote army census.
Infantry aiming shader: scale.w is the difference between generation-valid observed aim heading and locomotion body heading; both headings are bounded to[-pi,pi], hence difference[-2pi,2pi]. Wrap the difference to[-pi,pi] before multiplying authored reference-mask weights, preserving short rotation across the heading seam. This is derived presentation and does not impose an authoritative firing cone or anatomical clamp.

## Physical aircraft cannon prediction

`air_gun_intercept(XMM0..2=relativeXYZ, XMM3..5=observedTargetVelocityXYZ)`
returns EAX0/-1; success yields predicted relativeXYZ inXMM0..2 and travel
ticks inXMM3. Read-only SSE2 positive root of|r+v*t|=28*t, finite distance
squared in(0,192000000], target velocity squared<=64, travel ticks(0,40].
Rejects nonfinite/zero/distant/overspeed inputs. No allocation or future-state reads.

`projectile_air_gun_ready(EDI=livingFighterID)` returns EAX0/-1 and successful
normalized actual flightXYZ nose inXMM0..2. Guards live opposing current
positive generations, active roles, finite bounded coordinates/heights, original
1..180stores and ready cooldown, source speed5..7, actual finite velocity norm
(0,8], and dot(nose,predictedIntercept)>=0.985*length(predictedIntercept).
Caller owns actual target perception/LOS. No state writes; producer repeats the
predicate before slot/event/cursor/drop changes, emits28*nose, and leaves
finite store debit to the air FSM. Bomb velocity/gravity path is unchanged.
SysV preserved registers/alignment and authority are independently checked.
Public entity32/player64 and existing UDPv39/schema/content remain unchanged.

`air_gun_solution_ready(EDI=livingFighterID)` returns EAX0useful-shot/-1wait
or invalid. It first applies the producer physical-nose/metadata cone predicate,
then computes w=28*nose-observedTargetVelocity and t=dot(r,w)/dot(w,w).
Require0<t<=40 and length(r-w*t)<=SHELL_CONTACT_RADIUS. Caller owns current
actual target/LOS observation. This bounded read-only firing decision leaves
producer trajectories and admission/store ownership intact. No persistent
state, entity/player stride or UDPv39/schema0x212cb081/content0x7abe6425 change.

Client frame input helpers (private Linux NASM interface)

`bindings_event` receives GLFW key-callback arguments: RSI physical code,
ECX action (0 release, 1 press); mouse callbacks encode bit16 in the code.
Unknown codes and other actions are ignored. `bindings_frame_begin` snapshots
all31 mapped actions after event polling and consumes pending presses.
`bindings_frame_down` receives ESI logical action and returns EAX0/1, stable
throughout that input frame; out-of-range IDs return0. RDI window is unused.
All three preserve SysV nonvolatile GPRs and use fixed private input storage.
They change no public entity/player/UDP layouts or authoritative simulation.

Aircraft vertical actuator (private SysV/SSE2)

`air_vertical_step`: EDI role0/1, XMM0 requested vertical speed, XMM1 total
airspeed, XMM2 previous vertical speed. EAX0 success returns XMM0 new vertical
speed, XMM1 horizontal speed, XMM2 physical pitch. EAX−1 invalid returns three
zero floats. No pointers or state writes; SysV nonvolatile GPRs preserved.
Canonical bounds/accelerations are in air_flight.inc; see air-vertical-motion.md.

## Incoming cannon warning contract

Private NASM air_threats_build/air_threat_query observes actual current opposing cannon records and world LOS, with512fixed index slots and49cells/64candidates/2LOS per eligible actor. Query returns poolslot/-1 in EAX and committed lateral sign/0 in XMM0; gameplay read-only, diagnostics excluded from checksum. air_break_direction is private stable-ID gameplay state and is hashed. Public entity32/aircraft64/player64/UDP39 layouts unchanged; content fingerprint0x2a371472 requires compatible peers. Details and bounded selection limitations: docs/air-incoming-fire.md.

Aircraft holding private state:8bytes/physical ID, generation+arrived, separate from public E32/A64/UDP40. air_holding_goal returnsEAX1 andXMM0/1 steering point for valid owned recovery aircraft, else0/fallback; mutates only own generation/arrival state. air_recovery_goal remains pure point-policy/condition query for combat and independent policy probes. air_holding_init clears private records; air_holding_hash appends incomingRAX/R8 FNV. Policy version2/content0x0f2b459e includes all five holding fields. See docs/air-holding.md for exact behavior and limits.

Aircraft audio cosmetic interfaces: bank3 preloaded signed16 mono48kHz two-second recorded loop. audio_loop_begin; audio_loop_submit(EDI physical ID,ESI generation,XMM0/1/2 XYZ,XMM3 gain)->0accepted/1culled-or-voice-denied/-1invalid; audio_loop_end retire unsubmitted. Shared128voice pool, no authoritative state. audio_aircraft_update(XMM0/1/2 listenerXYZ) selects nearest8received/local living initialized aircraft; audio_aircraft_enabled is a paired-test cosmetic toggle. audio_written_frames counts accepted ALSA writes, not device latency. See docs/air-engine-audio.md. Asset content0xb2e14d6f, UDP40 and public layouts unchanged.

Linux explicit listen-host lifecycle: listen_host_start returns0/-1 before platform threads; owned sibling co-op8192/seed42 on ephemeral LAN port, validated readiness and loopback client. listen_host_check reaps unexpected owned termination0/-1; listen_host_stop stops/reaps only its own PID, never an external server; ready and final JSON diagnostics. No public entity/UDP layout change. Current CLI --listen conflicts with explicitport/connect/nondefaultscenario; normal solo unchanged. See listen-server.md for startup bounds, parent-death and coverage limits.

Dedicated/listen authored starts: server --scenario takes the four existing scenario names, applies birth once before socket bind and advertises numeric mode0..3 in control-plane readiness. listen_host_start(EDI=mode) validates exact mode along with8192 units/protocol/port; direct-connect clients cannot override authority scenario. Terminal server checksum/alive/engaged/event fields are read-only diagnostic JSON. No UDP40, E32/A64/P64, schema or content contract change. Army visibility IDs come only from army descriptor roles0..3/8 and actual marker mode; owned scenery roles5..7 remain zero-ID.

Authored squad deployment: trusted sim_scenario birth calls player_deployment_set(XMM0=x,XMM1=z). Private enabled/x/z authority configuration is cleared by player_init and included in player_hash when enabled; ordinary default hashes remain unchanged. No P64/E32/A64, UDP40/schema/content changes. Join/redeploy candidate search uses the anchor only behind an owned connected supplied front site and living allied ground formation; full physical/threat safety and site fallback preserved. Setter is internal birth configuration, not an untrusted network command.

Deployment explosive safety: deployment_blast_clear(XMM0x,XMM1y,XMM2z) returns EAX0clear/1unsafe, preserves SysV callee-owned registers and authority. Reads actual512 projectile and256 event slots, projects at most90 fixed-tick segments within TTL/map, uses production static contact only for near corridors, and30-tick hostile-impact cooldown. Dynamic actor/wreck interception is not assumed. Existing no-friendly-human-blast policy retained. No E32/P64/A64, UDP40, schema/content or new network command. Only spawn candidate selection changes.

Bloom cosmetic renderer: bloom_init(EDI=fullWidth,ESI=fullHeight) returns0/-1 and owns two ceil-half RGBA16F targets; bloom_render(EDI=sceneTexture) returns final texture/0disabled and performs three passes. Caller disables depth/blend and restores viewport/FBO/program/VAO. bloom_shutdown is idempotent. HDR owns lifecycle, reserves fragment texture unit15 and restores active0/full viewport; tactical bypass and post-present HUD preserved. No authority/UDP/schema/content changes. Details: docs/bloom.md.

Aircraft world contact: air_world_sweep(RDI output16,ESI capacity,XMM0..5 start/endXYZ) returns1hit/0clear/-1caller/-2source; hit16 = t:f32, kind1ground/2solid:u32, solidID/ground0:u32, reserved0. Output unchanged otherwise. air_world_warning(EDI physicalID) is a read-only own120tick velocity prediction; invalid metadata returns0, geometry errors propagate. CPU NASM/static terrain only. Private180tick motion commitment belongs to aircraft init/hash. Policy4/content0xd4b72e4f, UDP40/schema/public layouts unchanged. Details: docs/air-world.md.
