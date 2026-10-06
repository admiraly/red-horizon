# Road handling gameplay outcomes

`tests/test_ground_surface_outcomes.py LIBRARY --report REPORT` observes the actual public authoritative gameplay path. It sends orders, boards tanks, calls `player_input`, and advances `sim_tick`. It never calls `ground_step`, `terrain_surface`, or `terrain_road_body`, and never writes motion sidecars or future motion state.

Sparse fixtures place one legitimate tank or artillery birth, increment its generation, choose a long forward waypoint, and let a real tick seed the hull. Other initial fixture entities are absent. Health is not renewed; production combat and hazard policy are unchanged. These fixtures establish local handling and do not establish dense battle performance.

The observer independently reads canonical road geometry and evaluates point-to-segment distance. A hull counts as road-supported only when its whole documented circle fits within one road capsule. The test covers paired road/off-road AI tanks and artillery and player-driven tanks, first acceleration and sustained travel, centre-on-road bodies extending past an edge, different tank/artillery fit at a finite endcap, a diagonal dogleg, both boundaries during a real crossing, braking without an instantaneous speed clamp, reverse, AI/player/AI control transfer, camera and cannon independence, and exact same-build crossing replay. Every tick checks actual displacement against the stamped heading, signed speed and accepted velocity, finite authority, bounded turn and bounded speed changes.

The negative mode `--legacy` uses the immutable pre-surface runtime, which already implements hull inertia. It records missing surface-dependent acceleration and travel rather than attributing old movement shortcomings to the new feature. Exact candidate and negative library hashes and outcome results belong in the integrator's evidence record after running the final observer. Existing full-scale outcomes and graphics tests remain separate evidence.

These checks do not establish slope restrictions, oriented collision bodies, suspension, wheeled vehicles, strategic road preference, rendered road appearance, target GPU performance, or artistic acceptance.
