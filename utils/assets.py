import os
import discord
import logging

log = logging.getLogger(__name__)
_BASE = os.path.join(os.path.dirname(__file__), "..", "assets", "embeds")


def get_asset(path: str):
    full = os.path.join(_BASE, path)
    if not os.path.exists(full):
        log.debug("Asset missing: %s", full)
        return None
    return discord.File(full, filename=os.path.basename(full))


def get_panel_banner(name: str):
    return get_asset(f"panels/{name}_panel.png")


def get_weapon_icon(key: str, tier: int):
    return get_asset(f"weapons/{key}_t{tier}.png") or get_asset(f"weapons/{key}_t1.png")


def get_armor_icon(key: str, tier: int):
    return get_asset(f"armor/{key}_t{tier}.png") or get_asset(f"armor/{key}_t1.png")


def get_archetype_icon(archetype: str):
    return get_asset(f"archetypes/{archetype.lower().replace(' ','_')}.png")


def get_story_banner(scene_key: str, act_fallback: str = None):
    return get_asset(f"story/{scene_key}.png") or (get_panel_banner(act_fallback) if act_fallback else None)


def get_social_icon(event: str):
    return get_asset(f"social/{event}.png")


def get_relic_icon(key: str):
    return get_asset(f"relics/{key}.png")


def get_perk_icon(perk_id: str):
    return get_asset(f"perks/{perk_id.lower().replace(' ','_')}.png")


def apply_banner(embed: discord.Embed, f) -> list:
    if f:
        embed.set_image(url=f"attachment://{f.filename}")
        return [f]
    return []


def apply_thumbnail(embed: discord.Embed, f) -> list:
    if f:
        embed.set_thumbnail(url=f"attachment://{f.filename}")
        return [f]
    return []
