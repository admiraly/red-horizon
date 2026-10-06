# Terrain-supported driver eye integration

The stateless eye contract is now used by real tank boarding, entry LOS,
held driving and cannon targeting. `hull_eye_query` first validates the actual
live allied tank ID, entity generation, matching active motion generation/kind
and stamped heading. Existing reverse ownership and player-generation checks
remain in the surrounding vehicle APIs. Entry queries before acquiring a claim.
Held driving validates before movement and refreshes the eye after the actual
hull step. The query transforms the retained local `(0,3,0)` gameplay anchor
through unsmoothed terrain support, raised to the five-point contact floor.
It does not read the renderer's spring cache or depend on render timing.

Cannon targeting uses authoritative player eye XYZ plus the existing 600 m world
look vector. The shell source remains the existing upright hull-center launch
point. Camera yaw/pitch remain world look and camera roll remains absent. Exit
still chooses among the actual hull-center offsets, with LOS starting at the
current supported eye. This is a gameplay anchor, not a measured cockpit or
muzzle socket. Artillery remains AI driven; no new playable vehicle type is
claimed.

The connected Linux client suppresses infantry footstep preview while boarded.
Received driver XYZ feeds the existing correction smoothing. No vehicle motion
prediction or new wire layout is introduced. The ground-content digest includes
the eye contract version and local anchor height: `0x8b275091`, full canonical
SHA-256 `8b275091a755d20a2e53b01c8379cc707d6bed1c08376d6a232f831fd48d9170`.
UDP remains version7 with the existing schema hash.

Direct invalid entry leaves authority untouched. Invalid held support holds
physical/eye/motion state, claims, resources and events and prevents cannon fire.
The ordinary known-button input history is consumed before that support guard;
its first FIRE edge can change the checksum, while a repeated held edge remains
stable. Unknown buttons and invalid numeric inputs reject before that history
handling. Public gameplay evidence covers these distinctions explicitly.

Existing vehicle/grade/body observers now compare attachment against the actual
eye query rather than obsolete hull-center XZ/upright Y. Their independent
physical sweeps, radii, grade limits, speed/turn coherence, health, dense coverage
and arrival deadlines are preserved. Fixtures that change infantry into tank
before movement now initialize the new birth's generation-safe motion stamp;
no in-flight motion or health reset is introduced. The separate
`test_ground_eye_outcomes.py` computes its own least-squares terrain fit and
matrix/contact transform and never calls the production eye/support kernels.
It also checks actual shell direction and compares four natural hull traces
with the previous accepted runtime. Actual client proof separately uses the
production eye contract to verify local/received integration, keyboard controls,
correction convergence and boarded preview. Its frozen-server/aged-preview
fixture is cosmetic timing isolation, not UDP fault acceptance.

Prepared component evidence remains in ground-eye.md; public outcomes and
actual-client scopes are in ground-eye-outcomes.md and ground-eye-client.md.
Root frozen-job evidence, including initial obsolete-assertion and incomplete
birth-fixture failures, is retained under evidence/ground-eye-*.

Remaining vehicle work includes verified sockets and turret articulation,
terrain-aware muzzle launches, damage states and useful wreck cover, additional
vehicle roles and physical orientation. Software GL and null audio checks do
not establish target hardware performance, recorded sound listening or human
artistic acceptance. The complete game goal stays active.

Extended controls now establish live stamped births before disabling motion.
For the body-disabled legacy control only, leaving supported bounds must hold
the previous valid eye; ordinary candidate paths still require valid support
and exact attachment. The counterfactual controls do not disable new eye safety
for the sake of producing an old fault. Original physical negative controls and
all candidate movement/health/density gates remain.

Final root checkpoint: frozen full extended job6950d874d02f passed574.9486s
at89b957ed8cd41f9be1a3352cee22113669f79d1d-450d228a6b32576b,90reports
and all201authored inputs matched. Seventeen root jobs and four extra exec
sessions are terminal, including ten retained failed job attempts and one
failed extra body-control attempt. Current and old physical/rendered controls
remain separately labelled. See evidence/ground-eye-session.json for exact
source/artifact identities and limitations.
