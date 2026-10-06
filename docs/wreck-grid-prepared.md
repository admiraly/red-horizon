# Prepared finer-grid cost experiment

Isolated feature/wreck-query-grid retains the same pose bounds, segment clip,
identity tie, lifecycle invalidation and no-authority-write contracts. Only center
bucket geometry changes:128×128 cells at62.5m instead of32×32 at250m. Derived
memory rises from32784 to94224bytes; the worst full-map rectangle now visits16384
heads, although candidate records remain bounded1024. This is not integrated main
source and is not included in its full checkpoint.

The full component observer passes2063calls,1024transformed bounds,8628actual
frame0 vertices,2000nearest paths, malformed/lifecycle/ABI and assembled negatives.
Uniform short paths visit at most two records instead of four. All1024 coincident
records still require1024 candidates; this variation cannot remove unavoidable
coincident pressure.

The actual frozen current world is replayed unchanged900ticks at8192/16384,
producing813/930natural wrecks. Only wreck_query's object is replaced; all other
frozen object hashes are recorded. Full checksums match sampled30tick boundaries
and both final complete registries match byte for byte. Every measured first
contact output matches the accepted250m grid exactly; queries preserve authority.

For20m X-axis paths around every natural wreck, mean candidates change141.950→
17.503 and120.758→16.328; peaks484→62 and429→68. Alternating warm40group
measurements change group mean1.5437→.9408ms (813queries/group) and1.6799→
1.0762ms (930queries/group). The reference is the frozen full-checkpoint library;
Python/ctypes/assert overhead is included and first rebuild excluded. These are
controlled query probes, not actual cover/body/server tick budgets or guaranteed
speedups in every ray distribution. Long rays can scan16times more empty heads;
long-ray/DDA policy needs separate measurement before general LOS activation.

`tools/bench_wreck_grid.py` reproduces the object-substitution and real-world
comparison. The integrator retains source/hash/reports separately. Selection of
this grid for a future complete cover batch should preserve the full original
physical/health/arrival/graphics/network gates and measure mixed query lengths.
