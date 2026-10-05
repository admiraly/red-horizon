# Squad navigation and bounded shelter

`src/nav/squads.asm` implements a two-level controller: a squad visibility
corridor around the five authoritative static boxes, followed by the existing
per-actor swept local steering in `terrain_move`. This is not a streamed region
hierarchy, a terrain-slope mesh, or dynamic obstacle avoidance.

Squad keys combine side, front, and stable entity ID divided by16. IDs are
interleaved across fronts, so ID groups alone cannot identify a squad. The
fixed12,288-entry cache supports all32,768 actors without changing entity32.
Each256-byte entry holds start/final positions and at most22 corridor nodes.

A512-entry FIFO admits each pending squad once. `nav_tick` processes at most8
requests, yielding a64-tick upper bound for requests already admitted into a
full queue. Overflow leaves the entry invalid, increments a diagnostic, and
allows ordinary swept local steering; later calls retry admission. This is not
a latency guarantee for requests still outside the queue. Cache entries whose
final goal moves over64m are rebuilt; queued updates coalesce. A direct clear
segment always returns the exact current authoritative final goal, including
changes smaller than64m. Actors choose the furthest visible node in the cached
corridor, so they share a route without sharing a progress cursor.240 consecutive
nonprogress movement requests far from the goal schedule a recovery route from
the actor's actual position. Recovery does not teleport or promise escape from
an invalid spawn inside a solid.

Dijkstra runs over start, goal, and four4m-padded corners per box. Every proposed
edge uses `terrain_path_clear`, an exact two-dimensional slab sweep against
flag1 static solids and the map bounds. Both endpoints are checked. If the
obstacle table exceeds five entries, the bounded solver declines to produce a
corridor and leaves local steering active. No geometry allocation occurs.

Autonomous infantry may select a reachable sheltered point within40m of their
actual position. Selection requires a live hostile target previously acquired by
the authoritative world and a clear segment from the actor to shelter. A
physical eye-height LOS query must show that shelter blocks the observed target.
The selector considers opposite-X-face midpoints of the actual static boxes.
It is intentionally a small bounded cover set, not arbitrary tactical geometry.
A fixed shelter point remains committed for at most360 ticks; target loss during
the approach does not cause hidden target coordinates to be read. New selection
windows last30 ticks in each staggered1,080-tick cycle. After the commitment,
advance resumes. Human front override immediately cancels shelter. Ground
vehicles do not take infantry cover; aircraft bypass this module.

## Integration contract

Call `nav_init` after `ai_init` during successful world initialization. Call
`nav_tick` once per simulation tick after tactical updates and before movement.
For moving ground entities call `nav_entity_goal` with EDI stable actor ID and
XMM0/XMM1 final authoritative X/Z, then pass the returned intermediate X/Z to
existing `terrain_move`. Held entities need not call the goal function.
All routines preserve SysV nonvolatile registers. Chain `nav_hash` from the
world checksum with incoming RAX hash and R8 multiplier. State is fixed BSS.

`nav_metrics` is eight consecutive uint32 fields: pending requests, completed
requests, overflow fallbacks, corridor cache hits, stuck replans, cover
selections, requests processed on the last tick, maximum requests on one tick.
Counters wrap modulo2^32. Hash includes diagnostics, queue/cache and actor
progress/commitment state. Packed shelter expiry supports ordinary operations;
continuous worlds beyond2^28 ticks need an expiry representation revision.

## Focused evidence

`RED_HORIZON_NASM=/path/to/nasm python3 tests/test_navigation.py build/libsim.so`
executes the real assembly through a development-only SSE return adapter.
The proof checks2,000 independent segment/rectangle oracle queries, physical
arrival through four routes (including a bunker followed by a wall), side/front
cache separation,1,024 admitted FIFO requests with an8-request tick cap,
512 saturation fallbacks,240-call stuck recovery, and an infantry shelter
approach at0.12m per tick. The shelter fixture starts with actual clear target
LOS, reaches the committed point physically after target loss, verifies blocked
LOS there, then proves expiry and immediate manual-override cancellation.
Four0.5m-per-tick corridor routes arrived in879,8428,6324 and5206 ticks.
The terrain suite also passes its1,997 random clear-start swept movement cases
and64,973 accumulated role-speed arrival steps.

These focused results are nav/terrain driver evidence. They do not establish
integrated world-hook behavior, scale CPU budgets, dynamic cover destruction,
squad separation/crowd avoidance, full-map routing, or subjective play quality.
The integrator owns world-hook and frozen full-suite verification.
