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
0xcfb6fd7b, content0x1d824621, canonicalSHA256
1d82462178ed14655bf6f9574975ab41ee1ca2a33ba1b17c5b70cc1bff426124.

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
