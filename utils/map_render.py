# Map Render
# Pillow-based hex map with terrain colors, fog, player/enemy markers

import random
import math
import io
import discord
import utils.db as db

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False

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

TERRAIN_COLORS = {
    "coastal_beach":   (210, 185, 130),
    "jungle":          (34,  85,  34),
    "village":         (160, 130,  80),
    "mountain_pass":   (110, 100,  90),
    "farmland":        (140, 180,  80),
    "ruins":           (100,  90,  80),
    "river_ford":      (80,  130, 180),
    "hilltop":         (130, 115,  90),
    "dense_bamboo":    (20,  100,  50),
    "sacred_grove":    (60,  140,  60),
    "swamp":           (70,  100,  60),
    "cliff_edge":      (80,   70,  70),
    "port_town":       (90,  120, 160),
    "castle":          (120, 100,  80),
    "cave":            (80,   70,  90),
    "camp":            (160, 130,  70),
    "open":            (160, 175, 130),
}

TERRAIN_BORDER = {
    "coastal_beach":   (180, 155, 100),
    "jungle":          (20,  60,  20),
    "village":         (120,  90,  50),
    "mountain_pass":   (80,  70,  60),
    "farmland":        (100, 140,  50),
    "ruins":           (70,  60,  50),
    "river_ford":      (50,  90, 140),
    "hilltop":         (90,  80,  60),
    "dense_bamboo":    (10,  70,  30),
    "sacred_grove":    (30, 100,  30),
    "swamp":           (40,  70,  40),
    "cliff_edge":      (50,  40,  40),
    "port_town":       (60,  90, 130),
    "castle":          (80,  60,  40),
    "cave":            (50,  40,  60),
    "camp":            (120, 90,  40),
    "open":            (130, 145, 100),
}

FOG_COLOR    = (30, 30, 40)
FOG_BORDER   = (20, 20, 30)
PLAYER_COLOR = (255, 220, 50)
ENEMY_COLOR  = (220, 50,  50)
NAMED_RING   = (255, 255, 200)
LABEL_COLOR  = (255, 255, 255)
LABEL_SHADOW = (0, 0, 0)

TERRAIN_ICONS = {
    "castle":       "S",
    "port_town":    "P",
    "village":      "V",
    "cave":         "O",
    "camp":         "C",
    "ruins":        "#",
    "sacred_grove": "*",
    "mountain_pass":"^",
}

IMPASSABLE = {"cliff_edge"}
HEX_SIZE   = 18
VIEWPORT   = 17


def addr(x: int, y: int) -> str:
    return f"{x},{y}"


def parse(a: str) -> tuple[int, int]:
    p = a.split(",")
    return int(p[0]), int(p[1])


def in_bounds(x: int, y: int) -> bool:
    return 0 <= x < 60 and 0 <= y < 120


def _hex_corners_flat(cx: float, cy: float, r: float) -> list:
    pts = []
    for i in range(6):
        angle = math.radians(60 * i)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def _hex_center(gx: int, gy: int, r: float, ox: float, oy: float) -> tuple:
    w  = math.sqrt(3) * r
    h  = 2 * r
    cx = ox + gx * w + (gy % 2) * (w / 2)
    cy = oy + gy * (h * 0.75)
    return cx, cy


def render_hex_map(
    player_addr: str,
    hex_rows: list,
    satsuma_units: list,
    recon_radius: int = 3,
) -> discord.File | None:
    if not PILLOW_OK:
        return None

    r      = HEX_SIZE
    half   = VIEWPORT // 2
    px, py = parse(player_addr)

    hex_map = {row["address"]: row for row in hex_rows}
    sat_set = {u["hex_address"] for u in satsuma_units if u.get("is_active")}

    hex_w  = math.sqrt(3) * r
    hex_h  = 2 * r
    img_w  = int(VIEWPORT * hex_w + hex_w + 40)
    img_h  = int(VIEWPORT * hex_h * 0.75 + hex_h + 50)

    img  = Image.new("RGB", (img_w, img_h), (15, 15, 20))
    draw = ImageDraw.Draw(img)

    try:
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 7)
    except Exception:
        font_sm = ImageFont.load_default()
        font_lg = font_sm

    ox = 20.0
    oy = 20.0

    # First pass: draw all hex fills and borders
    for dy in range(-half, half + 1):
        for dx in range(-half, half + 1):
            wx, wy = px + dx, py + dy
            if not in_bounds(wx, wy):
                continue

            gx = dx + half
            gy = dy + half
            cx, cy = _hex_center(gx, gy, r, ox, oy)
            corners = _hex_corners_flat(cx, cy, r - 1)

            a    = addr(wx, wy)
            h    = hex_map.get(a)
            dist = max(abs(dx), abs(dy))

            is_player = (dx == 0 and dy == 0)
            in_recon  = dist <= recon_radius
            is_fog    = not h or (not h.get("is_explored") and not in_recon)

            if is_fog and not is_player:
                draw.polygon(corners, fill=FOG_COLOR, outline=FOG_BORDER)
                continue

            terrain  = h.get("terrain", "jungle") if h else "jungle"
            fill_col = TERRAIN_COLORS.get(terrain, (80, 80, 80))
            brdr_col = TERRAIN_BORDER.get(terrain, (50, 50, 50))
            is_named = h.get("is_named_location") if h else False

            border = NAMED_RING if is_named else brdr_col
            draw.polygon(corners, fill=fill_col, outline=border)

            # Satsuma marker
            if a in sat_set and in_recon and not is_player:
                draw.ellipse([cx-5, cy-5, cx+5, cy+5], fill=ENEMY_COLOR, outline=(160, 30, 30))
                draw.text((cx, cy), "!", font=font_sm, fill=(255, 255, 255), anchor="mm")
                continue

            # Terrain icon
            icon = TERRAIN_ICONS.get(terrain)
            if icon and is_named:
                draw.text((cx+1, cy+1), icon, font=font_sm, fill=LABEL_SHADOW, anchor="mm")
                draw.text((cx,   cy),   icon, font=font_sm, fill=LABEL_COLOR,  anchor="mm")

            # Player marker on top
            if is_player:
                draw.ellipse([cx-7, cy-7, cx+7, cy+7], fill=PLAYER_COLOR, outline=(200, 160, 0))
                draw.text((cx, cy), "@", font=font_sm, fill=(0, 0, 0), anchor="mm")

    # Second pass: named location labels (on top of everything)
    for dy in range(-half, half + 1):
        for dx in range(-half, half + 1):
            wx, wy = px + dx, py + dy
            if not in_bounds(wx, wy):
                continue
            a = addr(wx, wy)
            h = hex_map.get(a)
            if not h or not h.get("is_named_location") or not h.get("location_name"):
                continue
            dist = max(abs(dx), abs(dy))
            if not h.get("is_explored") and dist > recon_radius:
                continue
            gx = dx + half
            gy = dy + half
            cx, cy = _hex_center(gx, gy, r, ox, oy)
            label = h["location_name"]
            if len(label) > 11:
                label = label[:10] + "."
            draw.text((cx+1, cy - r - 2), label, font=font_lg, fill=LABEL_SHADOW, anchor="mm")
            draw.text((cx,   cy - r - 3), label, font=font_lg, fill=LABEL_COLOR,  anchor="mm")

    # Legend bar at bottom
    legend_y = img_h - 30
    draw.rectangle([0, legend_y - 5, img_w, img_h], fill=(20, 20, 30))
    items = [
        (PLAYER_COLOR, "@ You"),
        (ENEMY_COLOR,  "! Satsuma"),
        (TERRAIN_COLORS["village"],       "V Village"),
        (TERRAIN_COLORS["castle"],        "S Castle"),
        (TERRAIN_COLORS["jungle"],        "  Jungle"),
        (TERRAIN_COLORS["coastal_beach"], "  Coast"),
        (FOG_COLOR,                       "  Fog"),
    ]
    lx = 6
    for col, text in items:
        draw.rectangle([lx, legend_y, lx + 10, legend_y + 10], fill=col, outline=(80, 80, 80))
        draw.text((lx + 13, legend_y - 1), text, font=font_lg, fill=(200, 200, 200))
        lx += 85
        if lx > img_w - 60:
            break

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return discord.File(buf, filename="map.png")


async def render_viewport(guild_id: int, owner_id: int) -> discord.File | None:
    player = await db.get_player(guild_id, owner_id)
    if not player:
        return None
    a      = player.get("current_hex", "30,85")
    recon  = player.get("recon", 8)
    radius = max(2, recon // 3)
    px, py = parse(a)
    hexes  = await db.get_viewport_hexes(guild_id, owner_id, px, py)
    units  = await db.get_satsuma_units(guild_id, owner_id)
    return render_hex_map(a, hexes, units, radius)


def generate_viewport(player_addr, hex_rows, satsuma_units, recon_radius=3, viewport=17):
    """ASCII fallback."""
    px, py  = parse(player_addr)
    half    = viewport // 2
    hex_map = {r["address"]: r for r in hex_rows}
    sat_map = {u["hex_address"]: u for u in satsuma_units if u.get("is_active")}
    TC = {
        "coastal_beach":"~","jungle":"%","village":"V","mountain_pass":"^",
        "farmland":".","ruins":"#","river_ford":"=","hilltop":"n",
        "dense_bamboo":"|","sacred_grove":"*","swamp":"m","cliff_edge":"X",
        "port_town":"P","castle":"S","cave":"O","camp":"C",
    }
    lines = []
    for dy in range(-half, half+1):
        row = []
        for dx in range(-half, half+1):
            wx, wy = px+dx, py+dy
            if not in_bounds(wx, wy):
                row.append(" "); continue
            if dx == 0 and dy == 0:
                row.append("@"); continue
            a    = addr(wx, wy)
            dist = max(abs(dx), abs(dy))
            h    = hex_map.get(a)
            if not h or (not h.get("is_explored") and dist > recon_radius):
                row.append("·"); continue
            ch = TC.get(h.get("terrain","jungle"), ".")
            if a in sat_map and dist <= recon_radius:
                ch = "!"
            row.append(ch)
        lines.append(" ".join(row))
    return "```\n" + "\n".join(lines) + "\n```"


async def seed_player_map(guild_id: int, owner_id: int):
    rows = []
    for x in range(60):
        for y in range(120):
            a        = addr(x, y)
            terrain  = _terrain_for(x, y)
            is_named, loc_name = False, None
            for loc, (lx, ly) in NAMED_LOCATIONS.items():
                if lx == x and ly == y:
                    is_named = True
                    loc_name = loc.replace("_", " ").title()
                    terrain  = _named_terrain(loc)
                    break
            rows.append((guild_id, owner_id, a, terrain, "neutral", False, is_named, loc_name))
    await db.bulk_insert_hexes(guild_id, owner_id, rows)
    sx, sy  = NAMED_LOCATIONS["cave_of_refuge"]
    explore = [addr(sx+dx, sy+dy) for dx in range(-3,4) for dy in range(-3,4)
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
    if "castle" in loc or "shuri" in loc: return "castle"
    if "port" in loc or "naha" in loc:    return "port_town"
    if "village" in loc or "town" in loc: return "village"
    if "cave" in loc:                     return "cave"
    if "peninsula" in loc or "point" in loc or "cape" in loc: return "coastal_beach"
    if "camp" in loc:                     return "camp"
    if "farmstead" in loc:                return "farmland"
    return "jungle"


async def explore_around(guild_id: int, owner_id: int, hex_addr: str, radius: int):
    px, py  = parse(hex_addr)
    explore = [addr(px+dx, py+dy) for dx in range(-radius, radius+1)
               for dy in range(-radius, radius+1) if in_bounds(px+dx, py+dy)]
    await db.bulk_set_explored(guild_id, owner_id, explore)