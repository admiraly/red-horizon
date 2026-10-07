# Attached aircraft wreck combustion

Readonly NASM packing derives GPU emitters from the existing authoritative local
or admitted remote crash96 records. Pose, actual velocity, source sequence/state
and age come exclusively from these records and the current authority/server tick.
No independent lifetime clock can restart the effect during frozen frames. The
cosmetic envelope ends at600ticks (20seconds), fades18..20seconds, and disappears
on record expiry/reset. It does not extend or otherwise change crash lifetime.

Fixed128-slot scan selects at most32valid records within1500m horizontal camera
range. Each emitter draws16billowing smoke puffs and four fire quads (640logical
quads maximum); tactical view suppresses them. Slot-order selection can omit
additional simultaneous close wrecks. Smoke centres reconstruct the last0.6s of
ballistic travel from current recorded V/gravity, with bounded rise/wind drift;
landed smoke rises from the stationary record. GPU sequence seeds are independent
of emitter slot. Per-puff smoke alpha is at most0.06. Current fire is a flickering
billboard prototype, not production fire art/HDR/dynamic lighting.

Native766calls pass159overlapping aliases, ABI/source-readonly/atomic-error/expiry,
local-versus-remote selection, fixed32cap and frozen-tick repeat controls. Actual
embedded GL57cases/6840vertices pass independent centres (max error0.000061m),
finite positions/alpha, map/expiry hiding and slot-independent seed geometry.
Actual local and UDP client paired effect toggles show166..226changed pixels at
both real-cannon-replay aircraft roles' death/fall/contact, and zero at expiry.
Source records and living mesh counters remain unchanged. These are explicitly
frozen cosmetic source-clock client fixtures; separate public authority replays
use only declared initial births and genuine producer rounds, without live renewal.

Original actual aircraft bombing/cannon GL and43case GPU breakup regression pass:
bomb35→177, cannon destruction13,440paired death pixels and1145aging pixels.
No general flight realism, timing/quality/spectacle acceptance is inferred.

Three setup/quality failures were corrected without weakening gates: missing
sim_tick_count extern stopped first assembly; native test passed bytearray to
ctypes.memmove instead of immutable bytes; original small/occluded flame gave
23pixels against retained>25gate. The flame is now larger/above the body and the
trail sampling shorter/dense. All final focused checks pass, no frozen sources
were modified. Full443028e6200e remains pending. Evidence air-crash-plume-focused.json.
