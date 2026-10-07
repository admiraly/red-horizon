# Deployment outside incoming blast zones

`deployment_blast_clear` is a read-only NASM authority query. Joining and natural
redeployment call it after physical crowd/body/terrain clearance and before
publishing a player. Hostile tank shells, artillery shells and bombs are checked
against their actual stored positions, velocities, finite TTL and blast radius.
The next90 production fixed-tick segments use the same f32 position/gravity order;
a20m margin supplements blast radius. Friendly explosives and nonexplosive air
cannon rounds follow the existing player-damage policy and do not exclude sites.

Only a corridor near the candidate triggers production `world_contact_query`
forecasting. The first ground or solid contact ends that flight's danger; its
actual interpolated impact is tested instead. Actor interception and temporary
wrecks are not trusted to persist through future ticks. If no static contact ends
the nearby flight, the corridor remains conservative. Malformed active hostile
positions/velocities/radii/kinds and malformed contact sources fail closed.
Recent actual hostile tank/artillery/bomb impact records exclude their radius
plus margin for30 ticks, including unsigned tick/sequence wrap. The query never
changes projectiles, events, players, clocks or authority hashes.

Native controls exercise straight/ballistic/stationary/expired/off-map/high/far
trajectories, last pool slot, malformed data, first static terrain contact,
recent/expired impact boundaries and wrap. Real assembly probes preserve six
callee-owned registers/stack and authority bytes/hash. A public finite tank launch
at the otherwise valid initial deployment makes the real join choose x3700 rather
than3780; over60 genuine ticks it staysHP100. A development-only library omitting
only the player guard call joins3780 and reachesHP20 from the same real shot.
The safe-formation fixture and no-shot join prove this is caused by the guard,
not loss of squad support. No live pose/HP/ammo/projectile/clock renewal follows
setup. Four real UDP peers still deploy near both dense authored battles, and all
four120-tick dedicated runs match shared-authority replay exactly.

An initial corridor continued beyond terrain impacts and correctly failed the
near-battle network gate by falling back to distant sites. Production static
contact forecasting fixes that; the gate remains intact. First forecast revision
had a fallthrough caught by the off-corridor control and corrected before
integration. First native ABI wrapper lacked a PLT call and failed shared linking;
corrected development probe passes. These failures are retained. Initial tank
fixture killed allied support and could not prove causal deployment; final
supported/no-shot and omitted-hook controls replace that insufficient observation.

This is bounded three-second incoming exclusion and one-second recent-impact
cooldown, not protection from all future firing. Dynamic cover changes, future
body motion, full operation spawn-camping/revive/site-choice acceptance, worst-case
512-active-projectile forecast cost and target hardware budgets remain unverified.
Projection can over-reject a shot that would hit a moving actor or temporary wreck.
It adds no public layout, UDP40, schema/content or client-authored damage command.
