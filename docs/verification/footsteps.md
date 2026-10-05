# Recorded footstep starter bank

Worker implementation: bank2 in the existing NASM mixer, a separate NASM local
movement router, a pinned CC0 recorded source and offline conversion. The shared
voice budget stays128; expanding to three sample banks reserves an additional
384002 bytes of fixed preload storage. Runtime loading remains outside mixing.
Banks0/1 keep rifle/explosion behavior; invalid bank3 is rejected. Missing footstep
content makes audio_init return1, matching other required installed banks.

The source is GboxMikeFozzy's **Footsteps**, published2022-04-14 on
https://opengameart.org/content/footsteps-0, specifically01-footstep_0.ogg. The
primary submission links CC0-1.0 and describes recording the author's own subway
walk, then normalizing/reducing noise. Attribution is unnecessary under the
submission; voluntary credit is generated in CREDITS and THIRD_PARTY. Evidence is
content/licenses/footstep-license-evidence.json. Original9715byte SHA256:
33c9bef5e8aeb1069455699a34a0c5e1ef1787fd3f61594b0859d7e6bb9f9dec.
The installed14776byte mono48k signed16LE derivative contains7388samples, SHA256:
8c44c375ea796e1362ed19afe75dda6ec8bf966b8e88df4d9922ebb721bfe80d.
`python3 tools/footstep_assets.py` verifies the pinned source before attenuation
and short edge fades through ffmpeg, then verifies the exact derivative hash.
It never fetches assets or generates surrogate footfalls.

`audio_footsteps_update(EDI=localPlayer, XMM0=elapsedRenderSeconds)` runs on the
frame thread after the listener update. It reads the player64byte records,
vehicle associations and player_motion32byte sidecar, and calls terrain_height.
Generation-valid initialized local motion must be grounded. Network-only poses
without a current sidecar use consecutive terrain-relative standing1.8/crouch1.1
heights within0.04m. Invalid height, generation, death, disconnection, boarding or
teleport over3m resets travel. Each1.8m actual planar movement emits bank2 at the
actual XYZ with gain0.7, at most2footfalls per update. Stationary rendering never
adds travel. Invalid/nonpositive elapsed values reset the baseline; finite positive
elapsed is capped0.25s. There are no simulation writes, allocations, historical
catch-up bursts or remote-player/army footstep emitters.

Verification commands (worker; integration wiring belongs to the integrator):

- `python3 tests/test_footsteps.py --nasm /mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm`
  passes real derivative waveform against actual stereo mixer output, source and
  derived hash checks, three-bank overlap with bounded128voices, identical17
  footfalls for32m at30/60/120Hz and a30Hz stepped pose observed at120Hz. Checks
  stationary/dead/disconnected/boarded/airborne silence, generation/teleport resets,
  invalid dt, network-style standing/crouch fallback and landing reset; player,
  vehicle and motion state remain byte-identical during each router call.
- `python3 tests/test_audio.py --nasm /mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm`
  passes the existing mixer/spatial tests and actual ALSA null pumping plus missing
  installed footstep failure. Null output is not an audible quality assessment.
- `python3 tools/footstep_assets.py` and `python3 tools/assets.py` pass offline
  conversion/hash verification and generated license/credit validation.
- `RED_HORIZON_NASM=/mnt/titan_nv3/projects/red-horizon/.tools/nasm/nasm python3 tools/dev.py test --suite fast`
  passes (exit0), including existing CPU/audio/model/texture regression checks.
  The new standalone footstep test ran separately because the integrator owns
  the common suite driver.
- The same NASM override with `build --target client --objects-only` passes for
  the new audio modules; it does not establish linking, platform output or GLSL.

All worker test processes finished. An initial router test exposed an unaligned
SSE2 mask read; explicit16byte alignment fixed it and final focused tests passed.
An initial fast invocation lacked this worktree NASM path; the final configured
invocation passed. No pending worker jobs remain.

Limitations: one recorded hard-surface subway footfall serves all surfaces. This
is a starter footstep category, not acceptance of terrain-specific variations,
full recorded SFX coverage, occlusion/reverb, physical output latency or sound
quality. No human listening/playtest was performed. Network fallback uses available
player pose samples rather than a replicated grounded bit, so brief footsteps
between sparse snapshots may be missed. It does not infer remote sounds.
