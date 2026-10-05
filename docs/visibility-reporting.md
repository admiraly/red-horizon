# Pixel visibility reporting

The development driver accepts `--census` for bounded client runs and GPU
benchmarks. The client captures the final frame in an additional actor-ID pass;
submitted instance telemetry remains separate. Examples:

```sh
python3 tools/dev.py run --client --scenario scale-hotspot --frames 120 --census
python3 tools/dev.py bench --client --scenario scale-hotspot --seed 42 --width 1920 --height 1080 --frames 600 --census
```

A client run requires explicit `--frames 1..10000`. A GPU benchmark defaults to
600 frames and retains its existing 30..10000 profiler range. Headless use and
`--client --headless --census` fail before building. Unbounded runs do not silently
ignore the flag.

The report must contain exactly one JSON object marked `visibility_census: true`.
Required fields are `width`, `height`, `visible_actors`, `visible_high`,
`visible_low`, `visible_markers`, `individually_detailed_actors`, `source_tick`,
`invalid_codes`, and `readback_reduce_ms`. The driver checks requested dimensions,
integer bounded counts, mutually exclusive class totals, high-plus-low model
count, unsigned authoritative source tick, zero invalid actor codes, and finite
nonnegative cost. Missing, malformed, duplicated rows or duplicated JSON fields
fail instead of producing a successful benchmark with invented counts. Additional
capture metadata is retained verbatim.

Counts describe distinct actor IDs with surviving pixels in the opaque world
pass, including opaque weapon occlusion, before translucent effects and HUD.
High and low geometric models count as individually detailed; markers are
reported separately. These are actual final-frame pixel counts, not frustum
membership, submitted totals, a peak, or sustained visibility. The census alone
does not prove engagement, audible sound, visual quality, or the full hotspot
contract. Captures without a requested census retain `unmeasured` visibility and
only submitted final mesh telemetry for detail.

GPU benchmark JSON preserves the complete census object and maps its counts into
coverage. The extra final-frame allocation/draw/readback/reduction is excluded
from ordinary frame CPU/GPU timing; the module reports readback/reduction cost
separately. A benchmark's wall time still includes all executed work. Physical
ALSA output/listening remains unverified when the benchmark uses the null device.

Worker validation: `python3 tests/test_dense_driver.py` passes 15 development
mock tests for forwarding, scope errors and report rejection. These tests do not
execute NASM rendering, establish a GPU visibility count, or validate timing
exclusion. The integrator must verify those properties against the actual client
and record the exact revision and artifacts in `docs/status.md`.
