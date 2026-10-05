# ABI v1
Linux SysV AMD64, NASM, SSE2. Calls preserve RBX/RBP/R12–R15; RSP is 16-byte aligned before CALL. No pointers into reloadable code in persistent state.

Simulation: sim_init(EDI=count, ESI=seed) -> EAX=0 success/-1 invalid; sim_tick() -> void; sim_checksum() -> RAX deterministic hash; sim_order(EDI=side, ESI=front, EDX=mode) -> EAX status. Exports sim_count (u32), sim_tick_count (u32), sim_alive[2] (u32), sim_engaged (u32), sim_entities (capacity 32768, stride 32). Entity: x float offset 0, z float 4, hp u32 8, side u32 12, kind u32 16, front u32 20, target i32 24, generation u32 28. Coordinates 0..8000 metres. Kinds 0 infantry, 1 armour, 2 artillery, 3 aircraft. No client camera dependencies.

Headless and client are separate assembly entry points linking the same simulation. Renderer owns input, display and visual state, never simulation storage layout. Headless emits JSON statistics. Tools benchmark subprocesses, not a Python simulation.

Additional prototype APIs: sim_fire(EDI=index,ESI=damage1..100)->EAX0/-1 applies guarded damage to a living enemy only; sim_waypoint(EDI=side0/1,ESI=front0..2,XMM0=x,XMM1=z)->EAX0/-1 accepts finite0..8000 metre goals, preserves invalid state; sim_waypoints[6] has8-byte float x/z records in side*3+front order. Goals affect replay hashes. sim_spend(EDI=side,ESI=positivecost)->EAX0/-1 checks single-thread authoritative balance.

Twelve sites are described in docs/operation.md, with sim_sites stride32, sim_requisition/sim_supply[2], sim_operation_state. Operation state and warning timers are part of checksums; no saved schema migration exists. audio_init/audio_shot/audio_update/audio_shutdown and mixer test ABI are described in docs/audio.md. Standalone UDP proof has a separate version1 fixed32-byte contract in docs/network.md and is not yet the gameplay protocol.
