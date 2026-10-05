# Ground ordnance allocation oracle

`tests/test_ordnance_fairness.py LIBRARY` measures actual production `sim_tick`
launches. Its default mode requires balanced side grants under saturation; its
explicit `--legacy` mode instead verifies the former fixed-index bias. If the
admission module is present, the latter selects `ordnance_enabled=0` rather than
mistaking a changed production firing phase for the old implementation.

The controlled fixtures retain original tank/artillery roles, generation1,
finite64-round initial stores and health. Single-role fixtures have256 or512 living sources per
side inside8,192 or16,384 entity arrays; mixed fixtures have768 or1,536 per
side. Those controlled fixtures are not full-living-army scale evidence. They remove unrelated actors and deploy
the retained sources on two opposing, adjacent spatial cells with valid physical
LOS at300m, then issue real hold orders. All sources of a role share its original
index phase. No projectile, combat event or gameplay damage record is fabricated.
Hazard response is explicitly disabled in these fixtures to isolate admission;
the natural dense scenarios below keep it enabled. Positions overlap deliberately
for stress, so these fixtures establish no formation or crowd-motion acceptance.

After the first production volley, the oracle independently reads active shell
source IDs/generations, side, role, ammo decreases, cooldown and actual target LOS.
It checks the512-record pool has416 AI ground rounds and no duplicate grant to a
source. Side labels are swapped without reordering IDs, and every fixture is
replayed with an identical checksum. Mixed-role saturated fixtures additionally
require104 grants for each of the four side/weapon-role groups. Empty ammunition,
active cooldowns, wall-obstructed LOS and dead-source negative controls must
produce no launches or pool-pressure rejects.

On the immutable pre-admission code at
`49ccd4d352e345df80e463ed0f3eaecfef013a9a`, production tests demonstrated:

| Scenario | Eligible per side/role | Side0 grants | Side1 grants | Rejects |
| --- | ---: | ---: | ---: | ---: |
| 8,192 single tank or artillery phase |256 |256 |160 |96 |
| 16,384 single tank or artillery phase |512 |416 |0 |608 |
| 8,192 mixed tank/artillery |512 tanks +256 artillery |0 tanks +256 artillery |0 tanks +160 artillery |1,120 |

Swapping side labels swaps these grants, proving that the advantage follows ID
ordering rather than a faction policy, range, LOS, ammunition or cadence. The
mixed legacy fixture runs through tick4, whereas the queued admission fixture
runs tick1 because the new scheduler submits ready vehicles independently of the
infantry8-tick phase. Thus the mixed result also exposes the former phase-induced
role exclusion; it does not claim that faction imbalance alone explains every
natural battlefield difference.

The oracle also runs seed42 `scale-front` and `scale-hotspot` for120 production
ticks twice, with all8,192 original roles and normal hazard response. It counts
new active shell generations and distinct source IDs by side/weapon kind, retains
pool peak/drops and verifies same-build replay. These samples omit launches that
retire within the same simulation tick. They therefore must not be presented as
exact total launches or fairness among physically ineligible sources. Natural
losses, target selection, LOS and finite stores remain relevant explanations for
unequal counts; the isolated mirrored fixture supplies the causal proof.

Run against an actual linked production library, e.g. the `build/libsim.so`
created by `python3 tools/dev.py test --suite combat`:

```sh
python3 tests/test_ordnance_fairness.py build/libsim.so --report runs/ordnance-fairness.json
python3 tests/test_ordnance_fairness.py build/libsim.so --legacy --report runs/ordnance-legacy.json
```

This is allocation/eligibility and replay evidence. It does not prove complete
combined-arms tactics, air/player reservation fairness, sustained per-entity
maximum wait, rendering, audio, networking, dense-battle performance or art quality.

An independently linked candidate using the integrator's world hooks plus the
new admission module passed the production oracle:208/208 grants in single-role
fixtures and104 for each mixed-role group, at both8,192 and16,384 counts, with
side-label swaps and all eligibility negatives. Its explicit legacy mode retained
the old allocation counts and natural dense samples exactly (authoritative
checksums differ because the new private scheduling state is now hashed).

In120-tick natural seed42 samples the candidate retained252/259 tank launches
in `scale-front` and234/235 in `scale-hotspot` (side0/side1), versus334/33 and
341/28 in the legacy control. Artillery samples were173/157 and204/198. The
pool still peaked at480 including airborne ordnance. Drop counters rose from
7,772/9,793 to51,481/72,404 because ready ground sources now request every tick,
rather than only their8-tick phase; these counters therefore cannot be compared
as equivalent-cadence failure rates. This candidate check is not final frozen
integration evidence; the integrator records the accepted commit and full checks.

A sustained variant continues the16,384-ID single-tank fixture through120 more
production ticks. It begins with512 living sources on each side and leaves
projectile travel, physical impacts, finite health/ammunition and cooldowns alone.
The legacy control fired862 rounds from the lower-ID side and0 from the other,
although the latter supplied52,512 observed physically-ready source/tick samples.
Mirroring side labels reversed the advantage. The candidate fired451 rounds
from each side, left272 original sources alive on each side, and began110 of
the continued ticks at the416-round AI ground limit. All repeated outcomes and
checksums matched. Actual launch totals here derive from finite ammunition
expenditure and thus include same-tick shell retirements; no resupply/vehicle
operator runs in this isolated fixture. Equal casualties in this symmetric test
do not imply equal battlefield outcomes in naturally unequal deployments.
