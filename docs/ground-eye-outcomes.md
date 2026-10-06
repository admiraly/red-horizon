# Public gameplay driver-eye outcomes

`python3 tests/test_ground_eye_outcomes.py LIBRARY --source-revision REVISION
[--legacy] [--report FILE]` independently observes public `vehicle_enter`,
`player_input`, `vehicle_tick_player`, `sim_tick`, exit and disconnect paths.
It never invokes `ground_eye`, support/contact kernels, a probe adapter, or
presentation caches. This is a sparse friendly gameplay fixture; it does not
replace the existing army scale, combat health, arrival or network suites.

The expected eye is derived from actual `terrain_height` samples with a generic
least-squares plane solve, independently composed yaw/pitch/bank rotation
matrices, and a second set of fully rotated contact-corner samples. The observer
checks the retained local anchor `(0,3,0)` against actual player XYZ, distinct
from hull XZ. Sampling preserves the complete authoritative checksum. Matrix
and contact calculations share the declared chassis dimensions and contract,
but do not copy implementation helpers or its symmetric SSE arithmetic.

Four natural moving trajectories cover descending slope, compound bank/slope,
plateau-to-crest/descent, and the analytic ridge cusp. They use public direct or
world movement, reverse and bounded pivots. Initial friendly birth placement
and health are declared fixtures; after movement begins, no position/health is
rewritten except the explicitly labelled lifecycle/security injections. Each
tick preserves useful hull travel, the existing physical speed/turn envelope,
real hull-axis displacement, claimed health and eye attachment. Exact replay
compares the entire reported outcome and authoritative checksum. Separate
physical hull trace hashes allow attachment changes to be distinguished from
changed physical motion.

Four actual cannon launches independently construct the known world-look
target `expected eye + 600 * look`, then normalize its displacement from the
retained upright source `(hullX,terrain(hullXZ)+3,hullZ)`. These cases avoid range
clamps. This proves supported-eye aim targeting while explicitly retaining the
old physical shell origin; it does not establish a turret transform or cockpit
socket. Aim yaw/pitch do not rotate the stationary hull or alter its eye.

Actual exit remains centred on one of the eight physical hull offsets and
returns to ordinary infantry eye height. Natural AI/driver/AI transfer preserves
motion state through boarding/exit and useful continuing motion. Disconnect,
player death, recycled player generation and recycled entity generation release
the genuine claim without adopting another eye or firing. Generation/kind,
inactive and NaN-heading motion adversaries test direct rejected entry and held
claims. Rejected direct entry preserves the complete checksum. Held valid FIRE
input consumes its input-history edge before support validation, so its first
checksum can change; physical/eye/motion, vehicle caches, claim stamps,
ammunition, shells, events and counts must stay unchanged, and the second held
input must preserve the full checksum. Numeric/unknown-button invalid inputs
preserve complete authority before history handling.

## Candidate and prior accepted control

The worker built the unchanged runtime at
`5006c475839f7b68d8c2c1881e35c60a6997ef5e-64e1971ae59b3105`, using the absolute
workspace NASM executable and `tools.dev.build('headless')`, then linked the
actual sim/nav/AI/game objects into `build/libgroundeye.so`. Headless build time
was 0.4673 seconds; the private gameplay library SHA-256 is
`fd8a0c43a76328eb9b44c981381941bb4c930db33edc12f97679dcccf1013e8f`.
No runtime source or existing test was changed by this worker.

The candidate passes 23 replayed cases. Four moving eye errors are at most
0.0003441 m, versus actual horizontal eye/hull offsets up to 0.9058 m. Natural
hull travel is about 52.46 m in each 180-tick fixture and 218.78 m in the
600-tick crest fixture. Actual cannon velocity errors from independently
normalized supported-eye targets are at most 0.00000692 m/tick. All valid
movement maintains tank HP 400 and player HP 100; lifecycle changes are labelled
injections rather than fabricated combat acceptance.

The prior accepted immutable full-checkpoint library is retained under root job
`dfc1f67207e7`, source
`71c61c74c8a9514dcccddb92934db673db60762a-9af9b6d215bb4e7f`, SHA-256
`e078a793890c5ffc90cb06723e5d6e2e0fb70f85d342597410c7af46e2d36ecf`.
Running this real library with `--legacy` exposes measured upright-eye errors
0.06774–0.91668 m and cannon direction errors 0.00695–0.01527 m/tick. Legacy mode
records missing support-stamp rejection behavior rather than calling it a pass
of candidate security requirements. It preserves physical movement and resource
checks for otherwise valid paths. This actual older executable is a causal
control, rather than a replacement movement simulator.

Worker build and observer jobs are terminal. The initial candidate session 72184
flagged the valid FIRE-history checksum change; root confirmed its intended
pre-guard edge handling, then the observer separated complete rejected-entry
authority from held-history-only change without removing physical/resource
guards. Intermediate complete observations 56374, 20076 and 37127 passed.
Final exact-observer candidate/control sessions are 36179 and 5848, with their
reports `/tmp/ground-eye-candidate.json` and `/tmp/ground-eye-prior-accepted.json`.
Root owns evidence publication and final frozen integration checks.

These outcomes do not prove rendered camera presentation, multiplayer correction,
target-GPU performance, physical oriented hull/vertical collision, suspension
authority, measured seat/muzzle sockets, or complete vehicle realism. The full
game specification remains active; final integrated tests must preserve its
existing scale/health/arrival and graphics/UDP fault gates.
