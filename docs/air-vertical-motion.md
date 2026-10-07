# Aircraft vertical response

The aircraft actuator slews vertical velocity toward the existing mission request
at a role-specific acceleration. It computes horizontal speed from
`sqrt(total_speed² - vertical_speed²)`, and publishes pitch from
`atan2(vertical_speed, horizontal_speed)`. The heading-aligned XYZ displacement
therefore uses one conserved total airspeed. Bombs still inherit the actual XYZ
velocity; cannon rounds still follow the physical nose at their existing speed.

At the fixed 30 Hz step, bomber vertical acceleration is bounded to
0.012 metres/tick² (10.8 m/s²); fighter acceleration is bounded to 0.024
metres/tick² (21.6 m/s²). The existing vertical envelope remains ±0.5 metres/tick
(15 m/s), and cruise speeds remain 5 and 7 metres/tick (150 and 210 m/s).
A complete +0.5 to −0.5 reversal now takes 84 bomber ticks or 42 fighter ticks,
rather than one tick. These limits are canonical content policy.

`air_vertical_step` is a pure NASM/SSE2 helper. It rejects invalid role, nonfinite
inputs, speed outside 5–7 and requested/previous vertical velocity outside the
existing envelope, returning −1 and three zero floats. Success returns the new
vertical velocity, horizontal speed and pitch. It allocates nothing and writes
no authority. The caller owns publishing actual flight pose and velocity.

Entity32, aircraft64, player64 and the UDP wire layout are unchanged. AIR_SPEED
now consistently means total XYZ airspeed; changed content policy rejects mixed
peers through the existing NET_CONTENT check. The aircraft producer now previews
terrain clearance at the prospective horizontal step, then commits displacement
using the computed horizontal component.

This is a bounded kinematic flight improvement. Coordinated level turns still
use the existing bank/yaw approximation. Thrust, drag, aerodynamic lift, energy
loss in hard turns, fuel, stalls, landing, rearm, air separation, sustained steep
climbs/dives and tactical manoeuvre selection remain required work. No complete
flight-realism or spectacle acceptance follows from these checks.
