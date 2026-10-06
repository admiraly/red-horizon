# Next large gameplay batch: a coordinated assault

The current front controller in src/ai/tactics.asm surveys authored objectives,
uses actual acquired targets for threat counts, withdraws on observed overwhelming
strength or low own supply, and sends alternating squads along flank offsets.
Public-tick tests establish those limited outcomes. Aircraft independently align
bombing passes, intercept and break after damage. These are foundations, not a
coordinated company attack, protected bomber mission or complete commander.

The next player-visible batch must produce an actual autonomous combined-arms
assault in the full army. It must retain separate side knowledge and player
ownership: own formation readiness is authoritative; enemy force estimates come
from scoped, timestamped observations. Hidden positions must not choose tactical
goals. Explicit player orders take precedence and cancel conflicting commitments.

One integrator owns a bounded company-plan interface with persistent objective,
staging corridor, phase, observed threat estimate, readiness, support reservation,
commitment/cooldown and decision reason. Public operation orders and economics
remain the authority. Lower-rate planning must not stall continuous actuators,
fighter motion, emergency hazard response or player input. No new troop counts,
teleportation, free ammunition or replacement army may fabricate readiness.

A first complete demonstration must show scouts reaching useful observation,
infantry and armour approaching distinct reachable lanes, artillery genuinely
firing before an advance, and bombers making an actual finite-store pass while
fighters intercept aircraft threatening that mission. Plans must react to a
lost approach, observed excessive losses, supply interruption and destroyed
cover by adapting or withdrawing, rather than repeating a failed attack forever.
Readable formation intent, attack/abort acknowledgements and incoming warnings
must accompany the physical behaviour. Assets, shaders, animation, recorded
sound and effects should make these actions legible at normal player distance.

Acceptance must use production public ticks from initial fixtures, with no
in-flight pose/HP/store/clock renewal. Observe scouting before hidden-target
attack, arrival and held staging, actual release/damage/contact, infantry/armour
advance, withdrawal and recovery; report reasons and timings. Compare a causal
control without coordination, replay the same seed, swap faction labels and
retain original8k/16k motion,400tick health symmetry,360tick artillery arrival
and1200tick recovery gates. Follow with local and co-op rendered footage and
sound, independent visible/detailed/replicated counts and dense tick/frame cost.
State labels, event counts or submitted models cannot prove the assault.

Runtime work remains NASM/SSE2 and camera-independent. A full frozen checkpoint
with actual GL/audio and UDP fault coverage precedes integration. Human judgement
of spectacle, readable formations and enjoyable command remains separate and
unverified until feedback is obtained. This document records the next gameplay
acceptance contract; it does not claim implementation.
