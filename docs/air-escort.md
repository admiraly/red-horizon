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

Frozen fast f604660e9502 PASSED266.7072s at1c8ceb1-e6a5f9beaf846fcc,
including final-source original core/air/admission/motion checks. The actual
rendered-aircraft test passes production gun/bomb encounters, banking/silhouette,
trails, real impacts and aircraft destruction, with paired cosmetic authority
controls. A first command used the copied executable without its asset directory
and exited at startup; corrected immutable bundled execution passes. Two actual
frames were losslessly transcoded and inspected: level bomber silhouette is
recognizable; the destruction test frame has sparse small effects. Neither the
controlled sparse view nor pixel counts establishes spectacle/human-quality
acceptance. Client artifact/log hashes are recorded with the evidence.

Paired900tick production worlds on immutable v19/v20 libraries, seed42:
mean/p95ms baseline→mission,8k open16.398/19.216→16.397/19.297,
8k hotspot36.894/48.287→36.764/47.952,16k open34.861/43.347→35.098/44.704.
Gameplay/hash changes are expected; timings do not isolate one decision cost.
The candidate has138 valid living escort bindings at tick900 in the measured
16k open world. Dense/stretch remain above33.3ms. This is concurrent local CPU
wall timing, not GPU/network or reference-hardware acceptance. Scope, exact
library/source hashes and both worlds' health/stores/mission samples are in
 docs/evidence/air-mission-scale.json. No in-flight state renewal.

Matching full verification, co-op mission graphics and human quality remain pending. Timed
company strikes, explicit player-designated air missions, visible mission intent,
formation capacity/ownership and target-generation sidecars remain open. Friendly
nearest scans are periodic and spatially local but can be costly for pathological
all-aircraft scenes; no task budget or exhaustive enemy perception is claimed.
This candidate is not integrated; licensing/publication status is unchanged.

Initial fullcccb5e085005 FAILED613.2558s at the independent test_coop.py
schema/version/content constants, which remainedv19 while runtime/header correctly
advanced tov20. Independent content reconstruction had the new mission fields,
but the literal test header tuple was not updated. Corrected explicit literals
arev20/0xf1a4fcab/0xe84a7d53. Actual180tick8192army co-op checks now pass against
the exact failed-checkpoint server/adapter, including1195 airXZ refreshes. No
runtime source changed. The failed full result remains retained; rerun required.

Matching frozen fullac6766acbf40 passed1156.8059s at28de6f2-ecb28980ca2626e3. The complete authored-input comparison and structured report census are in docs/evidence/air-escort-integration.json. This verified escort batch is now integrated in main; the separate physical bank/retry candidate is not included.
