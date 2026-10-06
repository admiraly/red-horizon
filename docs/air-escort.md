# Isolated protected-aircraft mission candidate

Based on verified combined ground dc2c4fb/1e85074, separate from main. Authored
CPU runtime remains NASM/SSE2. A16byte own mission binds a fighter to a living,
finite-store, same-side/front bomber with both generations and a bounded180tick
commitment. Every30ticks a complete linked friendly-bomber grid picks the nearest
within1500m, with stableID ties; a live assignment may remain until2000m. Reviews
within30ticks of expiration prevent an unplanned gap. No enemy state chooses the
assignment. Inactive/dead/reused/empty/changed-side/front sources fail immediately.

When no perceived enemy is being intercepted, fighters steer toward a moving
16tick trailing goal80m to the side of the bomber. Existing7m/tick flight and
.04rad/tick yaw limits, bank/climb, boundary steering, damage breaks and return
remain. Fighter scoring weights enemy fighters near its own bomber by0.25; the
candidate must still pass the original750m3D range and physicalLOS. No enemy
intent is read and no hidden target is committed. Cell radius3 now covers that
750m range; the existing8air-ID reservoir remains and can omit crowded targets.
Mission state joins the authoritative hash; derived heads/links do not. No actor
pose, HP, ammunition, projectile or simulation clock is refreshed by the planner.

Current private compatibility: UDPv20/schema0xf1a4fcab/content0xe84a7d53,
canonicalSHA256 e84a7d5337a91b2c61c92c29e84ee0afe95d37e9afc3226d3ea9e059a38895ed.
Wire layouts remain unchanged. Both independent content reconstructions include
the mission constants and fighter acquisition envelope. Remote clients see actual
flight through existing self-contained aircraft poses; mission UI is not present.

Original aircraft/bomb release/air-admission tests passed before the final
near-expiry renewal edit; that earlier result is not final-source acceptance.
Matching focused mission tests pass1800public ticks. Two300tick following replays
close700m to130.399m with3600.002m combined travel and108 banked fighter ticks,
unchanged speeds/stores/HP and bounded yaw. Getter ABI/output/authority guards
cover invalid IDs, generations, roles, side/front, empty stores and invalid speed.
Both side labels choose the farther bomber threat over the nearer decoy. Four
cardinal650m targets are acquired; an assembled adjacent-cell control misses all
four. Original800m exclusion remains. A matched priority-disabled NASM control
chooses the decoy; production chooses the threat and inflicts24 actual damage.

In the controlled600tick contested runs, both bombers spend exactly one of eight
stores, release at tick26 and kill the ground target at176. All three fighters
launch genuine rounds from finite stores. Both bombers survive at200HP and the
friendly escort dies in both runs. This proves target preference and productive
physical gun/bomb action, not a survival benefit or universal competent tactics.
No in-flight HP/pose/ammo/clock fixture updates occur; corrupt getter fixtures are
separate. Exact logs/source hashes: docs/evidence/air-escort-*.

Fast/full/scale, co-op graphics and human quality acceptance are pending. Timed
company strikes, explicit player-designated air missions, visible mission intent,
formation capacity/ownership and target-generation sidecars remain open. Friendly
nearest scans are periodic and spatially local but can be costly for pathological
all-aircraft scenes; no task budget or exhaustive enemy perception is claimed.
This candidate is not integrated; licensing/publication status is unchanged.
