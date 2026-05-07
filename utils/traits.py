# Traits
import utils.db as db

# All 50 trait definitions
# counter: behavioral counter key. threshold: value to trigger assignment.
# counter=None means story-assigned only.
TRAIT_DEFS = {
    # Combat
    "Fearless":         {"counter":"battles_without_routing",  "threshold":10,  "stats":{"resolve":2},   "desc":"Immune to Fear. +2 Resolve."},
    "Duelist":          {"counter":"single_combat_kills",      "threshold":5,   "stats":{},              "desc":"+2 ATK in single-target engagements."},
    "Night Fighter":    {"counter":"night_battles",            "threshold":3,   "stats":{},              "desc":"No SPD/Recon penalties in darkness."},
    "Iron Will":        {"counter":"survived_critical_hp",     "threshold":3,   "stats":{"max_hp":15,"hp":15}, "desc":"+15 Max HP permanently."},
    "Bloodlust":        {"counter":"total_kills",              "threshold":20,  "stats":{"atk":1,"def":-1},    "desc":"+1 ATK. -1 DEF."},
    "Shield Wall":      {"counter":"last_unit_standing",       "threshold":3,   "stats":{"def":2},       "desc":"+3 DEF when no allies adjacent."},
    "Veteran":          {"counter":"battles_survived",         "threshold":25,  "stats":{"atk":1,"def":1,"spd":1,"resolve":1,"recon":1,"loyalty":1}, "desc":"+1 all stats. Morale aura."},
    "Battle-Scarred":   {"counter":"battles_with_injuries",    "threshold":3,   "stats":{"resolve":2},   "desc":"+2 Resolve. Intimidation on enemies."},
    "Executioner":      {"counter":"officer_kills",            "threshold":3,   "stats":{},              "desc":"+2 ATK vs high-stat enemies."},
    "Brawler":          {"counter":"unarmed_attacks",          "threshold":5,   "stats":{},              "desc":"+3 ATK when unarmed."},
    "Stalwart":         {"counter":"battles_no_retreat",       "threshold":5,   "stats":{"def":2},       "desc":"+2 DEF. Cannot retreat (locked in)."},
    "Tactician":        {"counter":"outnumbered_wins",         "threshold":5,   "stats":{},              "desc":"+1 SPD on tactical maps."},
    # Exploration
    "Wayfarer":         {"counter":"hexes_explored",           "threshold":500, "stats":{},              "desc":"Mountain/forest movement -1 SPD cost."},
    "Islander":         {"counter":"named_regions_explored",   "threshold":10,  "stats":{"recon":2},     "desc":"+2 Recon. Fog clears 1 hex further."},
    "Survivor":         {"counter":"low_supply_turns",         "threshold":10,  "stats":{"resolve":2},   "desc":"+2 Resolve."},
    "Wanderer":         {"counter":"villages_visited",         "threshold":10,  "stats":{},              "desc":"All villages start Neutral."},
    # Social / Loyalty
    "Inspiring":        {"counter":"high_loyalty_turns",       "threshold":10,  "stats":{},              "desc":"Band starts each combat with +1 morale."},
    "Grief-Hardened":   {"counter":"band_deaths_witnessed",    "threshold":5,   "stats":{"resolve":2},   "desc":"+2 Resolve. -1 Loyalty regen per turn."},
    "Beloved":          {"counter":"max_loyalty_turns",        "threshold":20,  "stats":{},              "desc":"Band members gain +1 DEF."},
    "Okinawan Tongue":  {"counter":"companion_diplomacy_uses", "threshold":10,  "stats":{},              "desc":"Ryukyuan NPCs trust +1 tier."},
    "Lone Wolf":        {"counter":"small_band_turns",         "threshold":5,   "stats":{"atk":2},       "desc":"+2 ATK. -1 Loyalty regen per turn."},
    "Iron Commander":   {"counter":"clean_battles",            "threshold":10,  "stats":{},              "desc":"+5 Loyalty on contract complete."},
    # Story-derived (counter=None, assigned by flags)
    "Heir's Burden":    {"counter":None, "threshold":None, "stats":{"resolve":2},  "desc":"+2 Resolve. Blade +1/Ghost -1 Satsuma standing."},
    "Commander's Legacy":{"counter":None,"threshold":None,"stats":{"def":2},       "desc":"+2 DEF. Morale aura within 2 hexes."},
    "Grief":            {"counter":None, "threshold":None, "stats":{},              "desc":"-1 ATK/-1 Resolve first 3 battles. Then +2 Resolve."},
    "Indebted":         {"counter":None, "threshold":None, "stats":{},              "desc":"Companion trust starts at Cautious Friend."},
    "Deserter":         {"counter":None, "threshold":None, "stats":{},              "desc":"Satsuma attacks on sight. Blade NPCs hostile."},
    "Oath-Bound":       {"counter":None, "threshold":None, "stats":{},              "desc":"Cannot defect. Ryukyuan resistance hostile."},
    "Mori's Debt":      {"counter":None, "threshold":None, "stats":{},              "desc":"Mori gives one free intel report per act."},
    # Negative (counter-based)
    "Fearful":          {"counter":"times_routed",             "threshold":3,   "stats":{"resolve":-2},  "desc":"-2 Resolve. 20% chance to lose initiative."},
    "Reckless":         {"counter":"unpositioned_charges",     "threshold":5,   "stats":{"def":-1},      "desc":"-1 DEF permanently."},
    "Haunted":          {"counter":None, "threshold":None,     "stats":{"atk":-1,"def":-1,"spd":-1,"resolve":-1,"recon":-1}, "desc":"-1 all stats for 5 turns."},
    "Supply Obsessed":  {"counter":"consecutive_scavenge",     "threshold":10,  "stats":{"atk":-1},      "desc":"-1 ATK. +2 supply efficiency."},
    "Paranoid":         {"counter":"detected_without_fight",   "threshold":5,   "stats":{"recon":-1},    "desc":"-1 Recon."},
    # Companion-specific (assigned to companion, not MC)
    "Island Blood":     {"counter":None, "threshold":None, "stats":{},              "desc":"Ignores terrain movement penalties."},
    "Resilient":        {"counter":"times_unconscious",        "threshold":5,   "stats":{"max_hp":3,"hp":3}, "desc":"Recovery halved. +3 Max HP."},
    "Trusted":          {"counter":None, "threshold":None, "stats":{"atk":2,"def":2,"spd":2,"resolve":2,"recon":2}, "desc":"+2 all stats."},
    "War-Weary":        {"counter":"consecutive_unconscious",  "threshold":3,   "stats":{"atk":-1,"resolve":1}, "desc":"-1 ATK. +1 Resolve."},
    "Indomitable":      {"counter":"times_unconscious",        "threshold":10,  "stats":{"resolve":5},   "desc":"+5 Resolve. Unique epilogue."},
    # Rare / hidden
    "Ghost King":       {"counter":None, "threshold":None, "stats":{},              "desc":"+3 all stats on NG+. Hall of Fame."},
    "Conqueror":        {"counter":None, "threshold":None, "stats":{},              "desc":"+3 all stats on NG+. Hall of Fame."},
    "The Unbroken":     {"counter":None, "threshold":None, "stats":{"atk":5,"def":5,"spd":5,"resolve":5,"recon":5}, "desc":"+5 all stats. Unique HOF entry."},
    "Blood and Ash":    {"counter":"total_band_deaths",        "threshold":20,  "stats":{},              "desc":"Unique eulogy flavor."},
    "Father's Shadow":  {"counter":None, "threshold":None, "stats":{},              "desc":"Unique epilogue scene."},
    "Traitor's Grace":  {"counter":None, "threshold":None, "stats":{},              "desc":"Unique epilogue — sword given to companion."},
    "Last of the Band": {"counter":"acts_with_small_band",     "threshold":1,   "stats":{},              "desc":"Unique companion dialogue."},
    "Ghost of the Isle":{"counter":None, "threshold":None, "stats":{},              "desc":"Unique story event flavor."},
    "Haunted (Faded)":  {"counter":None, "threshold":None, "stats":{},              "desc":"Haunted has run its course. No further effect."},
}

HALL_TRAITS = {"Ghost King", "Conqueror", "The Unbroken", "Blood and Ash"}


async def check_and_assign_mc_traits(guild_id: int, owner_id: int) -> list:
    player = await db.get_player(guild_id, owner_id)
    if not player:
        return []
    current  = list(player.get("traits") or [])
    counters = await db.get_trait_counters(guild_id, owner_id, "mc")
    new_traits = []

    for name, defn in TRAIT_DEFS.items():
        if name in current:
            continue
        ckey = defn.get("counter")
        thr  = defn.get("threshold")
        if ckey is None or thr is None:
            continue
        if counters.get(ckey, 0) >= thr:
            current.append(name)
            new_traits.append(name)

    if new_traits:
        stat_updates: dict = {}
        for name in new_traits:
            for stat, val in TRAIT_DEFS[name].get("stats", {}).items():
                stat_updates[stat] = stat_updates.get(stat, 0) + val
        final = {}
        for stat, delta in stat_updates.items():
            cur_val = player.get(stat, 8) or 8
            final[stat] = max(0, cur_val + delta)
        final["traits"] = current
        await db.update_player(guild_id, owner_id, **final)

    return new_traits


async def assign_story_trait(guild_id: int, owner_id: int, trait_name: str):
    player = await db.get_player(guild_id, owner_id)
    if not player:
        return
    current = list(player.get("traits") or [])
    if trait_name in current:
        return
    current.append(trait_name)
    stat_updates = {}
    for stat, val in TRAIT_DEFS.get(trait_name, {}).get("stats", {}).items():
        cur_val = player.get(stat, 8) or 8
        stat_updates[stat] = max(0, cur_val + val)
    stat_updates["traits"] = current
    await db.update_player(guild_id, owner_id, **stat_updates)


async def assign_companion_trait(guild_id: int, owner_id: int, trait_name: str):
    companion = await db.get_companion(guild_id, owner_id)
    if not companion:
        return
    current = list(companion.get("traits") or [])
    if trait_name in current:
        return
    current.append(trait_name)
    stat_updates = {}
    for stat, val in TRAIT_DEFS.get(trait_name, {}).get("stats", {}).items():
        cur_val = companion.get(stat, 8) or 8
        stat_updates[stat] = max(0, cur_val + val)
    stat_updates["traits"] = current
    await db.update_companion(guild_id, owner_id, **stat_updates)


async def tick_grief_trait(guild_id: int, owner_id: int):
    """Decrement grief counter. Remove Grief and apply +2 Resolve after 3 battles."""
    player = await db.get_player(guild_id, owner_id)
    if not player or "Grief" not in (player.get("traits") or []):
        return
    grief_count = player.get("grief_counter", 0) + 1
    if grief_count >= 3:
        traits = [t for t in player["traits"] if t != "Grief"]
        resolve = min(20, (player.get("resolve") or 8) + 2)
        await db.update_player(guild_id, owner_id, traits=traits, resolve=resolve, grief_counter=0)
    else:
        await db.update_player(guild_id, owner_id, grief_counter=grief_count)


async def remove_haunted_trait(guild_id: int, owner_id: int):
    """Remove Haunted after 5 turns and restore stats."""
    player = await db.get_player(guild_id, owner_id)
    if not player or "Haunted" not in (player.get("traits") or []):
        return
    traits  = [t for t in player["traits"] if t != "Haunted"]
    traits.append("Haunted (Faded)")
    bonuses = TRAIT_DEFS["Haunted"].get("stats", {})
    updates = {"traits": traits}
    for stat, val in bonuses.items():
        updates[stat] = max(1, (player.get(stat, 8) or 8) - val)  # reverse the penalty
    await db.update_player(guild_id, owner_id, **updates)
