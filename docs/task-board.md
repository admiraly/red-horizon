# Task graph and ready queue — initial session
| Task | Owner | Dependency | State / acceptance evidence |
|---|---|---|---|
| Canonical spec, ABI, isolated worktrees | integrator | repository | committed |
| Pinned incremental toolchain / frozen async jobs | integrator | ABI | tested cold/no-op/one-file invalidation, frozen job survives invalid source edit |
| Dense moving/targeting combat | simulation worker | ABI | baseline/stretch replay/count/order/damage/bounds/symmetry suites pass |
| Safe module / parameter reload proof | reload worker | NASM |19black-box cases pass; live host integration pending |
| Recorded audio /128voice mixer | reload worker + integrator | provenance/client |16groups including ALSA null pass; physical audio quality unverified |
| OpenGL first-person mass renderer | client worker | simulation |actual GL4.6 context,8192instances,finite screenshots/input checks pass |
| Rifle magazine/reload/cadence/recoil | client worker | input/damage/audio |held-fire/empty/reload/refill tests pass |
| Capture/supply/resources/results | simulation worker | world |12physical sites,cut/restoration,spend,recapture/victory/defeat tests pass |
| Finite formation destinations | simulation worker | world/sites |bounds/role speeds/arrival then capture tests pass |
| Four-client UDP transport proof | reload worker | protocol |45real datagrams plus timeout/malformed/reorder/lostACK pass; gameplay connection pending |
| Tactical markers/destination UI | client worker | site/waypoint ABI |privateXvfb input + markers/resources pass |
| CPU/GPU client profiling | integrator | GL renderer |bounded timer ring hooked; CPU/GPU samples observed headlessly |
| Local packaging | integrator | client/content |archive with hashes built; final revision package below session reports |
| Public GitHub | integrator | explicit authorization |repo created and first validated snapshot pushed |
| GitHub Actions | integrator |workflow credential scope |credential scope restored; workflow publishing, first remote result pending |
| Windows parity | ready/unassigned | platform ABI |pending |
| Hierarchical navigation/cover/intelligence | next ready | spatial/world |pending |
| Authoritative gameplay co-op | next ready | UDP/world |pending |
| Ground vehicles,artillery,VFX,licensed sound pack | next ready | world/render/audio |pending |
| Streaming map,complete operation/recovery | next ready | terrain/nav/logistics |pending |

No milestone completion claim: M0 needs live host reload/jobs diagnostics and Windows; M1 needs quality/action/art/audio performance evidence; M2–M5 acceptance remains largely outstanding. No percentages. Keep one integrator owning contracts and worker patches isolated. Reconcile launched jobs before handoff.
