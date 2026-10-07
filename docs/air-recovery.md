# Aircraft damage and ammunition recovery

Living initialized aircraft withdraw at60HP or below (30percent of the standard
200HP air birth), or when their own weapon stores are empty. The owned recovery
point is X2000/6000 by faction and Z2000/4000/6000 by front. These points lie
inside the existing1200m boundary-turn margin. The old empty-store X1000/7000
home points lay inside that margin and could be overridden toward the centre.
Recovery points are fixed own-side planning areas, not guaranteed secure bases.

The existing finite evasive manoeuvre completes first. Afterwards return mode
clears combat target/pass commitment, skips new combat acquisition/launches and
bypasses strike/pursuit guidance. Aircraft continue physical banked flight with
normal speed, vertical acceleration and map safeguards; no teleport, stopping,
landing, repair or ammunition refill occurs. Returning empty aircraft can still
observe dangerous incoming rounds and evade. Critical fighters and bombers are
ineligible for new/continued ordinary escort missions; own-side mission
validation remains read-only and no enemy positions are consulted for recovery.

The pure NASM goal helper validates owner identity, living aircraft kind,
faction/front, positive matching generation, active flag and role. Rejection
preserves fallback coordinates. Success uses only own health/stores and the
owned planning area, never another body or cached target. No private mutable
state is added. Content0xf5d0efa9 includes four recovery policy fields in both
canonicalizers. UDP39/schema0x212cb081/entity32/aircraft64/player64 are unchanged;
matching client/server policy is required.

The independent probe verifies9600 policy combinations,11 invalid owner cases,
ABI/stack/output guards, physical records read-only on every query and75 full
checksum policy samples plus malformed/hidden-target controls. An earlier slower
probe checked the full checksum on every combination; final development-only
sampling preserves every physical-body guard and reduces test overhead.

Four1200tick initial-empty-store flights cover both roles and factions. They
travel6000/8400m, retain200HP/zero stores/return mode, and approach within0.11 to
3.50m of their recovery point. These flights establish approach, not a stable
holding orbit or landing. A matched projectile-triggered case begins with six
real cannon producer rounds: criticalHP56 at tick5, finite evasion followed by
return at53, final recovery distance90.489m versus3424.694m with only the owning
fighter's recovery disabled. Both replay exactly, retain56HP/180rounds on each
plane and six initial gun events. The six direct producer calls do not debit
FSM stores; the shooter is already critical and withdraws under both policies.
No in-flight body/HP/ammo/generation/clock fixture writes occur. The result is
withdrawal behavior, not a general survival or coordinated air-cover claim.

Complete aircraft, original8192/16384900tick world bounds, fast core, ordinary
network and actual production-aircraft GL checks are separate evidence in
air-recovery-focused.json. Full extended verification remains a separate
integration checkpoint. Aerodynamic energy/fuel/stalls, runway/repair/rearm,
dynamic safe-base choice, withdrawal escorts and full tactical/visual quality
remain open, as does the complete game specification.
