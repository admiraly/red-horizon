# Wreck route relevance prototype — not integrated

Based on verified09c6ce8. VERSION2 selects at most eight wreck vertex sets
using corridor distance plus0.03125 source distance squared; the first hit is
retained. Every graph edge, selected leg and actual movement still checks all
wrecks. Omitted vertices can still prevent a route. Build scratch does not enter
future authority state; persistent policy constants enter the content fingerprint.
Private compatibility: UDPv15/schema0x2c40b526/content0x51010b86.

The focused navigation suite passes, including24 public-tick outcomes and the
1,035-request bounded FIFO contract. A nine-wreck fixture reaches the destination
in124ticks without penetration or graph failure, with one omitted-vertex window.
Exact terminal log: docs/evidence/wreck-nav-relevance-focused.log.

A natural900tick concurrent observer measured p95 at11.578ms (8k open),
26.806ms (16k open),41.002ms (8k hotspot). No causal timing improvement is claimed:
these runs had different combat outcomes and concurrent workloads. Hotspot is
still over33.3ms. Exact report: docs/evidence/wreck-nav-relevance-scale.json.

This prototype requires frozen full, network and graphics checks before main
integration. It does not establish full-game or performance acceptance.
