# Exact wreck-query envelope rejection — isolated candidate

Based on relevance prototype0b224d6, not main. Profiling replaces only direct
sim_tick calls in a development build with LFENCE/RDTSC wrappers. Production and
instrumented authority checksums agree every30ticks through900ticks in8k open
and8k hotspot worlds. Inclusive direct-call measurements put world_los at47.7%
and83.1% respectively; nested costs belong to those calls and outer loop work
is not included. Instrumentation itself adds overhead. No target-GPU claim.

Validated cached wreck bounds now reject candidate boxes outside the swept
endpoint envelope before expensive full slab/escape tests. Inflation uses the
original f32 radius arithmetic. A conservative4mm numerical allowance exceeds
f32 delta rounding at the allowed16km coordinate magnitude; survivors still use
the unchanged complete intersection and initial-overlap escape. This allowance
only admits extra expensive tests, never changes the physical skin or radius.
Active source validation and nearest identity/tie selection are retained.

Independent transformed-corner/nearest-contact, malformed-caller/source and
lifecycle tests pass. The original2,514 body cases,2,500 random paths and821
nondeepening-overlap cases pass, as do explicit source/revision switches and
actual network-cache lifecycle tests. The final focused terrain-body suite
passes. An initial exploratory suite overlapped a local source edit and is
excluded from exact-source acceptance despite exit0.

Paired alternating-order900tick hotspot worlds produce equal authority hashes
every30ticks and identical wreck records.36,772 direct query results, including
radius/boundary probes, are byte equal;23,790 hit. P95 is41.315ms baseline versus
35.065ms envelope; means34.454ms versus29.529ms. Both worlds have identical
physical state, but concurrent verification can affect timings. Hotspot still
exceeds33.3ms; this does not prove isolated hardware or full operation acceptance.
The first comparison failed only because a development observer converted a
signed-byte slice to bytes; the exact rejected log remains. The corrected
unsigned-byte observer passes. No runtime assertion was weakened.

Exact reports, artifact/source hashes and logs are docs/evidence/wreck-envelope-*
and wreck-sim-pass-profile.*. Full frozen verification is required before main
integration. The next large gameplay batch remains a demonstrated coordinated
assault with scoped intelligence and readable combined-arms behaviour.

Integration continuation: full97b74ea394b4 PASSED1036.1949782849988s,
125reports; all282 frozen authored inputs match main at integration. The
coherent batch includes VERSION2 relevant wreck vertices, the exact query
envelope, exterior deployment and the real Escape callback latch. Private
candidatev17 is now the integrated compatibility version. Exact full result,
source comparison and prior failed checkpoints are retained in
 docs/evidence/wreck-dense-routing-jobs.json. Earlier pending wording describes
pre-checkpoint history. Performance/playtest and site-building hull limits remain.
