# PvP Cog
import discord
from discord.ext import commands
from discord.ui import View, Button
import utils.db as db
from utils.embeds import base_embed, COLOR_COMBAT, COLOR_DEFEAT, COLOR_WARNING


class AcceptChallengeView(View):
    def __init__(self, challenger_id: int, defender_id: int, guild_id: int, channel_id: int):
        super().__init__(timeout=120)
        self.challenger_id = challenger_id
        self.defender_id   = defender_id
        self.guild_id      = guild_id
        self.channel_id    = channel_id

    @discord.ui.button(label="Accept",  style=discord.ButtonStyle.danger)
    async def accept(self, i: discord.Interaction, b: Button):
        if i.user.id != self.defender_id:
            await i.response.send_message("This challenge is not for you.", ephemeral=True); return
        await i.response.defer()
        self.stop()
        channel = i.client.get_channel(self.channel_id)
        if channel:
            combat_cog = i.client.cogs.get("CombatCog")
            if combat_cog:
                await combat_cog.trigger_pvp(self.guild_id, self.challenger_id, self.defender_id, channel)
        await i.edit_original_response(
            embed=base_embed("Challenge Accepted","Combat begins.", COLOR_COMBAT), view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary)
    async def decline(self, i: discord.Interaction, b: Button):
        if i.user.id != self.defender_id:
            await i.response.send_message("This challenge is not for you.", ephemeral=True); return
        self.stop()
        await i.response.edit_message(
            embed=base_embed("Challenge Declined","The duel was refused.", COLOR_WARNING), view=None)


class PvPCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="challenge", description="Challenge another player to combat.")
    @discord.app_commands.describe(opponent="The player to challenge")
    async def challenge(self, i: discord.Interaction, opponent: discord.Member):
        if opponent.id == i.user.id:
            await i.response.send_message(
                embed=base_embed("Invalid","You cannot challenge yourself.",COLOR_DEFEAT), ephemeral=True); return
        if opponent.bot:
            await i.response.send_message(
                embed=base_embed("Invalid","You cannot challenge a bot.",COLOR_DEFEAT), ephemeral=True); return

        challenger = await db.get_player(i.guild_id, i.user.id)
        defender   = await db.get_player(i.guild_id, opponent.id)

        if not challenger or not challenger.get("is_alive",True):
            await i.response.send_message(
                embed=base_embed("No Campaign","You need an active campaign.",COLOR_DEFEAT), ephemeral=True); return
        if not defender or not defender.get("is_alive",True):
            await i.response.send_message(
                embed=base_embed("No Campaign",f"{opponent.display_name} has no active campaign.",COLOR_DEFEAT),
                ephemeral=True); return

        c_mc = f"Shimazu {challenger['mc_first_name']}"
        d_mc = f"Shimazu {defender['mc_first_name']}"

        embed = discord.Embed(
            title=f"{c_mc} challenges {d_mc}",
            description=(
                f"{i.user.mention} — Act {challenger.get('current_act',0)}  "
                f"ATK {challenger['atk']}  DEF {challenger['def']}\n"
                f"{opponent.mention} — Act {defender.get('current_act',0)}  "
                f"ATK {defender['atk']}  DEF {defender['def']}\n\n"
                f"{opponent.mention} — Accept or Decline."
            ),
            color=COLOR_COMBAT,
        )
        view = AcceptChallengeView(i.user.id, opponent.id, i.guild_id, i.channel_id)
        await i.response.send_message(content=opponent.mention, embed=embed, view=view)

    @discord.app_commands.command(name="pvp_record", description="View your PvP record.")
    async def pvp_record(self, i: discord.Interaction):
        rec = await db.get_pvp_record(i.guild_id, i.user.id)
        embed = discord.Embed(
            title="PvP Record",
            description=f"Wins: {rec['wins']}  |  Total Fights: {rec['total']}",
            color=COLOR_COMBAT,
        )
        await i.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(PvPCog(bot))
