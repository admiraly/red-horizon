# Task graph and ready queue
| Task | Owner | Dependency | State / acceptance |
|---|---|---|---|
| Canonical spec, ABI, isolated worktrees | integrator | repository | committed |
| Incremental toolchain + immutable run outputs | integrator | ABI | implementing; build and no-op timings required |
| Dense simulation / bounded spatial targeting | simulation worker | ABI | tests in progress; 8192/16384 replay + invariants |
| First person GL4.5 client + mass instances | client worker | ABI, simulation | implementing; screenshot/context smoke required |
| Safe module + parameter reload proof | reload worker | NASM | 19 black-box cases passed, integration pending |
| Licensed recorded starter audio + mixer | integrator / next worker | provenance, client | ready |
| Linux asynchronous CI | integrator | integrated tests | authored; exact-SHA remote result pending |
| Windows ABI/platform parity | unassigned | stable host | pending |
| Hierarchical navigation, sightline intelligence | next ready | simulation | pending |
| Objectives/supply and squads | next ready | simulation | pending |
| UDP authoritative co-op | next ready | versioned protocol | pending |

Do not call M0 or M1 complete until their full acceptance criteria in docs/spec.txt pass. Independent work queue continues when CI runs. No percentage estimates.
