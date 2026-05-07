import discord
from discord.ui import View, Button, Modal, TextInput
import utils.db as db
from utils.embeds import base_embed, COLOR_STORY, COLOR_DEFAULT, COLOR_DEFEAT


class EnlistModal(Modal, title="Enlist — Ghost of Ryukyu"):
    first_name = TextInput(
        label="Your first name",
        placeholder="You are of the Shimazu clan. Your family name is already written.",
        min_length=1, max_length=20,
    )

    def __init__(self, gender: str):
        super().__init__()
        self.gender = gender

    async def on_submit(self, interaction: discord.Interaction):
        name = self.first_name.value.strip()
        if not name or not name.replace(" ","").isalpha():
            await interaction.response.send_message(
                embed=base_embed("Invalid Name","Letters only.",COLOR_DEFEAT), ephemeral=True)
            return
        existing = await db.get_player(interaction.guild_id, interaction.user.id)
        if existing and existing["is_alive"]:
            await interaction.response.send_message(
                embed=base_embed("Already Enlisted",
                    f"Active campaign: Shimazu {existing['mc_first_name']}.",COLOR_DEFEAT),
                ephemeral=True)
            return
        await db.create_player(interaction.guild_id, interaction.user.id, name, self.gender)
        comp = "Nabi" if self.gender == "male" else "Kenji"
        embed = discord.Embed(
            title="A Letter from Shimazu Takeo",
            description=(
                "*You will join me when the fleet makes port. Bring only what you can carry.*\n"
                "*Ryukyu is a small kingdom and its resistance will be brief.*\n"
                "*When it is done, there will be something worth showing you.*\n"
                "*Come ready to learn what it means to carry this name.*\n\n"
                "— Your Father\n\n"
                "*Received at Kagoshima, late winter, 1609.*"
            ),
            color=COLOR_STORY,
        )
        embed.add_field(name="Character Created", value=(
            f"Name: Shimazu {name}\n"
            f"Gender: {self.gender.capitalize()}\n"
            f"Companion: {comp}\n"
            "All stats at 8. Press Player Panel to begin Act 0."
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GenderSelectView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Male", style=discord.ButtonStyle.secondary)
    async def male(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EnlistModal("male"))

    @discord.ui.button(label="Female", style=discord.ButtonStyle.secondary)
    async def female(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EnlistModal("female"))


class MainMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enlist", style=discord.ButtonStyle.danger, custom_id="menu_enlist", row=0)
    async def enlist(self, interaction: discord.Interaction, button: Button):
        existing = await db.get_player(interaction.guild_id, interaction.user.id)
        if existing and existing["is_alive"]:
            await interaction.response.send_message(
                embed=base_embed("Already Enlisted",
                    f"Active campaign: Shimazu {existing['mc_first_name']}.",COLOR_DEFEAT),
                ephemeral=True)
            return
        await interaction.response.send_message(
            embed=base_embed("Choose Your Character",
                "Select your gender. Determines companion name. Permanent until MC death.",
                COLOR_STORY),
            view=GenderSelectView(), ephemeral=True)

    @discord.ui.button(label="Player Panel", style=discord.ButtonStyle.secondary, custom_id="menu_player", row=0)
    async def player_panel(self, interaction: discord.Interaction, button: Button):
        player = await db.get_player(interaction.guild_id, interaction.user.id)
        if not player:
            await interaction.response.send_message(
                embed=base_embed("No Campaign","Press Enlist to begin.",COLOR_DEFEAT),
                ephemeral=True)
            return
        if player.get("current_act",0)==0 and player.get("current_scene")=="act0_enlistment":
            story_cog = interaction.client.cogs.get("StoryCog")
            if story_cog:
                await interaction.response.send_message(
                    embed=base_embed("Campaign Starting","Your story begins in the commands channel.",COLOR_STORY),
                    ephemeral=True)
                await story_cog.deliver_scene(interaction.guild_id, interaction.user.id, "act0_enlistment")
                return
        from views.player_view import PlayerView
        pv = PlayerView(player, interaction.guild_id, interaction.user.id)
        embed, files = await pv.build_main_embed()
        await interaction.response.send_message(embed=embed, view=pv, files=files, ephemeral=True)

    @discord.ui.button(label="Hall of Fame", style=discord.ButtonStyle.secondary, custom_id="menu_hof", row=0)
    async def hof(self, interaction: discord.Interaction, button: Button):
        entries = await db.get_hall_of_fame(interaction.guild_id)
        if not entries:
            await interaction.response.send_message(
                embed=base_embed("Hall of Fame","No entries yet.",COLOR_DEFAULT), ephemeral=True)
            return
        embed = discord.Embed(title="Hall of Fame", color=COLOR_STORY)
        from utils.embeds import path_label, act_label
        for e in entries[:10]:
            ended = "Complete" if e["ended_by"]=="campaign_complete" else "Fallen"
            hall  = ", ".join(e.get("hall_traits") or [])
            embed.add_field(name=e["mc_name"], value=(
                f"{path_label(e.get('path_choice'))}  |  {act_label(e.get('act_reached',0))}  |  {ended}\n"
                f"Kills: {e['total_kills']}  |  Band Lost: {e['band_members_lost']}"
                + (f"\n{hall}" if hall else "")
            ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.secondary, custom_id="menu_lb", row=0)
    async def leaderboard(self, interaction: discord.Interaction, button: Button):
        entries = await db.get_leaderboard(interaction.guild_id)
        if not entries:
            await interaction.response.send_message(
                embed=base_embed("Leaderboard","No data yet.",COLOR_DEFAULT), ephemeral=True)
            return
        def fmt(field):
            top = sorted(entries, key=lambda x: x.get(field,0), reverse=True)[:5]
            return "\n".join(f"{i+1}. {e.get('mc_name','?')} — {e.get(field,0)}" for i,e in enumerate(top)) or "—"
        embed = discord.Embed(title="Leaderboard", color=COLOR_DEFAULT)
        embed.add_field(name="Enemies Killed",      value=fmt("enemies_killed"),      inline=True)
        embed.add_field(name="Contracts Completed", value=fmt("contracts_completed"),  inline=True)
        embed.add_field(name="Band Lost",           value=fmt("band_members_lost"),   inline=True)
        embed.add_field(name="PvP Wins",            value=fmt("pvp_wins"),            inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Help", style=discord.ButtonStyle.secondary, custom_id="menu_help", row=1)
    async def help_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="Ghost of Ryukyu — How to Play",
            description=(
                "You are the teenage child of a Satsuma officer. 1609. "
                "Your father's fleet has landed on Ryukyu. The compound burns at midnight.\n\n"
                "**Getting Started**\n"
                "Press Enlist to create your character. Press Player Panel to begin Act 0 "
                "in the commands channel.\n\n"
                "**The Story**\n"
                "Six escape choices in Act 0 determine your starting gear, allies, and traits. "
                "At the Act 1/2 boundary you choose Ghost or Blade — permanently.\n\n"
                "**Band and Loyalty**\n"
                "Recruit fighters at villages. Band Loyalty is shared — deaths and defeats drain it, "
                "victories and rest restore it. At 0, the band fragments.\n\n"
                "**Contracts**\n"
                "Take contracts from the overworld panel. Completing them earns coin, XP, and loyalty. "
                "Abandoning them costs loyalty.\n\n"
                "**Permadeath**\n"
                "Band members die permanently. If your MC falls, the campaign ends and is logged to the "
                "Hall of Fame. You have two save slots — use them before major missions."
            ),
            color=COLOR_DEFAULT,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
