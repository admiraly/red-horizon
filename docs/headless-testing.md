# Headless verification

Run the full suite without an existing desktop:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY python3 tools/dev.py test --suite all
```

Requirements: NASM2.16.03, GCC/libc, Python3, GLFW3.3+, Mesa OpenGL4.5, ALSA, Xvfb, libX11, libXtst. Ubuntu packages are listed in the local CI workflow. Fedora Xvfb package is xorg-x11-server-Xvfb. The graphics harness starts only its own private Xvfb with displayfd, disables TCP listening, forces software rendering, uses ALSA null, and stops that server in finally. It never sends input to the user's display.

`--suite headless` runs simulation, operation, waypoints, terrain/LOS, tactics, authoritative players, replay/bounds, reload, audio, proof UDP and actual co-op/adapter, tool/dependency/frozen-source and asset checks without window/GPU dependencies. `--suite graphics` runs the actual assembled client, shader compilation, first-person/tactical frame export and XTest controls on the private software display. Individual suites: simulation, reload, audio, network, tools. Add --background for an immutable source snapshot, job ID/log/result; collect JOB_ID reports terminal status.

The real assembly client submits8192 entity instances and12site markers. The graphics test checks nonblank framebuffer output in both views and uses the actual input path to test movement, automatic fire/magazine exhaustion, R reload blocking/refill, front selection, tactical waypoint acceptance/outside-bound rejection and Escape. The Python driver contains no game simulation or renderer. Screenshots, process logs, software renderer information, frame/GPU-query telemetry and controls results are stored under runs/headless-graphics-*. Background jobs keep these under their frozen source runs directory.

Profiler: src/render/metrics.asm uses a bounded8query GL_TIME_ELAPSED ring without blocking for query completion, and monotonic CPU wall samples (up to10000 each). CPU sample covers event/input/simulation/draw/swap work; the final screenshot sample also includes readback. GPU sample covers submitted render work; outstanding last queries are omitted. CPU includes swap pacing, not isolated CPU occupancy. Counters distinguish CPU/GPU sample counts. These are raw smoke measurements, not1080p reference-machine budgets, dense-hotspot performance, or particle/audio benchmarks. Actual hardware and software runs must remain separate.

Integrated headless graphics job3a04b8fcebf8 at source d9e86f5-38c61ecced0b6b06 passed two30frame views and controls in11.78seconds. XTest controls reported33shots,27rounds,1reload,front1,1waypointorder and goal4994.375/3904.444metres. A prior full CPU-only run with DISPLAY/WAYLAND_DISPLAY unset, job5dc88139d924, passed in13.45seconds. These results identify earlier integration inputs; the final session suite records a newer immutable revision/hash.

Coverage limits: physical audible output, target GPU budgets, gameplay co-op latency matrix, Windows, hierarchical navigation, strategic pacing, art quality, accessibility and human engagement require additional tests. Software images and null-device audio do not establish those properties. Current full tests exceed the10second iteration goal: scale/replay cases, a2second UDP inactivity case and real-time magazine/reload input account for substantial time. Focused suites provide the fast loop; splitting FAST versus SCALE is ready work.
