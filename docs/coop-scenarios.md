# Dedicated and listen authored battle starts

`python3 tools/dev.py coop --scenario scale-hotspot` selects the existing genuine
8192-unit/seed42 authored encounter; `scale-open`, `air-battle` and `scale-front`
also work. Native server arguments accept the same `--scenario` values and reject
duplicate/unknown/missing names or insufficient unit counts before socket bind.
`python3 tools/dev.py run --client --listen --scenario scale-front` propagates the
selection to the owned authority. Direct joining clients use `--connect` without
a local scenario override: the server owns the world.

The shared `sim_scenario` birth routine runs exactly once after initialization,
before any tick/join. It changes genuine starting poses/cohorts, not ongoing
combat events. Readiness carries the selected numeric mode0..3; the listen host
validates it against the request. UDP40/schema/content and gameplay layouts remain
unchanged. Final dedicated JSON adds read-only checksum, selected mode, alive
counts, current engaged count and event sequence, outside tick timing.

The default threat-checked deployment policy is retained. In particular dense
army starts do not guarantee players spawn at the authored solo camera. Matching
near-battle safe deployment/transport and sustained1024-visible stress remain
unfinished; no camera/health/clock renewal or runtime world reset is used.

Focused verification compares all four actual120-tick dedicated runs to the same
shared authority replay with exact full-state checksums, counts and real combat
events. Four real UDP peers join both dense modes, receive gameplay states, fair
regional actors and aircraft, and respect MTU. These are packet clients/default
deployment views, not four graphical fronts or full operation/fault acceptance.
Peers intentionally stop sending after admission/sampling; final disconnects are
expected, not evidence of continuous1–4-player play.

A stale pre-fourth-join state observer and a one-second helper waiting for a full
30 ticks initially failed. The observer now requires post-all-join source ticks
and services four sockets together within a bounded5s wall window. No authority
clock/state or frame-rate gate was changed; performance acceptance is separate.

The previous benchmark full2e17f744fa0c failed stale mocked dense CLI tests. The
fixture now supplies required phase/presentation/pacing/renderer telemetry and
selects the actual runtime command separately from platform metadata probes. New
negative controls reject missing phases, software rendering, incorrect framebuffer,
clock errors and incomplete phase samples. These mocks verify orchestration only;
they do not prove game density or GPU performance. Original failure retained.

Native front/hotspot listen measurements at1920x1080/FOV70/600frames capped60 on
Arc A770 pass with CPU work p951.479/1.195ms and final516/471 visible actors.
These are default safe joining views, not1024-visible acceptance. A census bug
previously encoded owned scenery as army actor0; descriptor roles now exclude
scenery from army IDs. Actual paired GL fixtures prove both ownership tints
still render51 pixels while contributing zero army IDs, preserving colour and
authority. Frozen ordinary network and all-extended results are tracked in status.
