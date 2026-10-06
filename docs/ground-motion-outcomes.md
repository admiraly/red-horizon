# Independent ground motion outcomes

`tests/test_ground_motion_outcomes.py LIBRARY [--legacy] [--report FILE]`
observes the real assembly `sim_tick`, `player_input`, boarding/exit, and public
`vehicle_tick_player` paths. It never calls `ground_step`, a probe adapter, or
another actuator entry point. Sparse initial actor placement and generation
changes are development fixtures; the observer never writes the ground sidecar.

Acceptance joins actual positions with generation-stamped heading, signed speed,
turn and accepted velocity. Each accepted segment must lie along the current
hull axis and match its reported speed/velocity. Broad practical acceleration
and turn bounds detect immediate translation and rotation without duplicating
the actuator's exact tuning constants. Straight, perpendicular steering, released
input braking, reversal through zero, stopped heading, independent camera aim
and twelve actual cannon direction cases retain useful movement and fire gates.
AI tanks and self-propelled artillery use public orders and waypoints. Actual
boarding/exit must preserve shared moving state; generation recycling must clear
old momentum. NaN/infinite/overrange input and enemy, stale entity-generation,
or disconnected claims cannot actuate the hull. The candidate also requires a
real private player-generation claim stamp; recycling a player generation must
reject and release the old claim without changing the physical hull.

Wall contact checks the whole accepted segment against the independently expanded
authored wall. Artillery/human contact checks relative swept circles. These are
conservative planar shapes, not oriented hulls or vertical geometry. Natural
8,192/16,384-entity hotspot runs observe every living tank/artillery displacement
for 120 ticks, both with armies alone and with four legitimately boarded tanks.
The four-driver cohorts also independently check nearby relative-circle sweeps
in O(4N) observation, retain useful living driver movement, and leave armies in
their original actual formations. All cohorts preserve actual combat/HP/ammo,
require useful surviving movement, and replay exactly. They do not establish every army pair, graphics, network
heading presentation, slopes, roads, wheeled chassis or performance targets.

The existing controller and terrain observers preserve human input signs,
component amplitudes and requested contact slides. Candidate drivers instead
require real hull-axis/velocity coherence with all original relative-circle and
static-solid sweeps. At diagonal wall/circle contact the driver explicitly requests
the free-edge tangent at tick 25; map-edge fixtures start only 0.25 m from the
body inset and receive that deliberate request at tick 5. A fixed tracked hull
axis cannot autonomously slide along an edge. The six driver diagonal map-edge
and corner fixtures allow 90 ticks for a bounded pivot plus acceleration while
retaining their >5 m useful recovery gate and every swept-solid test; the original
human 50-tick inputs and progress gates remain unchanged. Historical legacy modes
disable the new ground policy together with their original crowd/terrain policy
when a ground module exists, so their old input-vector assertions retain meaning.

## Original production negative control

[Baseline report](evidence/ground-motion-baseline.json) and
[provenance](evidence/ground-motion-baseline-provenance.json) record immutable
production library SHA-256
`d547457034be364788c6eca42c42ba15c376e0b5efab2aab2bf67789085439fa`,
source `1fbe5a78f9609061abc9a1750b09c823254001b8-fdbabe9158e8279f`.
Its crowd and terrain body policies remain enabled; it has no ground module.
The public direct and world driver paths each move immediately by about 0.6 m,
instantly strafe on perpendicular input, stop with zero braking travel, and
reverse immediately by about -0.6 m. AI tanks start at 0.5 m/tick and artillery
at about 0.2 m/tick, then stop instantly on hold. These measured faults provide
causal controls for the new physical policy. Safe existing actor/static collision
checks remain zero-fault controls, rather than falsely claiming the baseline
lacks collision protection.

The baseline performs real scale combat: 1,428/2,957 original ground vehicles
survive and move more than a metre, with 1,024/1,084 army deaths respectively.
Zero heading-coherence checks are explicitly reported because this baseline
has no authoritative ground sidecar. That absence alone is not the fault proof;
the actual immediate motion measurements establish the missing behavior.

The original vehicle ownership ABI stamps entity generation, not player
generation. Its baseline explicitly reports that incrementing a retained
player's generation still actuates the tank. The candidate must protect this
through a genuine private `vehicle_driver_generation[4]` stamp, not merely the
entity-generation field in the ground sidecar. A candidate ground-policy-off
control retains this ownership protection and must reject the stale claim;
the original immutable baseline independently records the older missing stamp.
Candidate acceptance and exact evidence will be added after integrated runtime
hooks exist; this document currently establishes the observer and real baseline.

## First integrated production candidate

Root supplied immutable `/tmp/rh-ground-first-candidate.so`, SHA-256
`56f40a356a694231fe315586981ad7b4c5d9916d1bf9d4861e0061ca29015009`,
committed source `dcd5ddf`. The public-path oracle completed with exit 0 in
session 49870. Both driver APIs accelerate by measured first steps about
0.020/0.040/0.060/0.080/0.100 m, travel 27.299 m over 60 straight ticks,
and travel 4.200 m while braking after release. Reversal first continues forward
at about 0.56/0.52/0.48 m, then passes through zero to -0.18 m/tick, with no
instant signed reversal. The 90-tick AI straight cases travel 39.000 m (tank)
and 16.097 m (artillery), then retain nonzero physical braking. Twelve real
shell direction cases, actual AI/driver/AI continuity, malformed input, recycled
entity claims and the newly stamped recycled-player claim all pass.

The four natural 120-tick scale cohorts perform respectively
178,387/178,672/363,636/363,307 surviving ground-vehicle coherence checks, with
zero faults. Their 8k/16k four-driver cohorts record 479/451 moving driver ticks
and 96/88 nearby relative sweeps with zero introduced/deepened overlap; actual
army combat continues. Exact replay is checked for every case and scale cohort.
The same candidate with only `ground_enabled=0` reproduces acceleration,
perpendicular-strafe, immediate-stop and immediate-reversal faults, while keeping
the independent new player-generation ownership protection active (session 85936,
exit 0, scale control scope 30 ticks).

These first-candidate outcomes prove the integrated public controller and AI paths,
not the later direct-kernel stamp follow-up or final release checkpoint. Root's
frozen full-suite, real graphics/network, and final source reconciliation remain
required. The evolving driver fixture changes are recorded separately rather
than claiming their inherited instant-slide semantics still apply to tracked hulls.
