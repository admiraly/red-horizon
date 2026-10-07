# Linux owned listen server

`python3 tools/dev.py run --client --listen` builds both native executables into
one immutable revision directory, launches the client, and starts the same real
8192-unit/seed42/30Hz authority used by dedicated co-op. `--listen` is explicit;
ordinary solo still uses the existing synchronous path. Other players can join
with `--connect HOST_IP --port PORT`. The flushed `listen_ready` JSON prints the
chosen ephemeral port and owned PID before graphics initialization. The authority
uses its existing LAN bind and four-player protocol; no discovery/account/relay
service is added. This batch verifies two graphical clients, not four players.

The runtime is NASM. Before GLFW/audio starts any workers, it resolves the sibling
`red-horizon-coop-server` relative to `/proc/self/exe`, forks, and executes that
absolute path with an argument array, without a shell or PATH search. The child
uses syscalls only before exec. A close-on-exec nonblocking pipe carries the exact
server readiness line. Eight625ms poll attempts bound readiness; format, protocol,
8192-unit count and port bounds are checked. The client joins loopback through the
existing versioned UDP transport and never calls `sim_tick` in listen mode.

Normal exit and initialization failures stop/reap only the owned PID and close
its pipe. Each frame observes/reaps an unexpectedly terminated authority and
returns a failed client status. Kernel `PR_SET_PDEATHSIG` plus a parent-identity
race check prevents a live army remaining after abrupt parent death. When the
parent is killed outright, the system init owns orphan reaping; the test observed
a dead zombie, not successful normal-parent reaping. Shutdown assumes the shipped
authority retains its normal SIGTERM policy; arbitrary replacements which ignore
SIGTERM are outside this contract.

`--listen` cannot combine with `--connect`, an explicit `--port`, or another
`--listen`. The client and owned server accept `--scenario scale-open|air-battle|
scale-front|scale-hotspot`; readiness includes and validates the selected mode.
Birth layouts run once before the server binds; later joins/redeployment retain
the ordinary current-body/threat/site deployment policy. They do not move an
existing camera or renew army health/ammunition to maintain density. No player/camera/state renewal is introduced.
The sibling executable is required; running a copied client alone fails clearly
and reaps the failed exec child. Packaging of a standalone listen pair, reconnect
continuation, saved authority state, interpolation/local prediction, Windows
process hosting and a player-facing host/join menu remain unfinished.

Focused evidence uses actual private-X llvmpipe clients and the real assembly
server: host plus independent player1, both local_sim_ticks0; normal owned-child
reaping; GL failure cleanup; unexpected server death; kernel parent-death shutdown;
missing sibling; six invalid combinations. Existing solo presentation/graphics
and controlled fresh-feedback regressions are run against the final linked client.
Native hidden Arc measurements are a separate scope; none of these small views
establishes dense battlefield, 1–4 player operation or spectacle acceptance.
