# Native army renderer measurements

The client now accepts bounded `--hidden --frames 1..10000`, `--no-vsync` and
optional `--frame-cap 30..240`. Hidden GLFW windows remain unmapped; actual X state,
viewport/framebuffer size, GL renderer and requested swap interval are reported.
The dev benchmark verifies that actual client settings agree with its request and
that the client renderer is hardware accelerated. Swap interval request is not
claimed to establish compositor pacing on a hidden window.

Frame capping is assembly-owned absolute CLOCK_MONOTONIC sleep outside CPU work
profiling. It retries EINTR at the same deadline, never spins, and rebases after a
full-period miss to avoid catch-up bursts. It does not alter simulation clocks or
bodies. Native30/60/240Hz tests, an interruption, a deliberately late frame,
invalid/disabled caps, actual hidden/visible windows and three complete8192
software render runs pass. A first software test wrongly required sleep despite
real frames exceeding the requested period:0waits/79rebases/errors0. The corrected
scope accepts overload; separate native deadline tests prove actual sleeping.

Final benchmark command per scenario:

```
RED_HORIZON_NASM=.tools/nasm/nasm python3 tools/dev.py bench --client \
  --scenario scale-hotspot --seed 42 --frames 600 --width 1920 --height 1080 \
  --fov 70 --hidden --no-vsync --frame-cap 60 --census
```

Runs are real live local-solo armies, not renewed/frozen actors or clocks. Hardware
is i7-14700K and Mesa Intel Arc A770, Mesa26.2.3/OpenGL4.6,1920x1080,70degree vertical
FOV, clear weather, ALSA null and one project simulation thread. Driver thread count
is unmeasured. A frozen full checkpoint was independently observed live during this
work; CPU affinity/concurrent runnable load were not controlled. Each final run
has600CPU samples/592completed GPU queries and about10seconds of elapsed play,
with no warmup exclusion. Last pending GPU queries and diagnostic census readback
are excluded from ordinary draw/work timing. Cap wait is outside work metrics.

| Scenario | CPU work p95/p99 ms | GPU draw p95 ms | Simulation phase p95 ms | Final visible / detailed |
| --- | --- | --- | --- | --- |
| Open |17.033 /20.606 |1.278 |15.598 |480 /466 |
| Front |16.085 /17.088 |1.323 |14.948 |960 /196 |
| Hotspot |22.904 /24.064 |1.492 |21.600 |827 /740 |

Rendering/routes phase p95 is1.140/1.006/.980ms and PCM-pump phase .237/.224/.230ms.
Phase percentiles are independent and must not be added. Simulation includes the
fixed-step loop per frame, including no-tick frames; rendering includes sync,
queries, cosmetic routing, submission and battle metrics. Audio pump is separate.
Other input/swap/driver costs remain in overall frame work. These measurements
identify synchronous simulation as the dominant observed local frame cost.

Earlier uncapped600frame runs covered only about1second and reached1739/1418
front actors/models and1430/1229hotspot actors/models at final readback. They are
retained as initial density evidence, not sustained performance acceptance.
During paced front play the player died and redeployed: final camera920/1300 and
generation2 differ from the authored starting view. Hotspot remains generation1
at3452/2300; finite combat/movement also changes its density. No health or camera
renewal was used to maintain a convenient result. Peaks of submitted models,
engagements, effects and voices need not coincide or be visible at final readback.

The baseline p95<16.7ms target remains unchanged and is missed in open terrain.
A provisional separate dense engineering target is p95work<=25ms/p99<=33.3ms on
this hardware/configuration, subject to proving the actual1024-visible stress
condition. This does not weaken the baseline60FPS target or certify the whole
operation. The final hotspot readback has only827visible actors, so this batch
cannot prove sustained1024-visible density acceptance. GPU timings leave room for
more visual work in these cases, but full frame latency, physical audio, native
simulation-thread performance,1-4client costs and30-60minute operation remain open.

Next optimization: separate local simulation scheduling from renderer scheduling
or measure/use the existing dedicated-authority path. Preserve full army state,
knowledge rules, update rates, finite stores and all fault/scale gates. Do not claim
performance by reducing AI decisions or replacing real actors with counters.

Exact stage reports, pinned executable hashes, failures and final source hashes
are in `docs/evidence/native-render-focused.json` and its referenced JSON/logs.
