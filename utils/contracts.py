# Contracts
import random
import utils.db as db
from utils.map_render import NAMED_LOCATIONS, addr

CONTRACT_TEMPLATES = {
    "escort": {
        "difficulty": "standard",
        "title_fmt": "Escort {target} to {destination}",
        "desc_fmt":  (
            "A {target} needs safe passage to {destination}. "
            "Satsuma patrols are active in the area. "
            "Get them there within {turns} turns."
        ),
        "turns": 8,
        "reward_coin": (10, 20),
        "reward_xp":   50,
    },
    "ambush": {
        "difficulty": "standard",
        "title_fmt": "Ambush Satsuma supply convoy near {location}",
        "desc_fmt":  (
            "A Satsuma supply convoy passes through {location} on a fixed route. "
            "Intercept and destroy it. They will be guarded."
        ),
        "turns": 6,
        "reward_coin": (15, 25),
        "reward_xp":   60,
    },
    "rescue": {
        "difficulty": "dangerous",
        "title_fmt": "Rescue prisoner from {location}",
        "desc_fmt":  (
            "A Ryukyuan fighter is being held at a Satsuma post near {location}. "
            "Breach, retrieve them, and withdraw before reinforcements arrive. "
            "{turns} turns."
        ),
        "turns": 7,
        "reward_coin": (20, 35),
        "reward_xp":   100,
    },
    "sabotage": {
        "difficulty": "dangerous",
        "title_fmt": "Sabotage supply depot at {location}",
        "desc_fmt":  (
            "Destroy the Satsuma supply depot near {location}. "
            "This will slow their advance by one act-cycle. "
            "Guards are posted."
        ),
        "turns": 5,
        "reward_coin": (25, 40),
        "reward_xp":   100,
    },
    "village_defense": {
        "difficulty": "standard",
        "title_fmt": "Defend {location} from Satsuma raid",
        "desc_fmt":  (
            "Satsuma forces are moving on {location}. "
            "Hold the village for {turns} turns. "
            "Casualties among villagers will cost standing."
        ),
        "turns": 10,
        "reward_coin": (15, 30),
        "reward_xp":   80,
        "reward_standing": ("ryukyuan", 1),
    },
    "intelligence": {
        "difficulty": "standard",
        "title_fmt": "Gather intelligence near {location}",
        "desc_fmt":  (
            "Move within 2 hexes of {location} and observe Satsuma positions "
            "for 3 consecutive turns without being detected. "
            "Do not engage."
        ),
        "turns": 12,
        "reward_coin": (10, 18),
        "reward_xp":   50,
    },
    "duel_challenge": {
        "difficulty": "deadly",
        "title_fmt": "Single combat against {target}",
        "desc_fmt":  (
            "A Satsuma officer has issued a formal challenge. "
            "Face {target} in single combat. Your band cannot intervene. "
            "Victory ends their unit's threat permanently."
        ),
        "turns": None,
        "reward_coin": (30, 50),
        "reward_xp":   180,
    },
    "supply_run": {
        "difficulty": "standard",
        "title_fmt": "Secure supplies from {location}",
        "desc_fmt":  (
            "Reach {location}, clear or avoid any guards, "
            "and return with the supply cache. "
            "{turns} turns before Satsuma sweeps the area."
        ),
        "turns": 9,
        "reward_coin": (8, 15),
        "reward_raw_metals": (2, 5),
        "reward_xp":   40,
    },
}

ESCORT_TARGETS       = ["a Ryukyuan elder","a wounded resistance fighter","a village healer","a messenger"]
DESTINATIONS         = ["Itoman","Yomitan","Motobu","the cave refuge","Nago Town"]
AMBUSH_LOCATIONS     = ["the river ford","the mountain pass","the coast road","the bamboo grove"]
HOSTILE_LOCATIONS    = list(NAMED_LOCATIONS.keys())
OFFICER_NAMES        = ["Lt. Harada","Capt. Fujiwara","Cpt. Nakamura","Lt. Sato","Sgt. Watanabe"]


def _pick(lst):
    return random.choice(lst)


def generate_contract(act: int, difficulty: str = None) -> dict:
    # Filter templates by act appropriateness
    available = list(CONTRACT_TEMPLATES.keys())
    if act == 0:
        available = []
    elif act == 1:
        available = ["escort","ambush","supply_run","village_defense","intelligence"]
    elif act == 2:
        available = ["escort","ambush","rescue","sabotage","village_defense","intelligence","supply_run"]
    elif act >= 3:
        available = list(CONTRACT_TEMPLATES.keys())

    if not available:
        return {}

    template_key = _pick(available)
    template     = CONTRACT_TEMPLATES[template_key]
    diff         = difficulty or template["difficulty"]

    location     = _pick(HOSTILE_LOCATIONS).replace("_"," ").title()
    target       = _pick(ESCORT_TARGETS)  if template_key == "escort"     else _pick(OFFICER_NAMES)
    destination  = _pick(DESTINATIONS)   if template_key == "escort"     else location
    amb_location = _pick(AMBUSH_LOCATIONS) if template_key == "ambush"   else location
    turns        = template["turns"]

    title = (template["title_fmt"]
             .replace("{target}", target)
             .replace("{destination}", destination)
             .replace("{location}", amb_location if template_key == "ambush" else location))
    desc  = (template["desc_fmt"]
             .replace("{target}", target)
             .replace("{destination}", destination)
             .replace("{location}", amb_location if template_key == "ambush" else location)
             .replace("{turns}", str(turns) if turns else "unlimited"))

    # Difficulty modifiers
    coin_range = template.get("reward_coin", (10,20))
    base_coin  = random.randint(*coin_range)
    base_xp    = template.get("reward_xp", 50)
    if diff == "dangerous":
        base_coin = int(base_coin * 1.5)
        base_xp   = int(base_xp * 1.5)
        if turns:
            turns = max(3, turns - 2)
    elif diff == "deadly":
        base_coin = base_coin * 2
        base_xp   = base_xp * 2

    reward = {"coin": base_coin, "xp": base_xp}
    if "reward_raw_metals" in template:
        reward["raw_metals"] = random.randint(*template["reward_raw_metals"])
    if "reward_standing" in template:
        faction, amount = template["reward_standing"]
        reward[f"standing_{faction}"] = amount

    # Objective hex — pick a hex near the named location if possible
    objective_hex = None
    named_list    = list(NAMED_LOCATIONS.values())
    if named_list:
        lx, ly = _pick(named_list)
        objective_hex = addr(lx, ly)

    return {
        "template_type": template_key,
        "difficulty":    diff,
        "title":         title,
        "description":   desc,
        "objective_hex": objective_hex,
        "reward":        reward,
        "turns_allowed": turns,
        "status":        "available",
    }


async def generate_and_store_contracts(guild_id: int, owner_id: int, count: int = 3) -> list:
    player    = await db.get_player(guild_id, owner_id)
    act       = player.get("current_act", 1) if player else 1
    existing  = await db.get_contracts(guild_id, owner_id, "available")
    # Don't exceed 3 available contracts
    to_gen    = max(0, count - len(existing))
    contracts = []
    for _ in range(to_gen):
        data = generate_contract(act)
        if data:
            c = await db.create_contract(guild_id, owner_id, data)
            contracts.append(c)
    return contracts


async def complete_contract_reward(guild_id: int, owner_id: int, contract: dict) -> dict:
    reward  = contract.get("reward") or {}
    player  = await db.get_player(guild_id, owner_id)
    updates = {}

    if "coin" in reward:
        updates["coin"] = (player.get("coin") or 0) + reward["coin"]
    if "raw_metals" in reward:
        updates["raw_metals"] = (player.get("raw_metals") or 0) + reward["raw_metals"]

    if updates:
        await db.update_player(guild_id, owner_id, **updates)

    if "xp" in reward:
        from utils.combat import apply_xp
        await apply_xp(guild_id, owner_id, reward["xp"])

    if "standing_ryukyuan" in reward:
        await db.adjust_faction_standing(guild_id, owner_id, "ryukyuan", reward["standing_ryukyuan"])
    if "standing_satsuma" in reward:
        await db.adjust_faction_standing(guild_id, owner_id, "satsuma", reward["standing_satsuma"])

    await db.increment_leaderboard(guild_id, owner_id, "contracts_completed")
    await db.complete_contract(contract["id"])

    from utils.loyalty import apply_loyalty_event
    await apply_loyalty_event(guild_id, owner_id, "contract_complete")

    return reward
