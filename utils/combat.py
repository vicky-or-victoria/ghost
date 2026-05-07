# Combat
import random
import utils.db as db
from utils.items_data import INJURIES, ARCHETYPES, XP_REWARDS, level_for_xp

# Tactical map terrain effects
TERRAIN_EFFECTS = {
    "jungle":        {"def_bonus": 1, "spd_cost": 2, "cover": True},
    "dense_bamboo":  {"def_bonus": 2, "spd_cost": 2, "cover": True},
    "mountain_pass": {"def_bonus": 2, "spd_cost": 3, "cover": False},
    "hilltop":       {"atk_bonus": 2, "def_bonus": 0, "spd_cost": 2, "cover": False},
    "coastal_beach": {"def_bonus": 0, "spd_cost": 1, "cover": False},
    "farmland":      {"def_bonus": 0, "spd_cost": 1, "cover": False},
    "ruins":         {"def_bonus": 1, "spd_cost": 1, "cover": True},
    "river_ford":    {"def_bonus": -1,"spd_cost": 2, "cover": False},
    "swamp":         {"def_bonus": -1,"spd_cost": 3, "cover": False},
    "sacred_grove":  {"def_bonus": 1, "spd_cost": 1, "resolve_bonus": 2, "cover": True},
    "village":       {"def_bonus": 1, "spd_cost": 1, "cover": True},
}

# Actions per turn
ACTIONS = {
    "Move":      {"ap": 1, "desc": "Move up to SPD hexes."},
    "Attack":    {"ap": 1, "desc": "Attack adjacent or ranged target."},
    "Special":   {"ap": 1, "desc": "Use weapon special or archetype ability."},
    "Item":      {"ap": 1, "desc": "Use a consumable from inventory."},
    "Hold":      {"ap": 0, "desc": "+2 DEF until next turn. Cannot move."},
    "Stabilize": {"ap": 1, "desc": "Stabilize a downed adjacent unit."},
    "Retreat":   {"ap": 1, "desc": "Exit combat. Loyalty -7 unless outnumbered."},
}

# Archetype special abilities
ARCHETYPE_SPECIALS = {
    "Ashigaru":          "Brace — +2 DEF vs charge this turn.",
    "Scout":             "Flank — Move through enemies freely this turn.",
    "Bushi":             "Steel Cut — ATK+4, ignores 2 DEF.",
    "Healer":            "Mend — Heal adjacent unit for 20 HP.",
    "Archer":            "Volley — Attack all enemies in a 2-hex line.",
    "Spear Corps":       "Set Spear — +3 DEF against charges this turn.",
    "Satsuma Regular":   "Discipline — Immune to morale loss this turn.",
    "Ryukyuan Fighter":  "Home Ground — +2 ATK/DEF on island terrain.",
    "Monk":              "Rally Cry — +3 Resolve to all allies for 2 turns.",
    "Cavalry":           "Charge — Move 6 hexes and attack for ATK+5.",
}


def roll_hit(atk: int, def_: int, terrain_atk_bonus: int = 0, terrain_def_bonus: int = 0) -> tuple[bool, int]:
    effective_atk = atk + terrain_atk_bonus + random.randint(1, 6)
    effective_def = def_ + terrain_def_bonus + random.randint(1, 4)
    if effective_atk <= effective_def:
        return False, 0
    damage = max(1, effective_atk - effective_def)
    return True, damage


def roll_injury() -> str | None:
    if random.random() > 0.25:
        return None
    return random.choice(list(INJURIES.keys()))


def initiative_order(units: list) -> list:
    return sorted(units, key=lambda u: (-(u.get("spd", 8) + random.randint(1, 4))))


def check_rout(unit: dict, loyalty: int, outnumbered: bool) -> bool:
    resolve   = unit.get("resolve", 8)
    threshold = resolve + loyalty // 10
    roll      = random.randint(1, 20)
    if outnumbered:
        threshold -= 2
    if "Fearless" in (unit.get("traits") or []):
        return False
    if "Stalwart" in (unit.get("traits") or []):
        return False
    return roll < (8 - threshold // 2)


def get_terrain_modifiers(terrain: str) -> dict:
    return TERRAIN_EFFECTS.get(terrain, {})


def apply_item_effect(effect: str, value: int, target: dict) -> dict:
    updates = {}
    if effect == "heal":
        updates["hp"] = min(target.get("max_hp", 80), target.get("hp", 0) + value)
    elif effect == "heal_minor":
        updates["hp"] = min(target.get("max_hp", 80), target.get("hp", 0) + value)
    elif effect == "stabilize":
        updates["is_downed"] = False
        updates["hp"]        = max(1, value)
    elif effect == "heal_injury":
        updates["hp"]       = min(target.get("max_hp", 80), target.get("hp", 0) + value)
        injuries             = list(target.get("injuries") or [])
        if injuries:
            injuries.pop(0)
        updates["injuries"] = injuries
    return updates


def calculate_xp_reward(enemy_type: str, is_named: bool = False) -> int:
    if is_named:
        return XP_REWARDS["kill_named"]
    key = f"kill_{enemy_type.replace(' ','_').lower()}"
    return XP_REWARDS.get(key, XP_REWARDS["kill_ashigaru"])


async def apply_xp(guild_id: int, owner_id: int, xp_gain: int):
    player = await db.get_player(guild_id, owner_id)
    if not player:
        return
    new_xp    = (player.get("xp") or 0) + xp_gain
    new_level = level_for_xp(new_xp)
    old_level = player.get("level", 1)
    updates   = {"xp": new_xp, "level": new_level}
    if new_level > old_level:
        # Level-up stat gains
        updates["max_hp"]  = (player.get("max_hp") or 60) + 5
        updates["hp"]      = min(updates["max_hp"], (player.get("hp") or 60) + 5)
        updates["atk"]     = (player.get("atk") or 8) + 1
        updates["def"]     = (player.get("def") or 8) + 1
    await db.update_player(guild_id, owner_id, **updates)
    await db.increment_trait_counter(guild_id, owner_id, "mc", "battles_survived", 1)


async def post_combat_resolution(
    guild_id: int, owner_id: int,
    victory: bool, casualties: list, enemies_killed: int,
    retreat: bool = False
):
    from utils.loyalty import apply_loyalty_event, GAINS, LOSSES
    from utils.traits  import check_and_assign_mc_traits, tick_grief_trait

    # XP
    xp = enemies_killed * XP_REWARDS.get("kill_ashigaru", 15)
    await apply_xp(guild_id, owner_id, xp)
    await db.increment_leaderboard(guild_id, owner_id, "enemies_killed", enemies_killed)

    # Loyalty
    if victory and not casualties:
        await apply_loyalty_event(guild_id, owner_id, "win_no_casualties")
    elif victory:
        await apply_loyalty_event(guild_id, owner_id, "win_with_casualties")
    elif retreat:
        await db.adjust_loyalty(guild_id, owner_id, LOSSES["rout"])
    else:
        await apply_loyalty_event(guild_id, owner_id, "lose_battle")

    # Grief trait tick
    await tick_grief_trait(guild_id, owner_id)

    # Process casualties
    for c in casualties:
        if c.get("type") == "band_member":
            await db.kill_band_member(guild_id, owner_id, c["id"], c.get("cause","killed in battle"))
            await apply_loyalty_event(guild_id, owner_id, "band_member_death", member=c)

    # Counter increments
    await db.increment_trait_counter(guild_id, owner_id, "mc", "total_kills", enemies_killed)
    if not retreat:
        await db.increment_trait_counter(guild_id, owner_id, "mc", "battles_without_routing", 1)
    if casualties:
        await db.increment_trait_counter(guild_id, owner_id, "mc", "battles_with_injuries", 1)

    # Trait check
    return await check_and_assign_mc_traits(guild_id, owner_id)
