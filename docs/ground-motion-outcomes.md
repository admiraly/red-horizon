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
or disconnected claims cannot actuate the hull.

Wall contact checks the whole accepted segment against the independently expanded
authored wall. Artillery/human contact checks relative swept circles. These are
conservative planar shapes, not oriented hulls or vertical geometry. Natural
8,192/16,384-entity hotspot runs observe every living tank/artillery displacement
for 120 ticks, preserve actual combat/HP/ammo, require useful surviving movement,
and replay exactly. They do not establish every army pair, graphics, network
heading presentation, slopes, roads, wheeled chassis or performance targets.

The existing controller and terrain observers preserve human input signs,
component amplitudes and requested contact slides. Candidate drivers instead
require real hull-axis/velocity coherence with all original relative-circle and
static-solid sweeps. At diagonal terrain contact the driver explicitly requests
the free-edge tangent at tick 25; a fixed tracked hull axis cannot autonomously
slide along an edge. Useful recovery remains required. Historical legacy modes
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

The existing vehicle ownership ABI stamps entity generation, not player
generation. This observer does not assert that merely incrementing the player
generation invalidates a retained claim, and does not claim that protection.
Candidate acceptance and exact evidence will be added after integrated runtime
hooks exist; this document currently establishes the observer and real baseline.
