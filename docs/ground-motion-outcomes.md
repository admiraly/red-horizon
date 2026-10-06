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
20.3 m clear goals additionally require useful approach, arrival within 0.6 m
at 120 tank/240 artillery ticks, and less than 0.03 m motion throughout the final
ten ticks; passing briefly through a goal does not establish a settled arrival.
The older crowd observer's held-armour/artillery and wall-route deadlines remain
unchanged and independently constrain detour progress.
Actual
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
The following first-candidate evidence is preliminary to root's final frozen
checkpoint; the full game goal remains incomplete.

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

The adapted controller observer completed in session 66350 with exit 0, retaining
29 controlled relative-circle cases, four crossing-controller configurations,
placement controls and natural 8k/16k mixed-controller combat sweeps. The adapted
terrain observer completed in session 38438 with exit 0: 33 controlled cases,
exact replay/faction comparisons, original arrival gates, and natural 8k/16k
120-tick expanded-solid checks. All nine driver cases have zero whole-solid
sweep and hull-axis coherence faults. The original inherited fixed-diagonal
slide fixture failed the tracked candidate before explicit steering was added;
the original 50-tick driver corner interval then proved too short for a bounded
pivot plus >5 m travel. Those driver-specific fixture semantics changed explicitly
as described above; human inputs/deadlines and physical penetration gates did not.

All worker-launched builds and observations are terminal, including baseline
build 12104, baseline observations 46891/73477/17642/58615/43269, historical
controller preservation 88234, historical terrain preservation 93711, candidate
ground 49870, candidate controller 66350, candidate policy-off 85936, failed
short-corner terrain 6845, and accepted terrain 38438. The initially unsuccessful
fixture observations were diagnosed before adaptation, never accepted as passes.

## Terminal approach review and later integrated candidate

The pre-convergence `a8fd4b7` library SHA-256
`e3b747db996dfde955cdb3b5e0dd3143a659611ed20c197929385840953fd0cd`
passes collision checks but fails the new clear-goal tank settled-arrival gate:
its maximum displacement over the last ten of 120 ticks is 0.2800 m. The exact
[negative control](evidence/ground-motion-baseline-preconvergence-arrival.json)
records actual pose/state and the failed assertion. Its artillery result is only
just below the 0.03 m late-motion gate. Root's original held-armour outcome also
exposed overshoot; none of its arrival tolerances or deadlines were removed.

Independent source review of actuator change `d1cf007` confirms it preserves
the original supplied navigation-goal range before the one-tick crowd steering
point replaces the local target. AI terminal speed uses that range while the
whole accepted segment still follows the bounded hull axis. The 0.15 gain begins
normal tank braking at about 3.333 m and normal artillery braking at 1.333 m,
ahead of their maximum steady AI discrete stopping travel of 2.88/0.7 m.
The enlarged 60-degree translation steering arc retains the prior role speed,
turn-rate and collision bounds. This remains a practical planar approximation;
it does not prove oriented hull dynamics, suspension or road/slope handling.
An AI handoff inheriting driver speed 0.6 can physically overshoot a newly
requested very close goal, so no universal no-overshoot handoff claim is made.
World manual hold supplies exactly current XZ and uses bounded shared braking;
review found no alternate hold bypass. Goal-range scratch is temporary; all
existing 32-byte persistent records and policy, plus the private player claim
stamps, remain covered by authoritative hashes.

Root's integrated `b53b7cd` immutable library SHA-256
`a1ca4eb6f6953211be63238d4a6194f40cf09f5f3d197487ea868248480eda77`
passes the complete current ground observer (session 93742, exit 0). Clear tank
arrival error is 0.00679 m with maximum late motion 0.001365 m; artillery error
is 0.000928 m with zero late motion. The four natural replayed scale cohorts
perform 178,246/178,928/363,243/363,274 surviving hull coherence checks, all with
zero faults, while actual combat and useful living motion remain. Refreshed
original baseline session 49510 is terminal exit 0 and retains the exact new
observer hash. Root's final full frozen checkpoint remains a separate requirement.
