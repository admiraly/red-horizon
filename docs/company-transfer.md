# Consented company exchanges

A connected player can propose exchanging their company with another player's
company. The recipient must explicitly accept the current proposal. Both keep
one company. This implements company transfer without leaving a player without
a command assignment; squad splitting, assistance, recruitment and arbitrary
multi-company ownership are separate work.

Proposals have a 15-second (450-tick) lifetime. Each captures both company keys,
body generations and lease serials. Accept, decline and cancel require the
exact proposal sequence. A different recipient, changed generation/lease,
disconnect, expiry or replaced proposal rejects before changing authority.
Acceptance updates both owner bindings and lease serials atomically, preserves
each company's current accepted intent, and invalidates all proposals involving
either participant. Player command/deployment fronts follow the new companies;
position, orientation, health, stores, generation and vehicle attachment are not
changed by the exchange. No transfer charges requisition or creates units.

NASM authority hashes and initializes the four bounded 48-byte proposal records.
Each ordinary tick clears expired or no-longer-valid proposals after player
updates. A proposal sequence cannot wrap into a reused or sentinel identifier;
exhausted request identities reject. Source generations/leases, not a pending
state name alone, authorize a transaction.

UDP v25 adds message 6 with a 12-byte action/other-player/sequence payload. Existing
endpoint/session/reliable-sequence checks deduplicate lost acknowledgements,
including an accepted exchange. Companies message 107 now carries 356 bytes of payload:
the four existing 40-byte assignments followed by four 48-byte proposals.
Clients validate the entire batch atomically against its captured assignments,
expiry and reserved fields. Delayed player/company packets hide an offer until
both current bodies corroborate it. No local ownership or spending is predicted.

Default keyboard controls are F5–F8 to request exchange with P0–P3, F9 to accept
the displayed incoming request, F10 to decline it, and F11 to cancel one's own.
Holding a key issues one edge request. Requests and consent queue behind an
unacknowledged movement packet, then use the reliable transport; a busy frame
does not discard the action. Incoming offers, reliable completion and
rejection appear in the window title. Multiple incoming requests are displayed
in stable requester order; accepting one invalidates competing affected offers.
When authority changes fronts, the tactical view follows if it was inspecting
the player's former own front; deliberate other-front inspection stays selected.
Old-front orders reject and the new owner can command the exchanged company.

Verification includes controlled physical hold/advance after cross-front swap,
nonvolatile-register preservation, stale sequence/generation/lease rejection,
public-tick expiry, real four-player UDP on the original 8192-unit world with a
read-only observer, lost propose/accept ACKs and production NASM adapter actions,
and actual two-render-client keyboard/feedback/front/highlight checks. A
separate rendered run uses two real UDP relays with 75 ms one-way delay,
deterministic loss, jitter and reordering, and observes a request queued behind
an in-flight movement packet before one accepted exchange. The
company parser additionally rejects 17 malformed proposal batches atomically.

The keyboard/window-title UI does not establish remappable contextual controls
or complete fullscreen text presentation. No human quality, GPU budget, full
operation, assistance or squad-splitting acceptance is claimed. Exact scoped
logs and hashes accompany the integration record; full checkpoint status must
be read separately from focused results.
