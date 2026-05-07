# Band Cog
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import utils.db as db
from utils.embeds import base_embed, COLOR_LOYALTY, COLOR_DEFEAT, COLOR_WARNING, wallet_line
from utils.items_data import ARCHETYPES


class RecruitModal(Modal, title="Recruit Fighter"):
    fighter_name = TextInput(label="Fighter Name",    min_length=1, max_length=30)
    archetype    = TextInput(label="Archetype",        placeholder="Ashigaru / Scout / Bushi / Healer / Archer / Spear Corps / Ryukyuan Fighter / Monk")

    async def on_submit(self, i: discord.Interaction):
        name = self.fighter_name.value.strip()
        arch = self.archetype.value.strip()
        if arch not in ARCHETYPES:
            await i.response.send_message(
                embed=base_embed("Invalid Archetype",
                    f"Valid archetypes:\n{', '.join(ARCHETYPES.keys())}", COLOR_DEFEAT),
                ephemeral=True)
            return
        player = await db.get_player(i.guild_id, i.user.id)
        if not player:
            await i.response.send_message(
                embed=base_embed("No Campaign","",COLOR_DEFEAT), ephemeral=True)
            return
        cost = ARCHETYPES[arch]["recruit_cost"]
        if (player.get("coin") or 0) < cost:
            await i.response.send_message(
                embed=base_embed("Insufficient Coin",
                    f"{arch} costs {cost} Coin. You have {player.get('coin',0)}.", COLOR_DEFEAT),
                ephemeral=True)
            return
        band_size = await db.get_band_size(i.guild_id, i.user.id)
        if band_size >= 30:
            await i.response.send_message(
                embed=base_embed("Band Full","Maximum 30 fighters.",COLOR_DEFEAT), ephemeral=True)
            return
        await db.update_player(i.guild_id, i.user.id, coin=player["coin"] - cost)
        stats = dict(ARCHETYPES[arch]["base"])
        stats["max_hp"] = stats["hp"]
        m = await db.add_band_member(i.guild_id, i.user.id, name, arch, stats)
        await db.adjust_loyalty(i.guild_id, i.user.id, 3)
        embed = discord.Embed(
            title=f"{name} Recruited",
            description=(
                f"Archetype: {arch}\n"
                f"HP: {m['hp']}  ATK: {m['atk']}  DEF: {m['def']}  SPD: {m['spd']}\n"
                f"Resolve: {m['resolve']}  Recon: {m['recon']}\n"
                f"Individual Loyalty: {m['individual_loyalty']}\n\n"
                f"Cost: {cost} Coin. Band size: {band_size+1}/30."
            ),
            color=COLOR_LOYALTY,
        )
        await i.response.send_message(embed=embed, ephemeral=True)


class DismissModal(Modal, title="Dismiss Fighter"):
    member_id = TextInput(label="Fighter ID", placeholder="See Band Roster for IDs")

    async def on_submit(self, i: discord.Interaction):
        try:
            mid = int(self.member_id.value.strip())
        except ValueError:
            await i.response.send_message(
                embed=base_embed("Invalid ID","Fighter ID must be a number.",COLOR_DEFEAT), ephemeral=True)
            return
        member = await db.get_band_member(mid)
        if not member or member["guild_id"] != i.guild_id or member["owner_id"] != i.user.id:
            await i.response.send_message(
                embed=base_embed("Not Found","No fighter with that ID in your band.",COLOR_DEFEAT), ephemeral=True)
            return
        pool = await db.get_pool()
        async with pool.acquire() as c:
            await c.execute("UPDATE band_members SET is_alive=FALSE WHERE id=$1", mid)
        await db.adjust_loyalty(i.guild_id, i.user.id, -5)
        await i.response.send_message(
            embed=base_embed("Fighter Dismissed",
                f"{member['member_name']} ({member['archetype']}) has been released. Loyalty -5.", COLOR_WARNING),
            ephemeral=True)


class BandManagementView(View):
    def __init__(self, guild_id: int, owner_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.owner_id = owner_id

    @discord.ui.button(label="Recruit Fighter", style=discord.ButtonStyle.secondary, row=0)
    async def recruit(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        player = await db.get_player(self.guild_id, self.owner_id)
        if not player or player.get("current_act",0) < 1:
            await i.response.send_message(
                embed=base_embed("Unavailable","Recruiting unlocks at Act 1.",COLOR_DEFEAT), ephemeral=True)
            return
        await i.response.send_modal(RecruitModal())

    @discord.ui.button(label="Dismiss Fighter",   style=discord.ButtonStyle.danger,     row=0)
    async def dismiss(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        await i.response.send_modal(DismissModal())

    @discord.ui.button(label="Band Roster",       style=discord.ButtonStyle.secondary,  row=1)
    async def roster(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        band  = await db.get_band(self.guild_id, self.owner_id)
        embed = discord.Embed(title="Band Roster", color=COLOR_LOYALTY)
        if not band:
            embed.description = "No fighters. Recruit from villages in Act 1+."
        for m in band:
            traits   = m.get("traits")   or []
            injuries = m.get("injuries") or []
            status   = " [DOWNED]" if m.get("is_downed") else ""
            embed.add_field(name=f"ID {m['id']} — {m['member_name']} ({m['archetype']}){status}", value=(
                f"HP: {m['hp']}/{m['max_hp']}  ATK: {m['atk']}  DEF: {m['def']}  "
                f"SPD: {m['spd']}  Resolve: {m['resolve']}  Recon: {m['recon']}\n"
                f"Battles: {m['battles_survived']}  Kills: {m['kills']}  "
                f"Loyalty: {m['individual_loyalty']}"
                + (f"\nTraits: {', '.join(traits)}"         if traits   else "")
                + (f"\nInjuries: {', '.join(injuries[:2])}" if injuries else "")
            ), inline=False)
        await i.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Memorial",          style=discord.ButtonStyle.secondary,  row=1)
    async def memorial(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        entries = await db.get_memorial(self.guild_id, self.owner_id)
        embed   = discord.Embed(title="Band Memorial", color=COLOR_LOYALTY)
        if not entries:
            embed.description = "None have fallen yet."
        for e in entries[:10]:
            embed.add_field(
                name=f"{e['member_name']} — {e['archetype']}",
                value=(
                    f"Cause: {e.get('cause_of_death','unknown')}\n"
                    f"Battles: {e.get('battles_survived',0)}  Kills: {e.get('kills',0)}\n"
                    + (e.get("eulogy","") or "")
                ),
                inline=False,
            )
        if len(entries) > 10:
            embed.set_footer(text=f"{len(entries)} total. Showing 10 most recent.")
        await i.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Contracts",         style=discord.ButtonStyle.secondary,  row=2)
    async def contracts(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        from views.contract_view import ContractBoardView
        view  = ContractBoardView(self.guild_id, self.owner_id)
        embed, _ = await view.build_embed()
        await i.response.send_message(embed=embed, view=view, ephemeral=True)


class BandCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(BandCog(bot))
