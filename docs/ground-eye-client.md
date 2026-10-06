# Actual graphical driver's supported eye

`python3 tests/test_ground_eye_client.py CLIENT SERVER` launches production
assembled executables on a private1280x720 Xvfb software-GL display with null
ALSA output. It compiles a read-only matching terrain/support/contact/eye query
library from the frozen sources. That query establishes component consistency
with the current support ABI; the separate independent mathematical kernel
oracle is still required to prove the math itself.

Initial positions are the only authoritative fixtures. Existing armies are
translated away from the encounter, an initialized living allied tank is placed
on the gentle relief shoulder, and a living player is placed within boarding
range. Entity/driver/ground generations, health, ammo, cooldowns and actuator
state are never renewed or overwritten after the encounter starts. Real keyboard
E establishes ownership. Real W drives; D/A turn; held S produces observed
negative signed hull speed; actual left-button fire increments authoritative cannon
shots. Q exits and clears reverse ownership and the driver-generation stamp.
The test observes actual moving entity poses, matching motion generations and
player XYZ, then checks visual_target and converged camera XYZ against the
unsmoothed supported eye. World yaw/pitch remain the aim inputs. It does not
manufacture a changing render pose to represent driving.

The second phase launches a real dedicated server and a real UDP graphical
client. Real E establishes a server claim, and the graphical client receives
its supported player XYZ and hull mapping. A clearly labelled cosmetic timing
fixture then freezes only this own server and extends the client's preview-age
threshold to10seconds. Actual held W must produce a nonzero wish while connected,
but every visual_target sample must remain equal to the received player XYZ.
This isolates the boarded preview path before the normal transport timeout. It
is not a latency/fault or long-term frozen-server transport acceptance test.
No local actuator prediction is added or exercised.

The previous accepted71c actual executable fails the same local observer after
successful real boarding: its upright eye X is about5795.024 while the supported
eye X is about5795.929, a0.9048m component error. The old run never reaches the
network phase, so this negative proof does not depend on mismatched protocol
fingerprints. Current transport and old-local-negative scopes remain separate.

The screenshot shows the actual driver's near-field relief view. The owned hull
is intentionally hidden by the existing first-person renderer. This demonstrates
a working software-GL view; target-GPU performance, artistic acceptance, a measured
cockpit/socket, a supported cannon muzzle, sound-device listening, and live entity
generation recycle are not established by this observer. Exit clearing is tested;
invalid-generation and lifecycle rules retain their separate kernel/network gates.
The legacy3m anchor is preserved and remains a gameplay anchor rather than an
accurately measured cockpit socket.

Runtime source is the frozen root candidate895ecbd. The old executable is the
accepted71c61c74 client in jobdfc1f67207e7. Focused logs are
`/tmp/ground-eye-client-final.log` and `/tmp/ground-eye-client-old-negative.log`;
initial build logs are `/tmp/eye-client-build.log` and `/tmp/eye-coop-build.log`.
Root owns wiring this observer into tools and verifying the integrated SHA.

Final focused result: current candidate exit0 with68 coherent supported-eye
samples; old-upright anchor gap0.915508m; observed reverse speed−0.144m/tick;
exit-generation clearing passed;35 connected held-W network preview samples
retained received XYZ. The old71c executable exit1 is the intended negative,
with actual supported-eye component error0.904785m. All private job handles were
collected and all test-owned processes reconciled. Screenshot:
`/home/levy/optane-tmp/red-horizon-supported-driver-eye.ppm`.
