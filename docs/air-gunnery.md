# Physical fighter firing decisions

The flight controller continues to steer toward its observed3D intercept.
`air_gun_solution_ready` waits to fire until the actual forward round would
pass within the current physical actor contact envelope, assuming constant
observed target velocity. It forms relative round-minus-target velocity,
computes closest approach within the real40tick lifetime, and checks the
shared `SHELL_CONTACT_RADIUS`. Existing living/opposing/current-generation,
finite-pose/store/cooldown and broad forward-cone guards run first.

This is a read-only decision. The producer still emits28m/tick along the
physical flight vector; no target-directed trajectory, new hitbox, damage,
ammunition or motion is introduced. Cannon store debit remains with actual
admitted launches. The same observed target range/LOS selection precedes
the decision; no new perception cache/FOV or future target truth is claimed.

Initial original8192/900tick closest-approach observer: broad-cone control
matched3648retained births with median17.58m/p90 56.20m miss and407within4m;
candidate matched848births with median2.20m/p90 3.75m and848within4m.
Actual target clearing left3/2unmatched births respectively. Exact observer
and limitations: evidence/air-gun-accuracy-miss-observer.json.

The assembled matched broad-cone control changes only the firing decision.
Its original8192/900tick battle spends3687rounds for9800actual airHP loss and
4aircraft destructions. Candidate spends886rounds for9176HP loss and4
destructions, with identical candidate replay. This is better ammunition
efficiency, with slightly lower total damage; no kill-rate or universal
survival/spectacle improvement is claimed. Hostile manoeuvres after release
can still evade. The existing4m sphere remains a simplified contact proxy.

Focused actual aircraft, bank, strike-retry, protected-threat priority,
admission/fairness and real GL gun/bomb/destruction encounters pass. Final900independent oracle cases (including150constructed successes and150
misses),8sphere boundary cases,11invalid/ABI cases, crossing lead and actual
900tick full-army causal/replay control pass. Frozen fast317e480f7db9 passes
and is collected399.631673s; fullffefa501153e remains pending. Original8192/
16384 public900tick finite flight and400tick every-actor ground label symmetry
pass. Permanent simulation test now includes both army sizes; its later16k
observer extension is separately focused-tested after the full freeze. This
is coherent batch verification, not whole-game acceptance.
