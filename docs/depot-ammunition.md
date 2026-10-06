# Finite depot inventory prerequisite

Isolated feature/depot-ammunition, based on integrated infantry merge6d62cc68.
The NASM module owns12 bounded16-byte stores. Fresh operation initialization
seeds only declared depot-role sites with12000 rounds. A debit must belong to
the requesting side at a healthy, connected, uncontested depot. Requests are
bounded1..90; partial last transfers exhaust exactly. Capture, route restoration,
repair or ownership changes do not create inventory. remaining+issued always
matches the declared initial stock; corrupt counters fail atomically.

The independent12-depot fixture spends144000 rounds over1608 successful calls,
including partial final withdrawals, and verifies side/role/cut/destruction/
contest gates plus malformed arguments and records. Evidence:
evidence/depot-ammunition-prerequisite.log. Actual authored operation has fewer
depots; this fixture is not a whole-operation inventory claim.

No world hooks, actor proximity validation, actor credits, received-round counter,
checksum integration, protocol/content revision, shortage UI or supply-aware
routes yet. Public debit requires the future caller to validate actor capacity
and proximity first; debit and credit must be one authoritative transaction.
This branch is an isolated prerequisite and is not merged or claimed as resupply.
Next: extend infantry conservation by cumulative received rounds; wire physically
nearby eligible actors to finite depots and test causal cut/restore/exhaustion,
then ABI/replay/original scale/UDP. No live encounter inventory renewal.
