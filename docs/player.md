# Authoritative player slice

Four 64-byte player records share the same NASM core as the army. `sim_init` resets them, `sim_tick` advances them at30Hz, and the replay checksum includes records, input intents and death/respawn counters. Clients provide finite movement/aim/buttons; they cannot provide HP, position, ammunition or rifle damage. Disconnected slots reject input. Runtime scratch is static and belongs to the single simulation thread.

Walking/sprinting covers5/9m per second with the same solid collision and height queries as army navigation. The rifle holds30 rounds, reloads in60ticks, and fires at most once per4ticks (133.3ms at30Hz). Each shot selects the closest living enemy in a450m aim cone with actual terrain/obstacle LOS and deals34damage. Allies and other humans are excluded. Suppression narrows the effective aim cone; visual camera shake is cosmetic.

Enemy pressure checks every16ticks per connected player. One visible enemy within160m contributes10damage and25suppression per check, independently of army density. Suppression decays each tick. This bounded threat rule avoids an8192-unit instant damage pileup; it is a prototype rule, not individual enemy rifle/projectile simulation.

Death disables movement/fire and starts a30tick deployment delay. Deployment first tries nearby allied formations while that front has a connected, healthy allied site, then connected healthy allied sites. Candidates must clear ground solids and have no visible living enemy within160m. If none are safe, the player remains dead and retries after30ticks. Air threat LOS uses actual altitude. Deployment does not spend requisition in this slice.

`tests/test_player.py` verifies rejected inputs leave records intact, measured speed, rifle hits and wall exclusions, firing cooldown/reload duration, enemy suppression/death, disabled dead controls, safe respawn and unavailable deployment, reset and intent-sensitive replay. These are development-only ctypes tests of real assembly objects.
