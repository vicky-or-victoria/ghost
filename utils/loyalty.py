# Loyalty
import utils.db as db
from utils.embeds import loyalty_state_label

GAINS = {
    "win_no_casualties":       8,
    "win_with_casualties":     3,
    "contract_complete":       5,
    "village_rest":            6,
    "morale_action":           4,
    "rescue_band_member":      10,
    "survived_outnumbered":    12,
    "mc_level_up":             3,
    "companion_trust_up":      5,
    "contract_bonus":          3,
    "used_war_drum":           4,
}

LOSSES = {
    "lose_battle":             -8,
    "band_member_death":       -5,
    "veteran_death":           -10,
    "beloved_death":           -12,
    "abandon_contract":        -12,
    "path_blade_companion":    -15,
    "consecutive_battle":      -6,
    "cruel_story_choice":      -8,
    "supply_drain":            -5,
    "leader_injury":           -3,
    "rout":                    -7,
}


async def apply_loyalty_event(guild_id: int, owner_id: int, event_key: str, **kwargs) -> tuple[int, int]:
    delta = GAINS.get(event_key) or LOSSES.get(event_key, 0)
    if event_key == "band_member_death":
        member = kwargs.get("member", {})
        traits = member.get("traits") or []
        if "Veteran" in traits:
            delta = LOSSES["veteran_death"]
        elif "Beloved" in traits:
            delta = LOSSES["beloved_death"]
    new_val = await db.adjust_loyalty(guild_id, owner_id, delta)
    await db.increment_trait_counter(guild_id, owner_id, "mc", "band_deaths_witnessed", 1)
    return delta, new_val


async def apply_upkeep(guild_id: int, owner_id: int) -> tuple[int, bool]:
    band_size = await db.get_band_size(guild_id, owner_id)
    player    = await db.get_player(guild_id, owner_id)
    if not player:
        return 0, True
    if band_size <= 5:
        cost = 1
    elif band_size <= 10:
        cost = 2
    elif band_size <= 20:
        cost = 4
    else:
        cost = 7
    coin = player.get("coin", 0)
    if coin >= cost:
        await db.update_player(guild_id, owner_id, coin=coin - cost)
        return cost, True
    else:
        await db.adjust_loyalty(guild_id, owner_id, LOSSES["supply_drain"])
        await db.increment_trait_counter(guild_id, owner_id, "mc", "low_supply_turns", 1)
        return cost, False


async def check_desertion(guild_id: int, owner_id: int) -> list:
    import random
    loyalty = await db.get_loyalty(guild_id, owner_id)
    if loyalty >= 30:
        return []
    band      = await db.get_band(guild_id, owner_id)
    deserters = []
    player    = await db.get_player(guild_id, owner_id)
    path      = player.get("path_choice") if player else None

    for m in band:
        ind  = m.get("individual_loyalty", 50)
        arch = m["archetype"]
        traits = m.get("traits") or []

        # Always desert at Collapsing/Broken
        always = (arch in ("Bushi","Satsuma Regular") and loyalty <= 14)
        # Oath-Bound band members never desert
        if "Oath-Bound" in traits:
            continue
        # Ghost path: Satsuma Regulars always desert
        if path == "ghost" and arch == "Satsuma Regular" and loyalty <= 29:
            always = True

        if always or (loyalty <= 29 and ind < 40 and random.random() < 0.20):
            pool = await db.get_pool()
            async with pool.acquire() as conn:
                await conn.execute("UPDATE band_members SET is_alive=FALSE WHERE id=$1", m["id"])
            deserters.append(m)

    return deserters


async def threshold_effects(guild_id: int, owner_id: int) -> list:
    loyalty = await db.get_loyalty(guild_id, owner_id)
    msgs = []
    if loyalty <= 4:
        msgs.append("Band has fragmented. Only MC and companion remain.")
    elif loyalty <= 14:
        msgs.append("Collapsing — Bushi and Satsuma Regulars will desert this turn.")
    elif loyalty <= 29:
        msgs.append("Fracturing — desertion possible each turn.")
    elif loyalty <= 49:
        msgs.append("Strained — rout chance increases in difficult combat.")
    return msgs
