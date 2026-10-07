# Next aircraft recovery integration

Current approach evidence establishes airborne circuit, final alignment, controlled descent and go-around. Touchdown cannot safely be added by setting height to terrain or refilling private fuel. The following current consumers constrain the next implementation.

| Consumer | Current authoritative rule | Required landing integration |
| --- | --- | --- |
| `air_bank_step`, `air_vertical_step` | Speed5..7m/tick; conserve XYZ total speed; bounded bank/vertical acceleration | Separate air approach and ground roll policy, validated speed/energy envelope and bounded longitudinal acceleration; preserve existing cruise math/negative controls |
| `air_fuel_step` | Rejects speed outside5..7; finite generation-scoped units and fixed-tick burn | Explicit grounded/engine state, no duplicate-tick burn or reset; finite depot-backed transfer only |
| `air_final_clear` |120 uninterrupted final ticks with production bank/vertical actuation and per-fragment terrain/solid hull sweeps; unsafe final releases airborne lease and rejoins circuit | Extend to variable-speed/energy envelope and ground-safe contact/rollout; retain malformed-source abort and actual hazardous-approach controls |
| `air_world_warning`, `air_world_sweep` |120-tick own-velocity forecast;4m swept hull; all living ground contact is fatal | Approach profile preview and guarded runway contact under geometry/heading/vertical-speed constraints; collision with terrain elsewhere, solids and airborne hazards must remain real |
| `air_separation_step`, `air_holding_goal` | Squared physical velocity24.9..49.1 | Role/mode-aware air/ground validation; no removal of original near-pass separation and unavailable-base holding controls |
| `net/client.asm` aircraft parser | Maximum public modeAIR_GLIDE4 and existing motion bounds | Versioned touchdown/rollout/parked/takeoff fields/modes and all-or-nothing malformed packet checks; maintain source generation, local alias protection and real UDP fault coverage |
| `audio/aircraft.asm` | Living engines switch off only inGLIDE | Ground engine idle/off and takeoff presentation from authoritative phase; no paused-loop disguising actual exhausted fuel |
| Recovery facility selection | Current friendly connected alive uncontested command/depot | Revalidate capability before touchdown/service; bounded deterministic runway reservation/expiry and abort paths; captured facilities and base loss remain real |
| Logistics stores | Existing finite owned supply/ammunition policies | Explicit fuel/repair/rearm costs and cadence, capacity/ownership checks and atomic consumption; no infinite or generation-based service refill |

Acceptance must use actual public flights from initial births, without recurring pose, HP, ammunition, fuel or clock renewal. Include both roles/sides, poor alignment, cross-track error, adverse bank/vertical speed, exhausted fuel, base loss and occupancy; verify unsafe approaches abort or suffer genuine contact. A successful lifecycle must physically approach, decelerate, contact under allowed limits, roll within available runway, park, consume finite resources and launch again. Matched negative controls should expose omitted braking, contact guards, traffic admission and store debit. Preserve original8192/16384 aircraft behavior, real graphics/UDP/fault checks and final exact-source replay hash evidence.

This is an implementation dependency/acceptance contract, not evidence that any landing/service feature exists. Full game completion still requires all other specification requirements and owner-approved licensing.
