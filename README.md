<img src="assets/icon.svg" width="64" height="64" alt="">

# RED HORIZON

**Command the offensive. Fight inside it.**

An assembly-first cooperative FPS/RTS under active development. The target is an 8 km battlefield with 4,096 real units on each side, three fronts, combined arms, command, logistics and recorded audio. This repository currently contains an early Linux prototype and verified scale/reload/audio foundations. It is **not the completed game**.

All project-authored CPU runtime code is NASM x86-64 assembly; GPU code is GLSL. Python and shell are development tools only. Read [the canonical specification](docs/spec.txt), [current evidence and gaps](docs/status.md), and [ABI](docs/interfaces.md).

## Local development

Requires Linux x86-64, Python 3, GCC/linker, NASM 2.16.03, GLFW 3, OpenGL 4.5 and ALSA development/runtime libraries. If NASM is absent, `bash tools/bootstrap-nasm.sh` downloads the pinned source, verifies its hash and builds under ignored `.tools/`.

```sh
python3 tools/dev.py doctor
python3 tools/dev.py build --changed
python3 tools/dev.py test --suite all
python3 tools/dev.py bench --scenario scale-open --ticks 600
python3 tools/dev.py bench --scenario scale-stretch --ticks 600
python3 tools/dev.py server --headless --ticks 300 --realtime
python3 tools/dev.py reload
```

The `server` command currently runs the shared **local headless simulation**, not a network server. Throughput mode is default; `--realtime` schedules at 30 Hz. Scale-front and scale-hotspot are reserved and fail explicitly until implemented. Headless metrics do not establish GPU frame rate or complete army intelligence.

Slow checks can append `--background`. A job receives a frozen source copy, revision/hash, log and result path. Use `python3 tools/dev.py jobs` and `collect JOB_ID` to reconcile results. Build outputs and evidence remain under ignored `build/` and `runs/`.

## Development status

Linux scale combat, same-build replay, front advance/defend/retreat orders, guarded local damage, compatible module reload proof and a 128-voice recorded PCM mixer have tests. Windows, playable co-op, navigation, full audiovisual production and complete operation acceptance are still pending. See [task board](docs/task-board.md), [simulation](docs/simulation.md), [reload](docs/reload.md), and [audio](docs/audio.md).

## Licences

Project code licence is pending owner approval. Public visibility does not grant reuse rights. Asset grants are separate; the recorded rifle sample is attributed under CC-BY-3.0 from its source archive. See [credits](content/CREDITS.md), [manifest](content/asset-manifest.json), and [third-party notices](THIRD_PARTY.md).
