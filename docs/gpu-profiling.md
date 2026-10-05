# Hardware GPU diagnostic

`python3 tools/dev.py bench --client --seed 42 --frames 600 --weather clear --background`
launches the real assembly client on the current X11/XWayland display. `--tactical`
and clear/overcast/rain/fog select the view and weather. The driver rejects software
GL contexts, records `glxinfo -B`, source revision, complete client telemetry,
CPU/GPU timing samples, an actual framebuffer screenshot and its SHA256.
Audio uses ALSA null; this does not measure physical playback.

The assembly profiler reports mean, p95 and p99 separately for frame CPU wall time
and GPU draw duration. Quantiles use the sorted nearest-rank sample. The bounded
8-query timer ring avoids blocking for unfinished GPU results; final pending
queries can be omitted. Up to10000 samples are retained; a benchmark rejects
fewer than30 or more than10000 requested frames. Warmup remains included.

The current graphical scenario is8192 initial entities, seed42, one local player,
an idle initial camera, and a1280x720 window. Simulation advances at30Hz while
rendering continues. Actors can die normally. Detail counts in exit telemetry are
the final submitted high/low/marker counts, not proof of visible pixel counts.
Swap interval1 is requested, but actual presentation pacing is compositor/driver
dependent. This measures an initial view, not dense front/hotspot or1080p acceptance.
Network rendering and streamed-map budgets require separate scenarios.

The pre-flight-change diagnostic report is docs/evidence/air-navigation-gpu-before.json.
It establishes actual Intel Arc A770 context availability on this host, rather
than reference-GPU acceptance for the complete operation.
