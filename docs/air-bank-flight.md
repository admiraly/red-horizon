# Coordinated bank and staged strike candidate

This isolated v21 candidate is not integrated. Runtime is NASM/SSE2 with libm;
Python is development observation only. Escort v20 remains the verified main.

A pure validated flight helper rolls at most0.06/0.1 radians per tick and derives
yaw from -0.0109*tan(bank)/horizontal speed at30Hz. Positive authored bank raises
the local+X wing, so heading turns the opposite direction. Horizontal speed
remains5/7 metres per tick; original yaw bounds0.025/0.04 remain. Normal maximum
bank is1.35/1.45 radians, emergency1.4/1.45. Pitch follows atan2(vertical velocity,
horizontal speed). The existing half-metre vertical bound remains. This is a
coordinated kinematic approximation, without thrust, stalls, fuel or separation.

Fighter steering solves the XZ projectile intercept equation using actual observed
target velocity and28m/tick round speed. Rounds still travel along the nose and
use real swept contact. Original750m range, LOS, stores and capacity remain.

A40byte per-owner strike record contains last observed XZ, target identity/
generation, owner generation,2400tick expiry, original approach direction and
stage. Only real range/LOS observation refreshes it. Recall does not read hidden
enemy state. Damage abort stages1800m behind the remembered objective; arrival
within150m starts a straight strike, and100m overshoot resets staging. A4byte own
boundary latch keeps centre steering until both axes return inside1200..6800.
All persistent fields participate in hash and initial/new-generation clearing.
Wire layouts remain unchanged; compatibility is deliberately v21, schema
0x3296bf93, content0x551748ea, canonicalSHA256
551748eabefaa269c2c67d31e1339dc3de4fb82a7fa2ca725f71461be70a1973.

Focused aircraft suite passes: original continuous motion/yaw/perception,
surviving-damage commitment/recovery/generation checks, bombing, finite stores,
replay and admission negatives. Default8192/900ticks produces6 releases,6impacts,
4021gun launches and4air destructions. No authority replenishment or pose writes.
The independent helper observes2020 equation cases/17invalids and preserves ABI;
actual assembled wrong-sign/instant-roll controls disagree2015/1930times.
Eight public aircraft traces run twice for4000ticks/32000actor steps, with maximum
yaw-equation error2.7844e-7 and minimum edge clearance77.5725m.

The old600tick contested escort strike expectation fails: improved fighter gun
contact aborts the first pass. Both policies have finite genuine damage, eight
unspent bombs and an intact objective at600. Without recall the actual assembled
control still has no strike at1500; production releases at1147 and destroys the
objective at1297, spending one bomb. Priority still selects the protected threat
and damages it24HP more than the disabled-priority control. The production bomber
has128HP versus176HP in that control; no general survival advantage is claimed.
The candidate explicitly changes this fixture's horizon to1500 and adds the
physical no-recall control. Original army motion/symmetry/held-arrival/recovery
thresholds remain unchanged. Original failure logs are retained.

The inherited-velocity bomb fixture declares its initial heading toward its
10m-offset target, avoiding an instantaneous first-frame yaw assumption. Both
old v20 and candidate pass this same birth fixture with3.8719/3.9845m impact error
under the unchanged6m threshold, four side/climb/descent cases and1004 root cases.
No in-flight fixture renewal occurs.

New broad corner observation caught a real late boundary failure at1991ticks;
the boundary latch fixes that trace. Artificial diagonal outward births only700m
from both edges were already geometrically unsafe and failed at111ticks. Corner
traces now start at the declared1200m envelope; face traces retain700m. Arbitrary
unsafe aircraft birth recovery remains unaccepted. Ingress points near world
edges can conflict with recovery steering; universal strike geometry is pending.

Exact logs/library hashes: docs/evidence/air-bank-focused.json. Focused checks do
not prove full scale/GL/UDP compatibility, performance budgets or human spectacle.

The first frozen fast195a64c32e56 passed257.4234s at00c3d9e-afae1bf596b7aae4,
but is not sufficient for integration. Actual paired900tick scale observation
caught out-of-map living aircraft (sample maxima4/1/3 at8k open/hotspot/16k open,
versus0 in v20). A separate full public observer captures first crossings and
source IDs. Fighter bank reversal needs clearance beyond the old650m trigger.
Flight policy2 now triggers every edge at1200m, retaining the recovery latch.
Fresh original8192/900ticks passes459956 living-aircraft bounds observations,
minimum clearance211.7851m, with9 releases/9 impacts/3594 gun launches/3 deaths.
The test now checks every living aircraft on every tick, without renewing state.
An added extended oracle preserves original8k hotspot/16k army sizes and checks
900ticks each, speed, finite poses and nonincreasing stores.

Actual GL and v21 real UDP evidence here cover the previous00c3d9e runtime,
not this later edge-policy correction. The same immutable client passes actual
bomb/gun/destruction and paired draw checks; inspected bank/destruction frames
are retained. Initial v21 peers pass8192/180ticks with1197 airXZ refreshes.
Those results do not establish cinematic spectacle or the later runtime.
Paired timings on the earlier runtime: mean/p95v20→candidate8k open
16.035/19.072→16.119/18.761,hotspot36.142/46.979→36.644/47.975,16k open
34.640/43.900→34.497/43.232ms. Dense/stretch still miss33.3ms. Exact source/library
hashes and concurrently observed outcome/expiry data are in air-bank-scale.json.
No later performance result is inferred from that measurement.

Corrected1f3ed26-42bc0ec70974dc4c now passes matching real GL and actual v21
8192/180tick co-op (air-bank-early-edge-client-coop.log). The dense900tick oracle
observes459461 bounded living-aircraft steps at8192 hotspot (380.8945m minimum
clearance) and920406 at16384 open (234.6461m). Original8192 open adds459956,
so all1,839,823 observed living-aircraft steps remain inside the map with original
speeds/nonincreasing stores. Exact source/library hashes and per100tick world
hashes: air-bank-early-edge-dense.log and air-bank-early-edge-default-bounds.log.
Frozen fast558332fecbfd and full extended831bb1419f53 are running on that same
immutable revision; main remains on verified v20 until full acceptance.
