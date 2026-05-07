import discord
from discord.ui import View, Button, Modal, TextInput
import utils.db as db
from utils.embeds import base_embed, COLOR_COMBAT, COLOR_VICTORY, COLOR_DEFEAT, COLOR_NEUTRAL
from utils.combat import (
    roll_hit, roll_injury, initiative_order, check_rout,
    get_terrain_modifiers, apply_item_effect, post_combat_resolution,
    ARCHETYPE_SPECIALS, ACTIONS,
)
from utils.items_data import get_consumable
import random
import json


async def build_combat_state(guild_id: int, owner_id: int) -> dict | None:
    return await db.get_tactical_map(guild_id, owner_id)


def render_tactical_map(state: dict, size: int = 9) -> str:
    grid      = state.get("hex_grid") or {}
    positions = state.get("unit_positions") or {}
    if isinstance(grid, str):
        grid = json.loads(grid)
    if isinstance(positions, str):
        positions = json.loads(positions)
    pos_map = {}
    for uid, pos in positions.items():
        pos_map[f"{pos['x']},{pos['y']}"] = uid

    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            key = f"{x},{y}"
            ter = grid.get(key, {}).get("terrain","open")
            if key in pos_map:
                uid = pos_map[key]
                ch  = "P" if uid == "mc" else ("C" if uid == "comp" else ("B" if uid.startswith("b") else "E"))
            else:
                ch_map = {
                    "jungle":"%" , "open":".", "ruins":"#",
                    "hilltop":"^", "river":"-", "village":"V",
                    "beach":"~",   "bamboo":"|",
                }
                ch = ch_map.get(ter, ".")
            row.append(ch)
        rows.append(" ".join(row))
    legend = "P MC  C Companion  B Band  E Enemy  % Jungle  ^ Hill  # Ruins  ~ Beach"
    return "```\n" + "\n".join(rows) + "\n```\n" + legend


class UseItemModal(Modal, title="Use Item"):
    item_key  = TextInput(label="Item Key", placeholder="e.g. medicine")
    target_id = TextInput(label="Target ID", placeholder="mc / comp / band member ID")

    def __init__(self, guild_id, owner_id, combat_view):
        super().__init__()
        self.guild_id    = guild_id
        self.owner_id    = owner_id
        self.combat_view = combat_view

    async def on_submit(self, interaction: discord.Interaction):
        key    = self.item_key.value.strip()
        target = self.target_id.value.strip()
        has    = await db.has_item(self.guild_id, self.owner_id, key)
        if not has:
            await interaction.response.send_message(f"You don't have {key}.", ephemeral=True)
            return
        c = get_consumable(key)
        if not c:
            await interaction.response.send_message(f"Unknown item: {key}.", ephemeral=True)
            return
        await db.remove_item(self.guild_id, self.owner_id, key, 1)
        if target == "mc":
            player = await db.get_player(self.guild_id, self.owner_id)
            updates = apply_item_effect(c["effect"], c["value"], player)
            if updates:
                await db.update_player(self.guild_id, self.owner_id, **updates)
        elif target == "comp":
            comp = await db.get_companion(self.guild_id, self.owner_id)
            if comp:
                updates = apply_item_effect(c["effect"], c["value"], comp)
                if updates:
                    await db.update_companion(self.guild_id, self.owner_id, **updates)
        else:
            try:
                mid = int(target)
                m   = await db.get_band_member(mid)
                if m:
                    updates = apply_item_effect(c["effect"], c["value"], m)
                    if updates:
                        await db.update_band_member(mid, **updates)
            except ValueError:
                pass
        await interaction.response.send_message(
            embed=base_embed("Item Used", f"{c['name']} used on {target}. {c['desc']}", COLOR_NEUTRAL),
            ephemeral=True)
        e, f = await self.combat_view.build_embed()
        await interaction.edit_original_response(embed=e, view=self.combat_view)


class CombatView(View):
    def __init__(self, guild_id: int, owner_id: int, combat_type: str = "encounter"):
        super().__init__(timeout=600)
        self.guild_id    = guild_id
        self.owner_id    = owner_id
        self.combat_type = combat_type
        self.turn        = 1
        self.casualties  : list = []
        self.enemies_killed = 0
        self.retreat_taken  = False

    async def build_embed(self):
        state  = await build_combat_state(self.guild_id, self.owner_id)
        player = await db.get_player(self.guild_id, self.owner_id)
        if not state or not player:
            return base_embed("No combat active.", color=COLOR_DEFEAT), []

        map_render = render_tactical_map(state, state.get("map_size", 9))
        positions  = state.get("unit_positions") or {}
        if isinstance(positions, str):
            positions = json.loads(positions)

        mc_pos   = positions.get("mc", {})
        cur_hex  = f"{mc_pos.get('x','?')},{mc_pos.get('y','?')}"
        band     = await db.get_band(self.guild_id, self.owner_id)
        comp     = await db.get_companion(self.guild_id, self.owner_id)
        loyalty  = await db.get_loyalty(self.guild_id, self.owner_id)
        enemies  = [v for k, v in positions.items() if k.startswith("e")]

        embed = discord.Embed(
            title=f"Tactical Combat — Turn {self.turn}",
            description=map_render,
            color=COLOR_COMBAT,
        )
        embed.add_field(name="MC", value=(
            f"HP: {player['hp']}/{player['max_hp']}  ATK: {player['atk']}  "
            f"DEF: {player['def']}  SPD: {player['spd']}\n"
            f"Resolve: {player['resolve']}  Pos: {cur_hex}"
        ), inline=False)

        if comp and comp.get("is_present") and not comp.get("is_downed"):
            comp_pos = positions.get("comp",{})
            embed.add_field(name=f"Companion: {comp['companion_name']}", value=(
                f"HP: {comp['hp']}/{comp['max_hp']}  ATK: {comp['atk']}  DEF: {comp['def']}\n"
                f"Pos: {comp_pos.get('x','?')},{comp_pos.get('y','?')}"
            ), inline=True)

        alive_band = [m for m in band if not m.get("is_downed")]
        if alive_band:
            band_str = "  ".join(
                f"{m['member_name']}({m['hp']}HP)" for m in alive_band[:5]
            )
            if len(alive_band) > 5:
                band_str += f" +{len(alive_band)-5} more"
            embed.add_field(name=f"Band ({len(alive_band)} active)", value=band_str, inline=False)

        embed.add_field(name=f"Enemies ({len(enemies)} remaining)",
            value=", ".join(f"E{k.replace('e','')}" for k in positions if k.startswith("e"))
                  or "None", inline=False)

        downed_band = [m for m in band if m.get("is_downed")]
        if downed_band:
            embed.add_field(name="Downed", value=", ".join(m["member_name"] for m in downed_band), inline=False)

        embed.set_footer(text=(
            f"Band Loyalty: {loyalty}  |  Turn {self.turn}  |  "
            f"Casualties this fight: {len(self.casualties)}"
        ))
        return embed, []

    async def _check_victory(self) -> bool:
        state = await build_combat_state(self.guild_id, self.owner_id)
        if not state:
            return False
        positions = state.get("unit_positions") or {}
        if isinstance(positions, str):
            positions = json.loads(positions)
        return not any(k.startswith("e") for k in positions)

    async def _check_defeat(self) -> bool:
        player = await db.get_player(self.guild_id, self.owner_id)
        if not player or player.get("hp", 0) <= 0:
            return True
        return False

    async def _end_combat(self, i: discord.Interaction, victory: bool):
        await db.clear_tactical_map(self.guild_id, self.owner_id)
        new_traits = await post_combat_resolution(
            self.guild_id, self.owner_id,
            victory, self.casualties, self.enemies_killed,
            retreat=self.retreat_taken,
        )
        if victory:
            desc = (
                f"Victory. Enemies: {self.enemies_killed} defeated.\n"
                f"Casualties: {len(self.casualties)}."
                + (f"\nNew traits: {', '.join(new_traits)}" if new_traits else "")
            )
            embed = base_embed("Victory", desc, COLOR_VICTORY)
        else:
            desc = (
                "Defeat. Your MC has fallen.\n"
                "Load a save or this campaign ends."
            )
            embed = base_embed("Defeat", desc, COLOR_DEFEAT)
            # MC death handling
            await db.update_player(self.guild_id, self.owner_id, is_alive=False)
            from cogs.social_cog import SocialCog
            cog = i.client.cogs.get("SocialCog")
            if cog:
                await cog.announce_mc_death(self.guild_id, self.owner_id, "killed in tactical combat")
        self.stop()
        await i.edit_original_response(embed=embed, view=None)

    # Action buttons

    @discord.ui.button(label="Attack",    style=discord.ButtonStyle.danger,     custom_id="cb_attack",    row=0)
    async def attack_btn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your combat.", ephemeral=True); return
        await i.response.defer()
        player  = await db.get_player(self.guild_id, self.owner_id)
        state   = await build_combat_state(self.guild_id, self.owner_id)
        if not state:
            await i.edit_original_response(embed=base_embed("No combat data.",color=COLOR_DEFEAT)); return

        positions = state.get("unit_positions") or {}
        if isinstance(positions, str):
            positions = json.loads(positions)
        enemy_keys = [k for k in positions if k.startswith("e")]
        if not enemy_keys:
            await self._end_combat(i, True); return

        # Attack the first available enemy
        target_key = enemy_keys[0]
        target     = positions[target_key]

        # Terrain modifier for MC position
        grid    = state.get("hex_grid") or {}
        if isinstance(grid, str):
            grid = json.loads(grid)
        mc_pos  = positions.get("mc", {})
        ter_key = f"{mc_pos.get('x',0)},{mc_pos.get('y',0)}"
        terrain = grid.get(ter_key, {}).get("terrain", "open")
        mods    = get_terrain_modifiers(terrain)

        hit, dmg = roll_hit(
            player["atk"], target.get("def", 8),
            mods.get("atk_bonus", 0), mods.get("def_bonus", 0)
        )
        log_msg = ""
        if hit:
            target["hp"] = max(0, target.get("hp", 80) - dmg)
            log_msg = f"Hit for {dmg} damage. Enemy HP: {target['hp']}."
            if target["hp"] <= 0:
                del positions[target_key]
                self.enemies_killed += 1
                await db.increment_trait_counter(self.guild_id, self.owner_id, "mc", "total_kills", 1)
                log_msg = f"Enemy defeated. +{self.enemies_killed} kill."
        else:
            log_msg = "Attack missed."

        # Save updated positions
        state_data = dict(state)
        state_data["unit_positions"] = positions
        await db.save_tactical_map(self.guild_id, self.owner_id, state_data)

        if await self._check_victory():
            await self._end_combat(i, True); return

        self.turn += 1
        e, f = await self.build_embed()
        e.add_field(name="Attack Result", value=log_msg, inline=False)
        await i.edit_original_response(embed=e, attachments=f, view=self)

    @discord.ui.button(label="Special",   style=discord.ButtonStyle.secondary,  custom_id="cb_special",   row=0)
    async def special_btn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your combat.", ephemeral=True); return
        player = await db.get_player(self.guild_id, self.owner_id)
        wkey   = player.get("equipped_weapon","katana")
        from utils.items_data import get_weapon
        w = get_weapon(wkey)
        wtype = w["type"] if w else "blade"
        # Weapon special effect
        if wtype == "bludgeon":
            desc = "Kanabo Slam — ignores 3 DEF this strike."
        elif wtype == "polearm":
            desc = "Set Polearm — +3 DEF until your next turn."
        elif wtype == "bow":
            desc = "Volley — attack all enemies in a 2-hex line."
        else:
            desc = "Quick Draw — attack with +2 ATK, cannot be countered."
        await i.response.send_message(
            embed=base_embed("Special Attack", desc, COLOR_COMBAT), ephemeral=True)

    @discord.ui.button(label="Item",      style=discord.ButtonStyle.secondary,  custom_id="cb_item",      row=0)
    async def item_btn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your combat.", ephemeral=True); return
        await i.response.send_modal(UseItemModal(self.guild_id, self.owner_id, self))

    @discord.ui.button(label="Hold",      style=discord.ButtonStyle.secondary,  custom_id="cb_hold",      row=1)
    async def hold_btn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your combat.", ephemeral=True); return
        await i.response.defer()
        player = await db.get_player(self.guild_id, self.owner_id)
        new_def = min(20, player["def"] + 2)
        await db.update_player(self.guild_id, self.owner_id, def_=new_def)
        self.turn += 1
        e, f = await self.build_embed()
        e.add_field(name="Hold Position", value="+2 DEF until your next action.", inline=False)
        await i.edit_original_response(embed=e, attachments=f, view=self)

    @discord.ui.button(label="Stabilize", style=discord.ButtonStyle.secondary,  custom_id="cb_stab",      row=1)
    async def stabilize_btn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your combat.", ephemeral=True); return
        await i.response.defer()
        band = await db.get_band(self.guild_id, self.owner_id)
        downed = [m for m in band if m.get("is_downed")]
        comp   = await db.get_companion(self.guild_id, self.owner_id)
        stab_msg = "No downed units in range."
        # Check if player has Field Medic perk (free stabilize)
        player = await db.get_player(self.guild_id, self.owner_id)
        perks  = player.get("perks") or []
        if downed:
            m = downed[0]
            await db.stabilize_band_member(m["id"])
            stab_msg = f"{m['member_name']} stabilized (1 HP)."
        elif comp and comp.get("is_present") and not comp.get("is_conscious"):
            await db.update_companion(self.guild_id, self.owner_id, is_conscious=True, hp=1)
            stab_msg = f"{comp['companion_name']} stabilized (1 HP)."
        self.turn += 1
        e, f = await self.build_embed()
        e.add_field(name="Stabilize", value=stab_msg, inline=False)
        await i.edit_original_response(embed=e, attachments=f, view=self)

    @discord.ui.button(label="Retreat",   style=discord.ButtonStyle.danger,     custom_id="cb_retreat",   row=1)
    async def retreat_btn(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your combat.", ephemeral=True); return
        await i.response.defer()
        self.retreat_taken = True
        await self._end_combat(i, False)
