# Pixel visibility reporting

The development driver accepts `--census` for bounded client runs and GPU
benchmarks. The client captures the final frame using an actor-ID attachment alongside the normal geometry draw;
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
`invalid_codes`, `readback_reduce_ms`, `authority_readonly`, `authority_before` and `authority_after`. The driver checks requested dimensions,
integer bounded counts, mutually exclusive class totals, high-plus-low model
count, unsigned authoritative source tick, zero invalid actor codes, and finite
nonnegative cost and identical sixteen-digit authoritative checksum strings. Missing, malformed, duplicated rows or duplicated JSON fields
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
coverage. Allocation occurs at startup. Final-frame MRT drawing and the pre-draw checksum
are included in the last CPU frame. Readback, reduction, blit, map writing and
reporting happen after that frame timer ends; the separate measured cost covers
readback/reduction only. The GPU timer may omit its final eight pending queries,
including the capture draw. A benchmark's wall time still includes all executed work. Physical
ALSA output/listening remains unverified when the benchmark uses the null device.

Worker validation: `python3 tests/test_dense_driver.py` passes 16 development
mock tests for forwarding, scope errors and report rejection. These tests do not
execute NASM rendering, establish a GPU visibility count, or validate timing
exclusion. The integrator must verify those properties against the actual client
and record the exact revision and artifacts in `docs/status.md`.

`--census-map PATH.r32ui` optionally saves the actual raw uint32 attachment. It
requires `--census`; dimensions and source tick are in the census JSON. This
allows an independent decoder to inspect exact actor IDs rather than only totals.
Production GL fixtures verify exact IDs/LOD, terrain/prop/actor occlusion and
authority immutability. A frozen normal/census image pair differs by at most
2/255 per colour channel; exact byte identity is not claimed.
