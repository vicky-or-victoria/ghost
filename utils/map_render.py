# Map Render
import random
import utils.db as db

NAMED_LOCATIONS = {
    "cave_of_refuge":     (30, 85),
    "naha_port":          (28, 110),
    "itoman_village":     (25, 108),
    "shuri_castle":       (31, 90),
    "katsuren_castle":    (45, 75),
    "nakagusuku_castle":  (38, 82),
    "yomitan_village":    (20, 88),
    "motobu_peninsula":   (18, 45),
    "hedo_point":         (22, 5),
    "cape_kyan":          (28, 118),
    "nago_town":          (24, 35),
    "urasoe_village":     (29, 95),
    "chinen_peninsula":   (40, 112),
    "iso_camp":           (33, 100),
    "hana_farmstead":     (27, 92),
}

TERRAIN_CHARS = {
    "coastal_beach":   "~",
    "jungle":          "%",
    "village":         "V",
    "mountain_pass":   "^",
    "farmland":        ".",
    "ruins":           "#",
    "river_ford":      "=",
    "hilltop":         "n",
    "dense_bamboo":    "|",
    "sacred_grove":    "*",
    "swamp":           "m",
    "cliff_edge":      "X",
    "port_town":       "P",
    "castle":          "S",
    "cave":            "O",
    "camp":            "C",
}

IMPASSABLE = {"cliff_edge"}
PLAYER_CHAR  = "@"
SATSUMA_CHAR = "!"
COMPANION_CHAR = "c"
FOG_CHAR     = "·"


def addr(x: int, y: int) -> str:
    return f"{x},{y}"


def parse(a: str) -> tuple[int, int]:
    p = a.split(",")
    return int(p[0]), int(p[1])


def in_bounds(x: int, y: int) -> bool:
    return 0 <= x < 60 and 0 <= y < 120


def terrain_char(hex_row: dict) -> str:
    t = hex_row.get("terrain", "jungle")
    if hex_row.get("is_named_location"):
        name = hex_row.get("location_name", "").lower()
        if "castle" in name or "shuri" in name:
            return "S"
        if "port" in name or "naha" in name:
            return "P"
        if "village" in name or "town" in name:
            return "V"
        if "cave" in name:
            return "O"
        if "camp" in name:
            return "C"
        if "point" in name or "cape" in name or "peninsula" in name:
            return "^"
        if "farmstead" in name or "farm" in name:
            return "."
    return TERRAIN_CHARS.get(t, ".")


def generate_viewport(
    player_addr: str,
    hex_rows: list,
    satsuma_units: list,
    recon_radius: int = 3,
    viewport: int = 17,
) -> str:
    px, py  = parse(player_addr)
    half    = viewport // 2
    hex_map = {r["address"]: r for r in hex_rows}
    sat_map = {u["hex_address"]: u for u in satsuma_units if u["is_active"]}
    lines   = []

    for dy in range(-half, half + 1):
        row = []
        for dx in range(-half, half + 1):
            wx, wy = px + dx, py + dy
            if not in_bounds(wx, wy):
                row.append(" ")
                continue
            if dx == 0 and dy == 0:
                row.append(PLAYER_CHAR)
                continue
            a    = addr(wx, wy)
            dist = max(abs(dx), abs(dy))
            h    = hex_map.get(a)
            in_recon = dist <= recon_radius

            if not h or not h["is_explored"]:
                if in_recon:
                    ch = terrain_char(h) if h else "."
                    if a in sat_map:
                        ch = SATSUMA_CHAR
                    row.append(ch)
                else:
                    row.append(FOG_CHAR)
                continue

            ch = terrain_char(h)
            if a in sat_map and in_recon:
                ch = SATSUMA_CHAR
            row.append(ch)
        lines.append(" ".join(row))

    legend = (
        "@ You   ! Satsuma   V Village   S Castle   P Port   O Cave\n"
        "^ Mountain   % Jungle   ~ Coast   # Ruins   · Unexplored"
    )
    return "```\n" + "\n".join(lines) + "\n```\n" + legend


async def render_viewport(guild_id: int, owner_id: int) -> str:
    player = await db.get_player(guild_id, owner_id)
    if not player:
        return "```\nNo player data.\n```"
    a       = player.get("current_hex", "30,85")
    recon   = player.get("recon", 8)
    radius  = max(2, recon // 3)
    px, py  = parse(a)
    hexes   = await db.get_viewport_hexes(guild_id, owner_id, px, py)
    units   = await db.get_satsuma_units(guild_id, owner_id)
    return generate_viewport(a, hexes, units, radius)


async def seed_player_map(guild_id: int, owner_id: int):
    rows = []
    for x in range(60):
        for y in range(120):
            a       = addr(x, y)
            terrain = _terrain_for(x, y)
            is_named, loc_name = False, None
            for loc, (lx, ly) in NAMED_LOCATIONS.items():
                if lx == x and ly == y:
                    is_named = True
                    loc_name = loc.replace("_", " ").title()
                    terrain  = _named_terrain(loc)
                    break
            rows.append((guild_id, owner_id, a, terrain, "neutral", False, is_named, loc_name))

    await db.bulk_insert_hexes(guild_id, owner_id, rows)

    # Explore starting area
    sx, sy   = NAMED_LOCATIONS["cave_of_refuge"]
    explore  = [addr(sx+dx, sy+dy) for dx in range(-3,4) for dy in range(-3,4)
                if in_bounds(sx+dx, sy+dy)]
    await db.bulk_set_explored(guild_id, owner_id, explore)


def _terrain_for(x: int, y: int) -> str:
    if y <= 20:
        pool = ["mountain_pass","mountain_pass","dense_bamboo","jungle","hilltop","ruins"]
    elif y <= 60:
        pool = ["jungle","jungle","farmland","dense_bamboo","sacred_grove","village","ruins","swamp","river_ford"]
    elif y <= 100:
        pool = ["farmland","jungle","village","ruins","swamp","dense_bamboo","hilltop"]
    else:
        pool = ["coastal_beach","coastal_beach","port_town","farmland","village"]
    if y == 70 and 15 <= x <= 50:
        return "river_ford" if x == 32 else "jungle"
    return random.choice(pool)


def _named_terrain(loc: str) -> str:
    if "castle" in loc or "shuri" in loc:
        return "castle"
    if "port" in loc or "naha" in loc:
        return "port_town"
    if "village" in loc or "town" in loc:
        return "village"
    if "cave" in loc:
        return "cave"
    if "peninsula" in loc or "point" in loc or "cape" in loc:
        return "coastal_beach"
    if "camp" in loc:
        return "camp"
    if "farmstead" in loc:
        return "farmland"
    return "jungle"


async def explore_around(guild_id: int, owner_id: int, hex_addr: str, radius: int):
    px, py  = parse(hex_addr)
    explore = [addr(px+dx, py+dy) for dx in range(-radius, radius+1)
               for dy in range(-radius, radius+1) if in_bounds(px+dx, py+dy)]
    await db.bulk_set_explored(guild_id, owner_id, explore)
