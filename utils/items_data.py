# Items Data
# Full catalog from GDD Appendix B

# Weapons: key -> {name, tiers: [{tier, atk_bonus, description}], type}
WEAPONS = {
    "katana": {
        "name": "Katana",
        "type": "blade",
        "tiers": [
            {"tier": 1, "atk_bonus": 2,  "desc": "Standard Satsuma-issue blade."},
            {"tier": 2, "atk_bonus": 4,  "desc": "Sharpened and balanced."},
            {"tier": 3, "atk_bonus": 6,  "desc": "Master-forged. Holds an edge longer."},
            {"tier": 4, "atk_bonus": 9,  "desc": "Legendary blade. Sings on the draw."},
        ],
    },
    "naginata": {
        "name": "Naginata",
        "type": "polearm",
        "tiers": [
            {"tier": 1, "atk_bonus": 2,  "desc": "Reach weapon. +1 DEF in open terrain."},
            {"tier": 2, "atk_bonus": 4,  "desc": "+1 DEF in open terrain."},
            {"tier": 3, "atk_bonus": 6,  "desc": "+2 DEF in open terrain."},
            {"tier": 4, "atk_bonus": 9,  "desc": "+3 DEF. Enemies cannot close freely."},
        ],
    },
    "yumi": {
        "name": "Yumi",
        "type": "bow",
        "tiers": [
            {"tier": 1, "atk_bonus": 2,  "desc": "Ranged. 3-hex range. -1 ATK in melee."},
            {"tier": 2, "atk_bonus": 4,  "desc": "3-hex range. -1 ATK in melee."},
            {"tier": 3, "atk_bonus": 6,  "desc": "4-hex range. No melee penalty."},
            {"tier": 4, "atk_bonus": 8,  "desc": "4-hex range. +1 ATK in first volley."},
        ],
    },
    "tanto": {
        "name": "Tanto",
        "type": "blade",
        "tiers": [
            {"tier": 1, "atk_bonus": 1,  "desc": "Fast. +1 SPD. Good for finishers."},
            {"tier": 2, "atk_bonus": 2,  "desc": "+1 SPD. Concealable."},
            {"tier": 3, "atk_bonus": 4,  "desc": "+2 SPD. Can be thrown once per combat."},
            {"tier": 4, "atk_bonus": 6,  "desc": "+3 SPD. Bypass light armor once per combat."},
        ],
    },
    "kanabo": {
        "name": "Kanabo",
        "type": "bludgeon",
        "tiers": [
            {"tier": 1, "atk_bonus": 3,  "desc": "Heavy. -1 SPD. Ignores 1 DEF."},
            {"tier": 2, "atk_bonus": 5,  "desc": "-1 SPD. Ignores 2 DEF."},
            {"tier": 3, "atk_bonus": 7,  "desc": "Ignores 2 DEF. Chance to stagger."},
            {"tier": 4, "atk_bonus": 10, "desc": "Ignores 3 DEF. Stagger on every hit."},
        ],
    },
    "ryukyuan_spear": {
        "name": "Ryukyuan Spear",
        "type": "polearm",
        "tiers": [
            {"tier": 1, "atk_bonus": 2,  "desc": "Local weapon. +1 Ryukyuan standing."},
            {"tier": 2, "atk_bonus": 4,  "desc": "+1 Ryukyuan standing. Reach 2."},
            {"tier": 3, "atk_bonus": 6,  "desc": "+2 Ryukyuan standing. Reach 2."},
            {"tier": 4, "atk_bonus": 8,  "desc": "Sacred weapon. +3 Ryukyuan standing."},
        ],
    },
    "takeda_blade": {
        "name": "Takeda's Blade",
        "type": "relic_blade",
        "tiers": [
            {"tier": 1, "atk_bonus": 5,  "desc": "Heir's Burden trait. +2 Resolve. Cannot be dropped."},
        ],
        "is_relic": True,
    },
}

# Armor: key -> {name, tiers: [{tier, def_bonus, spd_penalty, description}]}
ARMOR = {
    "ashigaru_armor": {
        "name": "Ashigaru Armor",
        "tiers": [
            {"tier": 1, "def_bonus": 2, "spd_penalty": 0, "desc": "Standard infantry armor."},
            {"tier": 2, "def_bonus": 4, "spd_penalty": 0, "desc": "Reinforced plates."},
            {"tier": 3, "def_bonus": 6, "spd_penalty": 1, "desc": "Heavy infantry. -1 SPD."},
            {"tier": 4, "def_bonus": 8, "spd_penalty": 1, "desc": "Full battle kit. -1 SPD."},
        ],
    },
    "light_scout": {
        "name": "Light Scout Armor",
        "tiers": [
            {"tier": 1, "def_bonus": 1, "spd_penalty": 0, "desc": "+1 SPD. Minimal protection."},
            {"tier": 2, "def_bonus": 2, "spd_penalty": 0, "desc": "+1 SPD."},
            {"tier": 3, "def_bonus": 3, "spd_penalty": 0, "desc": "+2 SPD."},
            {"tier": 4, "def_bonus": 5, "spd_penalty": 0, "desc": "+2 SPD. Near-invisible in jungle."},
        ],
    },
    "ryukyuan_lamellar": {
        "name": "Ryukyuan Lamellar",
        "tiers": [
            {"tier": 1, "def_bonus": 3, "spd_penalty": 0, "desc": "+1 Ryukyuan standing when worn."},
            {"tier": 2, "def_bonus": 5, "spd_penalty": 0, "desc": "+1 Ryukyuan standing."},
            {"tier": 3, "def_bonus": 7, "spd_penalty": 0, "desc": "+2 Ryukyuan standing."},
            {"tier": 4, "def_bonus": 9, "spd_penalty": 1, "desc": "Full plate. +2 standing."},
        ],
    },
    "satsuma_officer": {
        "name": "Satsuma Officer Armor",
        "tiers": [
            {"tier": 1, "def_bonus": 3, "spd_penalty": 0, "desc": "+1 Satsuma standing when worn."},
            {"tier": 2, "def_bonus": 5, "spd_penalty": 0, "desc": "+1 Satsuma standing."},
            {"tier": 3, "def_bonus": 7, "spd_penalty": 1, "desc": "+2 Satsuma standing."},
            {"tier": 4, "def_bonus": 10,"spd_penalty": 1, "desc": "Commander armor. +3 standing."},
        ],
    },
}

# Consumables: key -> {name, description, effect_key, value}
CONSUMABLES = {
    "medicine": {
        "name": "Medicine",
        "desc": "Restore 20 HP to any unit. One use.",
        "effect": "heal", "value": 20,
    },
    "bandage": {
        "name": "Bandage",
        "desc": "Stabilize a downed unit (1 HP). One use.",
        "effect": "stabilize", "value": 1,
    },
    "rations": {
        "name": "Rations",
        "desc": "Restore 5 HP. Prevents Hunger injury for 1 turn.",
        "effect": "heal_minor", "value": 5,
    },
    "smoke_bomb": {
        "name": "Smoke Bomb",
        "desc": "All enemies in 2-hex radius lose 2 Recon for 2 turns.",
        "effect": "smoke", "value": 2,
    },
    "fire_arrow": {
        "name": "Fire Arrow",
        "desc": "Sets hex terrain on fire. 3 damage per turn to units in hex.",
        "effect": "fire_hex", "value": 3,
    },
    "flash_powder": {
        "name": "Flash Powder",
        "desc": "Stuns adjacent enemies for 1 turn. -2 DEF while stunned.",
        "effect": "stun", "value": 2,
    },
    "stimulant": {
        "name": "Stimulant",
        "desc": "+3 SPD and +2 ATK for 3 turns. -1 DEF after wears off.",
        "effect": "stimulant", "value": 3,
    },
    "poison_vial": {
        "name": "Poison Vial",
        "desc": "Apply to weapon. Target takes 2 damage per turn for 3 turns.",
        "effect": "poison", "value": 2,
    },
    "war_drum": {
        "name": "War Drum",
        "desc": "Band gains +2 Resolve for the remainder of combat. One use.",
        "effect": "resolve_boost", "value": 2,
    },
    "signal_fire": {
        "name": "Signal Fire",
        "desc": "Call in 1 allied reinforcement to an adjacent hex. One use per contract.",
        "effect": "reinforce", "value": 1,
    },
    "iron_rations": {
        "name": "Iron Rations",
        "desc": "No upkeep cost this turn. One use.",
        "effect": "skip_upkeep", "value": 1,
    },
    "healing_salve": {
        "name": "Healing Salve",
        "desc": "Restore 10 HP and clear one injury. One use.",
        "effect": "heal_injury", "value": 10,
    },
}

# Relics: key -> {name, description, stat_effects, special}
RELICS = {
    "takeda_blade": {
        "name": "Takeda's Blade",
        "desc": "Your father's sword. ATK +5. Heir's Burden trait. Cannot be dropped or traded.",
        "stats": {"atk": 5, "resolve": 2},
        "special": "heir_burden",
        "path": None,
    },
    "nabi_stone": {
        "name": "Nabi's Stone",
        "desc": "+1 Resolve. If companion trust is Tier 3+, +1 ATK as well.",
        "stats": {"resolve": 1},
        "special": "companion_bond",
        "path": None,
    },
    "mori_seal": {
        "name": "Mori's Seal",
        "desc": "+1 Satsuma standing. Opens a unique Act 3 quest chain.",
        "stats": {},
        "special": "mori_quest",
        "path": None,
    },
    "katsuren_banner": {
        "name": "Katsuren Banner",
        "desc": "+2 band Loyalty when displayed at camp. One use per rest.",
        "stats": {},
        "special": "loyalty_rest",
        "path": None,
    },
    "ghost_veil": {
        "name": "The Ghost's Veil",
        "desc": "Stealth detection delayed +2 turns on overworld. Ghost Path only.",
        "stats": {},
        "special": "stealth_delay",
        "path": "ghost",
    },
    "sho_nei_missive": {
        "name": "Sho Nei's Missive",
        "desc": "Opens a unique diplomatic resolution path in the epilogue.",
        "stats": {},
        "special": "epilogue_diplomatic",
        "path": None,
    },
    "commander_seal": {
        "name": "Commander's Seal",
        "desc": "+2 DEF. Band cannot rout while MC is alive. Blade Path only.",
        "stats": {"def": 2},
        "special": "no_rout",
        "path": "blade",
    },
    "island_chart": {
        "name": "Island Chart",
        "desc": "Reveals all named overworld locations immediately. Fog still applies per hex.",
        "stats": {},
        "special": "reveal_named",
        "path": None,
    },
    "hana_token": {
        "name": "Hana's Token",
        "desc": "Hana's trust is locked at Tier 3. Unique dialogue in Act 3.",
        "stats": {"resolve": 1},
        "special": "hana_bond",
        "path": None,
    },
    "iso_orders": {
        "name": "Iso's Written Orders",
        "desc": "Satsuma units will not attack you on sight once. One use.",
        "stats": {},
        "special": "safe_passage",
        "path": "blade",
    },
}

# Perks: perk_id -> {name, description, stat_effects, requires_path, requires_level}
PERKS = {
    "killing_momentum": {
        "name": "Killing Momentum",
        "desc": "+1 ATK for each enemy killed this combat turn, up to +3.",
        "stats": {},
        "path": None, "level": 3,
    },
    "iron_discipline": {
        "name": "Iron Discipline",
        "desc": "Band loyalty loss from deaths reduced by 2.",
        "stats": {},
        "path": None, "level": 4,
    },
    "field_medic": {
        "name": "Field Medic",
        "desc": "Stabilize actions cost 0 AP. Medicine heals +10 HP.",
        "stats": {},
        "path": None, "level": 3,
    },
    "ghost_step": {
        "name": "Ghost Step",
        "desc": "Movement on overworld does not trigger Satsuma detection rolls in jungle terrain.",
        "stats": {},
        "path": "ghost", "level": 5,
    },
    "blade_oath": {
        "name": "Blade Oath",
        "desc": "After any unit in your band dies, +2 ATK for 3 turns.",
        "stats": {},
        "path": "blade", "level": 5,
    },
    "tactical_eye": {
        "name": "Tactical Eye",
        "desc": "+2 to initiative rolls. Can see enemy initiative positions before combat starts.",
        "stats": {"recon": 1},
        "path": None, "level": 6,
    },
    "island_tongue": {
        "name": "Island Tongue",
        "desc": "After language barrier breaks, all Ryukyuan village standing starts at Friendly.",
        "stats": {},
        "path": None, "level": 4,
    },
    "hardened": {
        "name": "Hardened",
        "desc": "+3 Max HP. Injuries heal one turn faster.",
        "stats": {"max_hp": 3},
        "path": None, "level": 2,
    },
    "shadow_band": {
        "name": "Shadow Band",
        "desc": "Band members with Scout archetype gain +2 Recon and +1 SPD.",
        "stats": {},
        "path": "ghost", "level": 6,
    },
    "satsuma_contacts": {
        "name": "Satsuma Contacts",
        "desc": "Once per act, get one piece of free intel about Sora's location.",
        "stats": {},
        "path": "blade", "level": 4,
    },
    "pain_tolerance": {
        "name": "Pain Tolerance",
        "desc": "No stat penalties from injuries until HP drops below 20.",
        "stats": {},
        "path": None, "level": 5,
    },
    "veteran_eye": {
        "name": "Veteran's Eye",
        "desc": "Can identify enemy archetypes and approximate stats before engaging.",
        "stats": {},
        "path": None, "level": 7,
    },
}

# Archetypes: key -> base stats and description
ARCHETYPES = {
    "Ashigaru": {
        "desc": "Standard foot soldier. Balanced stats.",
        "base": {"hp":80,"atk":8,"def":8,"spd":8,"resolve":7,"recon":7},
        "recruit_cost": 5,
    },
    "Scout": {
        "desc": "Fast and perceptive. Low HP.",
        "base": {"hp":65,"atk":7,"def":6,"spd":12,"resolve":7,"recon":12},
        "recruit_cost": 6,
    },
    "Bushi": {
        "desc": "Elite fighter. High ATK and DEF. Expensive.",
        "base": {"hp":90,"atk":11,"def":10,"spd":8,"resolve":10,"recon":7},
        "recruit_cost": 12,
    },
    "Healer": {
        "desc": "Cannot attack. Stabilize and Medicine actions are free.",
        "base": {"hp":70,"atk":4,"def":7,"spd":8,"resolve":9,"recon":8},
        "recruit_cost": 8,
    },
    "Archer": {
        "desc": "Ranged attacker. 3-hex range.",
        "base": {"hp":72,"atk":9,"def":6,"spd":8,"resolve":7,"recon":9},
        "recruit_cost": 7,
    },
    "Spear Corps": {
        "desc": "Polearm specialist. +1 DEF against charges.",
        "base": {"hp":85,"atk":9,"def":9,"spd":7,"resolve":8,"recon":7},
        "recruit_cost": 8,
    },
    "Satsuma Regular": {
        "desc": "Former enemy. High loyalty risk. Powerful stats.",
        "base": {"hp":90,"atk":10,"def":9,"spd":8,"resolve":9,"recon":8},
        "recruit_cost": 15,
    },
    "Ryukyuan Fighter": {
        "desc": "Local resistance. +1 Recon in Ryukyuan terrain.",
        "base": {"hp":78,"atk":8,"def":7,"spd":9,"resolve":8,"recon":10},
        "recruit_cost": 6,
    },
    "Monk": {
        "desc": "High Resolve. Boosts morale. Cannot use heavy weapons.",
        "base": {"hp":75,"atk":7,"def":8,"spd":8,"resolve":13,"recon":8},
        "recruit_cost": 9,
    },
    "Cavalry": {
        "desc": "Mounted. +4 SPD on open terrain. Cannot enter dense jungle.",
        "base": {"hp":85,"atk":12,"def":7,"spd":14,"resolve":8,"recon":7},
        "recruit_cost": 18,
    },
}

# XP thresholds per level (1-10)
LEVEL_XP = {1:0, 2:100, 3:250, 4:500, 5:900, 6:1400, 7:2000, 8:2800, 9:3800, 10:5000}

# XP rewards
XP_REWARDS = {
    "kill_ashigaru":     15,
    "kill_archer":       15,
    "kill_spear":        20,
    "kill_cavalry":      30,
    "kill_elite":        50,
    "kill_commander":    80,
    "kill_named":        100,
    "contract_standard": 50,
    "contract_dangerous":100,
    "contract_deadly":   180,
    "contract_story":    200,
    "act_complete":      300,
}

# Injury types and stat penalties
INJURIES = {
    "Sprained Ankle":   {"spd": -2, "desc": "SPD -2. Heals after 2 rests."},
    "Arm Wound":        {"atk": -2, "desc": "ATK -2. Heals after 2 rests."},
    "Cracked Rib":      {"def": -2, "desc": "DEF -2. Heals after 3 rests."},
    "Concussion":       {"resolve": -2, "recon": -2, "desc": "Resolve/Recon -2. Heals after 3 rests."},
    "Deep Cut":         {"hp_per_turn": -1, "desc": "Lose 1 HP per turn until stabilised."},
    "Broken Arm":       {"atk": -4, "desc": "ATK -4. Heals after 5 rests. Cannot use two-handed weapons."},
    "Leg Wound":        {"spd": -4, "desc": "SPD -4. Heals after 4 rests."},
    "Eye Injury":       {"recon": -4, "desc": "Recon -4. May be permanent."},
    "Hunger":           {"atk": -1, "def": -1, "desc": "All -1 until fed."},
}


def get_weapon(key: str) -> dict | None:
    return WEAPONS.get(key)


def get_weapon_tier(key: str, tier: int) -> dict | None:
    w = WEAPONS.get(key)
    if not w:
        return None
    for t in w["tiers"]:
        if t["tier"] == tier:
            return {**t, "name": w["name"], "type": w["type"]}
    return None


def get_armor(key: str) -> dict | None:
    return ARMOR.get(key)


def get_armor_tier(key: str, tier: int) -> dict | None:
    a = ARMOR.get(key)
    if not a:
        return None
    for t in a["tiers"]:
        if t["tier"] == tier:
            return {**t, "name": a["name"]}
    return None


def get_consumable(key: str) -> dict | None:
    return CONSUMABLES.get(key)


def get_relic(key: str) -> dict | None:
    return RELICS.get(key)


def get_perk(perk_id: str) -> dict | None:
    return PERKS.get(perk_id)


def get_archetype(name: str) -> dict | None:
    return ARCHETYPES.get(name)


def level_for_xp(xp: int) -> int:
    level = 1
    for lvl, threshold in LEVEL_XP.items():
        if xp >= threshold:
            level = lvl
    return min(level, 10)
