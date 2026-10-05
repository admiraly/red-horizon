<img src="assets/icon.svg" width="64" height="64" alt="">

# RED HORIZON

**Command the offensive. Fight inside it.**

An assembly-first cooperative FPS/RTS under active development. The target is an 8 km battlefield with 4,096 real units on each side, three fronts, combined arms, command, logistics and recorded audio. This repository currently contains an early Linux prototype with terrain-aware army tactics, authoritative FPS combat and a shared-world co-op server. It is **not the completed game**.

All project-authored CPU runtime code is NASM x86-64 assembly; GPU code is GLSL. Python and shell are development tools only. Read [the canonical specification](docs/spec.txt), [current evidence and gaps](docs/status.md), and [ABI](docs/interfaces.md).

![Actual assembly client with sourced terrain, animated models and cosmetic rain](docs/evidence/environment-rain.png)

## Local development

Requires Linux x86-64, Python 3, GCC/linker, NASM 2.16.03, GLFW 3, OpenGL 4.5 and ALSA development/runtime libraries. The full test suite also requires Xvfb; it creates a private software-rendered display, so your desktop is not required. If NASM is absent, `bash tools/bootstrap-nasm.sh` downloads the pinned source, verifies its hash and builds under ignored `.tools/`.

```sh
python3 tools/dev.py doctor
python3 tools/dev.py build --changed
python3 tools/dev.py test --suite fast # routine iteration
python3 tools/dev.py test --suite player # focused module check
python3 tools/dev.py test --suite all --extended --background # integration checkpoint
python3 tools/dev.py bench --scenario scale-open --ticks 600
python3 tools/dev.py bench --scenario scale-stretch --ticks 600
python3 tools/dev.py server --headless --ticks 300 --realtime
python3 tools/dev.py reload
python3 tools/dev.py build --target client
python3 tools/dev.py run --client
python3 tools/dev.py run --client --weather rain
python3 tools/dev.py run --client --width 1920 --height 1080 --fov 70 --sensitivity 0.002
python3 tools/dev.py run --client --scenario air-battle
# Direct-IP/LAN hosting and joining (in separate terminals):
python3 tools/dev.py coop --port 7777
python3 tools/dev.py run --client --connect 127.0.0.1 --port 7777
```

The `server` command runs the shared local headless simulation. `coop` hosts the actual shared-world UDP server; its default runs until interrupted, and `--ticks N` makes a finite test run. Throughput mode is default; `--realtime` schedules at 30 Hz. Scale-front and scale-hotspot are reserved and fail explicitly until implemented. Headless metrics do not establish GPU frame rate or complete army intelligence.

Client controls: WASD, Shift sprint, Ctrl crouch, Space grounded jump, mouse aim/fire, R reload, E enter nearby allied armor, Q exit, Tab tactical view, F1/F2/F3 front selection, F4 clear/overcast/rain/fog, 1/2/3 advance/hold/retreat, tactical click destination, Escape quit. Health, suppression, death and safe redeployment are authoritative. Network slots0–2 own their matching fronts; slot3 supports front0. Nearby actors use licensed source models with movement-driven authored soldier/tank animation; simplified source meshes and distant role/team markers preserve army visibility. The installed rifle, fortifications, trees and structures also use downloaded models. See [model pipeline and source limitations](docs/models.md). Photographed grass, mud, gravel and rocky terrain blend across the battlefield; cosmetic weather adds drifting clouds, rain, wet ground and distance fog. See [texture sources](docs/textures.md) and [weather controls](docs/environment-renderer.md). Recorded rifle/explosion/footstep PCM shares a128-voice stereo mixer with listener-relative panning and distance culling; a missing device is nonfatal. `RH_AUDIO_DEVICE=null` supports headless graphics smoke.

`test --suite fast` checks small real-core combat/replay, operation, waypoints, terrain, tactics, players, reload, audio and asset integrity including default8k/16k motion checks and baked-model provenance. It omits large combat scale/replay, real UDP, graphics and build-tool isolation checks; full extended verification retains them. Focused core suites: operation, waypoints, terrain, player, tactics, combat, vehicles, effects. `build --target client --objects-only` validates assembly without linking or a GPU; it does not compile GLSL. Actual transitive NASM include/incbin dependencies control incremental rebuilds.

Slow checks can append `--background`. A job receives a frozen source copy, revision/hash, log and result path. Use `python3 tools/dev.py jobs` and `collect JOB_ID` to reconcile results. Build outputs and evidence remain under ignored `build/` and `runs/`.

## Development status

Linux scale combat, same-build replay, physical terrain/obstacle LOS and detours, observed-intelligence scouting/flank bounds/withdrawal, player vulnerability and recovery, authoritative UDP world replication, pooled moving tank/artillery shells, ground armor control, bounded tracer/impact effects, compatible module reload proof and a128-voice spatial recorded PCM mixer have tests. Windows, hierarchical navigation, full audiovisual production, human gameplay balance and complete operation acceptance remain pending. Network entity replication is capped to nearby records; it does not send the full army each snapshot. See the [full specification acceptance audit](docs/spec-acceptance.md), [task board](docs/task-board.md), [simulation](docs/simulation.md), [reload](docs/reload.md), and [audio](docs/audio.md), [terrain/tactics](docs/tactics.md), [players](docs/player.md), and [co-op protocol](docs/coop.md).

## Licences

Project code licence is pending owner approval. Public visibility does not grant reuse rights. Asset grants are separate; the recorded rifle sample is attributed under CC-BY-3.0 from its source archive, and the selected starter model packs and Poly Haven terrain textures have documented CC0 grants. See [credits](content/CREDITS.md), [manifest](content/asset-manifest.json), and [third-party notices](THIRD_PARTY.md).

Additional verified slices: twelve capture sites with supply connectivity and operation outcomes; formation waypoints; a standalone four-client UDP proof (`python3 tools/dev.py test --suite network`). The rifle has magazine/reload/recoil feedback. `python3 tools/dev.py package` builds a local Linux archive with checksums and credits; it does not publish a release. `run --client --frames 30 --screenshot /tmp/frame.ppm --tactical` provides a finite visual smoke.

Headless verification: `env -u DISPLAY -u WAYLAND_DISPLAY python3 tools/dev.py test --suite all` runs CPU, operation, reload, audio, UDP, build-tool and actual-client software graphics checks. `--suite headless` runs the CPU/audio/UDP/tooling checks without opening a graphics context (the texture-loader test links system OpenGL); `--suite graphics` checks the renderer alone using an isolated Xvfb display and llvmpipe. Test graphics are smoke evidence, not target GPU performance.
