# Road handling gameplay outcomes

Root integration supplement: source `a429a7d` passed full frozen extended job
`2804557c94cf` (497.18s, 76 reports, 158 matched authored inputs).
Exact current scope, archived public traces and remaining limits are in
`status.md` and `evidence/ground-surfaces-session.json`. The worker-only proofs
below retain their original source scope. The earlier held-artillery failure is
resolved by bounded steering preview at root; road-preferring routing and steep
slope handling remain unimplemented.


`tests/test_ground_surface_outcomes.py LIBRARY --report REPORT` observes the actual public authoritative gameplay path. It sends orders, boards tanks, calls `player_input`, and advances `sim_tick`. It never calls `ground_step`, `terrain_surface`, or `terrain_road_body`, and never writes motion sidecars or future motion state.

Sparse fixtures place one legitimate tank or artillery birth, increment its generation, choose a long forward waypoint, and let a real tick seed the hull. Other initial fixture entities are absent. Health is not renewed; production combat and hazard policy are unchanged. These fixtures establish local handling and do not establish dense battle performance.

The observer independently reads canonical road geometry and evaluates point-to-segment distance. A hull counts as road-supported only when its whole documented circle fits within one road capsule. The test covers paired road/off-road AI tanks and artillery and player-driven tanks, first acceleration and sustained travel, centre-on-road bodies extending past an edge, different tank/artillery fit at a finite endcap, a diagonal dogleg, both boundaries during a real crossing, braking without an instantaneous speed clamp, reverse, unchanged braking and yaw at equal incoming momentum, AI/player/AI control transfer, camera and cannon independence, and exact same-build crossing replay. Every tick checks actual displacement against the stamped heading, signed speed and accepted velocity, finite authority, bounded turn and bounded speed changes.

The negative mode `--legacy` uses the immutable pre-surface runtime, which already implements hull inertia. It records missing surface-dependent acceleration and travel rather than attributing old movement shortcomings to the new feature. Exact candidate and negative library hashes and outcome results belong in the integrator's evidence record after running the final observer. Existing full-scale outcomes and graphics tests remain separate evidence.

These checks do not establish slope restrictions, oriented collision bodies, suspension, wheeled vehicles, strategic road preference, rendered road appearance, target GPU performance, or artistic acceptance.

## Verified candidate and causal negative

The final observer SHA-256 is `aef7185d69ae25b096364d65db3ae199fa3f0f85d3bd317b7ebeefbbbad0e078`. Its 17 public-path cases passed against the frozen root job `d85662117334`, source revision `08cc8e5bcec407b7a8606d67935cde3582c13131-2736139ce5adb029`, library SHA-256 `eee6b5c996e4275dae2ad51c62e43d3c1f76e61bb229f6171cfb447dca3201b1`. The same observer's negative mode passed against the immutable pre-surface library from job `8e107f76cc77`, SHA-256 `d0665f8c2465991477c879b4d58fbbbe6fcbc2e6f83f314796da35dc40332bd9`, exposing 19 absent-surface handling faults. Those faults are expected negative evidence, not candidate failures.

Over 75 actual ticks, the AI tank travelled 31.500 m on-road and 25.201 m off-road; AI artillery travelled 13.097 m and 9.171 m; the driven tank travelled 36.299 m and 29.039 m. Measured first-tick road/off-road acceleration was 0.020/0.016 m per tick for tanks and 0.010/0.007 for artillery. Sustained road/off-road signed speeds were 0.500/0.400 for AI tanks, approximately 0.200/0.140 for artillery, and 0.600/0.480 for driven tanks.

During the perpendicular crossing, the first whole-body road transition occurred at source `(2000,1293.6798)` on tick 43, changing speed from 0.480 to 0.500. The exit occurred at `(2000,1306.5795)` on tick 65, reducing speed from 0.600 to 0.560; subsequent ticks settled at 0.480. The initial exit retained momentum above the off-road target while braking normally. Centre-on-road bodies at Z=1308 retained the off-road cap, and the endcap distinguished the tank's fitting circle from the artillery's larger unsupported circle. Reverse settled at −0.180 on-road and −0.144 off-road. Equal incoming momentum produced equal braking and yaw behavior across surfaces.

Camera/cannon tests checked a real `vehicle_shots` increment and unchanged driving trajectories on both surfaces. Repeating the complete public crossing produced trajectory SHA-256 `f03123f3ea51ed13ae59853b4bfc45b90a26b465c506ce1bd40465a43573b308` and whole-world checksum `844aa2d1529ebb90`. All local executions were collected synchronously with exit 0. Full per-tick evidence is `/tmp/rh-road-candidate.json`; causal-negative evidence is `/tmp/rh-road-baseline.json`. The integrator should copy these into durable project evidence and retain the final frozen integration results separately.
