# Infantry resupply detours

The candidate keeps primary company/front goals and selects a temporary depot
for moving infantry with at most30 carried rounds. A source must be allied,
role1, alive, connected, uncontested, within600m and have a valid positive finite
inventory. Human advance permits a detour; hold, retreat, follow and defend do
not. Autonomous withdrawal is excluded. Existing hazard steering runs first.
The selector is read-only and never initializes or credits ammunition.

Supply routes have3072 separate256-byte cache records, indexed by physical site
and128-ID cohort, adding786432 bytes. Existing squad/scout caches, bounded FIFO,
terrain/body/wreck steering and role speeds remain. Selection is stateless; an
unavailable source or more than30 carried rounds returns movement to the stored
primary goal. This is nearby infantry resupply, not strategic convoy logistics.

The two-actor startup fixture then runs1500 genuine ticks with no live pose, HP,
clock or stock writes. At tick360 the actor is56.8m from the actual depot and the
existing proximity/LOS transaction credits90 reserve rounds: depot12000→11910,
carried12→102. Total ammunition is conserved and primary command bytes never
change. By1500 the actor has resumed toward900,4200. A separate genuine site
occupation captures the command root at600, cuts depot connectivity and returns
the actor toward its primary goal, with zero credit and store12000 intact.
Static query fixtures verify source/stock/pose/index/label gates and32 ABI calls.
An additional static navigation fixture retains ordinary and supply entries
through200 interleaved queries and admits a separate physical-site entry.

The read-only ammunition prerequisite separately passes268 ABI calls and an
independent128-actor initial/actual120-tick oracle. It never calls birth/refill.
Protocol32/schema0x125478c2/content0xcfc42bc9 records the changed behavior policy;
there are no new wire fields. Routine fast, actual UDP and unchanged8192/16384
verification are recorded separately in evidence/supply-routes-focused.json.

Limitations: no detour hysteresis, route reachability preflight, full strategic
logistics, convoys, production or player/vehicle/aircraft rearm. Existing local
cover/wreck responses can delay travel. Sparse traces and static selectors do
not establish massive-world encounters, rendered acceptance or hardware budgets.
Full extended verification remains a separate frozen checkpoint.

## Causal interruption and transport verification

The actual8192/four-peer UDP server journey uses one explicit startup actor
pose/front and conserved stock12 carried+108 prior expenditure, plus a front
objective. All6144 infantry stocks and12 finite depot records are observed
read-only; no writes/freeze/renewal follow setup. The actor receives90 at360,
store12000→11910, then returns toward900,4200 by480. Bounded retries handle
observations crossing multi-field writes and OS preemption; permanent invalid
conservation cannot satisfy the observation deadline. This is a server travel/
stock oracle, not an exact replicated-stock or rendered-detour oracle.

A one-round production artillery encounter changes only hazard_enabled between
controls. Danger response disabled: the supply-bound soldier dies with no credit.
Enabled: danger acquires at8, the soldier physically disperses, remains100HP,
receives90 at374 and resumes primary travel. The entire enabled run replays at
the same-build checksum. No projectile/event/damage or danger-table fabrication.

A separate initial depot position is declared60m beyond the canonical opaque
wall. Proximity cannot grant stock through the wall. The actor routes around the
lower end, receives90 at3150 with clear actual LOS, then routes around the upper
end to the original3970,4200 goal at6223 and holds30 further ticks. An independent
closed double-precision slab oracle checks all6223 displacement segments against
the actual wall expanded by0.551m. Primary command bytes and total ammunition
stay unchanged; every step remains within actual infantry speed. This synthetic
site-position fixture is not authored-site/streaming/full-scale acceptance.

Permanent tests: test_supply_route_interruptions.py in combat/fast/simulation;
test_supply_route_network.py in network. Exact epochs, logs and limitations:
evidence/supply-route-causality.json. Runtime sources/policy are unchanged.
