# Dense army fixtures

`sim_scenario(EDI)` accepts0 (unchanged),1 (existing air-battle),2 (scale-front),
and3 (scale-hotspot). Nonzero modes require authoritative tick0; dense modes
require at least8192 army entities. Invalid modes, undersized worlds and late
calls return-1 before writing state. Modes2/3 keep every soldier/vehicle entity,
HP, side, kind, front, generation and target. They set initial encounter poses,
including the existing finite-store real aircraft initialization, and relocate
connected players. They do not seed projectiles, damage, events or engagement
counters. The remaining army continues its existing three-front operation.

At8192 actors the unchanged full mix is6144 infantry,1024 armour,512 artillery,
and512 aircraft; each side has4096 actual entities. Each dense fixture selects
first qualifying entities in stable entity order, preserving the mixed roles.

| Fixture | Ground per side | Ground layout | Allied/enemy Z | Player X,Z |
| --- | ---: | --- | --- | --- |
| scale-front |1280|64columns ×20rows,10m ×8m spacing, X3200–3830|2400–2552 /2580–2732|3515,2280|
| scale-hotspot |1920|64columns ×30rows,8m ×6m spacing, X3200–3704|2400–2574 /2610–2784|3452,2300|

Both retain the air-battle32aircraft per side:8columns at40m spacing starting
X3400; allied rows start Z2100 and increase50m, enemy rows start Z3150 and
decrease50m. Real alternating bomber/fighter poses and finite8bomb/180gun
stores enter production flight, targeting and weapons. Player eye is terrain
height+1.8m and no health or ammunition is granted. Players begin behind the
allied ground line, approximately300m from the nearest enemy ground line.

Focused seed42 verification joins one local player and samples actual living
cohort enemy targets after production ticks1/8/16/30. Each target is independently
checked for enemy side, ground role, weapon range and production terrain LOS.
Front samples are2560/2012/1849/1047; hotspot samples are3837/974/772/2182.
Thus front establishes at least2048 actual engaged regional actors initially;
it does not establish sustained2048 engagement throughout an operation.

Through120ticks the joined-player fixture reports front155119 HP damage,
890dead actors and307actual shell-launch events; hotspot196431 HP damage,
1089dead actors and339shell launches. Both emit shell impacts, bombardment,
gunfire and aircraft impacts through the unchanged production systems. All
relocated actors move; exact same-build replay is checked twice per mode.
Standalone/no-player verification may produce different totals and checksums
because joining a player changes authoritative operation state.

These are physical concentration fixtures, not an acceptance claim for complete
intelligent coordinated offensives. Real ground-level occlusion can hide actors.
The3840-ground hotspot cohort is not proof of1024 pixel-visible actors,
individually detailed models, audio quality or target-machine frame rate.
Those require separately measured renderer/audio/hardware evidence. No camera
or observer position changes authoritative combat rules.
