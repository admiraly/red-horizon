# Isolated wreck row-search candidate

Based on accepted b0d1055/07d6536, this candidate preserves the existing 128×128,
62.5m centre grid. For each row it intersects the segment with that row's padded
Z band, then searches only the projected X interval. Double precision and an
extra 4mm allowance make the projection conservative. Original all-record
source validation, pose memoization, inflated slab tests, continuous escape
policy, stable contact ties and query output remain in force. Horizontal rays
use the existing rectangle. No combat timing, radius or actor stores change.

The unchanged transformed-corner oracle now additionally checks 256 long,
reverse, nearly horizontal and outside-map paths. The full-map diagonal visits
27 of 1,024 records; coincident geometry still visits all 1,024. All 2,000
original short-path comparisons, 33 invalid callers, 14 malformed sources,
lifecycle cases and three assembled negative controls pass. The body oracle
retains 2,500 original paths and adds 176 exhaustive long paths across original
radii 0/.551/3.551/4.491. Its escape and malformed-radius controls pass. The
explicit-context test passes 401 calls, cache-key negatives and real remote
receive/expire/retire/reset lifecycle checks. See the three wreck-row logs.

`tools/probe_wreck_row_query.py` copies baseline objects into a private temporary
folder and replaces only the query object. Both shared libraries are immutable
throughout each paired run. It alternates tick order and compares authoritative
checksums plus every entity byte each 30 ticks. Timings are local development
wall time, with a separate frozen integration checkpoint running concurrently.

This candidate is not integrated. Whole-runtime timing and routine fast checks
must be reconciled before promotion; spatial candidate reduction alone is not
performance acceptance. These tests do not establish graphics, UDP, every
actor pair, human quality or complete game-spec acceptance.

The initial 900-tick paired run preserves all 90 sampled world hashes and every
entity byte. Mean/p95 milliseconds (baseline→row) are 8k open
10.847/12.890→11.140/13.165, 8k hotspot32.363/38.461→27.790/32.859,
and 16k open24.029/29.748→24.667/30.223. Dense benefit has a small open-scene
regression; these are not reference hardware or graphics budget claims.

Initial330cc74 frozen fast e6091687a43d PASSED208.1878s. A subsequent small
rectangle fallback scans at most three columns directly, avoiding projection
cost for short rays. All same focused oracles pass at query sourceSHA256
 ecc446760d8c9fc9b84a717b7bac6df3cccad52380c2c3bc8e5f536234051bbb.
Its second900tick paired run again preserves90 hash/all-entity samples:
8k open mean/p9510.675/12.655→10.719/12.703ms;8k hotspot31.520/37.618→
27.270/32.387ms;16k open23.310/28.690→23.341/28.626ms. Open mean cost is now
within0.5% in these samples. This later runtime is not covered by the earlier
fast result and requires a matching coherent integration checkpoint.
