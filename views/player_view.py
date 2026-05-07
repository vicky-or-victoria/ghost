import discord
from discord.ui import View, Button
import utils.db as db
from utils.embeds import (
    base_embed, wallet_line, COLOR_DEFAULT, COLOR_STORY, COLOR_LOYALTY,
    COLOR_DEFEAT, COLOR_NEUTRAL, loyalty_state_label, act_label,
    path_label, trust_label, loyalty_tier_label,
)
from utils.assets import get_panel_banner, apply_banner
from utils.items_data import get_weapon_tier, get_armor_tier, get_relic, get_perk, ARCHETYPES


class PlayerView(View):
    def __init__(self, player: dict, guild_id: int, owner_id: int):
        super().__init__(timeout=300)
        self.player   = player
        self.guild_id = guild_id
        self.owner_id = owner_id

    async def _r(self):
        self.player = await db.get_player(self.guild_id, self.owner_id) or self.player

    # Main panel
    async def build_main_embed(self):
        await self._r()
        p         = self.player
        loyalty   = await db.get_loyalty(self.guild_id, self.owner_id)
        companion = await db.get_companion(self.guild_id, self.owner_id)
        band_size = await db.get_band_size(self.guild_id, self.owner_id)
        mc        = f"Shimazu {p['mc_first_name']}"
        desc = (
            f"{wallet_line(p)}\n\n"
            f"{act_label(p.get('current_act',0))}  |  {path_label(p.get('path_choice'))}\n"
            f"Location: {p.get('current_hex','?').replace(',',', ')}\n\n"
            f"HP: {p['hp']}/{p['max_hp']}  |  "
            f"Band Loyalty: {loyalty} ({loyalty_state_label(loyalty)})\n"
            f"Band Size: {band_size}/30  |  Level: {p.get('level',1)}  |  XP: {p.get('xp',0)}"
        )
        if companion:
            present = "Present" if companion["is_present"] else "Absent"
            desc += (
                f"\nCompanion: {companion['companion_name']} — "
                f"{trust_label(companion['trust_tier'])} ({present})"
            )
        embed = discord.Embed(title=mc, description=desc, color=COLOR_DEFAULT)
        embed.set_footer(text="Ghost of Ryukyu  |  1609  |  Ryukyu Kingdom")
        files  = []
        banner = get_panel_banner("player_main")
        files += apply_banner(embed, banner)
        return embed, files

    # Stats panel
    async def build_stats_embed(self):
        await self._r()
        p      = self.player
        mc     = f"Shimazu {p['mc_first_name']}"
        traits = p.get("traits") or []
        perks  = p.get("perks")  or []
        wkey   = p.get("equipped_weapon")
        akey   = p.get("equipped_armor")
        wt     = get_weapon_tier(wkey, p.get("equipped_weapon_tier",1)) if wkey else None
        at     = get_armor_tier(akey,  p.get("equipped_armor_tier",1))  if akey else None
        embed  = discord.Embed(
            title=f"{mc} — Stats and Perks",
            description=(
                f"{wallet_line(p)}\n\n"
                f"HP: {p['hp']}/{p['max_hp']}  |  Level {p.get('level',1)}  |  XP {p.get('xp',0)}\n"
                f"ATK: {p['atk']}  DEF: {p['def']}  SPD: {p['spd']}\n"
                f"Resolve: {p['resolve']}  Recon: {p['recon']}  Loyalty: {p['loyalty']}"
            ),
            color=COLOR_DEFAULT,
        )
        embed.add_field(name="Equipped Weapon",
            value=f"{wt['name']} T{p.get('equipped_weapon_tier',1)} — {wt['desc']}" if wt else "None",
            inline=False)
        embed.add_field(name="Equipped Armor",
            value=f"{at['name']} T{p.get('equipped_armor_tier',1)} — {at['desc']}" if at else "None",
            inline=False)
        embed.add_field(name="Traits",
            value="\n".join(f"**{t}**" for t in traits) if traits else "None assigned.", inline=False)
        embed.add_field(name="Perks",
            value="\n".join(
                f"**{pk}** — {get_perk(pk)['desc']}" if get_perk(pk) else pk for pk in perks
            ) if perks else "None taken.", inline=False)
        files  = []
        banner = get_panel_banner("stats")
        files += apply_banner(embed, banner)
        return embed, files

    # Inventory panel
    async def build_inventory_embed(self):
        await self._r()
        p     = self.player
        items = await db.get_items(self.guild_id, self.owner_id)
        cons  = [i for i in items if not i["is_relic"]]
        rels  = [i for i in items if i["is_relic"]]
        embed = discord.Embed(
            title=f"Shimazu {p['mc_first_name']} — Inventory",
            description=wallet_line(p),
            color=COLOR_DEFAULT,
        )
        if cons:
            from utils.items_data import get_consumable
            lines = []
            for i in cons:
                c = get_consumable(i["item_key"])
                name = c["name"] if c else i["item_key"].replace("_"," ").title()
                desc = c["desc"] if c else ""
                lines.append(f"**{name}** x{i['quantity']} — {desc}")
            embed.add_field(name="Consumables", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Consumables", value="None.", inline=False)
        if rels:
            lines = []
            for i in rels:
                r = get_relic(i["item_key"])
                name = r["name"] if r else i["item_key"].replace("_"," ").title()
                lines.append(f"**{name}**")
            embed.add_field(name="Relics", value="\n".join(lines), inline=False)
        files  = []
        banner = get_panel_banner("inventory")
        files += apply_banner(embed, banner)
        return embed, files

    # Relics panel
    async def build_relics_embed(self):
        await self._r()
        items = await db.get_items(self.guild_id, self.owner_id)
        rels  = [i for i in items if i["is_relic"]]
        embed = discord.Embed(
            title=f"Shimazu {self.player['mc_first_name']} — Relics",
            description=wallet_line(self.player),
            color=COLOR_STORY,
        )
        if rels:
            for i in rels:
                r = get_relic(i["item_key"])
                if r:
                    embed.add_field(name=r["name"], value=r["desc"], inline=False)
                else:
                    embed.add_field(name=i["item_key"].replace("_"," ").title(),
                        value="A unique item.", inline=False)
        else:
            embed.add_field(name="No Relics", value="Unique items appear here when found.", inline=False)
        return embed, []

    # Band panel
    async def build_band_embed(self, page: int = 0):
        band    = await db.get_band(self.guild_id, self.owner_id)
        loyalty = await db.get_loyalty(self.guild_id, self.owner_id)
        await self._r()
        p     = self.player
        start = page * 8
        shown = band[start:start+8]
        embed = discord.Embed(
            title=f"Shimazu {p['mc_first_name']} — Band Roster",
            description=(
                f"{wallet_line(p)}\n\n"
                f"Band Size: {len(band)}/30  |  "
                f"Loyalty: {loyalty} ({loyalty_state_label(loyalty)})"
            ),
            color=COLOR_LOYALTY,
        )
        if not band:
            embed.add_field(name="No Band Members",
                value="Recruit fighters from villages via the overworld panel.", inline=False)
        else:
            for m in shown:
                traits   = m.get("traits")   or []
                injuries = m.get("injuries") or []
                status   = " [DOWNED]" if m.get("is_downed") else ""
                embed.add_field(
                    name=f"{m['member_name']} — {m['archetype']}{status}",
                    value=(
                        f"HP: {m['hp']}/{m['max_hp']}  ATK: {m['atk']}  "
                        f"DEF: {m['def']}  SPD: {m['spd']}\n"
                        f"Resolve: {m['resolve']}  Recon: {m['recon']}  "
                        f"Loyalty: {m['individual_loyalty']}\n"
                        f"Battles: {m['battles_survived']}  Kills: {m['kills']}"
                        + (f"\nTraits: {', '.join(traits)}"         if traits   else "")
                        + (f"\nInjuries: {', '.join(injuries[:2])}" if injuries else "")
                    ),
                    inline=False,
                )
            if len(band) > 8:
                embed.set_footer(text=f"Page {page+1}/{(len(band)-1)//8+1}  |  {len(band)} fighters total.")
        return embed, []

    # Map panel (stub — full map opens in MapView)
    async def build_map_embed(self):
        await self._r()
        p = self.player
        embed = discord.Embed(
            title=f"Shimazu {p['mc_first_name']} — Overworld Map",
            description=(
                f"{wallet_line(p)}\n\n"
                f"Current Hex: {p.get('current_hex','?')}\n"
                f"{act_label(p.get('current_act',0))}\n\n"
                + ("The overworld map is available from Act 1 onward."
                   if p.get("current_act",0)==0
                   else "Press the Map button to open the full overworld movement interface.")
            ),
            color=COLOR_DEFAULT,
        )
        files  = []
        banner = get_panel_banner("map")
        files += apply_banner(embed, banner)
        return embed, files

    # Journal panel
    async def build_journal_embed(self):
        await self._r()
        p       = self.player
        row     = await db.get_story_flags(self.guild_id, self.owner_id)
        _flags  = row.get("flags") or {}
        import json
        flags   = json.loads(_flags) if isinstance(_flags, str) else (_flags or {})
        faction = await db.get_faction_standing(self.guild_id, self.owner_id)
        embed   = discord.Embed(
            title=f"Shimazu {p['mc_first_name']} — Journal",
            description=(
                f"{wallet_line(p)}\n\n"
                f"{act_label(p.get('current_act',0))}\n"
                f"Path: {path_label(p.get('path_choice'))}\n"
                f"Scene: {p.get('current_scene','?').replace('_',' ').title()}"
            ),
            color=COLOR_STORY,
        )
        embed.add_field(name="Faction Standing", value=(
            f"Satsuma: {loyalty_tier_label(faction.get('satsuma_standing',1),'satsuma')}\n"
            f"Ryukyuan Resistance: {loyalty_tier_label(faction.get('ryukyuan_standing',0),'ryukyuan')}"
        ), inline=True)

        notable = []
        if flags.get("FATHER_KILLER"):  notable.append("Father's killer identified: Sora")
        if flags.get("LOOKED_BACK"):    notable.append("Looked back at the fire")
        if flags.get("LANGUAGE_BREAKS"):notable.append("Language barrier lifted")
        if flags.get("PATH_CHOICE"):    notable.append(f"Path chosen: {flags['PATH_CHOICE'].capitalize()}")
        if flags.get("MORI_SAVED"):     notable.append("Lt. Mori survived")
        if flags.get("DAICHI_SAVED"):   notable.append("Daichi rescued")
        if flags.get("HANA_MET"):       notable.append("Met Hana")
        if flags.get("ISO_MET"):        notable.append("Met General Iso")
        dc = flags.get("SORA_DUEL_COUNT")
        if dc:                          notable.append(f"Duels with Sora: {dc}")
        if flags.get("SORA_SPARED"):    notable.append("Sora spared at Shuri")
        if flags.get("SORA_KILLED"):    notable.append("Sora killed at Shuri")
        if notable:
            embed.add_field(name="Notable Events", value="\n".join(notable), inline=False)

        active = await db.get_active_contract(self.guild_id, self.owner_id)
        if active:
            embed.add_field(name="Active Contract", value=(
                f"**{active['title']}**\n"
                f"Turns: {active.get('turns_elapsed',0)}/{active.get('turns_allowed','?')}"
            ), inline=False)
        files  = []
        banner = get_panel_banner("journal")
        files += apply_banner(embed, banner)
        return embed, files

    # Save panel
    async def build_save_embed(self):
        saves    = await db.get_saves(self.guild_id, self.owner_id)
        await self._r()
        save_map = {s["slot_number"]: s for s in saves}
        embed    = discord.Embed(
            title=f"Shimazu {self.player['mc_first_name']} — Save / Load",
            description=wallet_line(self.player),
            color=COLOR_NEUTRAL,
        )
        for slot in (1,2):
            if slot in save_map:
                s  = save_map[slot]
                ts = s["saved_at"].strftime("%Y-%m-%d %H:%M") if s.get("saved_at") else "?"
                embed.add_field(name=f"Slot {slot}", value=(
                    f"{s.get('act_label','?')} — Band: {s.get('band_size',0)}\nSaved: {ts}"
                ), inline=True)
            else:
                embed.add_field(name=f"Slot {slot}", value="Empty", inline=True)
        embed.set_footer(text="Saves available at village or camp, between contracts.")
        return embed, []

    # Buttons row 0
    @discord.ui.button(label="Stats and Perks", style=discord.ButtonStyle.secondary, custom_id="pp_stats",     row=0)
    async def stats_btn(self, i, b):
        e, f = await self.build_stats_embed()
        await i.response.edit_message(embed=e, attachments=f, view=self)

    @discord.ui.button(label="Inventory",       style=discord.ButtonStyle.secondary, custom_id="pp_inv",       row=0)
    async def inv_btn(self, i, b):
        e, f = await self.build_inventory_embed()
        await i.response.edit_message(embed=e, attachments=f, view=self)

    @discord.ui.button(label="Relics",          style=discord.ButtonStyle.secondary, custom_id="pp_relics",    row=0)
    async def rel_btn(self, i, b):
        e, f = await self.build_relics_embed()
        await i.response.edit_message(embed=e, attachments=f, view=self)

    @discord.ui.button(label="Band Roster",     style=discord.ButtonStyle.secondary, custom_id="pp_band",      row=0)
    async def band_btn(self, i, b):
        e, f = await self.build_band_embed()
        await i.response.edit_message(embed=e, attachments=f, view=self)

    @discord.ui.button(label="Map",             style=discord.ButtonStyle.secondary, custom_id="pp_map",       row=0)
    async def map_btn(self, i, b):
        player = await db.get_player(self.guild_id, self.owner_id)
        if not player or player.get("current_act",0)==0:
            await i.response.send_message(
                embed=base_embed("Map Unavailable","Unlocks at Act 1.",COLOR_DEFEAT), ephemeral=True)
            return
        from views.map_view import MapView
        mv = MapView(self.guild_id, self.owner_id)
        e, f = await mv.build_map_embed()
        await i.response.send_message(embed=e, view=mv, files=f, ephemeral=True)

    # Buttons row 1
    @discord.ui.button(label="Journal",         style=discord.ButtonStyle.secondary, custom_id="pp_journal",   row=1)
    async def journal_btn(self, i, b):
        e, f = await self.build_journal_embed()
        await i.response.edit_message(embed=e, attachments=f, view=self)

    @discord.ui.button(label="Save / Load",     style=discord.ButtonStyle.secondary, custom_id="pp_save",      row=1)
    async def save_btn(self, i, b):
        from views.save_view import SaveView
        e, _ = await self.build_save_embed()
        sv = SaveView(self.player, self.guild_id, self.owner_id, parent_view=self)
        await i.response.edit_message(embed=e, attachments=[], view=sv)

    @discord.ui.button(label="Back",            style=discord.ButtonStyle.secondary, custom_id="pp_back",      row=1)
    async def back_btn(self, i, b):
        e, f = await self.build_main_embed()
        await i.response.edit_message(embed=e, attachments=f, view=self)

    # Row 2 — Band and Forge
    @discord.ui.button(label="Band Management", style=discord.ButtonStyle.secondary, custom_id="pp_band_mgmt", row=2)
    async def band_mgmt_btn(self, i: discord.Interaction, b):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        player = await db.get_player(self.guild_id, self.owner_id)
        if not player or player.get("current_act",0) < 1:
            await i.response.send_message(
                embed=base_embed("Unavailable","Band Management unlocks at Act 1.",COLOR_DEFEAT),
                ephemeral=True); return
        from cogs.band_cog import BandManagementView
        view  = BandManagementView(self.guild_id, self.owner_id)
        band_size = await db.get_band_size(self.guild_id, self.owner_id)
        loyalty   = await db.get_loyalty(self.guild_id, self.owner_id)
        from utils.embeds import loyalty_state_label
        lsl = loyalty_state_label(loyalty)
        embed = base_embed("Band Management",
            f"Band Size: {band_size}/30  |  Loyalty: {loyalty} ({lsl})\n\n"
            "Recruit fighters, view your roster, check the memorial, and browse contracts.",
            COLOR_LOYALTY)
        await i.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Forge",           style=discord.ButtonStyle.secondary, custom_id="pp_forge",     row=2)
    async def forge_btn(self, i: discord.Interaction, b):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        player = await db.get_player(self.guild_id, self.owner_id)
        if not player or player.get("current_act",0) < 1:
            await i.response.send_message(
                embed=base_embed("Unavailable","The Forge unlocks at Act 1 villages.",COLOR_DEFEAT),
                ephemeral=True); return
        from cogs.economy_cog import ForgeView
        from utils.embeds import wallet_line
        view  = ForgeView(self.guild_id, self.owner_id)
        wl = wallet_line(player)
        embed = base_embed("Forge",
            f"{wl}\n\n"
            "Forge and upgrade weapons and armor.\n"
            "Tier 2: Raw Metals  |  Tier 3: Rare Metals  |  Tier 4: Shimazu Steel",
            COLOR_DEFAULT)
        await i.response.send_message(embed=embed, view=view, ephemeral=True)