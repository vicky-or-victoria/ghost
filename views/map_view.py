import discord
from discord.ui import View, Button
import utils.db as db
from utils.map_render import (
    render_viewport, render_region, explore_around,
    parse, addr, in_bounds, IMPASSABLE, moves_for_spd,
)
from utils.embeds import base_embed, wallet_line, COLOR_DEFAULT, COLOR_DEFEAT, act_label
from utils.loyalty import apply_upkeep, check_desertion, threshold_effects
from utils.traits import check_and_assign_mc_traits, remove_haunted_trait
from utils.satsuma_ai import resolve_end_turn_ai

MOVE_DIRS = {
    "nw": (-1,-1), "n": (0,-1), "ne": (1,-1),
    "w":  (-1, 0),              "e":  (1, 0),
    "sw": (-1, 1), "s": (0, 1), "se": (1, 1),
}

BAR_FULL  = "█"
BAR_EMPTY = "░"
BAR_LEN   = 10


def _moves_bar_text(left:int, total:int) -> str:
    filled = round(BAR_LEN * left / total) if total else 0
    bar    = BAR_FULL * filled + BAR_EMPTY * (BAR_LEN - filled)
    return f"`{bar}` {left}/{total}"


class RegionMapView(View):
    """Standalone view for the region map. Close returns to the overworld viewport."""
    def __init__(self, guild_id: int, owner_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.owner_id = owner_id

    @discord.ui.button(label="Back to Map", style=discord.ButtonStyle.secondary)
    async def close(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your map.", ephemeral=True)
            return
        await i.response.defer()
        map_view = MapView(self.guild_id, self.owner_id)
        embed, files = await map_view.build_map_embed()
        await i.edit_original_response(embed=embed, attachments=files, view=map_view)


class MapView(View):
    def __init__(self, guild_id: int, owner_id: int):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.owner_id = owner_id

    async def _get_moves(self) -> tuple[int,int]:
        """Returns (moves_left, moves_max) for current turn."""
        player   = await db.get_player(self.guild_id, self.owner_id)
        if not player:
            return 0, 0
        spd      = player.get("spd", 8)
        mx       = moves_for_spd(spd)
        counters = await db.get_trait_counters(self.guild_id, self.owner_id, "mc")
        used     = counters.get("moves_this_turn", 0)
        return max(0, mx - used), mx

    async def build_map_embed(self):
        player = await db.get_player(self.guild_id, self.owner_id)
        if not player:
            return base_embed("No player data.", color=COLOR_DEFEAT), []

        cur_hex  = player.get("current_hex","?")
        h        = await db.get_hex(self.guild_id, self.owner_id, cur_hex)
        loc_name = (h.get("location_name") or cur_hex) if h else cur_hex
        terrain  = (h.get("terrain","?").replace("_"," ").title()) if h else "?"
        ml, mx   = await self._get_moves()

        embed = discord.Embed(
            title=f"Overworld Map — {loc_name}",
            color=COLOR_DEFAULT,
        )
        embed.add_field(
            name="Status",
            value=(
                f"{wallet_line(player)}\n"
                f"{act_label(player.get('current_act',1))}  |  "
                f"Terrain: {terrain}  |  SPD: {player.get('spd',8)}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Moves This Turn",
            value=_moves_bar_text(ml, mx),
            inline=False,
        )
        embed.set_footer(text="8-directional movement. End Turn resets moves and resolves AI.")

        map_file = await render_viewport(self.guild_id, self.owner_id)
        if map_file:
            embed.set_image(url="attachment://map.png")
            return embed, [map_file]
        return embed, []

    async def _move(self, i: discord.Interaction, direction: str):
        if i.user.id != self.owner_id:
            await i.response.send_message("This is not your campaign.", ephemeral=True)
            return
        player = await db.get_player(self.guild_id, self.owner_id)
        if not player:
            await i.response.send_message("No player data.", ephemeral=True)
            return

        ml, mx = await self._get_moves()
        if ml <= 0:
            await i.response.send_message(
                embed=base_embed("No Moves Left",
                    f"You have used all {mx} moves this turn. Press End Turn to continue.",
                    COLOR_DEFEAT),
                ephemeral=True)
            return

        cx, cy   = parse(player.get("current_hex","30,85"))
        dx, dy   = MOVE_DIRS[direction]
        nx, ny   = cx+dx, cy+dy
        if not in_bounds(nx, ny):
            await i.response.send_message("Out of bounds.", ephemeral=True)
            return
        new_addr = addr(nx, ny)
        h = await db.get_hex(self.guild_id, self.owner_id, new_addr)
        if h and h.get("terrain") in IMPASSABLE:
            await i.response.send_message("Impassable terrain.", ephemeral=True)
            return

        recon       = player.get("recon", 8)
        explore_rad = max(1, recon // 4)
        await db.update_player(self.guild_id, self.owner_id, current_hex=new_addr)
        await explore_around(self.guild_id, self.owner_id, new_addr, explore_rad)
        await db.increment_trait_counter(self.guild_id, self.owner_id, "mc", "hexes_explored", 1)
        # Consume a move
        await db.increment_trait_counter(self.guild_id, self.owner_id, "mc", "moves_this_turn", 1)

        await i.response.defer()
        embed, files = await self.build_map_embed()
        h2 = await db.get_hex(self.guild_id, self.owner_id, new_addr)
        if h2 and h2.get("is_named_location") and h2.get("location_name"):
            embed.add_field(name=f"Arrived: {h2['location_name']}",
                value=f"Terrain: {h2.get('terrain','?').replace('_',' ').title()}", inline=False)
        await i.edit_original_response(embed=embed, attachments=files, view=self)

    # Row 0 — NW N NE
    @discord.ui.button(label="NW", style=discord.ButtonStyle.secondary, custom_id="map_nw", row=0)
    async def nw(self, i, b): await self._move(i, "nw")

    @discord.ui.button(label="N",  style=discord.ButtonStyle.secondary, custom_id="map_n",  row=0)
    async def n(self, i, b):  await self._move(i, "n")

    @discord.ui.button(label="NE", style=discord.ButtonStyle.secondary, custom_id="map_ne", row=0)
    async def ne(self, i, b): await self._move(i, "ne")

    # Row 1 — W HexInfo E
    @discord.ui.button(label="W",        style=discord.ButtonStyle.secondary, custom_id="map_w",    row=1)
    async def w(self, i, b): await self._move(i, "w")

    @discord.ui.button(label="Hex Info", style=discord.ButtonStyle.secondary, custom_id="map_info", row=1)
    async def hex_info(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("This is not your campaign.", ephemeral=True)
            return
        player = await db.get_player(self.guild_id, self.owner_id)
        h      = await db.get_hex(self.guild_id, self.owner_id, player.get("current_hex","?"))
        if not h:
            await i.response.send_message("No hex data.", ephemeral=True)
            return
        units = await db.get_satsuma_units(self.guild_id, self.owner_id)
        here  = [u for u in units if u["hex_address"]==h["address"] and u.get("is_active")]
        embed = base_embed(
            h.get("location_name") or h["address"],
            (
                f"Terrain: {h['terrain'].replace('_',' ').title()}\n"
                f"Controller: {h['controller'].title()}\n"
                f"Explored: {'Yes' if h['is_explored'] else 'No'}"
                + (f"\n\nSatsuma units here: {len(here)}" if here else "")
            ),
            COLOR_DEFAULT,
        )
        await i.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="E",        style=discord.ButtonStyle.secondary, custom_id="map_e",    row=1)
    async def e(self, i, b): await self._move(i, "e")

    # Row 2 — SW S SE
    @discord.ui.button(label="SW", style=discord.ButtonStyle.secondary, custom_id="map_sw", row=2)
    async def sw(self, i, b): await self._move(i, "sw")

    @discord.ui.button(label="S",  style=discord.ButtonStyle.secondary, custom_id="map_s",  row=2)
    async def s(self, i, b):  await self._move(i, "s")

    @discord.ui.button(label="SE", style=discord.ButtonStyle.secondary, custom_id="map_se", row=2)
    async def se(self, i, b): await self._move(i, "se")

    # Row 3 — End Turn | Region Map | Contracts | Refresh
    @discord.ui.button(label="End Turn",   style=discord.ButtonStyle.danger,     custom_id="map_end",       row=3)
    async def end_turn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("This is not your campaign.", ephemeral=True)
            return
        await i.response.defer()
        events = []

        # Reset moves for new turn
        pool = await db.get_pool()
        async with pool.acquire() as c:
            await c.execute(
                "UPDATE trait_tracker SET counter_value=0 "
                "WHERE guild_id=$1 AND owner_id=$2 AND unit_id='mc' AND counter_key='moves_this_turn'",
                self.guild_id, self.owner_id
            )

        cost, paid = await apply_upkeep(self.guild_id, self.owner_id)
        if not paid:
            events.append(f"Upkeep unpaid ({cost} Coin). Loyalty reduced.")

        ai_events = await resolve_end_turn_ai(self.guild_id, self.owner_id)
        for ev in ai_events:
            if ev.startswith("encounter:"):
                parts = ev.split(":")
                utype = parts[1].replace("_"," ").title() if len(parts)>1 else "Satsuma"
                events.append(f"Satsuma encounter: {utype}.")

        deserters = await check_desertion(self.guild_id, self.owner_id)
        for d in deserters:
            events.append(f"{d['member_name']} ({d['archetype']}) deserted.")

        events.extend(await threshold_effects(self.guild_id, self.owner_id))

        new_traits = await check_and_assign_mc_traits(self.guild_id, self.owner_id)
        for t in new_traits:
            events.append(f"New trait: {t}.")

        player = await db.get_player(self.guild_id, self.owner_id)
        if player and "Haunted" in (player.get("traits") or []):
            await db.increment_trait_counter(self.guild_id, self.owner_id, "mc", "haunted_turns", 1)
            counters = await db.get_trait_counters(self.guild_id, self.owner_id, "mc")
            if counters.get("haunted_turns",0) >= 5:
                await remove_haunted_trait(self.guild_id, self.owner_id)
                events.append("Haunted has faded.")

        embed, files = await self.build_map_embed()
        if events:
            embed.add_field(name="End of Turn", value="\n".join(events[:10]), inline=False)
        await i.edit_original_response(embed=embed, attachments=files, view=self)

    @discord.ui.button(label="Region Map", style=discord.ButtonStyle.secondary, custom_id="map_region",    row=3)
    async def region_map_btn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("This is not your campaign.", ephemeral=True)
            return
        await i.response.defer()
        region_file = await render_region(self.guild_id, self.owner_id)
        player      = await db.get_player(self.guild_id, self.owner_id)
        spd         = player.get("spd",8) if player else 8
        embed = discord.Embed(
            title="Region Map — Ryukyu",
            description=(
                "Full island overview. Explored tiles are shown in terrain color.\n"
                "Unexplored tiles are dark. Gold dots mark named locations.\n"
                "The bright box is your current viewport."
            ),
            color=COLOR_DEFAULT,
        )
        if region_file:
            embed.set_image(url="attachment://region_map.png")
            await i.edit_original_response(embed=embed, attachments=[region_file], view=RegionMapView(self.guild_id, self.owner_id))
        else:
            await i.edit_original_response(
                embed=base_embed("Region Map Unavailable","Map renderer not available.",COLOR_DEFEAT),
                view=self)

    @discord.ui.button(label="Contracts",  style=discord.ButtonStyle.secondary, custom_id="map_contracts",  row=3)
    async def contracts_btn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("This is not your campaign.", ephemeral=True)
            return
        player = await db.get_player(self.guild_id, self.owner_id)
        if not player or player.get("current_act",0) < 1:
            await i.response.send_message(
                embed=base_embed("Unavailable","Contracts unlock at Act 1.",COLOR_DEFEAT), ephemeral=True)
            return
        from views.contract_view import ContractBoardView
        view  = ContractBoardView(self.guild_id, self.owner_id)
        embed, _ = await view.build_embed()
        await i.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Refresh",    style=discord.ButtonStyle.secondary, custom_id="map_refresh",    row=3)
    async def refresh(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("This is not your campaign.", ephemeral=True)
            return
        await i.response.defer()
        e, f = await self.build_map_embed()
        await i.edit_original_response(embed=e, attachments=f, view=self)