# Status — initial integration, 2026-10-05

Not M0/M1 complete and not a base-game release. Linux x86-64/NASM 2.16.03/GCC16.2.1 on i7-1355U, Nobara44, kernel7.2.6. No Windows acceptance, multiplayer operation, targetGPU benchmark or playtest claim.

Implemented and verified: 8192/16384 individual moving/targeting combat entities, three lanes/fronts, four primitive roles, advance/defend/retreat orders, guarded player damage, deterministic same-build replay, bounded reservoir spatial candidates, exact side-label-swapped defensive damage symmetry; optional absolute-clock30Hz headless pacing. Capacity32768. No runtime C/Python simulation. CPU benchmarks are single-threaded; ranged combat lacks terrain sightlines/ammo/navigation/supply and is not tactical intelligence.

Reload proof:19 black-box cases preserve persistent host state through compatible swaps and rejected code/data; separate experiment, not live client hot reload. Audio:16 check groups cover128voice pool overlap/clipping/bounds/recycle/content validation and ALSA null playback; physical audible output unverified. One attributed recorded SKS shot is shipped; no full content pack.

Timing evidence: initial reservoir build worker measured seed1/600ticks p95 about2.47ms at8192 and5.23ms at16384. Measurements vary under concurrent builds/tests; full reports must name revision/hash and hardware. Integrated pre-fairness jobs at source3124294-a46748fb54b33699 measured p953.706/7.345ms while concurrent tests ran. Those older numbers do not validate the latest code. Integrated paced30tick job89449e9d9615 passed ~1second simulation. Integrated all-suite frozen-source job246a71cf1b67 passed in8.15seconds before audio integration. Reconcile newer reports before stating final acceptance.

Public repo https://github.com/admiraly/red-horizon was created with explicit session authorization. HTTPS OAuth token lacks workflow scope: GitHub rejected the initial push containing .github/workflows/verify.yml. Publish implementation on publication branch excluding that file; retain authored workflow locally. To enable Actions: gh auth refresh -h github.com -s workflow, then synchronize main. No workflow run has passed yet.

Next ready: integrate first-personclient and recordedaudio; verify context/screenshots and command/fire controls;12site territory/supply/capture state; bounded four-clientUDP protocol proof. Then navigation/cover/intelligence, real authoritative co-op integration, vehicles/VFX, stream map content, live reload host integration andWindows. See docs/task-board.md for dependencies.
