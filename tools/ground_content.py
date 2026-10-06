#!/usr/bin/env python3
"""Development-only compatibility fingerprint for canonical roads, relief, grade and rendering policy."""
import argparse, hashlib, json, pathlib, re
from terrain_world import PATCH
ROOT = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
definitions = dict(re.findall(r'^%define ([A-Z_]+) ([-+A-Za-z0-9_.]+)$',
    (ROOT/'schemas/company_transfer.inc').read_text()+'\n'+(ROOT/'schemas/company_remote.inc').read_text()+'\n'+(ROOT/'schemas/company_control.inc').read_text()+'\n'+(ROOT/'schemas/air_flight.inc').read_text()+'\n'+(ROOT/'schemas/air_escort.inc').read_text()+'\n'+(ROOT/'schemas/acquisition.inc').read_text()+'\n'+(ROOT/'schemas/company_assault.inc').read_text()+'\n'+(ROOT/'schemas/player.inc').read_text()+'\n'+(ROOT/'schemas/world_body.inc').read_text()+'\n'+(ROOT/'schemas/wreck_nav.inc').read_text()+'\n'+(ROOT/'schemas/projectile_remote.inc').read_text()+'\n'+(ROOT/'schemas/aircraft.inc').read_text()+'\n'+(ROOT/'schemas/ground_surfaces.inc').read_text()+'\n'+(ROOT/'schemas/terrain_body.inc').read_text()+'\n'+(ROOT/'schemas/terrain_grade.inc').read_text()+'\n'+(ROOT/'schemas/ground_support.inc').read_text()+'\n'+(ROOT/'schemas/ground_contact.inc').read_text()+'\n'+(ROOT/'schemas/suspension.inc').read_text()+'\n'+(ROOT/'schemas/ground_visual.inc').read_text()+'\n'+(ROOT/'schemas/ground_eye.inc').read_text()+'\n'+(ROOT/'schemas/wreck.inc').read_text()+'\n'+(ROOT/'schemas/wreck_remote.inc').read_text()+'\n'+(ROOT/'schemas/shell_contact.inc').read_text() + '\n' + (ROOT / 'schemas/world_contact.inc').read_text() + '\n' + (ROOT / 'schemas/world_los.inc').read_text() + '\n' + (ROOT / 'schemas/terrain_ground_query.inc').read_text() + '\n' + (ROOT / 'schemas/terrain_height.inc').read_text(), re.M))
keys = ('GROUND_SURFACE_VERSION', 'GROUND_TANK_OFFROAD', 'GROUND_ARTILLERY_OFFROAD', 'GROUND_TANK_RADIUS', 'GROUND_ARTILLERY_RADIUS')
def resolve(name, seen=()):
    assert name not in seen, 'Circular surface policy definition'
    value = definitions[name]
    return resolve(value, (*seen, name)) if value in definitions else value
policy = {name: resolve(name) for name in keys}
assert all(0 < float(policy[name]) <= 1 for name in keys[1:3]), 'Invalid surface multiplier'
assert all(0 <= float(policy[name]) <= 8000 for name in keys[3:]), 'Invalid body radius'
asset_fingerprint = hashlib.sha256((ROOT/'content/asset-manifest.json').read_bytes()).hexdigest()[:8]
payload = {'company_transfer': {name: resolve(name) for name in ('COMPANY_TRANSFER_VERSION','COMPANY_TRANSFER_PLAYERS','COMPANY_TRANSFER_STRIDE','COMPANY_TRANSFER_LIFETIME')}, 'company_remote': {name: resolve(name) for name in ('COMPANY_REMOTE_VERSION','COMPANY_REMOTE_COUNT','COMPANY_REMOTE_STRIDE','COMPANY_REMOTE_KEY_LIMIT')}, 'company_control': {name: resolve(name) for name in ('COMPANY_CONTROL_VERSION','COMPANY_CONTROL_SLOTS','COMPANY_CONTROL_STRIDE','COMPANY_CONTROL_PLAYERS','COMPANY_CONTROL_COST')}, 'air_flight': {name: resolve(name) for name in ('AIR_FLIGHT_VERSION', 'AIR_FLIGHT_GRAVITY', 'AIR_FLIGHT_MIN_SPEED', 'AIR_FLIGHT_MAX_SPEED', 'AIR_FLIGHT_HEADING_GAIN', 'AIR_FLIGHT_BOMBER_BANK', 'AIR_FLIGHT_FIGHTER_BANK', 'AIR_FLIGHT_BOMBER_EMERGENCY_BANK', 'AIR_FLIGHT_FIGHTER_EMERGENCY_BANK', 'AIR_FLIGHT_BOMBER_ROLL', 'AIR_FLIGHT_FIGHTER_ROLL', 'AIR_FLIGHT_BOMBER_YAW_BOUND', 'AIR_FLIGHT_FIGHTER_YAW_BOUND', 'AIR_FLIGHT_CORNER_MARGIN', 'AIR_FLIGHT_STRIKE_MEMORY', 'AIR_FLIGHT_STRIKE_STRIDE', 'AIR_FLIGHT_STRIKE_APPROACH', 'AIR_FLIGHT_STRIKE_REACHED_SQ')},
           'air_escort': {name: resolve(name) for name in ('AIR_ESCORT_VERSION', 'AIR_ACQUIRE_VERSION', 'AIR_ACQUIRE_CELLS', 'AIR_ESCORT_REVIEW', 'AIR_ESCORT_COMMITMENT', 'AIR_ESCORT_RANGE_SQUARED', 'AIR_ESCORT_BREAK_SQUARED', 'AIR_ESCORT_THREAT_SQUARED', 'AIR_ESCORT_TRAIL_TICKS', 'AIR_ESCORT_LATERAL', 'AIR_ESCORT_THREAT_WEIGHT')},
           'acquisition': {name: resolve(name) for name in ('ACQUIRE_VERSION','ACQUIRE_INF_CELLS','ACQUIRE_TANK_CELLS','ACQUIRE_ARTY_CELLS')}, 'company_assault': {name: resolve(name) for name in ('COMPANY_ASSAULT_VERSION', 'COMPANY_SLOTS', 'COMPANY_STRIDE', 'COMPANY_MIN_GROUND', 'COMPANY_NEAR_SQ', 'COMPANY_STAGE_DISTANCE', 'COMPANY_ARTY_BACK', 'COMPANY_ARMOUR_FORWARD', 'COMPANY_READY_SQ', 'COMPANY_STAGE_TIMEOUT', 'COMPANY_PREP_TIMEOUT', 'COMPANY_LOSS_PERCENT', 'COMPANY_INF_SPACING', 'COMPANY_INF_ROW', 'COMPANY_HULL_ROW', 'COMPANY_INF_LANE', 'COMPANY_ARMOUR_LANE', 'COMPANY_ARTY_LANE', 'COMPANY_WITHDRAW_DISTANCE')}, 'previous_content': asset_fingerprint, 'terrain_surface_abi': 1,
           'roads': json.loads((ROOT/'content/terrain/roads.json').read_text()),
           'tracked_policy': policy,
           'relief_abi': 1, 'grade_abi': 1,
           'relief': json.loads((ROOT/'content/terrain/relief.json').read_text()),
           'grade_policy': {name: resolve(name) for name in ('TERRAIN_GRADE_VERSION','GRADE_INF_LIMIT_SQ','GRADE_TANK_LIMIT_SQ','GRADE_ARTY_LIMIT_SQ','GRADE_GUARD_SQ','GRADE_BASE_X','GRADE_BASE_Z','BODY_INF_SWEEP_RADIUS','BODY_TANK_SWEEP_RADIUS','BODY_ARTY_SWEEP_RADIUS')},
           'wreck_presentation': {name: resolve(name) for name in ('WRECK_REMOTE_VERSION','WRECK_WIRE_STRIDE','WRECK_WIRE_MAX','WRECK_PRESENTATION_VERSION','WRECK_PRESENTATION_FRAME','WRECK_PRESENTATION_LOD')},
           'projectile_remote': {name: resolve(name) for name in ('PROJECTILE_REMOTE_POLICY_VERSION','PROJECTILE_OWNED_PRIORITY_MAX','PROJECTILE_WIRE_MAX')},
           'bomb_release': {name: resolve(name) for name in ('AIR_BOMB_RELEASE_VERSION',)},
           'player_deploy': {name: resolve(name) for name in ('PLAYER_DEPLOY_POLICY_VERSION',)},
           'world_body': {name: resolve(name) for name in ('WORLD_BODY_VERSION',)},
           'wreck_navigation': {name: resolve(name) for name in ('WRECK_NAV_VERSION', 'WRECK_NAV_QUEUE', 'WRECK_NAV_BUILDS_PER_TICK', 'WRECK_NAV_LOOKAHEAD', 'WRECK_NAV_PLAN_DISTANCE', 'WRECK_NAV_ENDPOINT_INCREMENT', 'WRECK_NAV_ENDPOINT_MAX_DISTANCE', 'WRECK_NAV_LOOKAHEAD_SQUARED', 'WRECK_NAV_PLAN_DISTANCE_SQUARED', 'WRECK_NAV_MAX_WRECKS', 'WRECK_NAV_MAX_NODES', 'WRECK_NAV_MAX_PATH', 'WRECK_NAV_WINDOW_MARGIN', 'WRECK_NAV_CORNER_MARGIN', 'WRECK_NAV_MAX_LEG_SQUARED', 'WRECK_NAV_GOAL_CHANGE_SQUARED', 'WRECK_NAV_REACHED_SQUARED', 'WRECK_NAV_SOURCE_DISTANCE_WEIGHT')},
           'world_los': {name: resolve(name) for name in ('WORLD_LOS_VERSION',)},
           'world_contact': {name: resolve(name) for name in ('WORLD_CONTACT_VERSION', 'WORLD_CONTACT_GROUND', 'WORLD_CONTACT_SOLID', 'WORLD_CONTACT_WRECK', 'WORLD_CONTACT_ACTOR', 'WORLD_CONTACT_BLAST_SKIN', 'TERRAIN_GROUND_QUERY_VERSION', 'TERRAIN_GROUND_QUERY_SKIN', 'TERRAIN_HEIGHT_CENTER', 'TERRAIN_HEIGHT_X_SCALE', 'TERRAIN_HEIGHT_Z_SCALE', 'TERRAIN_HEIGHT_RIDGE_SCALE', 'TERRAIN_HEIGHT_RIDGE_HEIGHT', 'TERRAIN_HEIGHT_BASE')},
           'shell_contact': {name: resolve(name) for name in ('SHELL_CONTACT_VERSION','SHELL_CONTACT_RADIUS','SHELL_CONTACT_MAX_SAMPLES')},
           'wreck_registry': {name: resolve(name) for name in ('WRECK_VERSION','WRECK_CAPACITY','WRECK_LIFETIME_TICKS')},
           'ground_eye': {name: resolve(name) for name in ('EYE_VERSION','EYE_LOCAL_HEIGHT')},
           'ground_visual': {name: resolve(name) for name in ('CONTACT_VERSION','SUSPENSION_VERSION','SUSPENSION_Y_OMEGA','SUSPENSION_PITCH_OMEGA','SUSPENSION_BANK_OMEGA','SUSPENSION_Y_LIMIT','SUSPENSION_ANGLE_LIMIT','SUSPENSION_Y_VELOCITY_LIMIT','SUSPENSION_ANGLE_VELOCITY_LIMIT','VISUAL_VERSION','VISUAL_MAX_DT','VISUAL_JUMP_SQ')},
           'render_patch': PATCH, 'ground_support': {name: resolve(name) for name in ('SUPPORT_VERSION','SUPPORT_TANK_HALF_WIDTH','SUPPORT_TANK_HALF_LENGTH','SUPPORT_TANK_CENTER_Z','SUPPORT_ARTY_HALF_WIDTH','SUPPORT_ARTY_HALF_LENGTH','SUPPORT_ARTY_CENTER_Z')}}
digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
fingerprint = digest[:8]
if args.check:
    actual = re.search(r'^%define NET_CONTENT 0x([0-9a-f]{8})$', (ROOT/'src/net/protocol.inc').read_text(), re.M)
    assert actual and actual.group(1) == fingerprint, f'Ground content compatibility mismatch: expected 0x{fingerprint}'
print(json.dumps({'ground_content': '0x'+fingerprint, 'canonical_sha256': digest, 'checked': args.check}))
