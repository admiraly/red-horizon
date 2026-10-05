# Task graph and ready queue — current integration
| Task | Owner | Dependency | State / acceptance evidence |
|---|---|---|---|
| Canonical spec, ABI, isolated worktrees | integrator | repository | committed |
| Pinned incremental toolchain / frozen async jobs | integrator | ABI | tested cold/no-op/one-file invalidation, frozen job survives invalid source edit |
| Dense moving/targeting combat | simulation worker | ABI | baseline/stretch replay/count/order/damage/bounds/symmetry suites pass |
| Safe module / parameter reload proof | reload worker | NASM |19black-box cases pass; live host integration pending |
| Recorded audio /128voice mixer | reload worker + integrator | provenance/client |legacy16groups plus spatial mix/recorded routing and stereo ALSA null pass; physical audio quality unverified |
| OpenGL first-person mass renderer | client worker | simulation |actual GL4.6 context,8192instances,finite screenshots/input checks pass |
| Rifle magazine/reload/cadence/recoil | client worker | input/damage/audio |held-fire/empty/reload/refill tests pass |
| Capture/supply/resources/results | simulation worker | world |12physical sites,cut/restoration,spend,recapture/victory/defeat tests pass |
| Finite formation destinations | simulation worker | world/sites |bounds/role speeds/arrival then capture tests pass |
| Four-client UDP transport proof | reload worker | protocol |45real datagrams plus timeout/malformed/reorder/lostACK pass; standalone legacy proof retained; shared-world gameplay has its own row |
| Tactical markers/destination UI | client worker | site/waypoint ABI |privateXvfb input + markers/resources pass |
| CPU/GPU client profiling | integrator | GL renderer |bounded timer ring hooked; CPU/GPU samples observed headlessly |
| Local packaging | integrator | client/content |archive with hashes built; final revision package below session reports |
| Public GitHub | integrator | explicit authorization |repo created and first validated snapshot pushed |
| GitHub Actions | integrator |workflow credential scope |credential scope restored; baseline remote Actions run37305579434 passed |
| Windows parity | ready/unassigned | platform ABI |pending |
| Shared terrain/LOS/local detours and observed tactics | simulation worker | spatial/world |physical wall rejection, scout→defender defeat→capture, flank bounds, observed/supply retreat and override tests pass |
| Nearest obstruction / swept navigation steps | integrator | terrain/controller | independent segment oracle and original-code negative control pass; full checkpoint recorded in docs/evidence/navigation-session.json |
| Hierarchical navigation/cover selection/strategic pacing | next ready | terrain/controller |pending |
| Authoritative players and shared-world co-op | integrator + workers | terrain/player/UDP |four real slots, movement/fire/order authority, duplicate spending, snapshots and disconnect recovery pass; two actual rendered clients, remote-player pixels, rejected ACK rollback and server freeze checks pass; full extended integrated job2699ac0fcf9c passed |
| Moving shells, player ground armor, bounded impact VFX, spatial rifle mixer | three subsystem workers + integrator | world/render/audio |full frozen extended job1ee7970cae70 passed102.73s; real UDP + two rendered clients drive/fire/exit; recorded spatial routing and actual impact/HUD pixels verified |
| Projectile flight/render cleanup, active default army, licensed animated starter models | three workers + integrator | combat feedback/source provenance | full frozen extended jobaf800b6d2a47 passed128.92s;16source meshes22clips, realGL pose/Walk/track/expired-shell checks, large motion/replay, local+two-client vehicle controls and UDPfaults |
| Sourced temperate terrain and cosmetic weather | client/source/review workers + integrator | texture provenance/rendering | full frozen extended jobd87a7d59c26e passed143.80s;4CC0 texture layers,13negative pack cases,all presets/F4,real moving precipitation across forward/side views,paired impact controls,existing scale/co-op/UDPfaults |
| Wider vehicles, layered recorded sound pack, production art/effects | next ready | current combat batch |pending |
| Streaming map,complete operation/recovery | next ready | terrain/nav/logistics |pending |

Current local FPS health/suppression/death/redeployment also passes actual XTest and GL HUD pixel checks.

No milestone completion claim: M0 needs live host reload/jobs diagnostics and Windows; M1 needs quality/action/art/audio performance evidence; M2–M5 acceptance remains largely outstanding. No percentages. Keep one integrator owning contracts and worker patches isolated. Reconcile launched jobs before handoff.
