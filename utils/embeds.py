import discord

# Embed border colors
COLOR_DEFAULT = 0x8B7355
COLOR_COMBAT  = 0xC0392B
COLOR_STORY   = 0x2C3E50
COLOR_VICTORY = 0x27AE60
COLOR_DEFEAT  = 0x7F8C8D
COLOR_LOYALTY = 0xE67E22
COLOR_WARNING = 0xF39C12
COLOR_SOCIAL  = 0x8E44AD
COLOR_NEUTRAL = 0x95A5A6
COLOR_GM      = 0x1ABC9C


def wallet_line(p: dict) -> str:
    return (
        f"Coin: {p.get('coin',0)}  |  "
        f"Raw Metals: {p.get('raw_metals',0)}  |  "
        f"Rare Metals: {p.get('rare_metals',0)}  |  "
        f"Shimazu Steel: {p.get('shimazu_steel',0)}"
    )


def base_embed(title: str, description: str = "", color: int = COLOR_DEFAULT) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


def error_embed(msg: str) -> discord.Embed:
    return discord.Embed(title="Error", description=msg, color=COLOR_DEFEAT)


def loyalty_state_label(loyalty: int) -> str:
    if loyalty >= 80:   return "Unshakeable"
    elif loyalty >= 50: return "Solid"
    elif loyalty >= 30: return "Strained"
    elif loyalty >= 15: return "Fracturing"
    elif loyalty >= 5:  return "Collapsing"
    else:               return "Broken"


def act_label(act: int) -> str:
    return {
        0: "Act 0 — Before the Fire",
        1: "Act 1 — Survival",
        2: "Act 2 — Allegiance",
        3: "Act 3 — The Reckoning",
    }.get(act, f"Act {act}")


def path_label(path) -> str:
    if path == "ghost": return "Path of the Ghost"
    if path == "blade": return "Path of the Blade"
    return "Undecided"


def trust_label(tier: int) -> str:
    return ["Cautious", "Cautious Friend", "Ally", "Bound", "Inseparable"][min(tier, 4)]


def loyalty_tier_label(standing: int, faction: str) -> str:
    if faction == "satsuma":
        return ["Stranger", "Asset", "Trusted Officer", "Inner Circle"][min(standing, 3)]
    if faction == "ryukyuan":
        return ["Unknown", "Suspicious", "Useful", "Trusted"][min(standing, 3)]
    if faction == "village":
        return ["Hostile", "Neutral", "Friendly", "Trusted"][min(standing, 3)]
    return str(standing)
