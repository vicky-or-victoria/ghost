# Satsuma AI
import random
import utils.db as db
from utils.map_render import parse, addr, in_bounds, NAMED_LOCATIONS

UNIT_TYPES = {
    "ashigaru_foot":     {"atk":8,  "def":8,  "spd":8,  "resolve":7,  "hp":80,  "max_hp":80},
    "ashigaru_archer":   {"atk":6,  "def":6,  "spd":8,  "resolve":7,  "hp":70,  "max_hp":70},
    "spear_corps":       {"atk":10, "def":8,  "spd":7,  "resolve":9,  "hp":90,  "max_hp":90},
    "mounted_cavalry":   {"atk":12, "def":7,  "spd":14, "resolve":8,  "hp":85,  "max_hp":85},
    "samurai_elite":     {"atk":14, "def":13, "spd":9,  "resolve":13, "hp":110, "max_hp":110},
    "ninja_infiltrator": {"atk":11, "def":7,  "spd":13, "resolve":8,  "hp":75,  "max_hp":75},
    "field_commander":   {"atk":13, "def":11, "spd":8,  "resolve":15, "hp":130, "max_hp":130},
}

ACT_SPAWNS = {
    1: [
        ("ashigaru_foot",   "patrol",  addr(*NAMED_LOCATIONS["naha_port"])),
        ("ashigaru_foot",   "advance", addr(29,112)),
        ("ashigaru_archer", "patrol",  addr(27,113)),
        ("ashigaru_foot",   "advance", addr(30,111)),
        ("spear_corps",     "hold",    addr(*NAMED_LOCATIONS["naha_port"])),
    ],
    2: [
        ("mounted_cavalry",   "advance", addr(35,95)),
        ("samurai_elite",     "hold",    addr(*NAMED_LOCATIONS["katsuren_castle"])),
        ("ninja_infiltrator", "ambush",  addr(32,88)),
        ("field_commander",   "advance", addr(30,100)),
        ("ashigaru_foot",     "advance", addr(26,100)),
        ("ashigaru_archer",   "patrol",  addr(33,95)),
    ],
    3: [
        ("samurai_elite",   "advance",   addr(*NAMED_LOCATIONS["shuri_castle"])),
        ("field_commander", "reinforce", addr(31,92)),
        ("ashigaru_foot",   "reinforce", addr(28,95)),
        ("ashigaru_foot",   "reinforce", addr(33,95)),
        ("spear_corps",     "advance",   addr(30,97)),
        ("mounted_cavalry", "flank",     addr(38,90)),
    ],
}


async def spawn_act_units(guild_id: int, owner_id: int, act: int):
    spawns = ACT_SPAWNS.get(act, [])
    for unit_type, behavior, hex_address in spawns:
        stats = UNIT_TYPES.get(unit_type, {})
        await db.spawn_satsuma_unit(guild_id, owner_id, {
            "unit_type":   unit_type,
            "behavior":    behavior,
            "hex_address": hex_address,
            **stats,
        })


def _move_toward(from_addr: str, target_addr: str, steps: int) -> str:
    ux, uy = parse(from_addr)
    tx, ty = parse(target_addr)
    for _ in range(steps):
        dx = tx - ux
        dy = ty - uy
        if dx == 0 and dy == 0:
            break
        if abs(dx) >= abs(dy):
            ux += 1 if dx > 0 else -1
        else:
            uy += 1 if dy > 0 else -1
        ux = max(0, min(59, ux))
        uy = max(0, min(119, uy))
    return addr(ux, uy)


def _patrol_step(from_addr: str) -> str:
    ux, uy = parse(from_addr)
    dx, dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
    nx, ny = max(0,min(59,ux+dx)), max(0,min(119,uy+dy))
    return addr(nx, ny)


async def resolve_end_turn_ai(guild_id: int, owner_id: int) -> list:
    player = await db.get_player(guild_id, owner_id)
    if not player:
        return []
    player_addr = player.get("current_hex", "30,85")
    act         = player.get("current_act", 1)
    path        = player.get("path_choice")
    units       = await db.get_satsuma_units(guild_id, owner_id)
    events      = []

    for u in units:
        uid      = u["id"]
        behavior = u["behavior"]
        uhex     = u["hex_address"]
        spd      = u["spd"] or 8
        steps    = max(1, spd // 4)
        new_hex  = uhex

        # Ghost path — elevated aggression
        if path == "ghost" and behavior == "patrol":
            behavior = "advance"

        if behavior == "patrol":
            new_hex = _patrol_step(uhex)
        elif behavior == "advance":
            new_hex = _move_toward(uhex, player_addr, steps)
        elif behavior == "pursue":
            new_hex = _move_toward(uhex, player_addr, steps + 2) if act >= 2 else uhex
        elif behavior == "hold":
            new_hex = uhex
        elif behavior == "flank":
            ux, uy = parse(uhex)
            px, py = parse(player_addr)
            ox, oy = random.choice([(3,0),(-3,0),(0,3),(0,-3)])
            tgt    = addr(max(0,min(59,px+ox)), max(0,min(119,py+oy)))
            new_hex = _move_toward(uhex, tgt, steps)
        elif behavior == "reinforce":
            new_hex = _move_toward(uhex, player_addr, steps) if act >= 3 else uhex
        elif behavior == "ambush":
            ux, uy = parse(uhex)
            px, py = parse(player_addr)
            dist   = max(abs(ux-px), abs(uy-py))
            if dist <= 2:
                behavior = "advance"
                new_hex  = _move_toward(uhex, player_addr, steps)

        await db.update_satsuma_unit(uid, hex_address=new_hex)

        # Encounter trigger
        nx, ny = parse(new_hex)
        ppx, ppy = parse(player_addr)
        if max(abs(nx-ppx), abs(ny-ppy)) <= 1:
            events.append(f"encounter:{u['unit_type']}:{uid}")

    return events
