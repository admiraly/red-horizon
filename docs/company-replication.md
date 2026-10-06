# Company ownership and intent replication

UDP v24 adds message107: a complete164-byte payload containing count4 and four
40-byte records. Each record carries player ID, own allied company key, owner
body generation, lease serial, order mode, explicit-intent flag, goal X/Z,
command sequence and command tick. Header/session/version/content checks remain
in the production NASM client parser. The common CPU mirror rejects malformed
whole batches, duplicate assigned keys, invalid coordinates and non-newer ticks
before writing any record. Unassigned records explicitly clear metadata while
retaining their lease serial. The mirror never executes orders or charges funds.

The renderer validates membership against the current connected player body
and front. A company update arriving before its corresponding player state is
hidden until the generation matches. Timeout, close and reopen reset the mirror.
Network rendering continues to use remote validation after timeout; it cannot
fall back to the initialized solo company. Solo rendering uses the actual local
lease. Owned allied ground actors receive green tint; tactical markers draw
owned actors after other army markers to preserve readability in dense groups.
Each actor still contributes once to the marker census.

Entity replication retains the existing two bounded32-record chunks per
snapshot. An actor in the recipient's own allied ground cohort is eligible even
outside the1200m local region, including HP0 retirement records. This adds no
remote enemy ground truth. At most128 entity IDs can belong to one cohort;
ordinary rolling transmission and its backlog still apply. Company metadata is
204 bytes including header per connected recipient per snapshot. Actual total
bandwidth remains measured in the network reports.

The tactical map selects the local owner's accepted company intent on their
front. When inspecting another front, it displays a validated allied owner's
accepted intent. An optimistic ACK cache does not supply authoritative goals.
The shared goal cross is verified through actual pixels and the second client's
selected-goal output, including after a genuine owner redeployment. This is one
selected-front goal, not a complete multi-company planning or countdown UI.

Evidence is collected in docs/evidence/company-replication-focused.json and
its raw logs. Focused checks include the actual NASM UDP parser, four real
players with the production adapter as player3, lost ACK/release/rejoin, solo
commands and markers, two actual software-GL clients, and timeout invalidation.
The far-company transport fixture declares one initial generation71 infantry
birth at7500/1300 before any player joins; no subsequent pose/HP/store/clock
writes occur. The separate original company-network test observes the original
8192-unit world without writes. Rendered co-op retains its existing documented
combat/vehicle encounter fixtures. These tests do not establish target GPU
performance, human art/play quality, transfer/assistance, shared countdowns,
recruitment or completion of the full game.
