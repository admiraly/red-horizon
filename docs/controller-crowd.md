# Controller and human body collision

The `crowd` kernel provides three bounded public queries. `crowd_move` keeps AI long-goal navigation and ten goal-relative steering candidates. `crowd_step` accepts the original local controller goal, normalizes it, limits a foot human to 0.3 m or a legitimately driven tank to 0.6 m per tick, and tries the full movement followed by its original X and Z components. It never turns a pure-axis command into a detour. `crowd_occupied` tests candidate placement for infantry, tank or artillery radii while ignoring one specified physical body ID. Terrain validation remains active for placement.

Army IDs remain unchanged. A foot human uses virtual ID 32768+player slot. The fixed army grid remains 8 m with bounded 3×3 infantry and 5×5 vehicle neighborhoods. Four human snapshot records add 128 bytes; humans do not occupy the army linked chains. Every enabled query counts four direct human records, including absent/disconnected/dead humans, plus inspected army records, up to 512 total. Saturation yields movement or rejects placement conservatively. Queries allocate nothing and never scan the whole army.

`crowd_begin` records living connected humans with nonzero generations and finite map coordinates. A human is excluded only when all boarding links agree: player slot, active vehicle claim, entity ID/generation, living allied tank kind and reverse driver owner. Stale/invalid boarding metadata therefore cannot hide a foot human. A driven source must prove this same claim. Army neighbor HP/kind/generation checks remain intact and retired IDs beyond the current count are ignored. A stale reverse-driver marker may conservatively retain the 0.6 m neighbor motion bound on an otherwise valid physical tank; it does not authorize that tank's controller source.

AI queries retain matching human tick snapshots, while checking current living/connection/boarding validity. Changed human generations refresh the bounded record. Controller and placement queries use current human records, covering joins, exits and earlier same-frame player movement without an army-wide search. The integrator refreshes the army snapshot before controller stages and placement; production hook timing and resulting rebuild cost require integration measurements.

Nominal physical radii are 0.55 m foot human/infantry,3.55 m tank and 4.49 m artillery. Every accepted movement uses production `terrain_body_move` or `terrain_body_step` and a circle-vs-segment neighbor test. Neighbor maximum movement expands clear-start safety. Inside the anticipation margin, motion must preserve minimum separation. Existing physical overlaps require strictly outward movement, with no decreasing separation along the sweep. Exact coincidence retains authoritative tick-parity/physical-ID priority; some controllers may safely hold until that symmetry can recover. Placement tests current radius sums without moving or ignoring the exiting hull.

Only the policy flag affects `crowd_hash`. Derived index/human records and diagnostics remain excluded. Queries never write authoritative army entities, players, vehicle claims or driver ownership.

## Worker verification

`RED_HORIZON_NASM=/mnt/titan_nv 3/projects/red-horizon/.tools/nasm/nasm python 3 tests/test_crowd.py` passes all previous strict AI/terrain/coincident/convoy/role-sized gates and adds:

- Foot humans and driven tanks against each army role,80 ticks each; pure-axis controls retain their axis and clear approaches advance.
- 160 relative human-human and human-tank controller sweeps, without introducing circle overlap.
- Human joins, generation changes, disconnect/death, valid boarded duplicate exclusion, invalid-generation/faction claims and live exits after an old snapshot.
- Exact role-sized placement, own-human ignore while retaining the hull, malformed placement/role rejection and saturation at 512 inspected records.
- Manual diagonal body contact sliding, terrain-wall/map-edge input component limits and outward-only partial-overlap recovery.
- AI navigation around a held human, disabled-policy causal body penetration and unchanged policy-only FNV hashing.
- Sixteen malformed controller steps/goals rejected before clamping, plus corrupted army-count safe holds before any grid query; read-only authoritative arrays and SysV callee-saved ABI for both new APIs.
- Three translated exact-counter queries inspect 6 records each, independent of grid coordinates. The original `.account` shifted stack offset was already correct; the separate accounting commit clarifies the visits argument without claiming a historical bug.

The isolated assembly-loop 8192-actor benchmark is not a complete-world budget. Root integration owns actual player/vehicle/spawn hooks, production observers, scale/frame refresh measurements, frozen full verification and `docs/status.md` acceptance evidence.

## Limits

Conservative circle bodies and axis-aligned terrain expansion do not implement oriented hull contact, rigid pushing, vehicle turn/acceleration physics, vertical human separation or full weapon/limb geometry. Controller straight input can deliberately stop behind an actor; it is not autonomous route finding. Dense or initially unsatisfiable arrangements may yield. A 512-record query cap is safe conservative rejection, not a guarantee of finding a route through every crowd. This worker evidence does not establish the complete operation, networking/graphics/audio or target-GPU performance.

Worker fast verification on frozen kernel commit `8ae9f56` returned 34 suite reports and exit 0 (`/tmp/controller-worker-fast-final.log`). That worktree still uses previous production controller hooks. Subsequent count/faction guards use the complete standalone kernel suite; root validates final integrated hooks and frozen source.
