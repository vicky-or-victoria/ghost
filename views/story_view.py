import discord
from discord.ui import View, Button
import utils.story_engine as story
from utils.embeds import base_embed, COLOR_STORY


def _guard(owner_id: int):
    async def check(interaction: discord.Interaction) -> bool:
        if interaction.user.id != owner_id:
            await interaction.response.send_message("This is not your campaign.", ephemeral=True)
            return False
        return True
    return check


class Scene1View(View):
    """Act 0 Scene 1 — Burning Tent"""
    def __init__(self, guild_id, owner_id, story_cog):
        super().__init__(timeout=300)
        self.guild_id  = guild_id
        self.owner_id  = owner_id
        self.story_cog = story_cog

    @discord.ui.button(label="Grab your gear", style=discord.ButtonStyle.secondary)
    async def grab(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene1_choice(self.guild_id, self.owner_id, "grab_gear")
        self.stop()
        await self.story_cog.scene_act0_courtyard_escape(self.guild_id, self.owner_id)

    @discord.ui.button(label="Run immediately", style=discord.ButtonStyle.secondary)
    async def run(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene1_choice(self.guild_id, self.owner_id, "run")
        self.stop()
        await self.story_cog.scene_act0_courtyard_escape(self.guild_id, self.owner_id)


class Scene2View(View):
    """Act 0 Scene 2 — Courtyard / Daichi"""
    def __init__(self, guild_id, owner_id, story_cog):
        super().__init__(timeout=300)
        self.guild_id  = guild_id
        self.owner_id  = owner_id
        self.story_cog = story_cog

    @discord.ui.button(label="Pull him free", style=discord.ButtonStyle.secondary)
    async def pull(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene2_choice(self.guild_id, self.owner_id, "pull_free")
        self.stop()
        await self.story_cog.scene_act0_armory(self.guild_id, self.owner_id)

    @discord.ui.button(label="Keep moving", style=discord.ButtonStyle.secondary)
    async def keep(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene2_choice(self.guild_id, self.owner_id, "keep_moving")
        self.stop()
        await self.story_cog.scene_act0_armory(self.guild_id, self.owner_id)


class Scene3View(View):
    """Act 0 Scene 3 — Armory"""
    def __init__(self, guild_id, owner_id, story_cog, unarmed: bool = False):
        super().__init__(timeout=300)
        self.guild_id  = guild_id
        self.owner_id  = owner_id
        self.story_cog = story_cog
        self.unarmed   = unarmed

    @discord.ui.button(label="Take father's sword", style=discord.ButtonStyle.secondary)
    async def sword(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene3_choice(self.guild_id, self.owner_id, "fathers_sword")
        self.stop()
        await self.story_cog.scene_act0_gate(self.guild_id, self.owner_id)

    @discord.ui.button(label="Take supplies instead", style=discord.ButtonStyle.secondary)
    async def supplies(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene3_choice(self.guild_id, self.owner_id, "supplies")
        self.stop()
        await self.story_cog.scene_act0_gate(self.guild_id, self.owner_id)

    @discord.ui.button(label="Take both (unarmed only)", style=discord.ButtonStyle.secondary)
    async def both(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        if not self.unarmed:
            await i.response.send_message("You already have a weapon.", ephemeral=True)
            return
        await i.response.defer()
        await story.scene3_choice(self.guild_id, self.owner_id, "both")
        self.stop()
        await self.story_cog.scene_act0_gate(self.guild_id, self.owner_id)


class Scene4View(View):
    """Act 0 Scene 4 — The Gate / Mori"""
    def __init__(self, guild_id, owner_id, story_cog):
        super().__init__(timeout=300)
        self.guild_id  = guild_id
        self.owner_id  = owner_id
        self.story_cog = story_cog

    @discord.ui.button(label="Carry him out", style=discord.ButtonStyle.secondary)
    async def carry(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene4_choice(self.guild_id, self.owner_id, "carry")
        self.stop()
        await self.story_cog.scene_act0_father(self.guild_id, self.owner_id)

    @discord.ui.button(label="Give him your weapon", style=discord.ButtonStyle.secondary)
    async def give(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene4_choice(self.guild_id, self.owner_id, "give_weapon")
        self.stop()
        await self.story_cog.scene_act0_father(self.guild_id, self.owner_id)

    @discord.ui.button(label="Leave him", style=discord.ButtonStyle.danger)
    async def leave(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene4_choice(self.guild_id, self.owner_id, "leave")
        self.stop()
        await self.story_cog.scene_act0_father(self.guild_id, self.owner_id)


class Scene6View(View):
    """Act 0 Scene 6 — Forest Edge"""
    def __init__(self, guild_id, owner_id, story_cog):
        super().__init__(timeout=300)
        self.guild_id  = guild_id
        self.owner_id  = owner_id
        self.story_cog = story_cog

    @discord.ui.button(label="Look back at the fire", style=discord.ButtonStyle.secondary)
    async def look(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene6_choice(self.guild_id, self.owner_id, "look_back")
        self.stop()
        await self.story_cog.scene_act0_complete(self.guild_id, self.owner_id)

    @discord.ui.button(label="Keep walking into the dark", style=discord.ButtonStyle.secondary)
    async def walk(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.scene6_choice(self.guild_id, self.owner_id, "keep_walking")
        self.stop()
        await self.story_cog.scene_act0_complete(self.guild_id, self.owner_id)


class PathChoiceView(View):
    """Act 1/2 boundary — permanent path choice"""
    def __init__(self, guild_id, owner_id, story_cog):
        super().__init__(timeout=600)
        self.guild_id  = guild_id
        self.owner_id  = owner_id
        self.story_cog = story_cog

    @discord.ui.button(label="Report to Iso. Finish what your father started.", style=discord.ButtonStyle.secondary)
    async def blade(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.apply_path_choice(self.guild_id, self.owner_id, "blade")
        self.stop()
        from utils.satsuma_ai import spawn_act_units
        await spawn_act_units(self.guild_id, self.owner_id, 2)
        embed = discord.Embed(
            title="Path of the Blade",
            description=(
                "*You pick up your gear.*\n\n"
                "You are of the Shimazu clan. You are on the right side. "
                "The officer waits. You follow him toward Naha.\n\n"
                "**Faction: Satsuma**\n"
                "**Companion has departed.**\n"
                "**Ryukyuan resistance is now hostile.**\n\n"
                "Act 2 — Allegiance begins."
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Path of the Blade  |  Act 2 begins")
        await self.story_cog._post_to_commands(self.guild_id, self.owner_id, embed)

    @discord.ui.button(label="Don't go. You're not going.", style=discord.ButtonStyle.secondary)
    async def ghost(self, i: discord.Interaction, b: Button):
        if not await _guard(self.owner_id)(i): return
        await i.response.defer()
        await story.apply_path_choice(self.guild_id, self.owner_id, "ghost")
        self.stop()
        from utils.satsuma_ai import spawn_act_units
        await spawn_act_units(self.guild_id, self.owner_id, 2)
        embed = discord.Embed(
            title="Path of the Ghost",
            description=(
                "*You sit back down by the coals.*\n\n"
                "The officer waits a long time. Then he leaves. "
                "The companion's face does not change.\n\n"
                "**Faction: Ryukyuan Resistance**\n"
                "**Companion trust: Bound.**\n"
                "**Satsuma forces are now hostile. Deserter flag active.**\n\n"
                "Act 2 — Allegiance begins."
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Path of the Ghost  |  Act 2 begins")
        await self.story_cog._post_to_commands(self.guild_id, self.owner_id, embed)


class EpilogueView(View):
    """Paginated epilogue delivery"""
    def __init__(self, guild_id, owner_id, segments: list):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.owner_id = owner_id
        self.segments = segments
        self.index    = 0
        self._sync_buttons()

    def _sync_buttons(self):
        self.prev_btn.disabled = self.index == 0
        self.next_btn.disabled = self.index >= len(self.segments) - 1

    def _embed(self) -> discord.Embed:
        seg   = self.segments[self.index]
        embed = discord.Embed(title=seg["title"], description=seg["text"], color=COLOR_STORY)
        embed.set_footer(text=f"Epilogue  |  {self.index+1}/{len(self.segments)}")
        return embed

    @discord.ui.button(label="Back",     style=discord.ButtonStyle.secondary, custom_id="ep_prev")
    async def prev_btn(self, i: discord.Interaction, b: Button):
        self.index = max(0, self.index - 1)
        self._sync_buttons()
        await i.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.secondary, custom_id="ep_next")
    async def next_btn(self, i: discord.Interaction, b: Button):
        self.index = min(len(self.segments)-1, self.index+1)
        self._sync_buttons()
        await i.response.edit_message(embed=self._embed(), view=self)
