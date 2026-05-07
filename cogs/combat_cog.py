# Combat Cog
import discord
from discord.ext import commands
import utils.db as db
from utils.embeds import base_embed, COLOR_COMBAT, COLOR_DEFEAT
from utils.combat import initiative_order
from utils.satsuma_ai import UNIT_TYPES
from views.combat_view import CombatView
import random
import json


def _build_starting_grid(terrain_type: str = "jungle", size: int = 9) -> dict:
    grid = {}
    for x in range(size):
        for y in range(size):
            # Randomise terrain with the given type as base
            if random.random() < 0.6:
                ter = terrain_type
            else:
                ter = random.choice(["open","ruins","hilltop","village"])
            grid[f"{x},{y}"] = {"terrain": ter}
    return grid


def _starting_positions(band_size: int, enemy_count: int, map_size: int = 9) -> dict:
    mid = map_size // 2
    positions = {
        "mc":   {"x": mid, "y": mid + 2, "hp": None},
        "comp": {"x": mid - 1, "y": mid + 2, "hp": None},
    }
    for i in range(min(band_size, 4)):
        positions[f"b{i}"] = {"x": mid - 2 + i, "y": mid + 3, "hp": None}
    for e in range(enemy_count):
        positions[f"e{e}"] = {
            "x": mid - enemy_count // 2 + e,
            "y": mid - 2,
            "hp": None,
            "def": 8,
            "atk": 8,
        }
    return positions


class CombatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def trigger_encounter(self, guild_id: int, owner_id: int,
                                  unit_type: str, unit_id: int, channel: discord.TextChannel):
        player = await db.get_player(guild_id, owner_id)
        if not player or not player.get("is_alive", True):
            return

        existing = await db.get_tactical_map(guild_id, owner_id)
        if existing:
            return  # Already in combat

        band_size = await db.get_band_size(guild_id, owner_id)
        u_stats   = UNIT_TYPES.get(unit_type, UNIT_TYPES["ashigaru_foot"])
        # Determine enemy count by difficulty
        act       = player.get("current_act", 1)
        if act == 1:
            enemy_count = random.randint(1, 3)
        elif act == 2:
            enemy_count = random.randint(2, 5)
        else:
            enemy_count = random.randint(3, 6)

        hex_addr = player.get("current_hex", "30,85")
        hex_row  = await db.get_hex(guild_id, owner_id, hex_addr)
        terrain  = hex_row.get("terrain", "jungle") if hex_row else "jungle"

        grid      = _build_starting_grid(terrain)
        positions = _starting_positions(band_size, enemy_count)

        # Stamp enemy HP from unit stats
        for k in list(positions.keys()):
            if k.startswith("e"):
                positions[k]["hp"]  = u_stats["hp"]
                positions[k]["max_hp"] = u_stats["max_hp"]
                positions[k]["atk"] = u_stats["atk"]
                positions[k]["def"] = u_stats["def"]

        # MC and companion HP
        positions["mc"]["hp"]   = player["hp"]
        positions["mc"]["atk"]  = player["atk"]
        positions["mc"]["def"]  = player["def"]
        positions["mc"]["spd"]  = player["spd"]
        comp = await db.get_companion(guild_id, owner_id)
        if comp and comp.get("is_present"):
            positions["comp"]["hp"]  = comp["hp"]
            positions["comp"]["atk"] = comp["atk"]
            positions["comp"]["def"] = comp["def"]

        state = {
            "hex_grid":         grid,
            "unit_positions":   positions,
            "turn_number":      1,
            "initiative_order": [],
            "is_active":        True,
            "combat_type":      "encounter",
            "map_size":         9,
        }
        await db.save_tactical_map(guild_id, owner_id, state)
        # Deactivate the triggering unit to prevent double-trigger
        await db.deactivate_satsuma_unit(unit_id)

        view  = CombatView(guild_id, owner_id, combat_type="encounter")
        embed, files = await view.build_embed()
        embed.title = f"Encounter — {unit_type.replace('_',' ').title()} ({enemy_count} units)"
        guild  = self.bot.get_guild(guild_id)
        member = guild.get_member(owner_id) if guild else None
        await channel.send(content=member.mention if member else None,
                           embed=embed, view=view, files=files)

    async def trigger_duel(self, guild_id: int, owner_id: int,
                             opponent_name: str, channel: discord.TextChannel, is_pvp: bool = False):
        player = await db.get_player(guild_id, owner_id)
        if not player or not player.get("is_alive", True):
            return

        grid = _build_starting_grid("open", 5)
        positions = {
            "mc":  {"x": 2, "y": 3, "hp": player["hp"], "atk": player["atk"], "def": player["def"]},
            "e0":  {"x": 2, "y": 1, "hp": 100, "max_hp": 100, "atk": 13, "def": 10},
        }
        state = {
            "hex_grid":       grid,
            "unit_positions": positions,
            "turn_number":    1,
            "initiative_order": [],
            "is_active":      True,
            "combat_type":    "duel",
            "map_size":       5,
        }
        await db.save_tactical_map(guild_id, owner_id, state)

        view  = CombatView(guild_id, owner_id, combat_type="duel")
        embed, _ = await view.build_embed()
        embed.title  = f"Duel — {opponent_name}"
        embed.color  = COLOR_COMBAT
        embed.description = (
            "*The space between you narrows to nothing. "
            "Your band cannot intervene. This ends between the two of you.*\n\n"
            + (embed.description or "")
        )
        guild  = self.bot.get_guild(guild_id)
        member = guild.get_member(owner_id) if guild else None
        await channel.send(content=member.mention if member else None, embed=embed, view=view)

    async def trigger_pvp(self, guild_id: int, challenger_id: int,
                           defender_id: int, channel: discord.TextChannel):
        challenger = await db.get_player(guild_id, challenger_id)
        defender   = await db.get_player(guild_id, defender_id)
        if not challenger or not defender:
            await channel.send(embed=base_embed("PvP Failed","Both players must have active campaigns.",COLOR_DEFEAT))
            return
        if not challenger.get("is_alive") or not defender.get("is_alive"):
            await channel.send(embed=base_embed("PvP Failed","Both players must be alive.",COLOR_DEFEAT))
            return

        # Simple stat-based resolution for now (full tactical PvP = future phase)
        c_score = challenger["atk"] + challenger["spd"] + random.randint(1, 10)
        d_score = defender["atk"]   + defender["spd"]   + random.randint(1, 10)

        if c_score > d_score:
            winner, loser = challenger_id, defender_id
            result = "challenger"
        elif d_score > c_score:
            winner, loser = defender_id, challenger_id
            result = "defender"
        else:
            winner, loser = None, None
            result = "draw"

        await db.record_pvp(guild_id, challenger_id, defender_id, winner, result)

        c_mc  = f"Shimazu {challenger['mc_first_name']}"
        d_mc  = f"Shimazu {defender['mc_first_name']}"
        if result == "draw":
            desc = f"{c_mc} vs {d_mc} — Draw. Neither yields."
        elif result == "challenger":
            desc = f"{c_mc} defeats {d_mc}."
        else:
            desc = f"{d_mc} defeats {c_mc}."

        embed = discord.Embed(title="PvP Combat", description=desc, color=COLOR_COMBAT)
        embed.add_field(name=c_mc, value=f"ATK {challenger['atk']}  SPD {challenger['spd']}", inline=True)
        embed.add_field(name=d_mc, value=f"ATK {defender['atk']}  SPD {defender['spd']}",   inline=True)
        guild   = self.bot.get_guild(guild_id)
        c_mem   = guild.get_member(challenger_id) if guild else None
        d_mem   = guild.get_member(defender_id)   if guild else None
        content = " ".join(filter(None, [c_mem.mention if c_mem else None,
                                         d_mem.mention if d_mem else None]))
        await channel.send(content=content or None, embed=embed)


async def setup(bot):
    await bot.add_cog(CombatCog(bot))
