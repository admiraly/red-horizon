# Infantry supply-route work in progress

Isolated feature/infantry-supply-routes exposes read-only infantry_weapon_rounds,
returning actual carried0..120 or-1 for invalid/dead/noninfantry/stale/corrupt
stock. It shares the production record/stock validation and never calls birth,
fire, debit, credit or refill.268 ABI probes and independent initial/actual120-tick
queries across128 actors pass with checksum preservation. Initial96 infantry
carry120;91 surviving infantry after120 actual ticks carry116..120. Invalid
IDs/counts and all malformed stock dimensions return unknown. Focused combat24
passes at its own build epoch. Evidence: evidence/supply-routes-query.json.

Not integrated and no detour behavior claimed. Next is a temporary physical
resupply destination with finite-store/ownership/connectivity/contest/health
checks, while retaining primary company intent. World movement resolves hazard
interrupts before company and AI goals; preserve that precedence and role speed.
Existing nav_entity_goal shares16-ID squad corridors with separate scout slots;
resupply goals need a distinct cache namespace to avoid repeatedly invalidating
healthy squad routes. Body/lease/front changes must not refill stocks. Arrival
must credit only through actual existing proximity/LOS finite depot transaction;
no pose/clock/HP/ammunition renewal. Then verify actual journey, depot debit,
resumed primary orders, source loss, hazards, original scale and UDP behavior.
