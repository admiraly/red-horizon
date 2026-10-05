#!/usr/bin/env python3
"""Physical danger outcomes over the production NASM world, with a negative control."""
import ctypes as C
import json
import math
import sys

lib = C.CDLL(sys.argv[1])
lib.sim_init.argtypes = [C.c_uint, C.c_uint]
lib.sim_checksum.restype = C.c_uint64
lib.projectile_launch.argtypes = [C.c_uint, C.c_uint, C.c_float, C.c_float, C.c_float]
lib.hazard_query.argtypes = [C.c_uint, C.c_float, C.c_float, C.c_float]
lib.terrain_height.argtypes = [C.c_float, C.c_float]
lib.terrain_height.restype = C.c_float
lib.terrain_blocked.argtypes = [C.c_float, C.c_float, C.c_uint]

class Entity(C.Structure):
    _fields_ = [("x", C.c_float), ("z", C.c_float), ("hp", C.c_uint),
                ("side", C.c_uint), ("kind", C.c_uint), ("front", C.c_uint),
                ("target", C.c_int), ("generation", C.c_uint)]

class Projectile(C.Structure):
    _fields_ = [(n, C.c_float) for n in ("x", "y", "z", "vx", "vy", "vz")] + [
        (n, C.c_uint) for n in ("ttl", "side", "kind", "damage")] + [
        ("radius", C.c_float)] + [(n, C.c_uint) for n in (
            "source", "generation", "active", "source_generation", "reserved")]

class Event(C.Structure):
    _fields_ = [(n, C.c_float) for n in ("x", "y", "z")] + [
        (n, C.c_uint) for n in ("kind", "side", "tick")] + [
        ("radius", C.c_float), ("sequence", C.c_uint)]

entities = (Entity * 32768).in_dll(lib, "sim_entities")
projectiles = (Projectile * 512).in_dll(lib, "sim_projectiles")
events = (Event * 256).in_dll(lib, "sim_events")
ammo = (C.c_uint * 32768).in_dll(lib, "sim_shell_ammo")
alive = (C.c_uint * 2).in_dll(lib, "sim_alive")
enabled = C.c_uint.in_dll(lib, "hazard_enabled")
class HazardState(C.Structure):
    _fields_ = [("generation", C.c_uint), ("until", C.c_uint),
                ("goal_x", C.c_float), ("goal_z", C.c_float),
                ("center_x", C.c_float), ("center_z", C.c_float),
                ("projectile", C.c_uint), ("projectile_generation", C.c_uint)]
states = (HazardState*32768).in_dll(lib, "hazard_states")
metrics = (C.c_uint64*8).in_dll(lib, "hazard_metrics")


def fixture(on, source=(1000, 2000), aim=(1240, 2000), victims=None):
    """Only pre-encounter poses/stocks are authored; launches/damage are production."""
    assert lib.sim_init(32, 73) == 0
    enabled.value = on
    for e in entities[:32]:
        e.hp = 0
    alive[0] = alive[1] = 0
    e = entities[14]
    e.x, e.z, e.hp, e.side, e.kind, e.front, e.target = *source, 100, 0, 2, 0, -1
    ammo[14] = 1  # One real incoming round prevents follow-up fire confusing outcomes.
    alive[0] = 1
    victims = victims or [(aim[0]+33, aim[1]), (aim[0], aim[1]+33), (aim[0], aim[1]-33)]
    for i, point in enumerate(victims, 16):
        e = entities[i]
        e.x, e.z, e.hp, e.side, e.kind, e.front, e.target = *point, 100, 1, 0, 0, -1
        alive[1] += 1
    for side in (0, 1):
        for front in range(3):
            assert lib.sim_order(side, front, 1) == 0  # Genuine manual hold, interrupted only by danger.
    lib.sim_tick()  # Builds the production spatial grid before the actual launch.
    assert lib.projectile_launch(14, 2, aim[0], lib.terrain_height(*aim), aim[1]) == 0
    assert ammo[14] == 0
    return aim, victims


class Aircraft(C.Structure):
    _fields_ = [(n,C.c_float) for n in ("y","heading","pitch","bank","speed")] + [
        (n,C.c_uint) for n in ("role","mode")] + [("target",C.c_int)] + [
        (n,C.c_uint) for n in ("cooldown","ammo","generation")] + [
        (n,C.c_float) for n in ("vx","vy","vz")] + [(n,C.c_uint) for n in ("pass_ticks","flags")]
aircraft=(Aircraft*32768).in_dll(lib,"sim_aircraft")

def run(on, bomb=False):
    aim, initial = fixture(on)
    if bomb:
        lib.projectile_init()
        e=entities[14]
        e.kind,e.x=3,1040
        lib.air_init()
        a=aircraft[14]
        a.y=lib.terrain_height(*aim)+.0109*40*39/2
        a.heading,a.pitch,a.bank,a.speed=math.pi/2,0,0,5
        a.role,a.mode,a.target,a.cooldown,a.ammo=0,0,-1,0,1
        a.generation,a.vx,a.vy,a.vz,a.pass_ticks,a.flags=e.generation,5,0,0,210,1
        assert lib.projectile_air_launch(14,3)==0
        assert a.ammo==1  # Launch primitive preserves stores; production air FSM owns spending.
    history = []
    peak_move = [0.0]*len(initial)
    first_moves = [None]*len(initial)
    for tick in range(1, 101):
        lib.sim_tick()
        row = []
        for n, (i, start) in enumerate(zip(range(16, 19), initial)):
            e = entities[i]
            distance = math.dist((e.x, e.z), aim)
            moved = math.dist((e.x, e.z), start)
            peak_move[n] = max(peak_move[n], moved)
            if moved > .01 and first_moves[n] is None:
                first_moves[n] = tick
            assert lib.terrain_blocked(e.x, e.z, e.kind) == 0
            if history:
                assert math.dist((e.x, e.z), history[-1][n][:2]) <= .1206, "danger must preserve infantry speed"
            row.append((e.x, e.z, e.hp, distance))
        history.append(row)
    impacts = [(e.x, e.y, e.z, e.kind, e.tick) for e in events if e.sequence and e.kind == (7 if bomb else 4)]
    assert impacts and entities[14].hp == 100 and (aircraft[14].ammo if bomb else ammo[14]) == (1 if bomb else 0)
    assert sum(p.active for p in projectiles) == 0
    # Once the finite danger commitment expires, the explicit hold resumes.
    assert history[-1] == history[-10]
    assert all(lib.hazard_entity_goal(i)==0 for i in range(16,19)), "expired danger did not restore orders"
    return {"enabled": bool(on), "initial_distances": [math.dist(p, aim) for p in initial],
            "final_distances": [r[3] for r in history[-1]],
            "final_hp": [r[2] for r in history[-1]], "first_movement_ticks": first_moves,
            "peak_displacements": peak_move, "impact_events": impacts,
            "source_hp": entities[14].hp, "source_remaining_rounds": aircraft[14].ammo if bomb else ammo[14],
            "decisions": {"acquired": metrics[2], "dispersion": metrics[3], "shelter": metrics[4]},
            "checksum": f"{lib.sim_checksum():016x}"}

control = run(0)
active = run(1)
repeat = run(1)
assert active == repeat, "identical physical encounters must replay deterministically"
assert control["final_hp"] != active["final_hp"], (control, active)
assert sum(active["final_hp"]) > sum(control["final_hp"]), (control, active)
assert all(d > 35 for d in active["final_distances"]), active
assert all(d == 0 for d in control["peak_displacements"]), control
assert all(d > 2 for d in active["peak_displacements"]), active
assert all(t is not None and t <= 8 for t in active["first_movement_ticks"]), active

bomb_control=run(0,True)
bomb_active=run(1,True)
assert bomb_active==run(1,True)
assert sum(bomb_active["final_hp"])>sum(bomb_control["final_hp"]), (bomb_control,bomb_active)
assert all(d>36 for d in bomb_active["final_distances"]), bomb_active

# An actual visible incoming shell induces a physically reachable shelter goal.
# The disabled actor is already blast-occluded here; this proves the selected
# path/cover, not a universal shelter survival advantage.
fixture(1,source=(4018,1050),aim=(4018,1110),victims=[(3980,1090)])
start=(entities[16].x,entities[16].z)
for _ in range(8): lib.sim_tick()
assert metrics[4] > 0 and lib.hazard_entity_goal(16)==1
shelter=(states[16].goal_x,states[16].goal_z)
assert math.dist(start,shelter)<=24
lib.terrain_path_clear.argtypes=[C.c_float]*4+[C.c_uint]
lib.terrain_los.argtypes=[C.c_float]*6
assert lib.terrain_path_clear(*start,*shelter,0)==1
assert lib.terrain_los(4018,lib.terrain_height(4018,1110)+1,1110,
                       shelter[0],lib.terrain_height(*shelter)+2,shelter[1])==0
for _ in range(50): lib.sim_tick()
assert entities[16].hp==100 and math.dist((entities[16].x,entities[16].z),start)>0.5
shelter_report={"initial_pose":start,"selected_goal":shelter,
                "final_pose":(entities[16].x,entities[16].z),"hp":entities[16].hp,
                "reason":"reachable physical terrain shelter", "survival_advantage_claimed":False}

# Perception is local, enemy-only and read-only. These cases use production
# launched rounds; no hazard table or damage/event fabrication.
fixture(1)
lib.hazard_tick()
def query(side, x, z):
    before = lib.sim_checksum()
    result = lib.hazard_query(side, x, lib.terrain_height(x,z)+2, z)
    assert lib.sim_checksum() == before, "read-only danger query altered authority"
    return result
assert query(1,1273,2000) >= 0
assert query(0,1273,2000) == -1  # Friendly artillery is not an observed enemy threat.
assert query(1,1800,2000) == -1  # Actual current projectile beyond300m.
fixture(1, source=(3970,1300), aim=(4010,1300), victims=[(4020,1300)])
lib.hazard_tick()
assert query(1,4020,1300) == -1  # Opaque wall separates observer from actual shell.

# Tank rounds still cause physical damage, but cannot manufacture artillery cues.
fixture(1)
lib.projectile_init()
entities[14].kind = 1
ammo[14] = 1
assert lib.projectile_launch(14,1,1240,lib.terrain_height(1240,2000),2000) == 0
lib.hazard_tick()
assert query(1,1273,2000) == -1

fixture(1)
for _ in range(8): lib.sim_tick()
assert lib.hazard_entity_goal(16) == 1
entities[16].generation += 1
assert lib.hazard_entity_goal(16) == 0, "reused actor inherited committed danger goal"
fixture(1)
for _ in range(8): lib.sim_tick()
assert lib.hazard_entity_goal(16) == 1
(C.c_int*32768).in_dll(lib,"vehicle_entity_driver")[16] = 0
assert lib.hazard_entity_goal(16) == 0, "boarded actor received independent steering"

print(json.dumps({"suite": "hazard_outcomes", "production_artillery": {
    "negative_control": control, "observed_dispersion": active,
    "deterministic_repeat": True}, "production_bomb": {"negative_control": bomb_control, "observed_dispersion": bomb_active, "deterministic_repeat": True}, "observed_shelter": shelter_report, "perception_exclusions": ["friendly", "out-of-range", "opaque-wall", "nonexplosive"], "state_rejections": ["generation-reuse", "boarded"], "scope": "Controlled initial poses, production artillery/bomb launch primitives and real world movement/collision/damage; not full air FSM, commander or dense-storm acceptance"}))
